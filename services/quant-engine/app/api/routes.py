from __future__ import annotations

import json
from datetime import date, datetime

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.data.fmp import FMPMarketDataProvider
from app.data.symbols import normalize_symbols
from app.db.repositories import (
    PersistenceConfigurationError,
    get_repository_registry,
    persistence_backend_info,
)
from app.jobs.scanner import scanner_state
from app.models.engine import ModelEngine
from app.schemas.market import (
    BacktestComparisonRequest,
    BacktestRequest,
    CalibrationAuditRequest,
    CounterfactualComparisonRequest,
    ExportRequest,
    IngestRequest,
    ModelComparisonRequest,
    ReplayBacktestRequest,
    ScannerStartRequest,
    ScoreCandidatesRequest,
    SensitivityRequest,
    TrainRequest,
)
from app.services.workflows import (
    BacktestService,
    CalibrationAuditService,
    DailyReviewService,
    DataIngestionService,
    ExportWorkflowService,
    FeatureBuildService,
    LabelBuildService,
    ModelActivationService,
    ModelComparisonService,
    ModelTrainingService,
    ReplayAwareScoringService,
    ValidationWorkflowService,
)
from app.utils.time import UTC

router = APIRouter()


def repos():
    return get_repository_registry()


def _request_date(request: ExportRequest | None) -> date | None:
    if request is None or request.date is None:
        return None
    return date.fromisoformat(request.date)


@router.get("/health")
async def health() -> dict[str, object]:
    try:
        persistence = repos().info()
        status = "ok" if persistence.get("database_reachable") is not False else "degraded"
    except PersistenceConfigurationError as exc:
        persistence = exc.safe_info
        status = "error"
    return {
        "status": status,
        "time": datetime.now(UTC).isoformat(),
        "persistence": persistence,
    }


@router.get("/config")
async def config() -> dict[str, object]:
    settings = get_settings()
    try:
        persistence = repos().info()
    except PersistenceConfigurationError:
        persistence = persistence_backend_info(settings)
    return {
        "app_name": settings.app_name,
        "default_symbols": settings.symbol_list,
        "timezone": settings.timezone,
        "min_confidence": settings.min_confidence,
        "fmp_api_key_configured": bool(settings.fmp_api_key),
        "persistence": persistence,
    }


@router.get("/symbols")
async def get_symbols() -> list[str]:
    stored = [row["symbol"] for row in repos().symbols.list_all()]
    return stored or get_settings().symbol_list


@router.post("/symbols")
async def post_symbols(symbols: list[str]) -> list[str]:
    normalized = normalize_symbols(symbols)
    repos().symbols.upsert_many(normalized)
    return normalized


@router.get("/provider/capabilities")
async def provider_capabilities() -> list[dict[str, object]]:
    return FMPMarketDataProvider().capability_matrix()


@router.get("/provider/health")
async def provider_health() -> dict[str, object]:
    return await FMPMarketDataProvider().health_check()


@router.post("/data/ingest")
async def ingest(request: IngestRequest) -> dict[str, object]:
    provider = FMPMarketDataProvider()
    result = await DataIngestionService(repos(), provider).ingest(
        request.symbols,
        list(request.intervals),
        request.start,
        request.end,
    )
    return {"status": "ok" if not result["errors"] else "partial", **result}


@router.get("/data/bars")
async def data_bars() -> list[dict[str, object]]:
    return [bar.model_dump(mode="json") for bar in repos().bars.list_all()]


@router.get("/data/quotes/latest")
async def latest_quotes() -> list[dict[str, object]]:
    quotes = await FMPMarketDataProvider().get_batch_quotes(get_settings().symbol_list)
    return [quote.model_dump(mode="json") for quote in quotes]


@router.post("/features/build")
async def build_features() -> dict[str, object]:
    result = FeatureBuildService(repos()).build()
    return {
        "status": "ok",
        "bars_read": result["bars_read"],
        "features": result["features_written"],
        "features_written": result["features_written"],
        "stale_ranges": result["stale_ranges"],
        "build_windows": result["build_windows"],
    }


@router.post("/labels/build")
async def build_labels() -> dict[str, object]:
    result = LabelBuildService(repos()).build()
    return {
        "status": "ok",
        "bars_read": result["bars_read"],
        "features_read": result["features_read"],
        "candidates": result["candidates_written"],
        "candidates_written": result["candidates_written"],
        "labels": result["labels_written"],
        "labels_written": result["labels_written"],
        "stale_ranges": result["stale_ranges"],
        "build_windows": result["build_windows"],
    }


