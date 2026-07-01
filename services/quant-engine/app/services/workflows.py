from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any

from app.backtesting.engine import BacktestEngine
from app.backtesting.replay import (
    SIMULATION_TYPE_LABEL_DERIVED,
    SIMULATION_TYPE_REPLAY,
    CandidateMarketReplayEngine,
    ReplayConfig,
)
from app.config import Settings, get_settings
from app.data.provider import MarketDataProvider
from app.data.symbols import normalize_symbols
from app.db.repositories import RepositoryRegistry
from app.exports.service import ExportService
from app.features.engine import FEATURE_SET_VERSION, FeatureEngine
from app.labels.engine import LABEL_CONFIG_VERSION, LabelingEngine
from app.models.engine import ModelEngine
from app.regimes.classifier import RegimeClassifier
from app.schemas.market import Bar, Signal
from app.signals.candidates import CandidateSignalEngine
from app.utils.time import UTC
from app.validation.engine import ValidationEngine


def _model_report_payload(report: Any, model_version: str | None = None) -> dict[str, Any]:
    if hasattr(report, "model_dump"):
        payload = report.model_dump(mode="json")
    elif hasattr(report, "__dataclass_fields__"):
        from dataclasses import asdict

        payload = asdict(report)
    else:
        payload = dict(report)
    if model_version:
        payload["model_version"] = model_version
    return payload


class DataIngestionService:
    def __init__(
        self,
        repos: RepositoryRegistry,
        provider: MarketDataProvider,
        settings: Settings | None = None,
    ) -> None:
        self.repos = repos
        self.provider = provider
        self.settings = settings or get_settings()

    async def ingest(
        self,
        symbols: list[str] | None,
        intervals: list[str],
        start: datetime,
        end: datetime,
    ) -> dict[str, Any]:
        selected_symbols = normalize_symbols(symbols or self.settings.symbol_list)
        rows_written = 0
        errors: list[dict[str, str]] = []
        for symbol in selected_symbols:
            for interval in intervals:
                try:
                    bars = await self.provider.get_historical_bars(symbol, interval, start, end)
                    rows_written += self.repos.bars.upsert_many(bars)
                    self.repos.provider_requests.record(
                        provider="fmp",
                        endpoint=f"historical-chart/{interval}",
                        status="ok",
                        symbol=symbol,
                        interval=interval,
                        row_count=len(bars),
                    )
                except Exception as exc:
                    errors.append({"symbol": symbol, "interval": interval, "error": str(exc)})
                    self.repos.provider_requests.record(
                        provider="fmp",
                        endpoint=f"historical-chart/{interval}",
                        status="error",
                        symbol=symbol,
                        interval=interval,
                        error_message=str(exc),
                    )
        return {
            "symbols": selected_symbols,
            "intervals": intervals,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "bars_written": rows_written,
            "dirty_ranges": self.repos.pipeline_windows.list_dirty(symbols=selected_symbols, intervals=intervals),
            "errors": errors,
        }


