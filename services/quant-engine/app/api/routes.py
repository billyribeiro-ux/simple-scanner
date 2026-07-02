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
    CalibrationDriftRequest,
    CounterfactualComparisonRequest,
    ExportRequest,
    FMPBarsIngestRequest,
    FMPIncrementalIntradayRequest,
    FMPQuoteIngestRequest,
    IngestRequest,
    ModelComparisonRequest,
    ModelReviewRequest,
    ProposalActivationRequest,
    ProposalDecisionRequest,
    ProviderCapabilityCheckRequest,
    ProviderExportRequest,
    ReplayBacktestRequest,
    ReplayWindowRunRequest,
    ReplayWindowSetRequest,
    ResearchCycleRequest,
    ResearchCycleRunRequest,
    ScannerStartRequest,
    SchedulerJobRequest,
    SchedulerRunPendingRequest,
    ScoreCandidatesRequest,
    SensitivityRequest,
    TrainRequest,
)
from app.services.fmp_pipeline import FMPLiveDataService
from app.services.research import ModelProposalService, ResearchCycleService, ResearchStatusService
from app.services.scheduler import SchedulerService
from app.services.workflows import (
    BacktestService,
    CalibrationAuditService,
    CalibrationDriftService,
    DailyReviewService,
    DataIngestionService,
    DataQualityService,
    ExportWorkflowService,
    FeatureBuildService,
    LabelBuildService,
    ModelActivationService,
    ModelComparisonService,
    ModelReviewReportService,
    ModelTrainingService,
    ReplayAwareScoringService,
    ReplayWindowOrchestrationService,
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
async def provider_capabilities() -> dict[str, object]:
    repository = repos()
    return {
        "provider": "fmp",
        "configured_capabilities": FMPMarketDataProvider().capability_matrix(),
        "latest_capabilities": repository.provider_capabilities.latest_matrix(provider="fmp"),
        "key_status": FMPLiveDataService(repository).key_status(),
    }


@router.post("/provider/capabilities/check")
async def provider_capabilities_check(request: ProviderCapabilityCheckRequest | None = None) -> dict[str, object]:
    request = request or ProviderCapabilityCheckRequest()
    return await FMPLiveDataService(repos()).capability_check(
        endpoint_keys=request.endpoint_keys,
        symbols=request.symbols,
        include_websocket=request.include_websocket,
    )


@router.get("/provider/capabilities/history")
async def provider_capabilities_history(
    endpoint_key: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> dict[str, object]:
    return {
        "provider": "fmp",
        "capabilities": repos().provider_capabilities.list(
            provider="fmp",
            endpoint_key=endpoint_key,
            limit=limit,
            offset=offset,
        ),
        "limit": limit,
        "offset": offset,
    }


@router.post("/provider/fmp/smoke")
async def provider_fmp_smoke() -> dict[str, object]:
    return await FMPLiveDataService(repos()).smoke()


@router.get("/operations/provider-status")
async def operations_provider_status() -> dict[str, object]:
    return FMPLiveDataService(repos()).provider_status()


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


@router.post("/data/ingest/fmp/quotes")
async def ingest_fmp_quotes(request: FMPQuoteIngestRequest | None = None) -> dict[str, object]:
    request = request or FMPQuoteIngestRequest()
    return await FMPLiveDataService(repos()).ingest_quotes(request.symbols)


@router.post("/data/ingest/fmp/eod")
async def ingest_fmp_eod(request: FMPBarsIngestRequest) -> dict[str, object]:
    return await FMPLiveDataService(repos()).ingest_eod(request.symbols, request.start, request.end)


@router.post("/data/ingest/fmp/intraday")
async def ingest_fmp_intraday(request: FMPBarsIngestRequest) -> dict[str, object]:
    return await FMPLiveDataService(repos()).ingest_intraday(request.symbols, request.intervals, request.start, request.end)


@router.post("/data/ingest/fmp/incremental-intraday")
async def ingest_fmp_incremental_intraday(request: FMPIncrementalIntradayRequest | None = None) -> dict[str, object]:
    request = request or FMPIncrementalIntradayRequest()
    return await FMPLiveDataService(repos()).incremental_intraday(request.symbols, request.intervals, request.end)


@router.get("/data/ingestion-runs")
async def data_ingestion_runs(limit: int = 100, offset: int = 0) -> dict[str, object]:
    return FMPLiveDataService(repos()).list_ingestion_runs(limit=limit, offset=offset)


@router.get("/data/ingestion-runs/{ingestion_run_id}")
async def data_ingestion_run(ingestion_run_id: str) -> dict[str, object]:
    return FMPLiveDataService(repos()).get_ingestion_run(ingestion_run_id)


@router.get("/data/bars")
async def data_bars() -> list[dict[str, object]]:
    return [bar.model_dump(mode="json") for bar in repos().bars.list_all()]


@router.get("/data/quality-report")
async def data_quality_report(
    symbols: str | None = None,
    intervals: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    session: str = "rth",
) -> dict[str, object]:
    return DataQualityService(repos()).report(
        symbols=[item.strip() for item in symbols.split(",") if item.strip()] if symbols else None,
        intervals=[item.strip() for item in intervals.split(",") if item.strip()] if intervals else None,
        start=start,
        end=end,
        session=session,
    )


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


@router.post("/models/{model_version}/calibration-drift")
async def create_calibration_drift(
    model_version: str,
    request: CalibrationDriftRequest | None = None,
) -> dict[str, object]:
    payload = request.model_dump(mode="json") if request else {}
    return CalibrationDriftService(repos()).create(model_version, payload)


@router.get("/models/{model_version}/calibration-drift")
async def list_calibration_drift(model_version: str, limit: int = 100, offset: int = 0) -> dict[str, object]:
    return CalibrationDriftService(repos()).list(model_version, limit=limit, offset=offset)


@router.get("/models/calibration-drift/{drift_report_id}")
async def get_calibration_drift(drift_report_id: str) -> dict[str, object]:
    return CalibrationDriftService(repos()).get(drift_report_id)


@router.get("/models/calibration-drift/{drift_report_id}/windows")
async def get_calibration_drift_windows(
    drift_report_id: str,
    limit: int = 500,
    offset: int = 0,
) -> dict[str, object]:
    return CalibrationDriftService(repos()).windows(drift_report_id, limit=limit, offset=offset)


@router.post("/models/compare")
async def compare_models(request: ModelComparisonRequest) -> dict[str, object]:
    return ModelComparisonService(repos()).compare(request.model_dump(mode="json"))


@router.post("/models/{model_version}/review-report")
async def create_model_review_report(
    model_version: str,
    request: ModelReviewRequest | None = None,
) -> dict[str, object]:
    payload = request.model_dump(mode="json") if request else {}
    return ModelReviewReportService(repos()).create(model_version, payload)


@router.get("/models/{model_version}/review-reports")
async def list_model_review_reports(model_version: str, limit: int = 100, offset: int = 0) -> dict[str, object]:
    return ModelReviewReportService(repos()).list(model_version, limit=limit, offset=offset)


@router.get("/models/review-reports/{review_report_id}")
async def get_model_review_report(review_report_id: str) -> dict[str, object]:
    return ModelReviewReportService(repos()).get(review_report_id)


@router.get("/models/{model_version}")
async def model(model_version: str) -> dict[str, object]:
    return repos().model_runs.get(model_version) or ModelEngine().load(model_version)


@router.post("/backtest/run")
async def run_backtest(request: BacktestRequest) -> dict[str, object]:
    return BacktestService(repos()).run(request.symbols, request.start, request.end, request.model_version)


@router.post("/backtest/replay")
async def run_replay_backtest(request: ReplayBacktestRequest) -> dict[str, object]:
    return BacktestService(repos()).run_replay(request.model_dump(mode="json"))


@router.post("/orchestration/replay-window-sets")
async def create_replay_window_set(request: ReplayWindowSetRequest) -> dict[str, object]:
    return ReplayWindowOrchestrationService(repos()).create(request.model_dump(mode="json"))


@router.get("/orchestration/replay-window-sets")
async def list_replay_window_sets(limit: int = 100, offset: int = 0) -> dict[str, object]:
    return ReplayWindowOrchestrationService(repos()).list(limit=limit, offset=offset)


@router.get("/orchestration/replay-window-sets/{window_set_id}")
async def get_replay_window_set(window_set_id: str) -> dict[str, object]:
    return ReplayWindowOrchestrationService(repos()).get(window_set_id)


@router.get("/orchestration/replay-window-sets/{window_set_id}/results")
async def get_replay_window_set_results(window_set_id: str, limit: int = 500, offset: int = 0) -> dict[str, object]:
    return ReplayWindowOrchestrationService(repos()).results(window_set_id, limit=limit, offset=offset)


@router.post("/orchestration/replay-window-sets/{window_set_id}/run")
async def run_replay_window_set(
    window_set_id: str,
    request: ReplayWindowRunRequest | None = None,
) -> dict[str, object]:
    payload = request.model_dump(mode="json") if request else {}
    return ReplayWindowOrchestrationService(repos()).run(window_set_id, payload)


@router.post("/orchestration/replay-window-sets/{window_set_id}/export")
async def export_replay_window_set(window_set_id: str) -> dict[str, object]:
    return ReplayWindowOrchestrationService(repos()).export(window_set_id)


@router.get("/pipeline/status")
async def pipeline_status() -> dict[str, object]:
    return BacktestService(repos()).pipeline_status()


@router.post("/research/cycles")
async def create_research_cycle(request: ResearchCycleRequest) -> dict[str, object]:
    return ResearchCycleService(repos()).create(request.model_dump(mode="json"))


@router.get("/research/cycles")
async def list_research_cycles(limit: int = 100, offset: int = 0, status: str | None = None) -> dict[str, object]:
    return ResearchCycleService(repos()).list(limit=limit, offset=offset, status=status)


@router.get("/research/cycles/{research_cycle_id}")
async def get_research_cycle(research_cycle_id: str) -> dict[str, object]:
    return ResearchCycleService(repos()).get(research_cycle_id)


@router.post("/research/cycles/{research_cycle_id}/run")
async def run_research_cycle(
    research_cycle_id: str,
    request: ResearchCycleRunRequest | None = None,
) -> dict[str, object]:
    payload = {key: value for key, value in request.model_dump(mode="json").items() if value is not None} if request else {}
    return ResearchCycleService(repos()).run(research_cycle_id, payload)


@router.post("/research/cycles/{research_cycle_id}/dry-run")
async def dry_run_research_cycle(research_cycle_id: str) -> dict[str, object]:
    return ResearchCycleService(repos()).dry_run(research_cycle_id)


@router.get("/research/cycles/{research_cycle_id}/artifacts")
async def research_cycle_artifacts(
    research_cycle_id: str,
    limit: int = 500,
    offset: int = 0,
) -> dict[str, object]:
    return ResearchCycleService(repos()).artifacts(research_cycle_id, limit=limit, offset=offset)


@router.post("/research/cycles/{research_cycle_id}/export")
async def export_research_cycle_report(research_cycle_id: str) -> dict[str, object]:
    return ResearchCycleService(repos()).export(research_cycle_id)


@router.get("/research/model-proposals")
async def list_model_proposals(limit: int = 100, offset: int = 0, status: str | None = None) -> dict[str, object]:
    return ModelProposalService(repos()).list(limit=limit, offset=offset, status=status)


@router.get("/research/model-proposals/{proposal_id}")
async def get_model_proposal(proposal_id: str) -> dict[str, object]:
    return ModelProposalService(repos()).get(proposal_id)


@router.post("/research/model-proposals/{proposal_id}/approve")
async def approve_model_proposal(
    proposal_id: str,
    request: ProposalDecisionRequest | None = None,
) -> dict[str, object]:
    return ModelProposalService(repos()).approve(proposal_id, actor=request.actor if request else None)


@router.post("/research/model-proposals/{proposal_id}/reject")
async def reject_model_proposal(
    proposal_id: str,
    request: ProposalDecisionRequest | None = None,
) -> dict[str, object]:
    return ModelProposalService(repos()).reject(
        proposal_id,
        actor=request.actor if request else None,
        reason_codes=request.reason_codes if request else None,
    )


@router.post("/research/model-proposals/{proposal_id}/activate")
async def activate_model_proposal(
    proposal_id: str,
    request: ProposalActivationRequest,
) -> dict[str, object]:
    return ModelProposalService(repos()).activate(
        proposal_id,
        actor=request.actor,
        confirm_manual_activation=request.confirm_manual_activation,
        validation_mode=request.validation_mode,
        calibration_audit_required=request.calibration_audit_required,
    )


@router.get("/research/decision-ledger")
async def decision_ledger(
    model_version: str | None = None,
    proposal_id: str | None = None,
    research_cycle_id: str | None = None,
    decision_type: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, object]:
    return {
        "decisions": repos().model_decision_ledger.list(
            model_version=model_version,
            proposal_id=proposal_id,
            research_cycle_id=research_cycle_id,
            decision_type=decision_type,
            start=start,
            end=end,
            limit=limit,
            offset=offset,
        ),
        "limit": limit,
        "offset": offset,
    }


@router.get("/operations/research-status")
async def operations_research_status() -> dict[str, object]:
    return ResearchStatusService(repos()).status()


@router.post("/scheduler/jobs")
async def create_scheduler_job(request: SchedulerJobRequest) -> dict[str, object]:
    return SchedulerService(repos()).create_job(request.model_dump(mode="json"))


@router.get("/scheduler/jobs")
async def list_scheduler_jobs(
    limit: int = 100,
    offset: int = 0,
    status: str | None = None,
    job_type: str | None = None,
) -> dict[str, object]:
    return SchedulerService(repos()).list_jobs(status=status, job_type=job_type, limit=limit, offset=offset)


@router.post("/scheduler/jobs/run-pending")
async def run_pending_scheduler_jobs(request: SchedulerRunPendingRequest | None = None) -> dict[str, object]:
    max_jobs = request.max_jobs if request else 3
    return SchedulerService(repos()).run_pending(max_jobs=max_jobs)


@router.get("/scheduler/jobs/{job_id}")
async def get_scheduler_job(job_id: str) -> dict[str, object]:
    return SchedulerService(repos()).get_job(job_id)


@router.post("/scheduler/jobs/{job_id}/run")
async def run_scheduler_job(job_id: str) -> dict[str, object]:
    return SchedulerService(repos()).run_job(job_id)


@router.post("/scheduler/jobs/{job_id}/cancel")
async def cancel_scheduler_job(job_id: str) -> dict[str, object]:
    return SchedulerService(repos()).cancel(job_id)


@router.get("/scheduler/jobs/{job_id}/events")
async def scheduler_job_events(job_id: str, limit: int = 500, offset: int = 0) -> dict[str, object]:
    return SchedulerService(repos()).events(job_id, limit=limit, offset=offset)


@router.get("/operations/scheduler-status")
async def operations_scheduler_status() -> dict[str, object]:
    return SchedulerService(repos()).status()


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


@router.post("/exports/replay-window-set.xlsx")
async def export_replay_window_set_xlsx(request: ExportRequest) -> dict[str, object]:
    if not request.run_id:
        return {"status": "error", "reason": "run_id_required"}
    return ExportWorkflowService(repos()).export_replay_window_set(request.run_id)


@router.post("/exports/calibration-drift.xlsx")
async def export_calibration_drift_xlsx(request: ExportRequest) -> dict[str, object]:
    if not request.run_id:
        return {"status": "error", "reason": "run_id_required"}
    return ExportWorkflowService(repos()).export_calibration_drift(request.run_id, "xlsx")


@router.post("/exports/calibration-drift.json")
async def export_calibration_drift_json(request: ExportRequest) -> dict[str, object]:
    if not request.run_id:
        return {"status": "error", "reason": "run_id_required"}
    return ExportWorkflowService(repos()).export_calibration_drift(request.run_id, "json")


@router.post("/exports/calibration-drift-windows.csv")
async def export_calibration_drift_windows_csv(request: ExportRequest) -> dict[str, object]:
    if not request.run_id:
        return {"status": "error", "reason": "run_id_required"}
    return ExportWorkflowService(repos()).export_calibration_drift_windows(request.run_id, "csv")


@router.post("/exports/calibration-drift-windows.xlsx")
async def export_calibration_drift_windows_xlsx(request: ExportRequest) -> dict[str, object]:
    if not request.run_id:
        return {"status": "error", "reason": "run_id_required"}
    return ExportWorkflowService(repos()).export_calibration_drift_windows(request.run_id, "xlsx")


@router.post("/exports/model-review.xlsx")
async def export_model_review_xlsx(request: ExportRequest) -> dict[str, object]:
    if not request.run_id:
        return {"status": "error", "reason": "run_id_required"}
    return ExportWorkflowService(repos()).export_model_review(request.run_id, "xlsx")


@router.post("/exports/model-review.json")
async def export_model_review_json(request: ExportRequest) -> dict[str, object]:
    if not request.run_id:
        return {"status": "error", "reason": "run_id_required"}
    return ExportWorkflowService(repos()).export_model_review(request.run_id, "json")


@router.post("/exports/research-cycle.xlsx")
async def export_research_cycle_xlsx(request: ExportRequest) -> dict[str, object]:
    if not request.run_id:
        return {"status": "error", "reason": "run_id_required"}
    return ExportWorkflowService(repos()).export_research_cycle(request.run_id, "xlsx")


@router.post("/exports/research-cycle.json")
async def export_research_cycle_json(request: ExportRequest) -> dict[str, object]:
    if not request.run_id:
        return {"status": "error", "reason": "run_id_required"}
    return ExportWorkflowService(repos()).export_research_cycle(request.run_id, "json")


@router.post("/exports/model-proposal.xlsx")
async def export_model_proposal_xlsx(request: ExportRequest) -> dict[str, object]:
    if not request.run_id:
        return {"status": "error", "reason": "run_id_required"}
    return ExportWorkflowService(repos()).export_model_proposal(request.run_id, "xlsx")


@router.post("/exports/model-proposal.json")
async def export_model_proposal_json(request: ExportRequest) -> dict[str, object]:
    if not request.run_id:
        return {"status": "error", "reason": "run_id_required"}
    return ExportWorkflowService(repos()).export_model_proposal(request.run_id, "json")


@router.post("/exports/champion-challenger-comparison.xlsx")
async def export_champion_challenger_comparison_xlsx(request: ExportRequest) -> dict[str, object]:
    if not request.run_id:
        return {"status": "error", "reason": "run_id_required"}
    return ExportWorkflowService(repos()).export_champion_challenger_comparison(request.run_id)


@router.post("/exports/fmp-capabilities")
async def export_fmp_capabilities(request: ProviderExportRequest | None = None) -> dict[str, object]:
    request = request or ProviderExportRequest()
    return FMPLiveDataService(repos()).export_capabilities(request.kind)


@router.post("/exports/fmp-ingestion-runs")
async def export_fmp_ingestion_runs(request: ProviderExportRequest | None = None) -> dict[str, object]:
    request = request or ProviderExportRequest()
    return FMPLiveDataService(repos()).export_ingestion_runs(request.kind)


@router.post("/exports/fmp-data-coverage")
async def export_fmp_data_coverage(request: ProviderExportRequest | None = None) -> dict[str, object]:
    request = request or ProviderExportRequest()
    return FMPLiveDataService(repos()).export_coverage(request.kind)


@router.post("/exports/fmp-provider-requests")
async def export_fmp_provider_requests(request: ProviderExportRequest | None = None) -> dict[str, object]:
    request = request or ProviderExportRequest(kind="csv")
    return FMPLiveDataService(repos()).export_provider_requests(request.kind)


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
