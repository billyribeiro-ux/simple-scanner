from __future__ import annotations

import builtins
import json
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from statistics import mean, median
from typing import Any

from app.backtesting.audit import (
    CANDIDATE_CONFIG_VERSION,
    REPLAY_CONFIG_VERSION,
    candidate_fingerprint,
    git_commit,
    replay_config_hash,
    replay_input_fingerprint,
    stable_hash,
)
from app.backtesting.engine import BacktestEngine
from app.backtesting.replay import (
    SIMULATION_TYPE_COUNTERFACTUAL,
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
from app.models.calibration_audit import ScoreCalibrationAuditEngine
from app.models.calibration_drift import CalibrationDriftEngine
from app.models.engine import ModelEngine
from app.models.replay_evidence import (
    REPLAY_AWARE_MODEL_TYPE,
    REPLAY_AWARE_SCHEMA_VERSION,
    REPLAY_AWARE_VALIDATION_MODE,
    REPLAY_AWARE_VALIDATION_PURPOSE,
    CandidateOutcomeDatasetBuilder,
    EvidenceCube,
    EvidenceCubeBuilder,
    ReplayAwareMetaScorer,
    default_scoring_config,
    model_config_hash,
    score_audit_from_score,
    summarize_outcome_rows,
    training_summary,
)
from app.orchestration.windowing import generate_replay_windows
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
        training_replay_run_ids: list[str] | None = None,
        validation_replay_run_ids: list[str] | None = None,
        test_replay_run_ids: list[str] | None = None,
        counterfactual_training_replay_run_ids: list[str] | None = None,
        portfolio_validation_replay_run_ids: list[str] | None = None,
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
    ) -> dict[str, Any]:
        if validation_mode == REPLAY_AWARE_VALIDATION_MODE:
            return self._validate_replay_aware(
                model_version=model_version,
                replay_run_id=replay_run_id,
                replay_filter=replay_filter,
                allow_latest_replay_fallback=allow_latest_replay_fallback,
                require_sensitivity=require_sensitivity,
                minimum_robustness_score=minimum_robustness_score,
                allow_stale_replay_validation=allow_stale_replay_validation,
                training_replay_run_ids=training_replay_run_ids,
                validation_replay_run_ids=validation_replay_run_ids,
                test_replay_run_ids=test_replay_run_ids,
                counterfactual_training_replay_run_ids=counterfactual_training_replay_run_ids,
                portfolio_validation_replay_run_ids=portfolio_validation_replay_run_ids,
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

    def _validate_replay_aware(
        self,
        *,
        model_version: str | None,
        replay_run_id: str | None,
        replay_filter: dict[str, Any] | None,
        allow_latest_replay_fallback: bool,
        require_sensitivity: bool,
        minimum_robustness_score: float,
        allow_stale_replay_validation: bool,
        training_replay_run_ids: list[str] | None,
        validation_replay_run_ids: list[str] | None,
        test_replay_run_ids: list[str] | None,
        counterfactual_training_replay_run_ids: list[str] | None,
        portfolio_validation_replay_run_ids: list[str] | None,
        train_start: datetime | None,
        train_end: datetime | None,
        validation_start: datetime | None,
        validation_end: datetime | None,
        test_start: datetime | None,
        test_end: datetime | None,
        embargo_minutes: int,
        require_counterfactual_training: bool,
        require_portfolio_validation: bool,
        calibration_audit_required: bool,
        calibration_audit_id: str | None,
    ) -> dict[str, Any]:
        if not model_version:
            return self._save_replay_aware_report(
                None,
                {"activation_decision": "rejected", "rejection_reasons": ["model_version_required"]},
            )
        model = self.repos.model_runs.get(model_version)
        if model is None:
            return self._save_replay_aware_report(
                model_version,
                {"activation_decision": "rejected", "rejection_reasons": ["model_not_found"]},
            )
        if model.get("model_type") != REPLAY_AWARE_MODEL_TYPE:
            return self._save_replay_aware_report(
                model_version,
                {"activation_decision": "rejected", "rejection_reasons": ["model_is_not_replay_aware"]},
            )
        explicit_training_ids = [*(training_replay_run_ids or []), *(counterfactual_training_replay_run_ids or [])]
        explicit_validation_ids = [*(validation_replay_run_ids or []), *(portfolio_validation_replay_run_ids or [])]
        explicit_test_ids = list(test_replay_run_ids or [])
        explicit_ids = list(dict.fromkeys([*explicit_training_ids, *explicit_validation_ids, *explicit_test_ids]))
        replay_runs = (
            [run for replay_id in explicit_ids if (run := self.repos.replays.get(replay_id)) is not None]
            if explicit_ids
            else self._validation_replay_runs(model, replay_run_id, replay_filter, allow_latest_replay_fallback)
        )
        if not replay_runs:
            return self._save_replay_aware_report(
                model_version,
                {"activation_decision": "rejected", "rejection_reasons": ["replay_run_selection_required"]},
            )
        replay_ids = [str(run["replay_run_id"]) for run in replay_runs]
        missing_explicit = sorted(set(explicit_ids) - set(replay_ids))
        if missing_explicit:
            return self._save_replay_aware_report(
                model_version,
                {
                    "activation_decision": "rejected",
                    "rejection_reasons": ["explicit_replay_run_not_found"],
                    "missing_replay_run_ids": missing_explicit,
                },
            )
        stale_replays = [run for run in replay_runs if self._replay_stale_status(run)["status"] != "clean"]
        if stale_replays and not allow_stale_replay_validation:
            return self._save_replay_aware_report(
                model_version,
                {
                    "activation_decision": "rejected",
                    "rejection_reasons": ["stale_replay_run"],
                    "replay_run_ids": replay_ids,
                    "stale_window_status": [self._replay_stale_status(run) for run in stale_replays],
                },
            )
        sensitivities_by_run = {replay_id: self.repos.replay_sensitivity.list_for_replay(replay_id) for replay_id in replay_ids}
        if require_sensitivity:
            missing = [replay_id for replay_id, runs in sensitivities_by_run.items() if not runs]
            weak = [
                replay_id
                for replay_id, runs in sensitivities_by_run.items()
                if runs and float(runs[0].get("robustness_score") or 0.0) < minimum_robustness_score
            ]
            if missing or weak:
                return self._save_replay_aware_report(
                    model_version,
                    {
                        "activation_decision": "rejected",
                        "rejection_reasons": [
                            *(["sensitivity_required"] if missing else []),
                            *(["sensitivity_robustness_below_threshold"] if weak else []),
                        ],
                        "missing_sensitivity_replay_run_ids": missing,
                        "weak_sensitivity_replay_run_ids": weak,
                    },
                )
        trades_by_run = {replay_id: self.repos.replays.list_trades(replay_id, limit=100_000) for replay_id in replay_ids}
        all_timestamps = [
            datetime.fromisoformat(str(trade.get("signal_timestamp_utc")).replace("Z", "+00:00"))
            for trades in trades_by_run.values()
            for trade in trades
            if trade.get("signal_timestamp_utc")
        ]
        start = min(all_timestamps) if all_timestamps else None
        end = max(all_timestamps) if all_timestamps else None
        features = self.repos.features.query(symbols=model.get("symbols"), intervals=model.get("intervals"), start=start, end=end)
        candidates = self.repos.candidate_signals.query(symbols=model.get("symbols"), intervals=model.get("intervals"), start=start, end=end)
        comparisons_by_run = {replay_id: self.repos.backtest_comparisons.list_for_replay(replay_id) for replay_id in replay_ids}
        rows = CandidateOutcomeDatasetBuilder().build(
            replay_runs=replay_runs,
            trades_by_run=trades_by_run,
            features=features,
            candidates=candidates,
            sensitivities_by_run=sensitivities_by_run,
            comparisons_by_run=comparisons_by_run,
            training_start=start,
            training_end=end,
            allow_stale=allow_stale_replay_validation,
            outcome_source=str(model.get("outcome_source") or "counterfactual_preferred"),
        )
        if len(rows) < 3:
            return self._save_replay_aware_report(
                model_version,
                {
                    "activation_decision": "rejected",
                    "rejection_reasons": ["insufficient_replay_aware_validation_rows"],
                    "replay_run_ids": replay_ids,
                    "summary": {"candidate_rows": len(rows)},
                },
            )
        rows.sort(key=lambda row: row["signal_timestamp_utc"])
        if explicit_ids:
            training_id_set = set(explicit_training_ids)
            validation_id_set = set(explicit_validation_ids)
            test_id_set = set(explicit_test_ids)
            training_pool = [row for row in rows if row.get("replay_run_id") in training_id_set] or rows[: max(1, int(len(rows) * 0.6))]
            validation_rows = [row for row in rows if row.get("replay_run_id") in validation_id_set]
            test_rows = [row for row in rows if row.get("replay_run_id") in test_id_set]
            if not validation_rows and not test_rows:
                validation_rows = [row for row in rows if row not in training_pool]
            split_index = len(training_pool)
        else:
            split_index = max(1, int(len(rows) * 0.6))
            training_pool = rows[:split_index]
            validation_rows = rows[split_index:]
            test_rows = []
        validation_rows = self._filter_rows_by_window(validation_rows, validation_start, validation_end)
        test_rows = self._filter_rows_by_window(test_rows, test_start, test_end)
        if train_start or train_end:
            training_pool = self._filter_rows_by_window(training_pool, train_start, train_end)
        embargo_cutoff = self._max_row_time(training_pool)
        validation_first = self._min_row_time(validation_rows or test_rows)
        rejection_reasons: list[str] = []
        if embargo_cutoff and validation_first and validation_first < embargo_cutoff + timedelta(minutes=embargo_minutes):
            rejection_reasons.append("embargo_violation")
        if require_counterfactual_training and not any(row.get("candidate_quality_source") == "counterfactual" and row.get("observed_outcome") for row in training_pool):
            rejection_reasons.append("counterfactual_training_required")
        if require_portfolio_validation:
            validation_run_ids = set(explicit_validation_ids or replay_ids)
            portfolio_validation_available = any(
                run.get("simulation_type") == SIMULATION_TYPE_REPLAY and run.get("replay_run_id") in validation_run_ids
                for run in replay_runs
            )
            if not portfolio_validation_available:
                rejection_reasons.append("portfolio_validation_required")
        if calibration_audit_required:
            audit = self.repos.model_calibration_audits.get(calibration_audit_id) if calibration_audit_id else self.repos.model_calibration_audits.latest(model_version)
            if audit is None:
                rejection_reasons.append("calibration_audit_required")
        selected_rows: list[dict[str, Any]] = []
        suppressed_rows: list[dict[str, Any]] = []
        score_rows: list[dict[str, Any]] = []
        scored_validation_rows = [*validation_rows, *test_rows]
        for row in scored_validation_rows:
            row_time = datetime.fromisoformat(str(row["signal_timestamp_utc"]).replace("Z", "+00:00"))
            train_rows = [
                prior
                for prior in training_pool
                if datetime.fromisoformat(str(prior["signal_timestamp_utc"]).replace("Z", "+00:00")) < row_time - timedelta(minutes=embargo_minutes)
            ]
            cube = EvidenceCubeBuilder().build(
                train_rows,
                minimum_cell_sample_size=int((model.get("scoring_config") or {}).get("minimum_cell_sample_size") or 5),
            )
            score = ReplayAwareMetaScorer(cube, dict(model.get("scoring_config") or {})).score(row, row.get("feature_snapshot") or {}, model_version=model_version)
            score_rows.append(score | {"used_training_rows": len(train_rows)})
            if score["action"] == "TAKE" and row.get("observed_outcome"):
                selected_rows.append(row)
            else:
                suppressed_rows.append(row)
        summary = summarize_outcome_rows(selected_rows, minimum_cell_sample_size=1)
        criteria = dict(model.get("activation_criteria") or {})
        rejection_reasons.extend(self._replay_aware_rejection_reasons(
            summary,
            selected_rows,
            leakage_warnings=[],
            minimum_selected_trades=int(criteria.get("minimum_selected_trades") or criteria.get("minimum_trades") or 5),
            minimum_profit_factor=float(criteria.get("minimum_profit_factor") or 1.05),
            maximum_drawdown_r=float(criteria.get("maximum_drawdown_r") or -10.0),
            maximum_symbol_profit_share=float(criteria.get("maximum_symbol_profit_share") or 0.70),
            maximum_setup_profit_share=float(criteria.get("maximum_setup_profit_share") or 0.80),
        ))
        rejection_reasons = sorted(set(rejection_reasons))
        payload = {
            "model_version": model_version,
            "validation_mode": REPLAY_AWARE_VALIDATION_MODE,
            "replay_run_ids": replay_ids,
            "training_replay_run_ids": explicit_training_ids or replay_ids[:split_index],
            "validation_replay_run_ids": explicit_validation_ids or replay_ids,
            "test_replay_run_ids": explicit_test_ids,
            "summary": {
                **summary,
                "selected_candidate_count": len(selected_rows),
                "suppressed_candidate_count": len(suppressed_rows),
                "scored_candidate_count": len(score_rows),
                "training_candidate_count": len(training_pool),
                "validation_candidate_count": len(validation_rows),
                "test_candidate_count": len(test_rows),
                "embargo_minutes": embargo_minutes,
            },
            "windows": [
                {
                    "window_id": "replay-aware-wf-001",
                    "split": {
                        "train_start": train_start.isoformat() if train_start else (training_pool[0]["signal_timestamp_utc"] if training_pool else None),
                        "train_end": train_end.isoformat() if train_end else (training_pool[-1]["signal_timestamp_utc"] if training_pool else None),
                        "validation_start": validation_rows[0]["signal_timestamp_utc"] if validation_rows else None,
                        "validation_end": validation_rows[-1]["signal_timestamp_utc"] if validation_rows else None,
                        "test_start": test_start.isoformat() if test_start else (test_rows[0]["signal_timestamp_utc"] if test_rows else None),
                        "test_end": test_end.isoformat() if test_end else (test_rows[-1]["signal_timestamp_utc"] if test_rows else None),
                    },
                    "metrics": {
                        "selected_candidate_count": len(selected_rows),
                        "suppressed_candidate_count": len(suppressed_rows),
                        "no_future_leakage_enforced": True,
                        "embargo_minutes": embargo_minutes,
                        "training_replay_run_ids": explicit_training_ids,
                        "validation_replay_run_ids": explicit_validation_ids,
                        "test_replay_run_ids": explicit_test_ids,
                    },
                    "accepted": not rejection_reasons,
                    "rejection_reasons": rejection_reasons,
                }
            ],
            "selected_trades": selected_rows,
            "suppressed_candidates": suppressed_rows,
            "score_rows": score_rows,
            "per_symbol": self._row_breakdown(selected_rows, "symbol"),
            "per_setup": self._row_breakdown(selected_rows, "setup_type"),
            "per_regime": self._row_breakdown(selected_rows, "market_regime"),
            "per_time_bucket": self._row_breakdown(selected_rows, "time_bucket"),
            "sensitivity_summary": {
                replay_id: self._sensitivity_summary((sensitivities_by_run.get(replay_id) or [None])[0])
                for replay_id in replay_ids
            },
            "stale_window_status": [self._replay_stale_status(run) for run in replay_runs],
            "leakage_warnings": [],
            "activation_decision": "rejected" if rejection_reasons else "accepted",
            "rejection_reasons": rejection_reasons,
            "created_at": datetime.now(UTC).isoformat(),
        }
        return self.repos.validation_reports.save(payload, model_version=model_version, purpose=REPLAY_AWARE_VALIDATION_PURPOSE)

    def _save_replay_aware_report(self, model_version: str | None, payload: dict[str, Any]) -> dict[str, Any]:
        report = {
            "model_version": model_version,
            "validation_mode": REPLAY_AWARE_VALIDATION_MODE,
            "summary": payload.get("summary") or self.backtest.summarize_trades([]),
            "windows": payload.get("windows") or [],
            "activation_decision": payload.get("activation_decision") or "rejected",
            "rejection_reasons": payload.get("rejection_reasons") or [],
            "leakage_warnings": payload.get("leakage_warnings") or [],
            "created_at": datetime.now(UTC).isoformat(),
            **payload,
        }
        return self.repos.validation_reports.save(report, model_version=model_version, purpose=REPLAY_AWARE_VALIDATION_PURPOSE)

    def _validation_replay_runs(
        self,
        model: dict[str, Any],
        replay_run_id: str | None,
        replay_filter: dict[str, Any] | None,
        allow_latest_replay_fallback: bool,
    ) -> list[dict[str, Any]]:
        if replay_run_id:
            run = self.repos.replays.get(replay_run_id)
            return [run] if run else []
        if replay_filter:
            return self.repos.replays.filter(replay_filter)
        replay_ids = [str(value) for value in model.get("replay_run_ids") or []]
        if replay_ids:
            return [run for replay_id in replay_ids if (run := self.repos.replays.get(replay_id)) is not None]
        if allow_latest_replay_fallback:
            runs = self.repos.replays.list_runs()
            return runs[:1]
        return []

    def _row_breakdown(self, rows: list[dict[str, Any]], field: str) -> dict[str, dict[str, Any]]:
        output = {}
        buckets: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            buckets.setdefault(str(row.get(field) or "unknown"), []).append(row)
        for key, bucket in buckets.items():
            output[key] = summarize_outcome_rows(bucket, minimum_cell_sample_size=1)
        return output

    def _filter_rows_by_window(
        self,
        rows: list[dict[str, Any]],
        start: datetime | None,
        end: datetime | None,
    ) -> list[dict[str, Any]]:
        if start is None and end is None:
            return rows
        output = []
        for row in rows:
            timestamp = datetime.fromisoformat(str(row["signal_timestamp_utc"]).replace("Z", "+00:00"))
            if start and timestamp < start:
                continue
            if end and timestamp > end:
                continue
            output.append(row)
        return output

    def _min_row_time(self, rows: list[dict[str, Any]]) -> datetime | None:
        timestamps = [
            datetime.fromisoformat(str(row["signal_timestamp_utc"]).replace("Z", "+00:00"))
            for row in rows
            if row.get("signal_timestamp_utc")
        ]
        return min(timestamps) if timestamps else None

    def _max_row_time(self, rows: list[dict[str, Any]]) -> datetime | None:
        timestamps = [
            datetime.fromisoformat(str(row["signal_timestamp_utc"]).replace("Z", "+00:00"))
            for row in rows
            if row.get("signal_timestamp_utc")
        ]
        return max(timestamps) if timestamps else None

    def _replay_aware_rejection_reasons(
        self,
        summary: dict[str, Any],
        selected_rows: list[dict[str, Any]],
        leakage_warnings: list[str],
        *,
        minimum_selected_trades: int,
        minimum_profit_factor: float,
        maximum_drawdown_r: float,
        maximum_symbol_profit_share: float,
        maximum_setup_profit_share: float,
    ) -> list[str]:
        reasons = []
        if int(summary.get("observed_outcome_count") or 0) < minimum_selected_trades:
            reasons.append("minimum_selected_candidate_sample_not_met")
        if float(summary.get("average_r") or 0.0) <= 0:
            reasons.append("out_of_sample_expectancy_not_positive")
        if float(summary.get("profit_factor") or 0.0) <= minimum_profit_factor:
            reasons.append("profit_factor_below_threshold")
        if float(summary.get("max_drawdown_r") or 0.0) < maximum_drawdown_r:
            reasons.append("max_drawdown_too_large")
        if leakage_warnings:
            reasons.append("critical_leakage_warnings_present")
        if self._row_profit_concentration(selected_rows, "symbol") > maximum_symbol_profit_share:
            reasons.append("single_symbol_profit_concentration_too_high")
        if self._row_profit_concentration(selected_rows, "setup_type") > maximum_setup_profit_share:
            reasons.append("single_setup_profit_concentration_too_high")
        return reasons

    def _row_profit_concentration(self, rows: list[dict[str, Any]], field: str) -> float:
        profits = [max(float(row.get("realized_r") or 0.0), 0.0) for row in rows]
        gross_profit = sum(profits)
        if gross_profit <= 0:
            return 0.0
        buckets: dict[str, float] = {}
        for row in rows:
            key = str(row.get(field) or "unknown")
            buckets[key] = buckets.get(key, 0.0) + max(float(row.get("realized_r") or 0.0), 0.0)
        return max(buckets.values()) / gross_profit if buckets else 0.0


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
        model_type: str = "statistical_evidence_baseline",
        intervals: list[str] | None = None,
        setup_types: list[str] | None = None,
        sides: list[str] | None = None,
        replay_run_ids: list[str] | None = None,
        counterfactual_replay_run_ids: list[str] | None = None,
        portfolio_replay_run_ids: list[str] | None = None,
        replay_filter: dict[str, Any] | None = None,
        outcome_source: str = "counterfactual_preferred",
        require_counterfactual: bool = False,
        minimum_counterfactual_outcomes: int = 0,
        maximum_portfolio_only_fraction: float = 1.0,
        overlap_density_filters: list[str] | None = None,
        concurrency_bucket_filters: list[str] | None = None,
        sensitivity_required: bool = False,
        minimum_observed_outcomes: int = 5,
        minimum_cell_sample_size: int = 5,
        shrinkage_strength: float = 20.0,
        scoring_config: dict[str, Any] | None = None,
        activation_criteria: dict[str, Any] | None = None,
        validation_mode: str = SIMULATION_TYPE_LABEL_DERIVED,
        allow_stale: bool = False,
    ) -> dict[str, Any]:
        if model_type == REPLAY_AWARE_MODEL_TYPE:
            return self._train_replay_aware(
                symbols=symbols,
                intervals=intervals,
                setup_types=setup_types,
                sides=sides,
                training_start=training_start,
                training_end=training_end,
                min_samples=min_samples,
                replay_run_ids=replay_run_ids,
                counterfactual_replay_run_ids=counterfactual_replay_run_ids,
                portfolio_replay_run_ids=portfolio_replay_run_ids,
                replay_filter=replay_filter,
                outcome_source=outcome_source,
                require_counterfactual=require_counterfactual,
                minimum_counterfactual_outcomes=minimum_counterfactual_outcomes,
                maximum_portfolio_only_fraction=maximum_portfolio_only_fraction,
                overlap_density_filters=overlap_density_filters,
                concurrency_bucket_filters=concurrency_bucket_filters,
                sensitivity_required=sensitivity_required,
                minimum_observed_outcomes=minimum_observed_outcomes,
                minimum_cell_sample_size=minimum_cell_sample_size,
                shrinkage_strength=shrinkage_strength,
                scoring_config=scoring_config or {},
                activation_criteria=activation_criteria or {},
                validation_mode=validation_mode,
                allow_stale=allow_stale,
            )
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

    def _train_replay_aware(
        self,
        *,
        symbols: list[str] | None,
        intervals: list[str] | None,
        setup_types: list[str] | None,
        sides: list[str] | None,
        training_start: datetime,
        training_end: datetime,
        min_samples: int,
        replay_run_ids: list[str] | None,
        counterfactual_replay_run_ids: list[str] | None,
        portfolio_replay_run_ids: list[str] | None,
        replay_filter: dict[str, Any] | None,
        outcome_source: str,
        require_counterfactual: bool,
        minimum_counterfactual_outcomes: int,
        maximum_portfolio_only_fraction: float,
        overlap_density_filters: list[str] | None,
        concurrency_bucket_filters: list[str] | None,
        sensitivity_required: bool,
        minimum_observed_outcomes: int,
        minimum_cell_sample_size: int,
        shrinkage_strength: float,
        scoring_config: dict[str, Any],
        activation_criteria: dict[str, Any],
        validation_mode: str,
        allow_stale: bool,
    ) -> dict[str, Any]:
        selected_symbols = normalize_symbols(symbols or get_settings().symbol_list)
        selected_intervals = intervals or ["1min"]
        replay_runs = self._training_replay_runs(
            replay_run_ids,
            replay_filter,
            counterfactual_replay_run_ids=counterfactual_replay_run_ids,
            portfolio_replay_run_ids=portfolio_replay_run_ids,
        )
        replay_runs = [
            run
            for run in replay_runs
            if self._replay_matches_training_scope(run, selected_symbols, selected_intervals, training_start, training_end)
        ]
        if not replay_runs:
            return {
                "trained": False,
                "reason": "no_eligible_replay_runs",
                "model_type": REPLAY_AWARE_MODEL_TYPE,
                "symbols": selected_symbols,
                "intervals": selected_intervals,
                "training_start": training_start.isoformat(),
                "training_end": training_end.isoformat(),
            }
        replay_ids = [str(run["replay_run_id"]) for run in replay_runs]
        trades_by_run = {replay_id: self.repos.replays.list_trades(replay_id, limit=100_000) for replay_id in replay_ids}
        features = self.repos.features.query(
            symbols=selected_symbols,
            intervals=selected_intervals,
            start=training_start,
            end=training_end,
        )
        candidates = self.repos.candidate_signals.query(
            symbols=selected_symbols,
            intervals=selected_intervals,
            start=training_start,
            end=training_end,
            sides=sides,
            setup_types=setup_types,
        )
        sensitivities_by_run = {replay_id: self.repos.replay_sensitivity.list_for_replay(replay_id) for replay_id in replay_ids}
        comparisons_by_run = {replay_id: self.repos.backtest_comparisons.list_for_replay(replay_id) for replay_id in replay_ids}
        missing_sensitivity = [replay_id for replay_id, runs in sensitivities_by_run.items() if not runs]
        if sensitivity_required and missing_sensitivity:
            return {
                "trained": False,
                "reason": "sensitivity_required",
                "model_type": REPLAY_AWARE_MODEL_TYPE,
                "missing_sensitivity_replay_run_ids": missing_sensitivity,
            }
        try:
            outcome_rows = CandidateOutcomeDatasetBuilder().build(
                replay_runs=replay_runs,
                trades_by_run=trades_by_run,
                features=features,
                candidates=candidates,
                sensitivities_by_run=sensitivities_by_run,
                comparisons_by_run=comparisons_by_run,
                training_start=training_start,
                training_end=training_end,
                allow_stale=allow_stale,
                outcome_source=outcome_source,
                counterfactual_replay_run_ids=counterfactual_replay_run_ids,
                portfolio_replay_run_ids=portfolio_replay_run_ids,
                overlap_density_filters=overlap_density_filters,
                concurrency_bucket_filters=concurrency_bucket_filters,
            )
        except ValueError as exc:
            return {
                "trained": False,
                "reason": str(exc),
                "model_type": REPLAY_AWARE_MODEL_TYPE,
                "allow_stale": allow_stale,
            }
        if setup_types:
            outcome_rows = [row for row in outcome_rows if str(row.get("setup_type")) in set(setup_types)]
        if sides:
            outcome_rows = [row for row in outcome_rows if str(row.get("side")) in set(sides)]
        observed = [row for row in outcome_rows if row.get("observed_outcome")]
        counterfactual_observed = [row for row in observed if row.get("candidate_quality_source") == "counterfactual"]
        portfolio_observed = [row for row in observed if row.get("candidate_quality_source") == "portfolio"]
        portfolio_only_fraction = len(portfolio_observed) / len(observed) if observed else 0.0
        if (require_counterfactual or outcome_source == "counterfactual_only") and not counterfactual_observed:
            return {
                "trained": False,
                "reason": "counterfactual_replay_required",
                "model_type": REPLAY_AWARE_MODEL_TYPE,
                "outcome_source": outcome_source,
                "counterfactual_observed_count": 0,
            }
        if minimum_counterfactual_outcomes and len(counterfactual_observed) < minimum_counterfactual_outcomes:
            return {
                "trained": False,
                "reason": "minimum_counterfactual_outcomes_not_met",
                "model_type": REPLAY_AWARE_MODEL_TYPE,
                "outcome_source": outcome_source,
                "counterfactual_observed_count": len(counterfactual_observed),
                "minimum_counterfactual_outcomes": minimum_counterfactual_outcomes,
            }
        if len(observed) < minimum_observed_outcomes:
            return {
                "trained": False,
                "reason": "minimum_observed_outcomes_not_met",
                "model_type": REPLAY_AWARE_MODEL_TYPE,
                "observed_outcome_count": len(observed),
                "minimum_observed_outcomes": minimum_observed_outcomes,
            }
        cube = EvidenceCubeBuilder().build(outcome_rows, minimum_cell_sample_size=minimum_cell_sample_size)
        merged_scoring_config = default_scoring_config(
            {
                **scoring_config,
                "outcome_source": outcome_source,
                "minimum_observed_outcomes": minimum_observed_outcomes,
                "minimum_cell_sample_size": minimum_cell_sample_size,
                "shrinkage_strength": shrinkage_strength,
            }
        )
        metrics = training_summary(outcome_rows, list(cube.cells))
        warnings: list[str] = []
        if len(outcome_rows) < min_samples:
            warnings.append("minimum_requested_samples_not_met")
        if missing_sensitivity:
            warnings.append("some_training_replay_runs_missing_sensitivity")
        if allow_stale:
            warnings.append("allow_stale_training_enabled")
        if not counterfactual_observed:
            warnings.append("portfolio_only_replay_outcomes_used")
        if portfolio_only_fraction > maximum_portfolio_only_fraction:
            warnings.append("maximum_portfolio_only_fraction_exceeded")
        rejection_reasons = []
        if len(observed) < min_samples:
            rejection_reasons.append("minimum_requested_samples_not_met")
        if portfolio_only_fraction > maximum_portfolio_only_fraction:
            rejection_reasons.append("portfolio_only_fraction_above_threshold")
        counterfactual_ids = [str(run["replay_run_id"]) for run in replay_runs if run.get("simulation_type") == SIMULATION_TYPE_COUNTERFACTUAL]
        portfolio_ids = [str(run["replay_run_id"]) for run in replay_runs if run.get("simulation_type") == SIMULATION_TYPE_REPLAY]
        model_version = f"amd-replay-aware-{training_end.strftime('%Y%m%d')}-{datetime.now(UTC).strftime('%H%M%S')}"
        model = {
            "trained": True,
            "model_version": model_version,
            "schema_version": REPLAY_AWARE_SCHEMA_VERSION,
            "model_type": REPLAY_AWARE_MODEL_TYPE,
            "feature_set_version": self._feature_set_version(features, replay_runs),
            "label_config_version": None,
            "training_window": {"start": training_start.isoformat(), "end": training_end.isoformat()},
            "training_start": training_start.isoformat(),
            "training_end": training_end.isoformat(),
            "symbols": selected_symbols,
            "intervals": selected_intervals,
            "setup_types": sorted(set(str(row.get("setup_type")) for row in outcome_rows)),
            "sides": sorted(set(str(row.get("side")) for row in outcome_rows)),
            "replay_run_ids": replay_ids,
            "counterfactual_replay_run_ids": counterfactual_ids,
            "portfolio_replay_run_ids": portfolio_ids,
            "outcome_source": outcome_source,
            "require_counterfactual": require_counterfactual,
            "minimum_counterfactual_outcomes": minimum_counterfactual_outcomes,
            "maximum_portfolio_only_fraction": maximum_portfolio_only_fraction,
            "portfolio_only_fraction": portfolio_only_fraction,
            "sensitivity_run_ids": [
                str(run.get("sensitivity_run_id"))
                for runs in sensitivities_by_run.values()
                for run in runs[:1]
            ],
            "replay_config_hashes": sorted({str(run.get("config_hash")) for run in replay_runs if run.get("config_hash")}),
            "input_fingerprints": sorted({str(run.get("input_fingerprint")) for run in replay_runs if run.get("input_fingerprint")}),
            "candidate_fingerprints": sorted({str(run.get("candidate_fingerprint")) for run in replay_runs if run.get("candidate_fingerprint")}),
            "candidate_outcome_row_count": len(outcome_rows),
            "counterfactual_observed_count": len(counterfactual_observed),
            "portfolio_observed_count": len(portfolio_observed),
            "evidence_cell_count": len(cube.cells),
            "config_hash": model_config_hash(merged_scoring_config),
            "scoring_config": merged_scoring_config,
            "activation_criteria": activation_criteria,
            "validation_mode": validation_mode,
            "metrics": metrics,
            "validation_metrics": {"passes_activation_gate": False, "rejection_reasons": ["validation_required"]},
            "activation_decision": "rejected",
            "rejection_reasons": rejection_reasons or ["validation_required"],
            "warnings": warnings,
            "active": False,
            "created_at": datetime.now(UTC).isoformat(),
            "code_version": git_commit(),
            "notes": "Replay-aware deterministic evidence baseline; not a calibrated probability and not a profitability claim.",
        }
        self.repos.model_runs.save(model)
        self.repos.model_evidence_cells.save_many(model_version, list(cube.cells))
        return model

    def _training_replay_runs(
        self,
        replay_run_ids: list[str] | None,
        replay_filter: dict[str, Any] | None,
        *,
        counterfactual_replay_run_ids: list[str] | None = None,
        portfolio_replay_run_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        explicit_ids = [
            *(counterfactual_replay_run_ids or []),
            *(portfolio_replay_run_ids or []),
            *(replay_run_ids or []),
        ]
        if explicit_ids:
            seen: set[str] = set()
            runs = []
            for replay_id in explicit_ids:
                if replay_id in seen:
                    continue
                seen.add(replay_id)
                run = self.repos.replays.get(replay_id)
                if run is not None:
                    runs.append(run)
            return runs
        if replay_run_ids:
            return [run for replay_id in replay_run_ids if (run := self.repos.replays.get(replay_id)) is not None]
        if replay_filter:
            return self.repos.replays.filter(replay_filter)
        return []

    def _replay_matches_training_scope(
        self,
        replay: dict[str, Any],
        symbols: list[str],
        intervals: list[str],
        start: datetime,
        end: datetime,
    ) -> bool:
        if replay.get("simulation_type") not in {SIMULATION_TYPE_REPLAY, SIMULATION_TYPE_COUNTERFACTUAL}:
            return False
        replay_symbols = {str(symbol).upper() for symbol in replay.get("symbols") or []}
        if replay_symbols and set(symbols).isdisjoint(replay_symbols):
            return False
        replay_intervals = {str(interval) for interval in replay.get("intervals") or []}
        if replay_intervals and set(intervals).isdisjoint(replay_intervals):
            return False
        replay_end = self._parse_optional_datetime(replay.get("end"))
        replay_start = self._parse_optional_datetime(replay.get("start"))
        if replay_end and replay_end < start:
            return False
        if replay_start and replay_start > end:
            return False
        return True

    def _feature_set_version(self, features: list[dict[str, Any]], replay_runs: list[dict[str, Any]]) -> str:
        for feature in features:
            if feature.get("feature_set_version"):
                return str(feature["feature_set_version"])
        for replay in replay_runs:
            if replay.get("feature_set_version"):
                return str(replay["feature_set_version"])
        return FEATURE_SET_VERSION

    def _parse_optional_datetime(self, value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


class ModelActivationService:
    def __init__(self, repos: RepositoryRegistry, settings: Settings | None = None) -> None:
        self.repos = repos
        self.settings = settings or get_settings()

    def activate(
        self,
        model_version: str,
        validation_mode: str = SIMULATION_TYPE_LABEL_DERIVED,
        *,
        calibration_audit_required: bool = False,
        calibration_audit_id: str | None = None,
        require_monotonic_score_bins: bool = False,
        require_take_outperforms_watch: bool = False,
        minimum_high_grade_samples: int | None = None,
        minimum_rank_correlation_score: float | None = None,
        max_allowed_calibration_warnings: int | None = None,
    ) -> dict[str, Any]:
        model = self.repos.model_runs.get(model_version) or ModelEngine().load(model_version)
        if not model or model.get("model_version") == "untrained-baseline":
            return {"activated": False, "reason": "model_not_found", "model_version": model_version}
        if model.get("model_type") == REPLAY_AWARE_MODEL_TYPE and validation_mode != REPLAY_AWARE_VALIDATION_MODE:
            return {
                "activated": False,
                "reason": "replay_aware_validation_required",
                "model_version": model_version,
                "validation_mode": validation_mode,
            }
        purpose = (
            REPLAY_AWARE_VALIDATION_PURPOSE
            if validation_mode == REPLAY_AWARE_VALIDATION_MODE
            else ("replay_validation" if validation_mode == SIMULATION_TYPE_REPLAY else "validation")
        )
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
        calibration_metadata = self._calibration_gate(
            model,
            calibration_audit_required=calibration_audit_required,
            calibration_audit_id=calibration_audit_id,
            require_monotonic_score_bins=require_monotonic_score_bins,
            require_take_outperforms_watch=require_take_outperforms_watch,
            minimum_high_grade_samples=minimum_high_grade_samples,
            minimum_rank_correlation_score=minimum_rank_correlation_score,
            max_allowed_calibration_warnings=max_allowed_calibration_warnings,
        )
        if calibration_metadata["status"] == "failed":
            return {
                "activated": False,
                "reason": "calibration_gate_failed",
                "model_version": model_version,
                "validation_mode": validation_mode,
                "report_id": report.get("report_id"),
                "calibration": calibration_metadata,
            }
        model["active"] = True
        model["activation_decision"] = "accepted"
        model["activation_validation_mode"] = validation_mode
        model["calibration"] = calibration_metadata
        model["calibration_required"] = bool(calibration_metadata.get("required"))
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
            "calibration": calibration_metadata,
            "active_model": active,
        }

    def _calibration_gate(
        self,
        model: dict[str, Any],
        *,
        calibration_audit_required: bool,
        calibration_audit_id: str | None,
        require_monotonic_score_bins: bool,
        require_take_outperforms_watch: bool,
        minimum_high_grade_samples: int | None,
        minimum_rank_correlation_score: float | None,
        max_allowed_calibration_warnings: int | None,
    ) -> dict[str, Any]:
        criteria = dict(model.get("activation_criteria") or {})
        required = bool(calibration_audit_required or criteria.get("calibration_audit_required"))
        audit_id = calibration_audit_id or criteria.get("calibration_audit_id")
        audit = self.repos.model_calibration_audits.get(str(audit_id)) if audit_id else self.repos.model_calibration_audits.latest(str(model["model_version"]))
        if not required and audit is None:
            return {"required": False, "status": "not_required", "calibration_audit_id": None, "calibration_warnings": []}
        if audit is None:
            return {
                "required": required,
                "status": "failed",
                "reason": "calibration_audit_required",
                "calibration_audit_id": audit_id,
                "calibration_warnings": [],
            }
        warnings = list(audit.get("calibration_warnings") or audit.get("warnings") or [])
        reasons = list(audit.get("rejection_reasons") or [])
        monotonicity_pass = bool(audit.get("monotonicity_pass"))
        rank = float(audit.get("rank_correlation_score") or 0.0)
        separation = dict(audit.get("separation_metrics") or {})
        high_grade_samples = sum(
            int(row.get("sample_size") or 0)
            for row in audit.get("grade_bins") or []
            if str(row.get("bin_key") or "").startswith("A")
        )
        if (require_monotonic_score_bins or criteria.get("require_monotonic_score_bins")) and not monotonicity_pass:
            reasons.append("score_bins_not_monotonic")
        if (require_take_outperforms_watch or criteria.get("require_take_outperforms_watch")) and float(separation.get("take_minus_watch_average_r") or 0.0) <= 0:
            reasons.append("take_does_not_outperform_watch")
        min_high = minimum_high_grade_samples if minimum_high_grade_samples is not None else criteria.get("minimum_high_grade_samples")
        if min_high is not None and high_grade_samples < int(min_high):
            reasons.append("minimum_high_grade_samples_not_met")
        min_rank = minimum_rank_correlation_score if minimum_rank_correlation_score is not None else criteria.get("minimum_rank_correlation_score")
        if min_rank is not None and rank < float(min_rank):
            reasons.append("rank_correlation_below_threshold")
        max_warnings = max_allowed_calibration_warnings if max_allowed_calibration_warnings is not None else criteria.get("max_allowed_calibration_warnings")
        if max_warnings is not None and len(warnings) > int(max_warnings):
            reasons.append("too_many_calibration_warnings")
        status = "failed" if reasons else "passed"
        return {
            "required": required,
            "status": status,
            "calibration_audit_id": audit.get("calibration_audit_id"),
            "monotonicity_pass": monotonicity_pass,
            "rank_correlation_score": rank,
            "calibration_warnings": warnings,
            "rejection_reasons": sorted(set(reasons)),
        }


class ReplayAwareScoringService:
    def __init__(self, repos: RepositoryRegistry) -> None:
        self.repos = repos

    def evidence(self, model_version: str, limit: int = 500, offset: int = 0) -> dict[str, Any]:
        return {
            "model_version": model_version,
            "summary": self.repos.model_evidence_cells.summary(model_version),
            "limit": limit,
            "offset": offset,
            "evidence_cells": self.repos.model_evidence_cells.list(model_version, limit=limit, offset=offset),
        }

    def score_candidates(
        self,
        model_version: str,
        *,
        candidate_ids: list[str] | None = None,
        candidates: list[dict[str, Any]] | None = None,
        persist_audit: bool = True,
    ) -> dict[str, Any]:
        model = self.repos.model_runs.get(model_version)
        if model is None:
            return {"status": "not_found", "model_version": model_version, "scores": []}
        if model.get("model_type") != REPLAY_AWARE_MODEL_TYPE:
            return {"status": "error", "reason": "model_is_not_replay_aware", "model_version": model_version, "scores": []}
        cells = self.repos.model_evidence_cells.list(model_version, limit=100_000)
        cube = EvidenceCube(tuple(cells))
        scorer = ReplayAwareMetaScorer(cube, dict(model.get("scoring_config") or {}))
        selected_candidates = list(candidates or [])
        if candidate_ids:
            candidate_id_set = set(candidate_ids)
            selected_candidates.extend(
                candidate
                for candidate in self.repos.candidate_signals.list_all()
                if str(candidate.get("candidate_id")) in candidate_id_set
            )
        features_by_key = {
            (
                str(feature.get("symbol") or "").upper(),
                str(feature.get("interval") or "1min"),
                str(feature.get("timestamp_utc") or feature.get("timestamp")),
            ): feature
            for feature in self.repos.features.list_all()
        }
        scores = []
        for candidate in selected_candidates:
            feature = features_by_key.get(
                (
                    str(candidate.get("symbol") or "").upper(),
                    str(candidate.get("interval") or "1min"),
                    str(candidate.get("timestamp_utc") or candidate.get("timestamp")),
                )
            )
            score = scorer.score(candidate, feature, model_version=model_version)
            scores.append(score)
            if persist_audit:
                self.repos.candidate_score_audits.save(score_audit_from_score(score))
        return {"status": "ok", "model_version": model_version, "scores": scores}

    def score_audits(
        self,
        model_version: str,
        limit: int = 500,
        offset: int = 0,
        symbol: str | None = None,
    ) -> dict[str, Any]:
        return {
            "model_version": model_version,
            "limit": limit,
            "offset": offset,
            "score_audits": self.repos.candidate_score_audits.list(
                model_version,
                limit=limit,
                offset=offset,
                symbol=symbol,
            ),
        }


class CalibrationAuditService:
    def __init__(self, repos: RepositoryRegistry) -> None:
        self.repos = repos
        self.engine = ScoreCalibrationAuditEngine()

    def create(self, model_version: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        model = self.repos.model_runs.get(model_version)
        if model is None:
            return {"status": "not_found", "model_version": model_version}
        replay_run_ids = [str(value) for value in payload.get("replay_run_ids") or model.get("counterfactual_replay_run_ids") or model.get("replay_run_ids") or []]
        outcome_source = str(payload.get("outcome_source") or model.get("outcome_source") or "counterfactual_preferred")
        score_audits = self.repos.candidate_score_audits.list(model_version, limit=100_000)
        outcome_rows = self._outcome_rows(
            model,
            replay_run_ids,
            outcome_source=outcome_source,
        )
        audit = self.engine.run(
            model_version=model_version,
            score_audits=score_audits,
            outcome_rows=outcome_rows,
            replay_run_ids=replay_run_ids,
            validation_report_id=payload.get("validation_report_id"),
            outcome_source=outcome_source,
            config={
                "score_bins": payload.get("score_bins"),
                "minimum_high_grade_samples": payload.get("minimum_high_grade_samples", 5),
                "require_monotonic_score_bins": payload.get("require_monotonic_score_bins", False),
                "require_take_outperforms_watch": payload.get("require_take_outperforms_watch", False),
                "minimum_rank_correlation_score": payload.get("minimum_rank_correlation_score"),
                "max_allowed_calibration_warnings": payload.get("max_allowed_calibration_warnings"),
            },
        )
        saved = self.repos.model_calibration_audits.save(audit)
        return {"status": "ok", **saved}

    def list(self, model_version: str, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        return {
            "model_version": model_version,
            "limit": limit,
            "offset": offset,
            "calibration_audits": self.repos.model_calibration_audits.list(model_version, limit=limit, offset=offset),
        }

    def get(self, calibration_audit_id: str) -> dict[str, Any]:
        audit = self.repos.model_calibration_audits.get(calibration_audit_id)
        return audit or {"status": "not_found", "calibration_audit_id": calibration_audit_id}

    def bins(self, calibration_audit_id: str, limit: int = 500, offset: int = 0, bin_type: str | None = None) -> dict[str, Any]:
        return {
            "calibration_audit_id": calibration_audit_id,
            "limit": limit,
            "offset": offset,
            "bins": self.repos.model_calibration_audits.list_bins(
                calibration_audit_id,
                limit=limit,
                offset=offset,
                bin_type=bin_type,
            ),
        }

    def _outcome_rows(self, model: dict[str, Any], replay_run_ids: builtins.list[str], *, outcome_source: str) -> builtins.list[dict[str, Any]]:
        replay_runs = [run for replay_id in replay_run_ids if (run := self.repos.replays.get(replay_id)) is not None]
        trades_by_run = {str(run["replay_run_id"]): self.repos.replays.list_trades(str(run["replay_run_id"]), limit=100_000) for run in replay_runs}
        timestamps = [
            datetime.fromisoformat(str(trade.get("signal_timestamp_utc")).replace("Z", "+00:00"))
            for trades in trades_by_run.values()
            for trade in trades
            if trade.get("signal_timestamp_utc")
        ]
        start = min(timestamps) if timestamps else self._parse_optional_datetime(model.get("training_start"))
        end = max(timestamps) if timestamps else self._parse_optional_datetime(model.get("training_end"))
        features = self.repos.features.query(symbols=model.get("symbols"), intervals=model.get("intervals"), start=start, end=end)
        candidates = self.repos.candidate_signals.query(symbols=model.get("symbols"), intervals=model.get("intervals"), start=start, end=end)
        return CandidateOutcomeDatasetBuilder().build(
            replay_runs=replay_runs,
            trades_by_run=trades_by_run,
            features=features,
            candidates=candidates,
            training_start=start,
            training_end=end,
            allow_stale=True,
            outcome_source=outcome_source,
        )

    def _parse_optional_datetime(self, value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


class ModelComparisonService:
    def __init__(self, repos: RepositoryRegistry) -> None:
        self.repos = repos

    def compare(self, payload: dict[str, Any]) -> dict[str, Any]:
        model_versions = [str(value) for value in payload.get("model_versions") or []]
        models = [model for version in model_versions if (model := self.repos.model_runs.get(version)) is not None]
        validation_reports = [
            report
            for report in self.repos.validation_reports.list_all()
            if report.get("model_version") in model_versions
            or report.get("report_id") in set(payload.get("validation_report_ids") or [])
        ]
        calibration_ids = [str(value) for value in payload.get("calibration_audit_ids") or []]
        calibrations = [
            audit
            for audit_id in calibration_ids
            if (audit := self.repos.model_calibration_audits.get(audit_id)) is not None
        ]
        if not calibration_ids:
            calibrations = [
                audit
                for version in model_versions
                if (audit := self.repos.model_calibration_audits.latest(version)) is not None
            ]
        summary = {
            "model_count": len(models),
            "validation_report_count": len(validation_reports),
            "calibration_audit_count": len(calibrations),
            "diagnostic_only": True,
            "warnings": ["Model comparison is a research artifact and does not auto-activate a model."],
        }
        ranking = sorted(
            [
                {
                    "model_version": model.get("model_version"),
                    "observed_outcome_count": (model.get("metrics") or {}).get("observed_outcome_count"),
                    "average_r": (model.get("metrics") or {}).get("average_r"),
                    "profit_factor": (model.get("metrics") or {}).get("profit_factor"),
                    "active": bool(model.get("active")),
                }
                for model in models
            ],
            key=lambda row: (float(row.get("average_r") or 0.0), float(row.get("profit_factor") or 0.0)),
            reverse=True,
        )
        comparison = {
            "comparison_type": "model_comparison",
            "model_versions": model_versions,
            "validation_report_ids": payload.get("validation_report_ids") or [report.get("report_id") for report in validation_reports],
            "calibration_audit_ids": calibration_ids or [str(audit.get("calibration_audit_id")) for audit in calibrations if audit.get("calibration_audit_id")],
            "replay_run_ids": payload.get("replay_run_ids") or [],
            "comparison_window": payload.get("comparison_window") or {},
            "models": models,
            "validation_reports": validation_reports,
            "calibration_audits": calibrations,
            "robustness_ranking": ranking,
            "recommended_for_review": ranking[0]["model_version"] if ranking else None,
            "summary": summary,
            "warnings": summary["warnings"],
            "created_at": datetime.now(UTC).isoformat(),
        }
        saved = self.repos.model_comparisons.save(comparison)
        return {"status": "ok", **saved}

    def get(self, comparison_id: str) -> dict[str, Any]:
        return self.repos.model_comparisons.get(comparison_id) or {"status": "not_found", "comparison_id": comparison_id}


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
            config.simulation_type,
            {
                "replay_run_id": run.replay_run_id,
                "simulation_type": config.simulation_type,
                "replay_purpose": config.replay_purpose,
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

    def compare_counterfactual_vs_portfolio(self, payload: dict[str, Any]) -> dict[str, Any]:
        counterfactual_id = str(payload.get("counterfactual_replay_run_id") or "")
        portfolio_id = str(payload.get("portfolio_replay_run_id") or "")
        counterfactual = self.repos.replays.get(counterfactual_id)
        portfolio = self.repos.replays.get(portfolio_id)
        if counterfactual is None:
            return {"status": "not_found", "counterfactual_replay_run_id": counterfactual_id}
        if portfolio is None:
            return {"status": "not_found", "portfolio_replay_run_id": portfolio_id}
        warnings = ["Counterfactual-vs-portfolio comparison is analytical and not a trading instruction."]
        if counterfactual.get("simulation_type") != SIMULATION_TYPE_COUNTERFACTUAL:
            warnings.append("counterfactual_run_has_unexpected_simulation_type")
        if portfolio.get("simulation_type") != SIMULATION_TYPE_REPLAY:
            warnings.append("portfolio_run_has_unexpected_simulation_type")
        counterfactual_trades = self.repos.replays.list_trades(counterfactual_id, limit=100_000)
        portfolio_trades = self.repos.replays.list_trades(portfolio_id, limit=100_000)
        symbols = {str(symbol).upper() for symbol in payload.get("symbols") or []}
        setups = {str(setup) for setup in payload.get("setups") or []}
        if symbols:
            counterfactual_trades = [trade for trade in counterfactual_trades if str(trade.get("symbol") or "").upper() in symbols]
            portfolio_trades = [trade for trade in portfolio_trades if str(trade.get("symbol") or "").upper() in symbols]
        if setups:
            counterfactual_trades = [trade for trade in counterfactual_trades if str(trade.get("setup_type") or "") in setups]
            portfolio_trades = [trade for trade in portfolio_trades if str(trade.get("setup_type") or "") in setups]
        portfolio_by_candidate = {str(trade.get("candidate_id")): trade for trade in portfolio_trades if trade.get("candidate_id")}
        observed_counterfactual = [trade for trade in counterfactual_trades if str(trade.get("status")) == "TAKEN"]
        portfolio_executed = [trade for trade in portfolio_trades if str(trade.get("status")) == "TAKEN"]
        portfolio_skipped = [trade for trade in portfolio_trades if str(trade.get("status")) == "SKIPPED"]
        constraint_skips = {"overlapping_trade", "portfolio_trade_limit", "cooldown_active"}
        missed_edge = []
        for trade in observed_counterfactual:
            portfolio_trade = portfolio_by_candidate.get(str(trade.get("candidate_id")))
            if portfolio_trade and str(portfolio_trade.get("skip_reason")) in constraint_skips:
                missed_edge.append(trade)
        summary = {
            "counterfactual_replay_run_id": counterfactual_id,
            "portfolio_replay_run_id": portfolio_id,
            "independent_candidate_count": len(observed_counterfactual),
            "portfolio_executed_count": len(portfolio_executed),
            "portfolio_skipped_count": len(portfolio_skipped),
            "counterfactual_expectancy": self._average_r(observed_counterfactual),
            "portfolio_expectancy": self._average_r(portfolio_executed),
            "overlap_cost_estimate": sum(max(float(trade.get("realized_r") or 0.0), 0.0) for trade in missed_edge),
            "missed_edge_due_to_portfolio_constraints": len(missed_edge),
            "constraint_drag": self._average_r(observed_counterfactual) - self._average_r(portfolio_executed),
            "concurrency_hotspots": self._concurrency_hotspots(observed_counterfactual),
            "per_symbol_constraint_drag": self._constraint_drag(observed_counterfactual, portfolio_executed, "symbol"),
            "per_setup_constraint_drag": self._constraint_drag(observed_counterfactual, portfolio_executed, "setup_type"),
            "warnings": warnings,
        }
        comparison = {
            "comparison_type": "counterfactual_vs_portfolio",
            "label_run_id": counterfactual_id,
            "replay_run_id": portfolio_id,
            "counterfactual_replay_run_id": counterfactual_id,
            "portfolio_replay_run_id": portfolio_id,
            "summary": summary,
            "counterfactual_summary": counterfactual.get("summary_metrics") or {},
            "portfolio_summary": portfolio.get("summary_metrics") or {},
            "warnings": warnings,
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

    def _average_r(self, trades: list[dict[str, Any]]) -> float:
        values = [float(trade.get("realized_r") or 0.0) for trade in trades]
        return sum(values) / len(values) if values else 0.0

    def _constraint_drag(self, counterfactual: list[dict[str, Any]], portfolio: list[dict[str, Any]], field: str) -> dict[str, dict[str, float]]:
        keys = sorted({str(trade.get(field) or "unknown") for trade in [*counterfactual, *portfolio]})
        output = {}
        for key in keys:
            cf_rows = [trade for trade in counterfactual if str(trade.get(field) or "unknown") == key]
            pf_rows = [trade for trade in portfolio if str(trade.get(field) or "unknown") == key]
            output[key] = {
                "counterfactual_expectancy": self._average_r(cf_rows),
                "portfolio_expectancy": self._average_r(pf_rows),
                "constraint_drag": self._average_r(cf_rows) - self._average_r(pf_rows),
            }
        return output

    def _concurrency_hotspots(self, trades: list[dict[str, Any]]) -> dict[str, int]:
        hotspots: dict[str, int] = {}
        for trade in trades:
            metadata = dict(trade.get("metadata") or {})
            bucket = str(metadata.get("concurrency_bucket") or "unknown")
            hotspots[bucket] = hotspots.get(bucket, 0) + 1
        return hotspots


class DataQualityService:
    def __init__(self, repos: RepositoryRegistry) -> None:
        self.repos = repos

    def report(
        self,
        *,
        symbols: list[str] | None = None,
        intervals: list[str] | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        session: str = "rth",
    ) -> dict[str, Any]:
        selected_symbols = normalize_symbols(symbols or [])
        bars = self.repos.bars.query(
            symbols=selected_symbols or None,
            intervals=intervals,
            start=start,
            end=end,
        )
        duplicates = self._duplicates(bars)
        invalid_rows = self._invalid_rows(bars)
        missing_windows = self._missing_windows(bars)
        dirty_windows = self.repos.pipeline_windows.list_dirty(symbols=selected_symbols or None, intervals=intervals)
        provider_requests = self.repos.provider_requests.list_all()
        provider_errors = [
            row
            for row in provider_requests
            if str(row.get("status") or "").lower() not in {"ok", "success", "cached"}
        ]
        return {
            "status": "ok",
            "generated_at": datetime.now(UTC).isoformat(),
            "symbols": selected_symbols or sorted({bar.symbol for bar in bars}),
            "intervals": intervals or sorted({bar.interval for bar in bars}),
            "start": start.isoformat() if start else None,
            "end": end.isoformat() if end else None,
            "session": session,
            "summary": {
                "bar_count": len(bars),
                "duplicate_timestamp_count": len(duplicates),
                "invalid_price_or_volume_count": len(invalid_rows),
                "missing_bar_window_count": len(missing_windows),
                "dirty_pipeline_window_count": len(dirty_windows),
                "provider_error_count": len(provider_errors),
            },
            "duplicates": duplicates,
            "invalid_rows": invalid_rows,
            "missing_bar_windows": missing_windows,
            "dirty_pipeline_windows": dirty_windows,
            "provider_errors": provider_errors[:100],
            "warnings": self._quality_warnings(duplicates, invalid_rows, missing_windows, dirty_windows, provider_errors),
        }

    def _duplicates(self, bars: list[Bar]) -> list[dict[str, Any]]:
        counts = Counter((bar.symbol, bar.interval, bar.timestamp_utc.isoformat()) for bar in bars)
        return [
            {"symbol": symbol, "interval": interval, "timestamp_utc": timestamp, "count": count}
            for (symbol, interval, timestamp), count in sorted(counts.items())
            if count > 1
        ]

    def _invalid_rows(self, bars: list[Bar]) -> list[dict[str, Any]]:
        invalid = []
        for bar in bars:
            reasons = []
            if min(bar.open, bar.high, bar.low, bar.close) <= 0:
                reasons.append("non_positive_ohlc")
            if bar.high < bar.low:
                reasons.append("high_below_low")
            if bar.close > bar.high or bar.close < bar.low:
                reasons.append("close_outside_high_low")
            if bar.volume < 0:
                reasons.append("negative_volume")
            if reasons:
                invalid.append(
                    {
                        "symbol": bar.symbol,
                        "interval": bar.interval,
                        "timestamp_utc": bar.timestamp_utc.isoformat(),
                        "reasons": reasons,
                    }
                )
        return invalid

    def _missing_windows(self, bars: list[Bar]) -> list[dict[str, Any]]:
        by_key: dict[tuple[str, str], list[Bar]] = defaultdict(list)
        for bar in bars:
            by_key[(bar.symbol, bar.interval)].append(bar)
        output = []
        for (symbol, interval), rows in sorted(by_key.items()):
            expected_minutes = self._interval_minutes(interval)
            if expected_minutes <= 0:
                continue
            ordered = sorted(rows, key=lambda row: row.timestamp_utc)
            for previous, current in zip(ordered, ordered[1:], strict=False):
                gap_minutes = (current.timestamp_utc - previous.timestamp_utc).total_seconds() / 60.0
                if gap_minutes > expected_minutes * 1.5:
                    output.append(
                        {
                            "symbol": symbol,
                            "interval": interval,
                            "gap_start": previous.timestamp_utc.isoformat(),
                            "gap_end": current.timestamp_utc.isoformat(),
                            "expected_interval_minutes": expected_minutes,
                            "observed_gap_minutes": gap_minutes,
                        }
                    )
        return output

    def _interval_minutes(self, interval: str) -> int:
        if interval.endswith("min"):
            return int(interval.removesuffix("min"))
        return 0

    def _quality_warnings(
        self,
        duplicates: list[dict[str, Any]],
        invalid_rows: list[dict[str, Any]],
        missing_windows: list[dict[str, Any]],
        dirty_windows: list[dict[str, Any]],
        provider_errors: list[dict[str, Any]],
    ) -> list[str]:
        warnings = []
        if duplicates:
            warnings.append("duplicate_bars_detected")
        if invalid_rows:
            warnings.append("invalid_price_or_volume_detected")
        if missing_windows:
            warnings.append("missing_bar_windows_detected")
        if dirty_windows:
            warnings.append("dirty_pipeline_windows_detected")
        if provider_errors:
            warnings.append("provider_request_errors_detected")
        return warnings


class ReplayWindowOrchestrationService:
    def __init__(self, repos: RepositoryRegistry) -> None:
        self.repos = repos

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        windows, warnings = generate_replay_windows(payload)
        max_windows = int(payload.get("max_windows") or 50)
        allow_large = bool(payload.get("allow_large_window_count", False))
        status = "created"
        if len(windows) > max_windows and not allow_large:
            status = "rejected"
            warnings.append("window_count_exceeds_limit")
        enriched_windows = [self._annotate_window(window, payload) for window in windows]
        selected_symbols = normalize_symbols(payload.get("symbols") or (payload.get("replay_config") or {}).get("symbols") or [])
        selected_intervals = [str(value) for value in payload.get("intervals") or (payload.get("replay_config") or {}).get("intervals") or ["1min"]]
        created_at = datetime.now(UTC).isoformat()
        window_set = {
            "name": payload.get("name") or f"replay-window-set-{created_at[:10]}",
            "description": payload.get("description"),
            "symbols": selected_symbols,
            "intervals": selected_intervals,
            "setup_types": payload.get("setup_types") or payload.get("candidate_setup_types") or [],
            "start": payload.get("start"),
            "end": payload.get("end"),
            "window_mode": payload.get("window_mode") or payload.get("mode") or "custom",
            "window_size_days": payload.get("window_size_days"),
            "step_days": payload.get("step_days"),
            "embargo_minutes": payload.get("embargo_minutes") or 0,
            "session": payload.get("session") or "rth",
            "generated_windows": enriched_windows,
            "replay_config": payload.get("replay_config") or {},
            "sensitivity_config": payload.get("sensitivity_config") or {},
            "validation_config": payload.get("validation_config") or {},
            "model_version": payload.get("model_version"),
            "status": status,
            "warnings": sorted(set(warnings)),
            "summary": self._summary([], window_count=len(enriched_windows), status=status),
            "config_hash": stable_hash(payload),
            "created_at": created_at,
        }
        saved = self.repos.replay_windows.save_set(window_set)
        if status == "created" and payload.get("run_immediately"):
            run_result = self.run(str(saved["window_set_id"]), payload)
            return saved | {"run": run_result, "summary": run_result.get("summary", saved.get("summary"))}
        return {"status": status, **saved}

    def list(self, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        return {"window_sets": self.repos.replay_windows.list_sets(limit=limit, offset=offset), "limit": limit, "offset": offset}

    def get(self, window_set_id: str) -> dict[str, Any]:
        return self.repos.replay_windows.get_set(window_set_id) or {"status": "not_found", "window_set_id": window_set_id}

    def results(self, window_set_id: str, limit: int = 500, offset: int = 0) -> dict[str, Any]:
        return {
            "window_set_id": window_set_id,
            "results": self.repos.replay_windows.list_results(window_set_id, limit=limit, offset=offset),
            "limit": limit,
            "offset": offset,
        }

    def run(self, window_set_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        window_set = self.repos.replay_windows.get_set(window_set_id)
        if window_set is None:
            return {"status": "not_found", "window_set_id": window_set_id}
        payload = payload or {}
        existing = {
            int(result.get("window_index") or 0): result
            for result in self.repos.replay_windows.list_results(window_set_id, limit=100_000)
        }
        rerun = bool(payload.get("rerun", False))
        results = []
        for window in window_set.get("generated_windows") or []:
            index = int(window.get("window_index") or 0)
            if existing.get(index) and not rerun:
                results.append(existing[index] | {"status": existing[index].get("status") or "completed"})
                continue
            results.append(self._run_window(window_set, window, payload))
        summary = self._summary(results, window_count=len(window_set.get("generated_windows") or []), status="completed")
        updated = self.repos.replay_windows.save_set(
            window_set
            | {
                "status": "completed",
                "summary": summary,
                "completed_at": datetime.now(UTC).isoformat(),
            }
        )
        return {"status": "ok", "window_set_id": window_set_id, "summary": summary, "results": results, "window_set": updated}

    def export(self, window_set_id: str) -> dict[str, Any]:
        return ExportWorkflowService(self.repos).export_replay_window_set(window_set_id)

    def _annotate_window(self, window: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        start = self._parse_dt(window.get("replay_start"))
        end = self._parse_dt(window.get("replay_end"))
        symbols = normalize_symbols(payload.get("symbols") or (payload.get("replay_config") or {}).get("symbols") or [])
        intervals = [str(value) for value in payload.get("intervals") or (payload.get("replay_config") or {}).get("intervals") or ["1min"]]
        bars = self.repos.bars.query(symbols=symbols or None, intervals=intervals, start=start, end=end, limit=1)
        warnings = list(window.get("warnings") or [])
        if not bars:
            warnings.append("insufficient_data_no_bars")
        return window | {"warnings": sorted(set(warnings))}

    def _run_window(self, window_set: dict[str, Any], window: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        warnings = list(window.get("warnings") or [])
        replay_config = dict(window_set.get("replay_config") or {})
        symbols = window_set.get("symbols") or replay_config.get("symbols") or []
        intervals = window_set.get("intervals") or replay_config.get("intervals") or ["1min"]
        base = replay_config | {
            "symbols": symbols,
            "intervals": intervals,
            "start": window.get("replay_start"),
            "end": window.get("replay_end"),
            "session": window_set.get("session") or replay_config.get("session") or "rth",
            "candidate_setup_types": window_set.get("setup_types") or replay_config.get("candidate_setup_types") or [],
            "allow_stale": bool(replay_config.get("allow_stale", True)),
        }
        replay_run_ids: list[str] = []
        counterfactual = {}
        portfolio = {}
        if payload.get("run_replay", True):
            counterfactual = BacktestService(self.repos).run_replay(
                base
                | {
                    "replay_purpose": "model_training_counterfactual",
                    "simulation_type": SIMULATION_TYPE_COUNTERFACTUAL,
                    "allow_overlapping_trades": True,
                    "enforce_portfolio_constraints": False,
                    "enforce_symbol_overlap": False,
                    "counterfactual_include_invalid_candidates": True,
                }
            )
            portfolio = BacktestService(self.repos).run_replay(
                base
                | {
                    "replay_purpose": "portfolio_execution",
                    "simulation_type": SIMULATION_TYPE_REPLAY,
                    "enforce_portfolio_constraints": True,
                    "enforce_symbol_overlap": True,
                }
            )
            for run in (counterfactual, portfolio):
                if run.get("replay_run_id"):
                    replay_run_ids.append(str(run["replay_run_id"]))
                if run.get("status") == "error" or run.get("reason"):
                    warnings.append(str(run.get("reason") or "replay_run_error"))
                warnings.extend(str(item) for item in run.get("warnings") or [])
        comparison_ids = []
        if counterfactual.get("replay_run_id") and portfolio.get("replay_run_id"):
            comparison = BacktestService(self.repos).compare_counterfactual_vs_portfolio(
                {
                    "counterfactual_replay_run_id": counterfactual["replay_run_id"],
                    "portfolio_replay_run_id": portfolio["replay_run_id"],
                    "symbols": symbols,
                    "setups": window_set.get("setup_types") or [],
                }
            )
            if comparison.get("comparison_id"):
                comparison_ids.append(str(comparison["comparison_id"]))
        calibration_ids = []
        model_versions = [str(window_set["model_version"])] if window_set.get("model_version") else []
        if model_versions and payload.get("run_calibration"):
            calibration = CalibrationAuditService(self.repos).create(
                model_versions[0],
                {
                    "replay_run_ids": [counterfactual.get("replay_run_id") or portfolio.get("replay_run_id")],
                    "outcome_source": "counterfactual_preferred",
                },
            )
            if calibration.get("calibration_audit_id"):
                calibration_ids.append(str(calibration["calibration_audit_id"]))
            elif calibration.get("status") == "not_found":
                warnings.append("model_not_found_for_window_calibration")
        metrics = self._window_metrics(counterfactual, portfolio)
        result = {
            "window_set_id": window_set["window_set_id"],
            "window_index": window.get("window_index"),
            "window_id": window.get("window_id"),
            "train_start": window.get("train_start"),
            "train_end": window.get("train_end"),
            "validation_start": window.get("validation_start"),
            "validation_end": window.get("validation_end"),
            "test_start": window.get("test_start"),
            "test_end": window.get("test_end"),
            "replay_start": window.get("replay_start"),
            "replay_end": window.get("replay_end"),
            "replay_run_ids": replay_run_ids,
            "counterfactual_replay_run_id": counterfactual.get("replay_run_id"),
            "portfolio_replay_run_id": portfolio.get("replay_run_id"),
            "sensitivity_run_ids": [],
            "calibration_audit_ids": calibration_ids,
            "comparison_ids": comparison_ids,
            "model_versions": model_versions,
            "metrics": metrics,
            "status": "completed",
            "warnings": sorted(set(warnings)),
            "created_at": datetime.now(UTC).isoformat(),
            "completed_at": datetime.now(UTC).isoformat(),
        }
        return self.repos.replay_windows.save_result(result)

    def _window_metrics(self, counterfactual: dict[str, Any], portfolio: dict[str, Any]) -> dict[str, Any]:
        cf_metrics = dict(counterfactual.get("summary_metrics") or counterfactual.get("metrics") or {})
        pf_metrics = dict(portfolio.get("summary_metrics") or portfolio.get("metrics") or {})
        return {
            "counterfactual_total_trades": int(cf_metrics.get("total_trades") or 0),
            "portfolio_total_trades": int(pf_metrics.get("total_trades") or 0),
            "counterfactual_average_r": float(cf_metrics.get("average_r") or 0.0),
            "portfolio_average_r": float(pf_metrics.get("average_r") or 0.0),
            "average_r": float(pf_metrics.get("average_r") or cf_metrics.get("average_r") or 0.0),
            "profit_factor": float(pf_metrics.get("profit_factor") or cf_metrics.get("profit_factor") or 0.0),
            "max_drawdown_r": float(pf_metrics.get("max_drawdown_r") or cf_metrics.get("max_drawdown_r") or 0.0),
            "total_trades": int(pf_metrics.get("total_trades") or cf_metrics.get("total_trades") or 0),
            "constraint_drag": float(cf_metrics.get("average_r") or 0.0) - float(pf_metrics.get("average_r") or 0.0),
        }

    def _summary(self, results: builtins.list[dict[str, Any]], *, window_count: int, status: str) -> dict[str, Any]:
        completed = [row for row in results if str(row.get("status")) == "completed"]
        failed = [row for row in results if str(row.get("status")) == "failed"]
        averages = [float((row.get("metrics") or {}).get("average_r") or 0.0) for row in completed]
        return {
            "status": status,
            "window_count": window_count,
            "completed_window_count": len(completed),
            "failed_window_count": len(failed),
            "warning_count": sum(len(row.get("warnings") or []) for row in results),
            "average_window_expectancy_r": mean(averages) if averages else 0.0,
            "median_window_expectancy_r": median(averages) if averages else 0.0,
            "worst_window_expectancy_r": min(averages) if averages else 0.0,
            "best_window_expectancy_r": max(averages) if averages else 0.0,
            "total_trades": sum(int((row.get("metrics") or {}).get("total_trades") or 0) for row in completed),
            "diagnostic_only": True,
        }

    def _parse_dt(self, value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


class CalibrationDriftService:
    def __init__(self, repos: RepositoryRegistry) -> None:
        self.repos = repos
        self.engine = CalibrationDriftEngine()

    def create(self, model_version: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        model = self.repos.model_runs.get(model_version)
        if model is None:
            return {"status": "not_found", "model_version": model_version}
        audits = self._calibration_audits(model_version, payload)
        window_results = self._window_results(payload)
        replay_runs = self._replay_runs(payload, audits, window_results)
        report = self.engine.run(
            model_version=model_version,
            calibration_audits=audits,
            window_results=window_results,
            replay_runs=replay_runs,
            config=payload,
        )
        saved = self.repos.model_calibration_drift.save(report)
        return {"status": "ok", **saved}

    def list(self, model_version: str, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        return {
            "model_version": model_version,
            "drift_reports": self.repos.model_calibration_drift.list(model_version, limit=limit, offset=offset),
            "limit": limit,
            "offset": offset,
        }

    def get(self, drift_report_id: str) -> dict[str, Any]:
        return self.repos.model_calibration_drift.get(drift_report_id) or {"status": "not_found", "drift_report_id": drift_report_id}

    def windows(self, drift_report_id: str, limit: int = 500, offset: int = 0) -> dict[str, Any]:
        return {
            "drift_report_id": drift_report_id,
            "windows": self.repos.model_calibration_drift.list_windows(drift_report_id, limit=limit, offset=offset),
            "limit": limit,
            "offset": offset,
        }

    def _calibration_audits(self, model_version: str, payload: dict[str, Any]) -> builtins.list[dict[str, Any]]:
        ids = [str(value) for value in payload.get("calibration_audit_ids") or []]
        if ids:
            return [audit for audit_id in ids if (audit := self.repos.model_calibration_audits.get(audit_id)) is not None]
        return builtins.list(reversed(self.repos.model_calibration_audits.list(model_version, limit=int(payload.get("limit") or 20))))

    def _window_results(self, payload: dict[str, Any]) -> builtins.list[dict[str, Any]]:
        if payload.get("window_set_id"):
            return self.repos.replay_windows.list_results(str(payload["window_set_id"]), limit=100_000)
        ids = {str(value) for value in payload.get("window_result_ids") or []}
        if not ids:
            return []
        return [
            result
            for window_set in self.repos.replay_windows.list_sets(limit=100_000)
            for result in self.repos.replay_windows.list_results(str(window_set["window_set_id"]), limit=100_000)
            if str(result.get("window_result_id")) in ids
        ]

    def _replay_runs(
        self,
        payload: dict[str, Any],
        audits: builtins.list[dict[str, Any]],
        window_results: builtins.list[dict[str, Any]],
    ) -> builtins.list[dict[str, Any]]:
        replay_ids = {
            str(value)
            for value in payload.get("replay_run_ids") or []
            if value
        }
        for audit in audits:
            replay_ids.update(str(value) for value in builtins.list(audit.get("replay_run_ids") or []) if value)
        for result in window_results:
            replay_ids.update(str(value) for value in builtins.list(result.get("replay_run_ids") or []) if value)
        return [run for replay_id in replay_ids if (run := self.repos.replays.get(replay_id)) is not None]


class ModelReviewReportService:
    def __init__(self, repos: RepositoryRegistry) -> None:
        self.repos = repos

    def create(self, model_version: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        model = self.repos.model_runs.get(model_version)
        if model is None:
            return {"status": "not_found", "model_version": model_version}
        validation_reports = self._validation_reports(model_version, payload)
        calibrations = self._calibrations(model_version, payload)
        drift_reports = self._drift_reports(model_version, payload)
        window_set = self.repos.replay_windows.get_set(str(payload.get("window_set_id"))) if payload.get("window_set_id") else None
        readiness_status, readiness_reasons, unresolved_warnings = self._readiness(
            model,
            validation_reports,
            calibrations,
            drift_reports,
            window_set,
            payload,
        )
        report = {
            "model_version": model_version,
            "window_set_id": payload.get("window_set_id"),
            "validation_report_ids": [str(row.get("report_id")) for row in validation_reports if row.get("report_id")],
            "calibration_audit_ids": [str(row.get("calibration_audit_id")) for row in calibrations if row.get("calibration_audit_id")],
            "drift_report_ids": [str(row.get("drift_report_id")) for row in drift_reports if row.get("drift_report_id")],
            "sensitivity_run_ids": [str(value) for value in payload.get("sensitivity_run_ids") or []],
            "comparison_ids": [str(value) for value in payload.get("comparison_ids") or []],
            "model_summary": {
                "model_type": model.get("model_type"),
                "activation_decision": model.get("activation_decision"),
                "active": bool(model.get("active")),
                "metrics": model.get("metrics") or {},
            },
            "validation_reports": validation_reports,
            "calibration_audits": calibrations,
            "drift_reports": drift_reports,
            "window_set_summary": window_set.get("summary") if window_set else None,
            "readiness_status": readiness_status,
            "readiness_reasons": readiness_reasons,
            "unresolved_warnings": sorted(set(unresolved_warnings)),
            "summary": {
                "validation_report_count": len(validation_reports),
                "calibration_audit_count": len(calibrations),
                "drift_report_count": len(drift_reports),
                "readiness_status": readiness_status,
                "model_activation_unchanged": True,
                "diagnostic_only": True,
            },
            "warnings": ["Model review reports are advisory and do not activate or route orders."],
            "created_at": datetime.now(UTC).isoformat(),
        }
        saved = self.repos.model_review_reports.save(report)
        return {"status": "ok", **saved}

    def list(self, model_version: str, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        return {
            "model_version": model_version,
            "review_reports": self.repos.model_review_reports.list(model_version, limit=limit, offset=offset),
            "limit": limit,
            "offset": offset,
        }

    def get(self, review_report_id: str) -> dict[str, Any]:
        return self.repos.model_review_reports.get(review_report_id) or {"status": "not_found", "review_report_id": review_report_id}

    def _validation_reports(self, model_version: str, payload: dict[str, Any]) -> builtins.list[dict[str, Any]]:
        ids = {str(value) for value in payload.get("validation_report_ids") or []}
        reports = self.repos.validation_reports.list_all()
        if ids:
            return [row for row in reports if str(row.get("report_id")) in ids]
        return [row for row in reports if str(row.get("model_version")) == model_version]

    def _calibrations(self, model_version: str, payload: dict[str, Any]) -> builtins.list[dict[str, Any]]:
        ids = [str(value) for value in payload.get("calibration_audit_ids") or []]
        if ids:
            return [audit for audit_id in ids if (audit := self.repos.model_calibration_audits.get(audit_id)) is not None]
        latest = self.repos.model_calibration_audits.latest(model_version)
        return [latest] if latest else []

    def _drift_reports(self, model_version: str, payload: dict[str, Any]) -> builtins.list[dict[str, Any]]:
        ids = {str(value) for value in payload.get("drift_report_ids") or []}
        reports = self.repos.model_calibration_drift.list(model_version, limit=100)
        if ids:
            return [row for row in reports if str(row.get("drift_report_id")) in ids]
        return reports[:1]

    def _readiness(
        self,
        model: dict[str, Any],
        validation_reports: builtins.list[dict[str, Any]],
        calibrations: builtins.list[dict[str, Any]],
        drift_reports: builtins.list[dict[str, Any]],
        window_set: dict[str, Any] | None,
        payload: dict[str, Any],
    ) -> tuple[str, builtins.list[str], builtins.list[str]]:
        reasons: builtins.list[str] = []
        unresolved_warnings: builtins.list[str] = []
        status = "PASS"
        if not validation_reports:
            reasons.append("missing_validation_report")
            status = "REVIEW"
        if any(str(row.get("activation_decision")) == "rejected" for row in validation_reports):
            reasons.append("validation_rejected")
            status = "BLOCK"
        if not calibrations:
            reasons.append("missing_calibration_audit")
            status = "BLOCK" if payload.get("calibration_required") else self._max_status(status, "REVIEW")
        for audit in calibrations:
            unresolved_warnings.extend(str(item) for item in audit.get("calibration_warnings") or audit.get("warnings") or [])
            if audit.get("rejection_reasons"):
                reasons.extend(str(item) for item in audit.get("rejection_reasons") or [])
                status = self._max_status(status, "REVIEW")
        for drift in drift_reports:
            severity = str(drift.get("severity") or "INFO")
            unresolved_warnings.extend(str(item) for item in drift.get("drift_flags") or [])
            if severity == "BLOCKING":
                reasons.append("calibration_drift_blocking")
                status = "BLOCK"
            elif severity == "REVIEW":
                reasons.append("calibration_drift_requires_review")
                status = self._max_status(status, "REVIEW")
            elif severity == "WATCH":
                reasons.append("calibration_drift_watch")
                status = self._max_status(status, "WATCH")
        if window_set and (window_set.get("summary") or {}).get("failed_window_count"):
            reasons.append("replay_window_failures_present")
            status = self._max_status(status, "REVIEW")
        if model.get("warnings"):
            unresolved_warnings.extend(str(item) for item in model.get("warnings") or [])
        return status, sorted(set(reasons)), sorted(set(unresolved_warnings))

    def _max_status(self, current: str, candidate: str) -> str:
        order = {"PASS": 0, "WATCH": 1, "REVIEW": 2, "BLOCK": 3}
        return candidate if order[candidate] > order[current] else current


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
                {"simulation_type": replay.get("simulation_type"), "created_at": datetime.now(UTC).isoformat(), "filters": replay.get("config") or {}},
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
                {"simulation_type": replay.get("simulation_type"), "created_at": datetime.now(UTC).isoformat(), "filters": replay.get("config") or {}},
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
                {"simulation_type": replay.get("simulation_type"), "created_at": datetime.now(UTC).isoformat(), "filters": replay.get("config") or {}},
            ),
            self.repos.exports.record(
                "replay_metrics",
                "json",
                metrics_path,
                1,
                replay_run_id,
                {"simulation_type": replay.get("simulation_type"), "created_at": datetime.now(UTC).isoformat(), "filters": replay.get("config") or {}},
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

    def export_replay_aware_model_summary(self, model_version: str) -> dict[str, Any]:
        model = self.repos.model_runs.get(model_version)
        if model is None:
            return {"status": "not_found", "model_version": model_version}
        cells = self.repos.model_evidence_cells.list(model_version, limit=100_000)
        path = self.exporter.export_replay_aware_model_summary_xlsx(model, cells)
        record = self.repos.exports.record(
            "replay_aware_model_summary",
            "xlsx",
            path,
            len(cells),
            model_version,
            {"model_type": model.get("model_type"), "warnings": model.get("warnings") or []},
        )
        return {"status": "ok", "path": str(path), "rows": len(cells), "export": record}

    def export_evidence_cells(self, model_version: str, kind: str) -> dict[str, Any]:
        model = self.repos.model_runs.get(model_version)
        if model is None:
            return {"status": "not_found", "model_version": model_version}
        cells = self.repos.model_evidence_cells.list(model_version, limit=100_000)
        if kind == "csv":
            path = self.exporter.export_evidence_cells_csv(model_version, cells)
        elif kind == "xlsx":
            path = self.exporter.export_evidence_cells_xlsx(model_version, cells)
        else:
            raise ValueError("evidence export kind must be csv or xlsx")
        record = self.repos.exports.record(
            "model_evidence_cells",
            kind,
            path,
            len(cells),
            model_version,
            {"model_type": model.get("model_type")},
        )
        return {"status": "ok", "kind": kind, "path": str(path), "rows": len(cells), "export": record}

    def export_score_audits(self, model_version: str, kind: str) -> dict[str, Any]:
        model = self.repos.model_runs.get(model_version)
        if model is None:
            return {"status": "not_found", "model_version": model_version}
        audits = self.repos.candidate_score_audits.list(model_version, limit=100_000)
        if kind == "csv":
            path = self.exporter.export_score_audits_csv(model_version, audits)
        elif kind == "xlsx":
            path = self.exporter.export_score_audits_xlsx(model_version, audits)
        else:
            raise ValueError("score audit export kind must be csv or xlsx")
        record = self.repos.exports.record(
            "candidate_score_audits",
            kind,
            path,
            len(audits),
            model_version,
            {"model_type": model.get("model_type")},
        )
        return {"status": "ok", "kind": kind, "path": str(path), "rows": len(audits), "export": record}

    def export_replay_aware_validation(self, report_id: str | None, model_version: str | None = None) -> dict[str, Any]:
        report = None
        for item in self.repos.validation_reports.list_all(purpose=REPLAY_AWARE_VALIDATION_PURPOSE):
            if (report_id and item.get("report_id") == report_id) or (
                not report_id and (model_version is None or item.get("model_version") == model_version)
            ):
                report = item
                break
        if report is None:
            return {"status": "not_found", "report_id": report_id, "model_version": model_version}
        path = self.exporter.export_replay_aware_validation_xlsx(report)
        record = self.repos.exports.record(
            "replay_aware_validation",
            "xlsx",
            path,
            1,
            str(report.get("model_version") or model_version or report_id),
            {"validation_mode": REPLAY_AWARE_VALIDATION_MODE, "report_id": report.get("report_id")},
        )
        return {"status": "ok", "path": str(path), "rows": 1, "export": record}

    def export_calibration_audit(self, calibration_audit_id: str) -> dict[str, Any]:
        audit = self.repos.model_calibration_audits.get(calibration_audit_id)
        if audit is None:
            return {"status": "not_found", "calibration_audit_id": calibration_audit_id}
        bins = self.repos.model_calibration_audits.list_bins(calibration_audit_id, limit=100_000)
        path = self.exporter.export_calibration_audit_xlsx(audit, bins)
        record = self.repos.exports.record(
            "calibration_audit",
            "xlsx",
            path,
            len(bins),
            calibration_audit_id,
            {"model_version": audit.get("model_version"), "calibration_audit_id": calibration_audit_id},
        )
        return {"status": "ok", "path": str(path), "rows": len(bins), "export": record}

    def export_calibration_bins(self, calibration_audit_id: str, kind: str) -> dict[str, Any]:
        audit = self.repos.model_calibration_audits.get(calibration_audit_id)
        if audit is None:
            return {"status": "not_found", "calibration_audit_id": calibration_audit_id}
        bins = self.repos.model_calibration_audits.list_bins(calibration_audit_id, limit=100_000)
        if kind == "csv":
            path = self.exporter.export_calibration_bins_csv(calibration_audit_id, bins)
        elif kind == "xlsx":
            path = self.exporter.export_calibration_bins_xlsx(calibration_audit_id, bins)
        else:
            raise ValueError("calibration bin export kind must be csv or xlsx")
        record = self.repos.exports.record(
            "calibration_bins",
            kind,
            path,
            len(bins),
            calibration_audit_id,
            {"model_version": audit.get("model_version"), "calibration_audit_id": calibration_audit_id},
        )
        return {"status": "ok", "kind": kind, "path": str(path), "rows": len(bins), "export": record}

    def export_calibration_metrics(self, calibration_audit_id: str) -> dict[str, Any]:
        audit = self.repos.model_calibration_audits.get(calibration_audit_id)
        if audit is None:
            return {"status": "not_found", "calibration_audit_id": calibration_audit_id}
        path = self.exporter.export_calibration_metrics_json(audit)
        record = self.repos.exports.record(
            "calibration_metrics",
            "json",
            path,
            1,
            calibration_audit_id,
            {"model_version": audit.get("model_version"), "calibration_audit_id": calibration_audit_id},
        )
        return {"status": "ok", "path": str(path), "rows": 1, "export": record}

    def export_model_comparison(self, comparison_id: str) -> dict[str, Any]:
        comparison = self.repos.model_comparisons.get(comparison_id)
        if comparison is None:
            return {"status": "not_found", "comparison_id": comparison_id}
        path = self.exporter.export_model_comparison_xlsx(comparison)
        record = self.repos.exports.record(
            "model_comparison",
            "xlsx",
            path,
            len(comparison.get("models") or []),
            comparison_id,
            {"comparison_type": comparison.get("comparison_type"), "diagnostic_only": True},
        )
        return {"status": "ok", "path": str(path), "rows": len(comparison.get("models") or []), "export": record}

    def export_replay_window_set(self, window_set_id: str) -> dict[str, Any]:
        window_set = self.repos.replay_windows.get_set(window_set_id)
        if window_set is None:
            return {"status": "not_found", "window_set_id": window_set_id}
        results = self.repos.replay_windows.list_results(window_set_id, limit=100_000)
        path = self.exporter.export_replay_window_set_xlsx(window_set, results)
        record = self.repos.exports.record(
            "replay_window_set",
            "xlsx",
            path,
            len(results),
            window_set_id,
            {
                "window_set_id": window_set_id,
                "window_mode": window_set.get("window_mode"),
                "diagnostic_only": True,
                "config_hash": window_set.get("config_hash"),
            },
        )
        return {"status": "ok", "path": str(path), "rows": len(results), "export": record}

    def export_calibration_drift(self, drift_report_id: str, kind: str) -> dict[str, Any]:
        report = self.repos.model_calibration_drift.get(drift_report_id)
        if report is None:
            return {"status": "not_found", "drift_report_id": drift_report_id}
        windows = self.repos.model_calibration_drift.list_windows(drift_report_id, limit=100_000)
        if kind == "xlsx":
            path = self.exporter.export_calibration_drift_xlsx(report, windows)
        elif kind == "json":
            path = self.exporter.export_calibration_drift_json(report)
        else:
            raise ValueError("calibration drift export kind must be xlsx or json")
        record = self.repos.exports.record(
            "calibration_drift",
            kind,
            path,
            len(windows),
            drift_report_id,
            {
                "model_version": report.get("model_version"),
                "severity": report.get("severity"),
                "diagnostic_only": True,
            },
        )
        return {"status": "ok", "kind": kind, "path": str(path), "rows": len(windows), "export": record}

    def export_calibration_drift_windows(self, drift_report_id: str, kind: str) -> dict[str, Any]:
        report = self.repos.model_calibration_drift.get(drift_report_id)
        if report is None:
            return {"status": "not_found", "drift_report_id": drift_report_id}
        windows = self.repos.model_calibration_drift.list_windows(drift_report_id, limit=100_000)
        if kind == "csv":
            path = self.exporter.export_calibration_drift_windows_csv(drift_report_id, windows)
        elif kind == "xlsx":
            path = self.exporter.export_calibration_drift_windows_xlsx(drift_report_id, windows)
        else:
            raise ValueError("calibration drift windows export kind must be csv or xlsx")
        record = self.repos.exports.record(
            "calibration_drift_windows",
            kind,
            path,
            len(windows),
            drift_report_id,
            {"model_version": report.get("model_version"), "diagnostic_only": True},
        )
        return {"status": "ok", "kind": kind, "path": str(path), "rows": len(windows), "export": record}

    def export_model_review(self, review_report_id: str, kind: str) -> dict[str, Any]:
        report = self.repos.model_review_reports.get(review_report_id)
        if report is None:
            return {"status": "not_found", "review_report_id": review_report_id}
        if kind == "xlsx":
            path = self.exporter.export_model_review_xlsx(report)
        elif kind == "json":
            path = self.exporter.export_model_review_json(report)
        else:
            raise ValueError("model review export kind must be xlsx or json")
        record = self.repos.exports.record(
            "model_review",
            kind,
            path,
            1,
            review_report_id,
            {
                "model_version": report.get("model_version"),
                "readiness_status": report.get("readiness_status"),
                "diagnostic_only": True,
                "model_activation_unchanged": True,
            },
        )
        return {"status": "ok", "kind": kind, "path": str(path), "rows": 1, "export": record}

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