@router.post("/models/train")
async def train_model(request: TrainRequest) -> dict[str, object]:
    repository = repos()
    model = ModelTrainingService(repository).train(
        request.symbols,
        request.training_start,
        request.training_end,
        request.min_samples,
        model_type=request.model_type,
        intervals=request.intervals,
        setup_types=request.setup_types,
        sides=request.sides,
        replay_run_ids=request.replay_run_ids,
        counterfactual_replay_run_ids=request.counterfactual_replay_run_ids,
        portfolio_replay_run_ids=request.portfolio_replay_run_ids,
        replay_filter=request.replay_filter,
        outcome_source=request.outcome_source,
        require_counterfactual=request.require_counterfactual,
        minimum_counterfactual_outcomes=request.minimum_counterfactual_outcomes,
        maximum_portfolio_only_fraction=request.maximum_portfolio_only_fraction,
        overlap_density_filters=request.overlap_density_filters,
        concurrency_bucket_filters=request.concurrency_bucket_filters,
        sensitivity_required=request.sensitivity_required,
        minimum_observed_outcomes=request.minimum_observed_outcomes,
        minimum_cell_sample_size=request.minimum_cell_sample_size,
        shrinkage_strength=request.shrinkage_strength,
        scoring_config=request.scoring_config,
        activation_criteria=request.activation_criteria,
        validation_mode=request.validation_mode,
        allow_stale=request.allow_stale,
    )
    if request.activate_if_passes and model.get("model_version"):
        ValidationWorkflowService(repository).validate(
            model_version=str(model["model_version"]),
            symbols=request.symbols,
            start=request.training_start,
            end=request.training_end,
            validation_mode=request.validation_mode,
            replay_run_id=(request.replay_run_ids or [None])[0],
            replay_filter=request.replay_filter,
            require_sensitivity=request.sensitivity_required,
            allow_stale_replay_validation=request.allow_stale,
        )
        model["activation"] = ModelActivationService(repository).activate(
            str(model["model_version"]),
            validation_mode=request.validation_mode,
        )
    return model


@router.post("/models/validate")
async def validate_model(
    model_version: str | None = None,
    validation_mode: str = "label_derived",
    replay_run_id: str | None = None,
    replay_filter: str | None = None,
    allow_latest_replay_fallback: bool = False,
    sensitivity_run_id: str | None = None,
    require_sensitivity: bool = False,
    minimum_robustness_score: float = 0.0,
    allow_stale_replay_validation: bool = False,
    training_replay_run_ids: str | None = None,
    validation_replay_run_ids: str | None = None,
    test_replay_run_ids: str | None = None,
    counterfactual_training_replay_run_ids: str | None = None,
    portfolio_validation_replay_run_ids: str | None = None,
    train_start: datetime | None = None,
    train_end: datetime | None = None,
    validation_start: datetime | None = None,
    validation_end: datetime | None = None,
    test_start: datetime | None = None,
    test_end: datetime | None = None,
    embargo_minutes: int = 0,
    require_counterfactual_training: bool = False,
    require_portfolio_validation: bool = False,
    calibration_audit_required: bool = False,
    calibration_audit_id: str | None = None,
) -> dict[str, object]:
    parsed_filter = json.loads(replay_filter) if replay_filter else None
    def parsed_ids(value: str | None) -> list[str] | None:
        if not value:
            return None
        if value.strip().startswith("["):
            return [str(item) for item in json.loads(value)]
        return [item.strip() for item in value.split(",") if item.strip()]

    return ValidationWorkflowService(repos()).validate(
        model_version=model_version,
        validation_mode=validation_mode,
        replay_run_id=replay_run_id,
        replay_filter=parsed_filter,
        allow_latest_replay_fallback=allow_latest_replay_fallback,
        sensitivity_run_id=sensitivity_run_id,
        require_sensitivity=require_sensitivity,
        minimum_robustness_score=minimum_robustness_score,
        allow_stale_replay_validation=allow_stale_replay_validation,
        training_replay_run_ids=parsed_ids(training_replay_run_ids),
        validation_replay_run_ids=parsed_ids(validation_replay_run_ids),
        test_replay_run_ids=parsed_ids(test_replay_run_ids),
        counterfactual_training_replay_run_ids=parsed_ids(counterfactual_training_replay_run_ids),
        portfolio_validation_replay_run_ids=parsed_ids(portfolio_validation_replay_run_ids),
        train_start=train_start,
        train_end=train_end,
        validation_start=validation_start,
        validation_end=validation_end,
        test_start=test_start,
        test_end=test_end,
        embargo_minutes=embargo_minutes,
        require_counterfactual_training=require_counterfactual_training,
        require_portfolio_validation=require_portfolio_validation,
        calibration_audit_required=calibration_audit_required,
        calibration_audit_id=calibration_audit_id,
    )


