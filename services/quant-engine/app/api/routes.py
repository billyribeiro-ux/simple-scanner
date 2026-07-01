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
    BacktestRequest,
    ExportRequest,
    IngestRequest,
    ScannerStartRequest,
    TrainRequest,
)
from app.services.workflows import (
    BacktestService,
    DailyReviewService,
    DataIngestionService,
    ExportWorkflowService,
    FeatureBuildService,
    LabelBuildService,
    ModelActivationService,
    ModelTrainingService,
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
    }


@router.post("/labels/build")
async def build_labels() -> dict[str, object]:
    result = LabelBuildService(repos()).build()
    return {
        "status": "ok",
        "bars_read": result["bars_read"],
        "features_read": result["features_read"],
        "candidates": result["candidates_written"],
        "labels": result["labels_written"],
    }


@router.post("/models/train")
async def train_model(request: TrainRequest) -> dict[str, object]:
    repository = repos()
    model = ModelTrainingService(repository).train(
        request.symbols,
        request.training_start,
        request.training_end,
        request.min_samples,
    )
    if request.activate_if_passes and model.get("model_version"):
        ValidationWorkflowService(repository).validate(
            model_version=str(model["model_version"]),
            symbols=request.symbols,
            start=request.training_start,
            end=request.training_end,
        )
        model["activation"] = ModelActivationService(repository).activate(str(model["model_version"]))
    return model


@router.post("/models/validate")
async def validate_model(model_version: str | None = None) -> dict[str, object]:
    return ValidationWorkflowService(repos()).validate(model_version=model_version)


@router.post("/models/activate")
async def activate_model(model_version: str) -> dict[str, object]:
    return ModelActivationService(repos()).activate(model_version)


@router.get("/models")
async def models() -> list[dict[str, object]]:
    repository_models = repos().model_runs.list_all()
    artifact_models = ModelEngine().list_models()
    versions = {str(model.get("model_version")) for model in repository_models}
    return repository_models + [model for model in artifact_models if str(model.get("model_version")) not in versions]


@router.get("/models/{model_version}")
async def model(model_version: str) -> dict[str, object]:
    return repos().model_runs.get(model_version) or ModelEngine().load(model_version)


@router.post("/backtest/run")
async def run_backtest(request: BacktestRequest) -> dict[str, object]:
    return BacktestService(repos()).run(request.symbols, request.start, request.end, request.model_version)


@router.get("/backtest/runs")
async def backtest_runs() -> list[dict[str, object]]:
    return BacktestService(repos()).list_runs()


@router.get("/backtest/runs/{run_id}")
async def backtest_run(run_id: str) -> dict[str, object]:
    for run in BacktestService(repos()).list_runs():
        if run.get("report_id") == run_id:
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