class FeatureBuildService:
    def __init__(self, repos: RepositoryRegistry) -> None:
        self.repos = repos
        self.engine = FeatureEngine()
        self.regimes = RegimeClassifier()

    def build(
        self,
        symbols: list[str] | None = None,
        intervals: list[str] | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> dict[str, Any]:
        stale_ranges = self.repos.pipeline_windows.list_dirty("features", symbols=symbols, intervals=intervals)
        bars = self.repos.bars.query(symbols=symbols, intervals=intervals, start=start, end=end)
        features = self.engine.build_features(bars)
        bars_by_key: dict[tuple[str, str], list[Bar]] = {}
        for bar in bars:
            bars_by_key.setdefault((bar.symbol, bar.interval), []).append(bar)
        for feature in features:
            key = (str(feature["symbol"]), str(feature.get("interval") or "1min"))
            history = [bar for bar in bars_by_key.get(key, []) if bar.timestamp_utc <= feature["timestamp_utc"]]
            feature["market_regime"] = self.regimes.classify_market(history)
            feature["ticker_regime"] = self.regimes.classify_ticker(feature)
        written = self.repos.features.upsert_many(features)
        selected_symbols = normalize_symbols(symbols or sorted({bar.symbol for bar in bars}))
        selected_intervals = intervals or sorted({bar.interval for bar in bars}) or ["1min"]
        build_start = start or (min((bar.timestamp_utc for bar in bars), default=None))
        build_end = end or (max((bar.timestamp_utc for bar in bars), default=None))
        build_windows = self.repos.pipeline_windows.mark_built(
            "features",
            selected_symbols,
            selected_intervals,
            build_start,
            build_end,
            FEATURE_SET_VERSION,
            {"features_written": written},
        ) if selected_symbols else []
        return {
            "bars_read": len(bars),
            "features_written": written,
            "features": features,
            "stale_ranges": stale_ranges,
            "build_windows": build_windows,
        }


class LabelBuildService:
    def __init__(self, repos: RepositoryRegistry, settings: Settings | None = None) -> None:
        self.repos = repos
        self.settings = settings or get_settings()
        self.labels = LabelingEngine(max_hold_bars=self.settings.max_hold_minutes, target_r=self.settings.target_r)
        self.candidates = CandidateSignalEngine()

    def build(
        self,
        symbols: list[str] | None = None,
        intervals: list[str] | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> dict[str, Any]:
        stale_ranges = {
            "candidates": self.repos.pipeline_windows.list_dirty("candidates", symbols=symbols, intervals=intervals),
            "labels": self.repos.pipeline_windows.list_dirty("labels", symbols=symbols, intervals=intervals),
        }
        bars = self.repos.bars.query(symbols=symbols, intervals=intervals, start=start, end=end)
        features = self.repos.features.query(symbols=symbols, intervals=intervals, start=start, end=end)
        candidates = []
        for feature in features:
            candidates.extend(self.candidates.detect(feature))
        label_rows = self.labels.build_label_rows(bars, features)
        labels = self.labels.build_labels(bars, features)
        self.repos.candidate_signals.upsert_many(candidates)
        written = self.repos.labels.upsert_many(label_rows)
        selected_symbols = normalize_symbols(symbols or sorted({bar.symbol for bar in bars}))
        selected_intervals = intervals or sorted({bar.interval for bar in bars}) or ["1min"]
        build_start = start or (min((bar.timestamp_utc for bar in bars), default=None))
        build_end = end or (max((bar.timestamp_utc for bar in bars), default=None))
        build_windows = []
        if selected_symbols:
            build_windows.extend(
                self.repos.pipeline_windows.mark_built(
                    "candidates",
                    selected_symbols,
                    selected_intervals,
                    build_start,
                    build_end,
                    "candidate_signals.v1",
                    {"candidates_written": len(candidates)},
                )
            )
            build_windows.extend(
                self.repos.pipeline_windows.mark_built(
                    "labels",
                    selected_symbols,
                    selected_intervals,
                    build_start,
                    build_end,
                    LABEL_CONFIG_VERSION,
                    {"labels_written": written},
                )
            )
        return {
            "bars_read": len(bars),
            "features_read": len(features),
            "candidates_written": len(candidates),
            "labels_written": written,
            "labels": labels,
            "stale_ranges": stale_ranges,
            "build_windows": build_windows,
        }


class ValidationWorkflowService:
    def __init__(self, repos: RepositoryRegistry) -> None:
        self.repos = repos
        self.validation = ValidationEngine()
        self.backtest = BacktestEngine()

    def validate(
        self,
        model_version: str | None = None,
        symbols: list[str] | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        validation_mode: str = SIMULATION_TYPE_LABEL_DERIVED,
    ) -> dict[str, Any]:
        if validation_mode == SIMULATION_TYPE_REPLAY:
            replay_runs = self.repos.replays.list_runs()
            replay = replay_runs[0] if replay_runs else None
            if replay is None:
                report = {
                    "report_id": None,
                    "model_version": model_version,
                    "validation_mode": SIMULATION_TYPE_REPLAY,
                    "summary": self.backtest.summarize_trades([]),
                    "windows": [],
                    "activation_decision": "rejected",
                    "rejection_reasons": ["no_replay_run_available"],
                    "leakage_warnings": [],
                    "created_at": datetime.now(UTC).isoformat(),
                }
                return self.repos.validation_reports.save(report, model_version=model_version, purpose="replay_validation")
            metrics = dict(replay.get("summary_metrics") or {})
            decision = self.validation.activation_decision(metrics, [], [])
            payload = {
                "model_version": model_version,
                "validation_mode": SIMULATION_TYPE_REPLAY,
                "replay_run_id": replay["replay_run_id"],
                "summary": metrics,
                "windows": [],
                "per_symbol": metrics.get("per_symbol_metrics") or {},
                "per_setup": metrics.get("per_setup_metrics") or {},
                "per_regime": metrics.get("per_regime_metrics") or {},
                "per_time_bucket": metrics.get("per_time_bucket_metrics") or {},
                "leakage_warnings": [],
                "activation_decision": decision["activation_decision"],
                "rejection_reasons": decision["rejection_reasons"],
                "created_at": datetime.now(UTC).isoformat(),
            }
            return self.repos.validation_reports.save(payload, model_version=model_version, purpose="replay_validation")

        labels = self.repos.labels.query(symbols=symbols, start=start, end=end)
        features = self.repos.features.query(symbols=symbols, start=start, end=end)
        if not labels:
            report = {
                "report_id": None,
                "model_version": model_version,
                "validation_mode": SIMULATION_TYPE_LABEL_DERIVED,
                "summary": self.backtest.summarize_labels([]),
                "windows": [],
                "activation_decision": "rejected",
                "rejection_reasons": ["no_labels_available"],
                "leakage_warnings": [],
                "created_at": datetime.now(UTC).isoformat(),
            }
            return self.repos.validation_reports.save(report, model_version=model_version, purpose="validation")
        timestamps = [label.timestamp for label in labels]
        start_time = min(timestamps)
        end_time = max(timestamps) + timedelta(minutes=1)
        trades = self.backtest.simulate_labels(labels, one_open_trade_per_symbol=True)
        leakage_warnings = self.validation.leakage_warnings(features=features, labels=labels)
        try:
            split = self.validation.chronological_split(start_time, end_time, embargo_minutes=0)
            report = self.validation.validate_trades(trades, [split], leakage_warnings)
            payload = _model_report_payload(report, model_version=model_version)
            payload["validation_mode"] = SIMULATION_TYPE_LABEL_DERIVED
        except ValueError as exc:
            payload = {
                "model_version": model_version,
                "validation_mode": SIMULATION_TYPE_LABEL_DERIVED,
                "summary": self.backtest.summarize_trades(trades),
                "windows": [],
                "per_symbol": {},
                "per_setup": {},
                "per_regime": {},
                "leakage_warnings": leakage_warnings,
                "activation_decision": "rejected",
                "rejection_reasons": [str(exc)],
                "created_at": datetime.now(UTC).isoformat(),
            }
        return self.repos.validation_reports.save(payload, model_version=model_version, purpose="validation")


class ModelTrainingService:
    def __init__(self, repos: RepositoryRegistry) -> None:
        self.repos = repos
        self.engine = ModelEngine()

    def train(
        self,
        symbols: list[str] | None,
        training_start: datetime,
        training_end: datetime,
        min_samples: int = 30,
    ) -> dict[str, Any]:
        selected_symbols = normalize_symbols(symbols or get_settings().symbol_list)
        labels = self.repos.labels.query(symbols=selected_symbols, start=training_start, end=training_end)
        features = self.repos.features.query(symbols=selected_symbols, start=training_start, end=training_end)
        if not labels:
            return {
                "trained": False,
                "reason": "no_labels_available",
                "symbols": selected_symbols,
                "training_start": training_start.isoformat(),
                "training_end": training_end.isoformat(),
            }
        model = self.engine.train(labels, features, training_start, training_end, selected_symbols)
        model["minimum_samples_met"] = len(labels) >= min_samples
        if len(labels) < min_samples:
            model.setdefault("rejection_reasons", []).append("minimum_requested_samples_not_met")
            model["activation_decision"] = "rejected"
        self.repos.model_runs.save(model)
        return model


class ModelActivationService:
    def __init__(self, repos: RepositoryRegistry, settings: Settings | None = None) -> None:
        self.repos = repos
        self.settings = settings or get_settings()

    def activate(self, model_version: str, validation_mode: str = SIMULATION_TYPE_LABEL_DERIVED) -> dict[str, Any]:
        model = self.repos.model_runs.get(model_version) or ModelEngine().load(model_version)
        if not model or model.get("model_version") == "untrained-baseline":
            return {"activated": False, "reason": "model_not_found", "model_version": model_version}
        purpose = "replay_validation" if validation_mode == SIMULATION_TYPE_REPLAY else "validation"
        report = self.repos.validation_reports.latest(model_version=model_version, purpose=purpose)
        if not report:
            return {
                "activated": False,
                "reason": "accepted_validation_report_required",
                "model_version": model_version,
                "validation_mode": validation_mode,
            }
        if report.get("activation_decision") != "accepted":
            return {
                "activated": False,
                "reason": "validation_gate_failed",
                "model_version": model_version,
                "validation_mode": validation_mode,
                "rejection_reasons": report.get("rejection_reasons") or [],
                "report_id": report.get("report_id"),
            }
        model["active"] = True
        model["activation_decision"] = "accepted"
        model["activation_validation_mode"] = validation_mode
        active = self.repos.active_models.activate(model, validation_report_id=report.get("report_id"))
        self.settings.model_artifacts_dir.mkdir(parents=True, exist_ok=True)
        (self.settings.model_artifacts_dir / "active_model.json").write_text(
            json.dumps(model, indent=2, default=str),
            encoding="utf-8",
        )
        return {
            "activated": True,
            "model_version": model_version,
            "report_id": report.get("report_id"),
            "validation_mode": validation_mode,
            "active_model": active,
        }


class BacktestService:
    def __init__(self, repos: RepositoryRegistry) -> None:
        self.repos = repos
        self.engine = BacktestEngine()
        self.replay_engine = CandidateMarketReplayEngine()

    def run(
        self,
        symbols: list[str] | None,
        start: datetime,
        end: datetime,
        model_version: str | None = None,
    ) -> dict[str, Any]:
        labels = self.repos.labels.query(symbols=symbols, start=start, end=end)
        trades = self.engine.simulate_labels(labels, one_open_trade_per_symbol=True)
        report = {
            "model_version": model_version,
            "summary": self.engine.summarize_trades(trades),
            "windows": [],
            "per_symbol": self.engine.breakdown_trades(trades, "symbol"),
            "per_setup": self.engine.breakdown_trades(trades, "setup_type"),
            "per_regime": self.engine.breakdown_trades(trades, "market_regime"),
            "leakage_warnings": [],
            "activation_decision": "not_applicable",
            "rejection_reasons": [],
            "simulation_type": SIMULATION_TYPE_LABEL_DERIVED,
            "created_at": datetime.now(UTC).isoformat(),
        }
        persisted = self.repos.validation_reports.save(report, model_version=model_version, purpose="backtest")
        persisted["simulation_type"] = SIMULATION_TYPE_LABEL_DERIVED
        return persisted

    def run_replay(self, payload: dict[str, Any]) -> dict[str, Any]:
        config = ReplayConfig.from_payload(payload)
        bars = self.repos.bars.query(
            symbols=list(config.symbols),
            intervals=list(config.intervals),
            start=config.start,
            end=config.end,
        )
        features = self.repos.features.query(
            symbols=list(config.symbols),
            intervals=list(config.intervals),
            start=config.start,
            end=config.end,
        )
        candidates = self.repos.candidate_signals.query(
            symbols=list(config.symbols),
            intervals=list(config.intervals),
            start=config.start,
            end=config.end,
            sides=list(config.sides),
            setup_types=list(config.candidate_setup_types),
        )
        run = self.replay_engine.replay(bars, features, candidates, config)
        persisted = self.repos.replays.save(run.to_dict(), [trade.to_dict() for trade in run.trades])
        self.repos.pipeline_windows.mark_built(
            "replay",
            list(config.symbols) or sorted({bar.symbol for bar in bars}),
            list(config.intervals) or sorted({bar.interval for bar in bars}) or ["1min"],
            config.start,
            config.end,
            SIMULATION_TYPE_REPLAY,
            {
                "replay_run_id": run.replay_run_id,
                "total_candidates": run.metrics.get("total_candidates"),
                "total_trades": run.metrics.get("total_trades"),
            },
        )
        return persisted

    def get_replay(self, replay_run_id: str) -> dict[str, Any] | None:
        return self.repos.replays.get(replay_run_id)

    def replay_trades(self, replay_run_id: str, limit: int = 500, offset: int = 0, status: str | None = None) -> list[dict[str, Any]]:
        return self.repos.replays.list_trades(replay_run_id, limit=limit, offset=offset, status=status)

    def list_runs(self) -> list[dict[str, Any]]:
        label_runs = [
            run | {"simulation_type": run.get("simulation_type") or SIMULATION_TYPE_LABEL_DERIVED}
            for run in self.repos.validation_reports.list_all(purpose="backtest")
        ]
        replay_runs = self.repos.replays.list_runs()
        return sorted(
            [*label_runs, *replay_runs],
            key=lambda run: str(run.get("created_at") or ""),
            reverse=True,
        )

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        replay = self.repos.replays.get(run_id)
        if replay is not None:
            return replay
        for run in self.repos.validation_reports.list_all(purpose="backtest"):
            if run.get("report_id") == run_id:
                return run | {"simulation_type": run.get("simulation_type") or SIMULATION_TYPE_LABEL_DERIVED}
        return None


class ExportWorkflowService:
    def __init__(self, repos: RepositoryRegistry, exporter: ExportService | None = None) -> None:
        self.repos = repos
        self.exporter = exporter or ExportService()

    def export_signals(self, kind: str, run_date: date | None = None, run_id: str | None = None) -> dict[str, Any]:
        signals = self.repos.live_signals.list_latest(limit=1000)
        if kind == "csv":
            path = self.exporter.export_signals_csv(signals, run_date)
            record = self.repos.exports.record("live_signals", "csv", path, len(signals), run_id)
            return {"kind": kind, "path": str(path), "rows": len(signals), "export": record}
        if kind == "xlsx":
            path = self.exporter.export_signals_xlsx(signals, run_date)
            record = self.repos.exports.record("live_signals", "xlsx", path, len(signals), run_id)
            return {"kind": kind, "path": str(path), "rows": len(signals), "export": record}
        raise ValueError("export kind must be csv or xlsx")

    def export_daily_review(self, payload: dict[str, Any], run_date: date | None = None) -> dict[str, Any]:
        paths = self.exporter.export_daily_review(payload, run_date)
        records = [
            self.repos.exports.record("daily_review", path.suffix.removeprefix("."), path, 1)
            for path in paths
        ]
        return {"paths": [str(path) for path in paths], "exports": records}

    def export_replay_trades(self, replay_run_id: str, kind: str) -> dict[str, Any]:
        replay = self.repos.replays.get(replay_run_id)
        if replay is None:
            return {"status": "not_found", "replay_run_id": replay_run_id}
        trades = self.repos.replays.list_trades(replay_run_id, limit=100_000)
        if kind == "csv":
            path = self.exporter.export_replay_trades_csv(replay_run_id, trades)
            record = self.repos.exports.record(
                "replay_trades",
                "csv",
                path,
                len(trades),
                replay_run_id,
                {"simulation_type": SIMULATION_TYPE_REPLAY, "created_at": datetime.now(UTC).isoformat(), "filters": replay.get("config") or {}},
            )
            return {"status": "ok", "kind": kind, "path": str(path), "rows": len(trades), "export": record}
        if kind == "xlsx":
            path = self.exporter.export_replay_trades_xlsx(replay_run_id, trades)
            record = self.repos.exports.record(
                "replay_trades",
                "xlsx",
                path,
                len(trades),
                replay_run_id,
                {"simulation_type": SIMULATION_TYPE_REPLAY, "created_at": datetime.now(UTC).isoformat(), "filters": replay.get("config") or {}},
            )
            return {"status": "ok", "kind": kind, "path": str(path), "rows": len(trades), "export": record}
        raise ValueError("replay trade export kind must be csv or xlsx")

    def export_replay_summary(self, replay_run_id: str) -> dict[str, Any]:
        replay = self.repos.replays.get(replay_run_id)
        if replay is None:
            return {"status": "not_found", "replay_run_id": replay_run_id}
        trades = self.repos.replays.list_trades(replay_run_id, limit=100_000)
        summary_path = self.exporter.export_replay_summary_xlsx(replay, trades)
        metrics_path = self.exporter.export_replay_metrics_json(replay)
        records = [
            self.repos.exports.record(
                "replay_summary",
                "xlsx",
                summary_path,
                1,
                replay_run_id,
                {"simulation_type": SIMULATION_TYPE_REPLAY, "created_at": datetime.now(UTC).isoformat(), "filters": replay.get("config") or {}},
            ),
            self.repos.exports.record(
                "replay_metrics",
                "json",
                metrics_path,
                1,
                replay_run_id,
                {"simulation_type": SIMULATION_TYPE_REPLAY, "created_at": datetime.now(UTC).isoformat(), "filters": replay.get("config") or {}},
            ),
        ]
        return {"status": "ok", "paths": [str(summary_path), str(metrics_path)], "exports": records}


class DailyReviewService:
    def __init__(self, repos: RepositoryRegistry) -> None:
        self.repos = repos

    def build(self, run_date: date | None = None) -> dict[str, Any]:
        run_date = run_date or datetime.now(UTC).date()
        signals = self.repos.live_signals.list_latest(limit=1000)
        payload = {
            "date": run_date.isoformat(),
            "signals_reviewed": len(signals),
            "signals_fired": [signal.model_dump(mode="json") for signal in signals],
            "missed_moves": [],
            "false_positives": [],
            "false_negatives": [],
            "ticker_notes": {},
            "regime_notes": {},
            "recommendations": [
                "Daily review scaffold only; analyst annotations are required before any methodology changes."
            ],
        }
        saved = self.repos.daily_reviews.save(run_date, payload)
        return saved | {"payload": payload}


class ScannerPersistenceService:
    def __init__(self, repos: RepositoryRegistry) -> None:
        self.repos = repos

    def persist_signal(self, signal: Signal, scanner_run_id: str | None = None) -> None:
        self.repos.live_signals.upsert_many([signal], scanner_run_id=scanner_run_id)

    def active_model(self) -> dict[str, Any]:
        return self.repos.active_models.get_active() or ModelEngine().load()

    def context_bars(
        self,
        symbol: str,
        interval: str,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[Bar]:
        return self.repos.bars.query(symbols=[symbol], intervals=[interval], start=start, end=end)
