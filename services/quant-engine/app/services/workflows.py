from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any

from app.backtesting.audit import (
    CANDIDATE_CONFIG_VERSION,
    REPLAY_CONFIG_VERSION,
    candidate_fingerprint,
    git_commit,
    replay_config_hash,
    replay_input_fingerprint,
)
from app.backtesting.engine import BacktestEngine
from app.backtesting.replay import (
    SIMULATION_TYPE_LABEL_DERIVED,
    SIMULATION_TYPE_REPLAY,
    CandidateMarketReplayEngine,
    ReplayConfig,
)
from app.backtesting.sensitivity import ReplaySensitivityEngine, SensitivityConfig
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
        replay_run_id: str | None = None,
        replay_filter: dict[str, Any] | None = None,
        allow_latest_replay_fallback: bool = False,
        sensitivity_run_id: str | None = None,
        require_sensitivity: bool = False,
        minimum_robustness_score: float = 0.0,
        allow_stale_replay_validation: bool = False,
    ) -> dict[str, Any]:
        if validation_mode == SIMULATION_TYPE_REPLAY:
            replay, selection = self._select_replay_run(
                replay_run_id=replay_run_id,
                replay_filter=replay_filter,
                allow_latest_replay_fallback=allow_latest_replay_fallback,
            )
            if replay is None:
                reason = str(selection.get("reason") or "no_replay_run_available")
                return self._save_replay_rejection(
                    model_version,
                    selection,
                    [reason if reason in {"replay_run_selection_required", "replay_run_not_found", "no_replay_run_matching_filter"} else "no_replay_run_available"],
                )
            if str(replay.get("simulation_type")) != SIMULATION_TYPE_REPLAY:
                return self._save_replay_rejection(model_version, selection, ["invalid_replay_simulation_type"])
            stale_status = self._replay_stale_status(replay)
            if stale_status["status"] != "clean" and not allow_stale_replay_validation:
                return self._save_replay_rejection(
                    model_version,
                    selection,
                    ["stale_replay_run"],
                    replay=replay,
                    stale_status=stale_status,
                )
            metrics = dict(replay.get("summary_metrics") or {})
            decision = self.validation.activation_decision(metrics, [], [])
            rejection_reasons = list(decision["rejection_reasons"])
            sensitivity = None
            if require_sensitivity and not sensitivity_run_id:
                rejection_reasons.append("sensitivity_required")
            if sensitivity_run_id:
                sensitivity = self.repos.replay_sensitivity.get(sensitivity_run_id)
                if sensitivity is None:
                    rejection_reasons.append("sensitivity_run_not_found")
                elif sensitivity.get("replay_run_id") != replay.get("replay_run_id"):
                    rejection_reasons.append("sensitivity_replay_run_mismatch")
                else:
                    robustness = float(sensitivity.get("robustness_score") or 0.0)
                    if robustness < minimum_robustness_score:
                        rejection_reasons.append("sensitivity_robustness_below_threshold")
                    if sensitivity.get("pass_fail") != "pass":
                        rejection_reasons.append("sensitivity_gate_failed")
            activation_decision = "rejected" if rejection_reasons else str(decision["activation_decision"])
            payload = {
                "model_version": model_version,
                "validation_mode": SIMULATION_TYPE_REPLAY,
                "replay_run_id": replay["replay_run_id"],
                "replay_run_selection": selection,
                "stale_window_status": stale_status,
                "sensitivity_run_id": sensitivity_run_id,
                "sensitivity_summary": self._sensitivity_summary(sensitivity),
                "minimum_robustness_score": minimum_robustness_score,
                "summary": metrics,
                "windows": [],
                "per_symbol": metrics.get("per_symbol_metrics") or {},
                "per_setup": metrics.get("per_setup_metrics") or {},
                "per_regime": metrics.get("per_regime_metrics") or {},
                "per_time_bucket": metrics.get("per_time_bucket_metrics") or {},
                "leakage_warnings": [],
                "activation_decision": activation_decision,
                "rejection_reasons": rejection_reasons,
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

    def _select_replay_run(
        self,
        replay_run_id: str | None,
        replay_filter: dict[str, Any] | None,
        allow_latest_replay_fallback: bool,
    ) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        if replay_run_id:
            replay = self.repos.replays.get(replay_run_id)
            return replay, {
                "requested_replay_run_id": replay_run_id,
                "selected_replay_run_id": replay.get("replay_run_id") if replay else None,
                "reason": "explicit_replay_run_id" if replay else "replay_run_not_found",
                "allow_latest_replay_fallback": allow_latest_replay_fallback,
            }
        if replay_filter:
            replay = self.repos.replays.select(replay_filter)
            return replay, {
                "replay_filter": replay_filter,
                "selected_replay_run_id": replay.get("replay_run_id") if replay else None,
                "reason": "newest_created_at_matching_filter" if replay else "no_replay_run_matching_filter",
                "allow_latest_replay_fallback": allow_latest_replay_fallback,
            }
        if allow_latest_replay_fallback:
            replay_runs = self.repos.replays.list_runs()
            replay = replay_runs[0] if replay_runs else None
            return replay, {
                "selected_replay_run_id": replay.get("replay_run_id") if replay else None,
                "reason": "latest_replay_fallback",
                "allow_latest_replay_fallback": True,
            }
        return None, {"reason": "replay_run_selection_required", "allow_latest_replay_fallback": False}

    def _save_replay_rejection(
        self,
        model_version: str | None,
        selection: dict[str, Any],
        reasons: list[str],
        replay: dict[str, Any] | None = None,
        stale_status: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "report_id": None,
            "model_version": model_version,
            "validation_mode": SIMULATION_TYPE_REPLAY,
            "replay_run_id": replay.get("replay_run_id") if replay else None,
            "replay_run_selection": selection,
            "stale_window_status": stale_status or {},
            "summary": dict(replay.get("summary_metrics") or {}) if replay else self.backtest.summarize_trades([]),
            "windows": [],
            "activation_decision": "rejected",
            "rejection_reasons": reasons,
            "leakage_warnings": [],
            "created_at": datetime.now(UTC).isoformat(),
        }
        return self.repos.validation_reports.save(payload, model_version=model_version, purpose="replay_validation")

    def _replay_stale_status(self, replay: dict[str, Any]) -> dict[str, Any]:
        symbols = replay.get("symbols") or []
        intervals = replay.get("intervals") or []
        dirty = self.repos.pipeline_windows.list_dirty("replay", symbols=symbols, intervals=intervals)
        saved_status = replay.get("stale_window_status") or {}
        if dirty:
            return {
                "status": "dirty",
                "source": "pipeline_build_windows",
                "stale_window_ids": [row.get("build_window_id") for row in dirty],
                "dirty_windows": dirty,
                "saved_status": saved_status,
            }
        if isinstance(saved_status, dict) and saved_status.get("status") and saved_status.get("status") != "clean":
            return saved_status
        return {"status": "clean", "stale_window_ids": []}

    def _sensitivity_summary(self, sensitivity: dict[str, Any] | None) -> dict[str, Any] | None:
        if sensitivity is None:
            return None
        return {
            "sensitivity_run_id": sensitivity.get("sensitivity_run_id"),
            "replay_run_id": sensitivity.get("replay_run_id"),
            "robustness_score": sensitivity.get("robustness_score"),
            "pass_fail": sensitivity.get("pass_fail"),
            "fragility_flags": sensitivity.get("fragility_flags") or [],
            "gate_results": sensitivity.get("gate_results") or {},
        }


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
            "replay_run_id": report.get("replay_run_id"),
            "replay_run_selection": report.get("replay_run_selection"),
            "sensitivity_run_id": report.get("sensitivity_run_id"),
            "sensitivity_summary": report.get("sensitivity_summary"),
            "active_model": active,
        }


