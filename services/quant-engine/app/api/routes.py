from __future__ import annotations

import json
from datetime import datetime

from app.utils.time import UTC

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.backtesting.engine import BacktestEngine
from app.config import get_settings
from app.data.fmp import FMPMarketDataProvider
from app.data.symbols import normalize_symbols
from app.exports.service import ExportService
from app.features.engine import FeatureEngine
from app.jobs.scanner import scanner_state
from app.labels.engine import LabelingEngine
from app.models.engine import ModelEngine
from app.regimes.classifier import RegimeClassifier
from app.schemas.market import (
    BacktestRequest,
    Bar,
    ExportRequest,
    IngestRequest,
    ScannerStartRequest,
    TrainRequest,
)

router = APIRouter()

_MEMORY: dict[str, object] = {
    "bars": [],
    "features": [],
    "labels": [],
    "backtests": [],
}


@router.get("/health")
async def health() -> dict[str, object]:
    return {"status": "ok", "time": datetime.now(UTC).isoformat()}


@router.get("/config")
async def config() -> dict[str, object]:
    settings = get_settings()
    return {
        "app_name": settings.app_name,
        "default_symbols": settings.symbol_list,
        "timezone": settings.timezone,
        "min_confidence": settings.min_confidence,
        "fmp_api_key_configured": bool(settings.fmp_api_key),
    }


@router.get("/symbols")
async def get_symbols() -> list[str]:
    return get_settings().symbol_list


@router.post("/symbols")
async def post_symbols(symbols: list[str]) -> list[str]:
    return normalize_symbols(symbols)


@router.get("/provider/capabilities")
async def provider_capabilities() -> list[dict[str, object]]:
    return FMPMarketDataProvider().capability_matrix()


@router.get("/provider/health")
async def provider_health() -> dict[str, object]:
    return await FMPMarketDataProvider().health_check()


@router.post("/data/ingest")
async def ingest(request: IngestRequest) -> dict[str, object]:
    provider = FMPMarketDataProvider()
    symbols = normalize_symbols(request.symbols or get_settings().symbol_list)
    bars: list[Bar] = []
    for symbol in symbols:
        for interval in request.intervals:
            bars.extend(await provider.get_historical_bars(symbol, interval, request.start, request.end))
    _MEMORY["bars"] = bars
    return {"status": "ok", "bars": len(bars), "symbols": symbols, "intervals": request.intervals}


@router.get("/data/bars")
async def data_bars() -> list[dict[str, object]]:
    bars = _MEMORY["bars"]
    return [bar.model_dump(mode="json") for bar in bars]  # type: ignore[union-attr]


@router.get("/data/quotes/latest")
async def latest_quotes() -> list[dict[str, object]]:
    quotes = await FMPMarketDataProvider().get_batch_quotes(get_settings().symbol_list)
    return [quote.model_dump(mode="json") for quote in quotes]


@router.post("/features/build")
async def build_features() -> dict[str, object]:
    bars: list[Bar] = _MEMORY["bars"]  # type: ignore[assignment]
    features = FeatureEngine().build_features(bars)
    classifier = RegimeClassifier()
    market_regime = classifier.classify_market(bars)
    for feature in features:
        feature["market_regime"] = market_regime
        feature["ticker_regime"] = classifier.classify_ticker(feature)
    _MEMORY["features"] = features
    return {"status": "ok", "features": len(features), "market_regime": market_regime}


@router.post("/labels/build")
async def build_labels() -> dict[str, object]:
    bars: list[Bar] = _MEMORY["bars"]  # type: ignore[assignment]
    features: list[dict[str, object]] = _MEMORY["features"]  # type: ignore[assignment]
    labels = LabelingEngine(max_hold_bars=get_settings().max_hold_minutes).build_labels(bars, features)
    _MEMORY["labels"] = labels
    return {"status": "ok", "labels": len(labels)}


@router.post("/models/train")
async def train_model(request: TrainRequest) -> dict[str, object]:
    labels = _MEMORY["labels"]  # type: ignore[assignment]
    features = _MEMORY["features"]  # type: ignore[assignment]
    model = ModelEngine().train(
        labels,
        features,
        request.training_start,
        request.training_end,
        normalize_symbols(request.symbols or get_settings().symbol_list),
    )
    if request.activate_if_passes:
        model["activation"] = ModelEngine().activate(model["model_version"])
    return model