@router.post("/models/activate")
async def activate_model(
    model_version: str,
    validation_mode: str = "label_derived",
    calibration_audit_required: bool = False,
    calibration_audit_id: str | None = None,
    require_monotonic_score_bins: bool = False,
    require_take_outperforms_watch: bool = False,
    minimum_high_grade_samples: int | None = None,
    minimum_rank_correlation_score: float | None = None,
    max_allowed_calibration_warnings: int | None = None,
) -> dict[str, object]:
    return ModelActivationService(repos()).activate(
        model_version,
        validation_mode=validation_mode,
        calibration_audit_required=calibration_audit_required,
        calibration_audit_id=calibration_audit_id,
        require_monotonic_score_bins=require_monotonic_score_bins,
        require_take_outperforms_watch=require_take_outperforms_watch,
        minimum_high_grade_samples=minimum_high_grade_samples,
        minimum_rank_correlation_score=minimum_rank_correlation_score,
        max_allowed_calibration_warnings=max_allowed_calibration_warnings,
    )


@router.get("/models")
async def models() -> list[dict[str, object]]:
    repository_models = repos().model_runs.list_all()
    artifact_models = ModelEngine().list_models()
    versions = {str(model.get("model_version")) for model in repository_models}
    return repository_models + [model for model in artifact_models if str(model.get("model_version")) not in versions]


@router.get("/models/{model_version}/evidence")
async def model_evidence(model_version: str, limit: int = 500, offset: int = 0) -> dict[str, object]:
    return ReplayAwareScoringService(repos()).evidence(model_version, limit=limit, offset=offset)


@router.post("/models/{model_version}/score-candidates")
async def score_model_candidates(model_version: str, request: ScoreCandidatesRequest | None = None) -> dict[str, object]:
    request = request or ScoreCandidatesRequest()
    return ReplayAwareScoringService(repos()).score_candidates(
        model_version,
        candidate_ids=request.candidate_ids,
        candidates=request.candidates,
        persist_audit=request.persist_audit,
    )


@router.get("/models/{model_version}/score-audits")
async def model_score_audits(
    model_version: str,
    limit: int = 500,
    offset: int = 0,
    symbol: str | None = None,
) -> dict[str, object]:
    return ReplayAwareScoringService(repos()).score_audits(model_version, limit=limit, offset=offset, symbol=symbol)


@router.post("/models/{model_version}/calibration-audit")
async def create_calibration_audit(
    model_version: str,
    request: CalibrationAuditRequest | None = None,
) -> dict[str, object]:
    payload = request.model_dump(mode="json") if request else {}
    return CalibrationAuditService(repos()).create(model_version, payload)


@router.get("/models/{model_version}/calibration-audits")
async def list_calibration_audits(model_version: str, limit: int = 100, offset: int = 0) -> dict[str, object]:
    return CalibrationAuditService(repos()).list(model_version, limit=limit, offset=offset)


@router.get("/models/calibration-audits/{calibration_audit_id}")
async def get_calibration_audit(calibration_audit_id: str) -> dict[str, object]:
    return CalibrationAuditService(repos()).get(calibration_audit_id)


@router.get("/models/calibration-audits/{calibration_audit_id}/bins")
async def get_calibration_audit_bins(
    calibration_audit_id: str,
    limit: int = 500,
    offset: int = 0,
    bin_type: str | None = None,
) -> dict[str, object]:
    return CalibrationAuditService(repos()).bins(calibration_audit_id, limit=limit, offset=offset, bin_type=bin_type)


@router.post("/models/compare")
async def compare_models(request: ModelComparisonRequest) -> dict[str, object]:
    return ModelComparisonService(repos()).compare(request.model_dump(mode="json"))


@router.get("/models/{model_version}")
async def model(model_version: str) -> dict[str, object]:
    return repos().model_runs.get(model_version) or ModelEngine().load(model_version)