class BacktestService:
    def __init__(self, repos: RepositoryRegistry) -> None:
        self.repos = repos
        self.engine = BacktestEngine()
        self.replay_engine = CandidateMarketReplayEngine()
        self.sensitivity_engine = ReplaySensitivityEngine(self.replay_engine)

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
        stale_status = self._replay_input_stale_status(config)
        if stale_status["status"] != "clean" and not config.allow_stale:
            return {
                "status": "error",
                "reason": "stale_replay_inputs",
                "stale_window_status": stale_status,
                "hint": "Run /features/build and /labels/build or retry with allow_stale=true for an explicit audit-marked replay.",
            }
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
        replay_payload = run.to_dict()
        replay_payload.update(
            self._replay_provenance(
                config=config,
                bars=bars,
                features=features,
                candidates=candidates,
                run_payload=replay_payload,
                stale_status=stale_status,
            )
        )
        if stale_status["status"] != "clean":
            replay_payload.setdefault("warnings", []).append("replay_inputs_allowed_with_stale_pipeline_windows")
        persisted = self.repos.replays.save(replay_payload, [trade.to_dict() for trade in run.trades])
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

    def pipeline_status(self, symbols: list[str] | None = None, intervals: list[str] | None = None) -> dict[str, Any]:
        return self.repos.pipeline_windows.status(symbols=symbols, intervals=intervals) | {
            "persistence": self.repos.info()
        }

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

    def run_sensitivity(self, replay_run_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        replay = self.repos.replays.get(replay_run_id)
        if replay is None:
            return {"status": "not_found", "replay_run_id": replay_run_id}
        config = ReplayConfig.from_payload(dict(replay.get("config") or {}))
        bars, features, candidates = self._replay_sources(config)
        sensitivity = self.sensitivity_engine.run(
            replay_run_id,
            bars,
            features,
            candidates,
            config,
            SensitivityConfig.from_payload(payload),
        )
        sensitivity["source_config_hash"] = replay.get("config_hash")
        sensitivity["source_input_fingerprint"] = replay.get("input_fingerprint")
        sensitivity["source_candidate_fingerprint"] = replay.get("candidate_fingerprint")
        saved = self.repos.replay_sensitivity.save(sensitivity)
        return {"status": "ok", **saved}

    def get_sensitivity(self, sensitivity_run_id: str) -> dict[str, Any] | None:
        return self.repos.replay_sensitivity.get(sensitivity_run_id)

    def list_sensitivity(self, replay_run_id: str) -> list[dict[str, Any]]:
        return self.repos.replay_sensitivity.list_for_replay(replay_run_id)

    def sensitivity_scenarios(self, sensitivity_run_id: str) -> list[dict[str, Any]]:
        return self.repos.replay_sensitivity.list_scenarios(sensitivity_run_id)

    def compare_label_vs_replay(self, payload: dict[str, Any]) -> dict[str, Any]:
        replay_run_id = str(payload.get("replay_run_id") or "")
        replay = self.repos.replays.get(replay_run_id)
        if replay is None:
            return {"status": "not_found", "replay_run_id": replay_run_id}
        config = ReplayConfig.from_payload(dict(replay.get("config") or {}))
        labels = self.repos.labels.query(
            symbols=payload.get("symbols") or list(config.symbols),
            intervals=list(config.intervals),
            start=config.start,
            end=config.end,
        )
        label_trades = self.engine.simulate_labels(labels, one_open_trade_per_symbol=True)
        label_summary = self.engine.summarize_trades(label_trades)
        replay_summary = dict(replay.get("summary_metrics") or {})
        summary = self._comparison_summary(label_summary, replay_summary)
        comparison = {
            "comparison_type": "label_vs_replay",
            "label_run_id": payload.get("label_run_id"),
            "replay_run_id": replay_run_id,
            "label_summary": label_summary,
            "replay_summary": replay_summary,
            "summary": summary,
            "created_at": datetime.now(UTC).isoformat(),
        }
        saved = self.repos.backtest_comparisons.save(comparison)
        return {"status": "ok", **saved}

    def get_comparison(self, comparison_id: str) -> dict[str, Any] | None:
        return self.repos.backtest_comparisons.get(comparison_id)

    def _replay_sources(self, config: ReplayConfig) -> tuple[list[Bar], list[dict[str, Any]], list[dict[str, Any]]]:
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
        return bars, features, candidates

    def _replay_input_stale_status(self, config: ReplayConfig) -> dict[str, Any]:
        dirty = [
            row
            for row in self.repos.pipeline_windows.list_dirty(
                symbols=list(config.symbols),
                intervals=list(config.intervals),
            )
            if row.get("artifact_type") in {"features", "candidates"}
        ]
        return {
            "status": "dirty" if dirty else "clean",
            "stale_window_ids": [row.get("build_window_id") for row in dirty],
            "dirty_windows": dirty,
        }

    def _replay_provenance(
        self,
        config: ReplayConfig,
        bars: list[Bar],
        features: list[dict[str, Any]],
        candidates: list[dict[str, Any]],
        run_payload: dict[str, Any],
        stale_status: dict[str, Any],
    ) -> dict[str, Any]:
        config_payload = config.to_dict()
        return {
            "replay_config_version": REPLAY_CONFIG_VERSION,
            "feature_set_version": FEATURE_SET_VERSION,
            "candidate_config_version": CANDIDATE_CONFIG_VERSION,
            "label_config_version": LABEL_CONFIG_VERSION,
            "source_bar_count": len(bars),
            "source_feature_count": len(features),
            "source_candidate_count": len(candidates),
            "taken_trade_count": int((run_payload.get("summary_metrics") or {}).get("candidates_taken") or 0),
            "skipped_candidate_count": int((run_payload.get("summary_metrics") or {}).get("candidates_skipped") or 0),
            "repository_backend": self.repos.backend,
            "database_migration_revision": self.repos.info().get("alembic_version") or "sqlite-local",
            "git_commit": git_commit(),
            "config_hash": replay_config_hash(config_payload),
            "input_fingerprint": replay_input_fingerprint(bars, features, candidates, config_payload),
            "candidate_fingerprint": candidate_fingerprint(candidates),
            "stale_window_status": stale_status,
            "stale_window_ids": stale_status.get("stale_window_ids") or [],
        }

    def _comparison_summary(self, label_summary: dict[str, Any], replay_summary: dict[str, Any]) -> dict[str, Any]:
        def value(summary: dict[str, Any], key: str) -> float:
            return float(summary.get(key) or 0.0)

        deltas = {
            "total_trades": value(replay_summary, "total_trades") - value(label_summary, "total_trades"),
            "average_r": value(replay_summary, "average_r") - value(label_summary, "average_r"),
            "win_rate": value(replay_summary, "win_rate") - value(label_summary, "win_rate"),
            "profit_factor": value(replay_summary, "profit_factor") - value(label_summary, "profit_factor"),
            "max_drawdown_r": value(replay_summary, "max_drawdown_r") - value(label_summary, "max_drawdown_r"),
        }
        flags = []
        if abs(deltas["average_r"]) >= 0.25:
            flags.append("average_r_disagreement")
        if abs(deltas["win_rate"]) >= 0.15:
            flags.append("win_rate_disagreement")
        if abs(deltas["total_trades"]) >= max(5.0, value(label_summary, "total_trades") * 0.25):
            flags.append("trade_count_disagreement")
        return {
            "deltas": deltas,
            "material_disagreements": flags,
            "status": "material_disagreement" if flags else "aligned_with_tolerance",
        }


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

    def export_sensitivity_summary(self, sensitivity_run_id: str) -> dict[str, Any]:
        sensitivity = self.repos.replay_sensitivity.get(sensitivity_run_id)
        if sensitivity is None:
            return {"status": "not_found", "sensitivity_run_id": sensitivity_run_id}
        scenarios = self.repos.replay_sensitivity.list_scenarios(sensitivity_run_id)
        path = self.exporter.export_sensitivity_summary_xlsx(sensitivity, scenarios)
        record = self.repos.exports.record(
            "replay_sensitivity_summary",
            "xlsx",
            path,
            len(scenarios),
            str(sensitivity.get("replay_run_id")),
            self._sensitivity_export_payload(sensitivity, "summary"),
        )
        return {"status": "ok", "path": str(path), "rows": len(scenarios), "export": record}

    def export_sensitivity_scenarios(self, sensitivity_run_id: str, kind: str) -> dict[str, Any]:
        sensitivity = self.repos.replay_sensitivity.get(sensitivity_run_id)
        if sensitivity is None:
            return {"status": "not_found", "sensitivity_run_id": sensitivity_run_id}
        scenarios = self.repos.replay_sensitivity.list_scenarios(sensitivity_run_id)
        if kind == "csv":
            path = self.exporter.export_sensitivity_scenarios_csv(sensitivity_run_id, scenarios)
        elif kind == "xlsx":
            path = self.exporter.export_sensitivity_scenarios_xlsx(sensitivity_run_id, scenarios)
        else:
            raise ValueError("sensitivity scenario export kind must be csv or xlsx")
        record = self.repos.exports.record(
            "replay_sensitivity_scenarios",
            kind,
            path,
            len(scenarios),
            str(sensitivity.get("replay_run_id")),
            self._sensitivity_export_payload(sensitivity, "scenarios"),
        )
        return {"status": "ok", "kind": kind, "path": str(path), "rows": len(scenarios), "export": record}

    def export_sensitivity_metrics(self, sensitivity_run_id: str) -> dict[str, Any]:
        sensitivity = self.repos.replay_sensitivity.get(sensitivity_run_id)
        if sensitivity is None:
            return {"status": "not_found", "sensitivity_run_id": sensitivity_run_id}
        scenarios = self.repos.replay_sensitivity.list_scenarios(sensitivity_run_id)
        path = self.exporter.export_sensitivity_metrics_json(sensitivity, scenarios)
        record = self.repos.exports.record(
            "replay_sensitivity_metrics",
            "json",
            path,
            len(scenarios),
            str(sensitivity.get("replay_run_id")),
            self._sensitivity_export_payload(sensitivity, "metrics"),
        )
        return {"status": "ok", "path": str(path), "rows": len(scenarios), "export": record}

    def _sensitivity_export_payload(self, sensitivity: dict[str, Any], export_scope: str) -> dict[str, Any]:
        return {
            "simulation_type": SIMULATION_TYPE_REPLAY,
            "source_simulation_type": SIMULATION_TYPE_REPLAY,
            "sensitivity_run_id": sensitivity.get("sensitivity_run_id"),
            "replay_run_id": sensitivity.get("replay_run_id"),
            "config_hash": sensitivity.get("source_config_hash"),
            "input_fingerprint": sensitivity.get("source_input_fingerprint"),
            "candidate_fingerprint": sensitivity.get("source_candidate_fingerprint"),
            "filters": sensitivity.get("config") or {},
            "warnings": ["Sensitivity exports are reproducibility artifacts, not profitability claims."],
            "export_scope": export_scope,
            "created_at": datetime.now(UTC).isoformat(),
        }


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