@router.post("/models/validate")
async def validate_model(model_version: str | None = None) -> dict[str, object]:
    engine = ModelEngine()
    return engine.validate(engine.load(model_version))


@router.post("/models/activate")
async def activate_model(model_version: str) -> dict[str, object]:
    return ModelEngine().activate(model_version)


@router.get("/models")
async def models() -> list[dict[str, object]]:
    return ModelEngine().list_models()


@router.get("/models/{model_version}")
async def model(model_version: str) -> dict[str, object]:
    return ModelEngine().load(model_version)


@router.post("/backtest/run")
async def run_backtest(_request: BacktestRequest) -> dict[str, object]:
    labels = _MEMORY["labels"]  # type: ignore[assignment]
    engine = BacktestEngine()
    result = {
        "run_id": f"bt-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
        "summary": engine.summarize_labels(labels),
        "per_symbol": engine.breakdown(labels, "symbol"),
        "per_setup": engine.breakdown(labels, "setup_type"),
        "per_regime": engine.breakdown(labels, "market_regime"),
    }
    _MEMORY["backtests"] = [result, *_MEMORY["backtests"]]  # type: ignore[list-item]
    return result


@router.get("/backtest/runs")
async def backtest_runs() -> list[dict[str, object]]:
    return _MEMORY["backtests"]  # type: ignore[return-value]


@router.get("/backtest/runs/{run_id}")
async def backtest_run(run_id: str) -> dict[str, object]:
    for run in _MEMORY["backtests"]:  # type: ignore[union-attr]
        if run["run_id"] == run_id:
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
    return scanner_state.status()


@router.get("/signals/live")
async def signals_live() -> list[dict[str, object]]:
    return [signal.model_dump(mode="json") for signal in scanner_state.latest_signals]


@router.get("/signals/history")
async def signals_history() -> list[dict[str, object]]:
    return [signal.model_dump(mode="json") for signal in scanner_state.latest_signals]


@router.get("/signals/stream")
async def signals_stream() -> StreamingResponse:
    async def events():
        async for signal in scanner_state.stream():
            yield f"data: {json.dumps(signal.model_dump(mode='json'))}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@router.post("/exports/signals.csv")
async def export_signals_csv(_request: ExportRequest | None = None) -> dict[str, object]:
    path = ExportService().export_signals_csv(scanner_state.latest_signals)
    return {"status": "ok", "path": str(path)}


@router.post("/exports/signals.xlsx")
async def export_signals_xlsx(_request: ExportRequest | None = None) -> dict[str, object]:
    path = ExportService().export_signals_xlsx(scanner_state.latest_signals)
    return {"status": "ok", "path": str(path)}


@router.post("/exports/backtest.xlsx")
async def export_backtest_xlsx(_request: ExportRequest | None = None) -> dict[str, object]:
    path = ExportService().export_signals_xlsx(scanner_state.latest_signals)
    return {"status": "ok", "path": str(path), "note": "V1 workbook scaffold"}


@router.post("/exports/daily-review.xlsx")
async def export_daily_review_xlsx(_request: ExportRequest | None = None) -> dict[str, object]:
    paths = ExportService().export_daily_review(await daily_review())
    return {"status": "ok", "paths": [str(path) for path in paths]}


@router.get("/exports/{export_id}")
async def export_status(export_id: str) -> dict[str, object]:
    return {"export_id": export_id, "status": "local-file"}


@router.post("/review/daily")
async def daily_review() -> dict[str, object]:
    signals = scanner_state.latest_signals
    return {
        "date": datetime.now(UTC).date().isoformat(),
        "signals_fired": len([signal for signal in signals if signal.side.value != "NO_TRADE"]),
        "signals_skipped": len([signal for signal in signals if signal.side.value == "NO_TRADE"]),
        "missed_moves": [],
        "false_positives": [],
        "false_negatives": [],
        "ticker_notes": [],
        "regime_notes": [],
        "recommendations": ["Collect more labeled samples before trusting high-grade signals."],
    }


@router.get("/review/daily/{review_date}")
async def get_daily_review(review_date: str) -> dict[str, object]:
    return {"date": review_date, "status": "available after POST /review/daily"}