@router.post("/backtest/run")
async def run_backtest(request: BacktestRequest) -> dict[str, object]:
    return BacktestService(repos()).run(request.symbols, request.start, request.end, request.model_version)


@router.post("/backtest/replay")
async def run_replay_backtest(request: ReplayBacktestRequest) -> dict[str, object]:
    return BacktestService(repos()).run_replay(request.model_dump(mode="json"))


@router.get("/pipeline/status")
async def pipeline_status() -> dict[str, object]:
    return BacktestService(repos()).pipeline_status()


@router.post("/backtest/replay/{replay_run_id}/sensitivity")
async def run_replay_sensitivity(
    replay_run_id: str,
    request: SensitivityRequest | None = None,
) -> dict[str, object]:
    payload = request.model_dump(mode="json") if request else {}
    return BacktestService(repos()).run_sensitivity(replay_run_id, payload)


@router.get("/backtest/replay/sensitivity/{sensitivity_run_id}")
async def replay_sensitivity(sensitivity_run_id: str) -> dict[str, object]:
    sensitivity = BacktestService(repos()).get_sensitivity(sensitivity_run_id)
    return sensitivity or {"sensitivity_run_id": sensitivity_run_id, "status": "not_found"}


@router.get("/backtest/replay/sensitivity/{sensitivity_run_id}/scenarios")
async def replay_sensitivity_scenarios(sensitivity_run_id: str) -> dict[str, object]:
    return {
        "sensitivity_run_id": sensitivity_run_id,
        "scenarios": BacktestService(repos()).sensitivity_scenarios(sensitivity_run_id),
    }


@router.get("/backtest/replay/{replay_run_id}/sensitivity")
async def replay_sensitivity_for_run(replay_run_id: str) -> dict[str, object]:
    return {"replay_run_id": replay_run_id, "sensitivity_runs": BacktestService(repos()).list_sensitivity(replay_run_id)}


@router.post("/backtest/compare-label-vs-replay")
async def compare_label_vs_replay(request: BacktestComparisonRequest) -> dict[str, object]:
    return BacktestService(repos()).compare_label_vs_replay(request.model_dump(mode="json"))


@router.post("/backtest/compare-counterfactual-vs-portfolio")
async def compare_counterfactual_vs_portfolio(request: CounterfactualComparisonRequest) -> dict[str, object]:
    return BacktestService(repos()).compare_counterfactual_vs_portfolio(request.model_dump(mode="json"))


@router.get("/backtest/counterfactual-comparisons/{comparison_id}")
async def counterfactual_comparison(comparison_id: str) -> dict[str, object]:
    comparison = BacktestService(repos()).get_comparison(comparison_id)
    return comparison or {"comparison_id": comparison_id, "status": "not_found"}


@router.get("/backtest/comparisons/{comparison_id}")
async def backtest_comparison(comparison_id: str) -> dict[str, object]:
    comparison = BacktestService(repos()).get_comparison(comparison_id)
    return comparison or {"comparison_id": comparison_id, "status": "not_found"}


@router.get("/backtest/replay/{replay_run_id}")
async def replay_backtest(replay_run_id: str) -> dict[str, object]:
    replay = BacktestService(repos()).get_replay(replay_run_id)
    return replay or {"replay_run_id": replay_run_id, "status": "not_found"}


@router.get("/backtest/replay/{replay_run_id}/trades")
async def replay_backtest_trades(
    replay_run_id: str,
    limit: int = 500,
    offset: int = 0,
    status: str | None = None,
) -> dict[str, object]:
    trades = BacktestService(repos()).replay_trades(replay_run_id, limit=limit, offset=offset, status=status)
    return {"replay_run_id": replay_run_id, "limit": limit, "offset": offset, "trades": trades}


@router.get("/backtest/runs")
async def backtest_runs() -> list[dict[str, object]]:
    return BacktestService(repos()).list_runs()


@router.get("/backtest/runs/{run_id}")
async def backtest_run(run_id: str) -> dict[str, object]:
    run = BacktestService(repos()).get_run(run_id)
    if run is not None:
        return run
    return {"run_id": run_id, "status": "not_found"}


@router.post("/scanner/start")
async def scanner_start(request: ScannerStartRequest | None = None) -> dict[str, object]:
    request = request or ScannerStartRequest()
    await scanner_state.start(request.symbols, request.confidence_threshold)
    return scanner_state.status()


@router.post("/scanner/stop")
async def scanner_stop() -> dict[str, object]:
    await scanner_state.stop()
    return scanner_state.status()


@router.get("/scanner/status")
async def scanner_status() -> dict[str, object]:
    status = scanner_state.status()
    status["latest_persisted_run"] = repos().scanner_runs.latest()
    return status


@router.get("/signals/live")
async def signals_live() -> list[dict[str, object]]:
    return [signal.model_dump(mode="json") for signal in repos().live_signals.list_latest()]


@router.get("/signals/history")
async def signals_history() -> list[dict[str, object]]:
    return [signal.model_dump(mode="json") for signal in repos().live_signals.history()]


@router.get("/signals/stream")
async def signals_stream() -> StreamingResponse:
    async def events():
        async for signal in scanner_state.stream():
            yield f"data: {json.dumps(signal.model_dump(mode='json'))}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@router.post("/exports/signals.csv")
async def export_signals_csv(request: ExportRequest | None = None) -> dict[str, object]:
    result = ExportWorkflowService(repos()).export_signals("csv", _request_date(request), request.run_id if request else None)
    return {"status": "ok", **result}


@router.post("/exports/signals.xlsx")
async def export_signals_xlsx(request: ExportRequest | None = None) -> dict[str, object]:
    result = ExportWorkflowService(repos()).export_signals("xlsx", _request_date(request), request.run_id if request else None)
    return {"status": "ok", **result}


@router.post("/exports/backtest.xlsx")
async def export_backtest_xlsx(request: ExportRequest | None = None) -> dict[str, object]:
    result = ExportWorkflowService(repos()).export_signals("xlsx", _request_date(request), request.run_id if request else None)
    return {"status": "ok", "note": "V1 workbook scaffold", **result}


@router.post("/exports/daily-review.xlsx")
async def export_daily_review_xlsx(request: ExportRequest | None = None) -> dict[str, object]:
    payload = DailyReviewService(repos()).build(_request_date(request))["payload"]
    result = ExportWorkflowService(repos()).export_daily_review(payload, _request_date(request))
    return {"status": "ok", **result}


@router.post("/exports/replay-summary.xlsx")
async def export_replay_summary_xlsx(request: ExportRequest) -> dict[str, object]:
    if not request.run_id:
        return {"status": "error", "reason": "run_id_required"}
    return ExportWorkflowService(repos()).export_replay_summary(request.run_id)


@router.post("/exports/replay-trades.csv")
async def export_replay_trades_csv(request: ExportRequest) -> dict[str, object]:
    if not request.run_id:
        return {"status": "error", "reason": "run_id_required"}
    return ExportWorkflowService(repos()).export_replay_trades(request.run_id, "csv")


@router.post("/exports/replay-trades.xlsx")
async def export_replay_trades_xlsx(request: ExportRequest) -> dict[str, object]:
    if not request.run_id:
        return {"status": "error", "reason": "run_id_required"}
    return ExportWorkflowService(repos()).export_replay_trades(request.run_id, "xlsx")


@router.post("/exports/sensitivity-summary.xlsx")
async def export_sensitivity_summary_xlsx(request: ExportRequest) -> dict[str, object]:
    if not request.run_id:
        return {"status": "error", "reason": "run_id_required"}
    return ExportWorkflowService(repos()).export_sensitivity_summary(request.run_id)


@router.post("/exports/sensitivity-scenarios.csv")
async def export_sensitivity_scenarios_csv(request: ExportRequest) -> dict[str, object]:
    if not request.run_id:
        return {"status": "error", "reason": "run_id_required"}
    return ExportWorkflowService(repos()).export_sensitivity_scenarios(request.run_id, "csv")


@router.post("/exports/sensitivity-scenarios.xlsx")
async def export_sensitivity_scenarios_xlsx(request: ExportRequest) -> dict[str, object]:
    if not request.run_id:
        return {"status": "error", "reason": "run_id_required"}
    return ExportWorkflowService(repos()).export_sensitivity_scenarios(request.run_id, "xlsx")


@router.post("/exports/sensitivity-metrics.json")
async def export_sensitivity_metrics_json(request: ExportRequest) -> dict[str, object]:
    if not request.run_id:
        return {"status": "error", "reason": "run_id_required"}
    return ExportWorkflowService(repos()).export_sensitivity_metrics(request.run_id)


@router.post("/exports/replay-aware-model-summary.xlsx")
async def export_replay_aware_model_summary_xlsx(request: ExportRequest) -> dict[str, object]:
    if not request.run_id:
        return {"status": "error", "reason": "run_id_required"}
    return ExportWorkflowService(repos()).export_replay_aware_model_summary(request.run_id)


@router.post("/exports/evidence-cells.csv")
async def export_evidence_cells_csv(request: ExportRequest) -> dict[str, object]:
    if not request.run_id:
        return {"status": "error", "reason": "run_id_required"}
    return ExportWorkflowService(repos()).export_evidence_cells(request.run_id, "csv")


@router.post("/exports/evidence-cells.xlsx")
async def export_evidence_cells_xlsx(request: ExportRequest) -> dict[str, object]:
    if not request.run_id:
        return {"status": "error", "reason": "run_id_required"}
    return ExportWorkflowService(repos()).export_evidence_cells(request.run_id, "xlsx")


@router.post("/exports/score-audits.csv")
async def export_score_audits_csv(request: ExportRequest) -> dict[str, object]:
    if not request.run_id:
        return {"status": "error", "reason": "run_id_required"}
    return ExportWorkflowService(repos()).export_score_audits(request.run_id, "csv")


@router.post("/exports/score-audits.xlsx")
async def export_score_audits_xlsx(request: ExportRequest) -> dict[str, object]:
    if not request.run_id:
        return {"status": "error", "reason": "run_id_required"}
    return ExportWorkflowService(repos()).export_score_audits(request.run_id, "xlsx")


@router.post("/exports/replay-aware-validation.xlsx")
async def export_replay_aware_validation_xlsx(request: ExportRequest) -> dict[str, object]:
    return ExportWorkflowService(repos()).export_replay_aware_validation(request.run_id)


@router.post("/exports/calibration-audit.xlsx")
async def export_calibration_audit_xlsx(request: ExportRequest) -> dict[str, object]:
    if not request.run_id:
        return {"status": "error", "reason": "run_id_required"}
    return ExportWorkflowService(repos()).export_calibration_audit(request.run_id)


@router.post("/exports/calibration-bins.csv")
async def export_calibration_bins_csv(request: ExportRequest) -> dict[str, object]:
    if not request.run_id:
        return {"status": "error", "reason": "run_id_required"}
    return ExportWorkflowService(repos()).export_calibration_bins(request.run_id, "csv")


@router.post("/exports/calibration-bins.xlsx")
async def export_calibration_bins_xlsx(request: ExportRequest) -> dict[str, object]:
    if not request.run_id:
        return {"status": "error", "reason": "run_id_required"}
    return ExportWorkflowService(repos()).export_calibration_bins(request.run_id, "xlsx")


@router.post("/exports/calibration-metrics.json")
async def export_calibration_metrics_json(request: ExportRequest) -> dict[str, object]:
    if not request.run_id:
        return {"status": "error", "reason": "run_id_required"}
    return ExportWorkflowService(repos()).export_calibration_metrics(request.run_id)


@router.post("/exports/model-comparison.xlsx")
async def export_model_comparison_xlsx(request: ExportRequest) -> dict[str, object]:
    if not request.run_id:
        return {"status": "error", "reason": "run_id_required"}
    return ExportWorkflowService(repos()).export_model_comparison(request.run_id)


@router.get("/exports/{export_id}")
async def export_status(export_id: str) -> dict[str, object]:
    for export in repos().exports.list_all():
        if export.get("export_id") == export_id:
            return export | {"status": "local-file"}
    return {"export_id": export_id, "status": "not_found"}


@router.post("/review/daily")
async def daily_review() -> dict[str, object]:
    saved = DailyReviewService(repos()).build()
    payload = saved["payload"]
    signals = repos().live_signals.list_latest(limit=1000)
    return {
        "review_id": saved["review_id"],
        "date": payload["date"],
        "signals_fired": len([signal for signal in signals if signal.side.value != "NO_TRADE"]),
        "signals_skipped": len([signal for signal in signals if signal.side.value == "NO_TRADE"]),
        "missed_moves": payload["missed_moves"],
        "false_positives": payload["false_positives"],
        "false_negatives": payload["false_negatives"],
        "ticker_notes": payload["ticker_notes"],
        "regime_notes": payload["regime_notes"],
        "recommendations": payload["recommendations"],
    }


@router.get("/review/daily/{review_date}")
async def get_daily_review(review_date: str) -> dict[str, object]:
    saved = repos().daily_reviews.get(date.fromisoformat(review_date))
    if saved is None:
        return {"date": review_date, "status": "not_found"}
    return saved | {"status": "local-file"}
