from __future__ import annotations

import csv
import json
import os
from collections import Counter
from datetime import date, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from app.backtesting.audit import CANDIDATE_CONFIG_VERSION
from app.backtesting.replay import SIMULATION_TYPE_COUNTERFACTUAL, SIMULATION_TYPE_REPLAY
from app.config import get_settings
from app.data.symbols import normalize_symbols
from app.db.repositories import RepositoryRegistry
from app.features.engine import FEATURE_SET_VERSION
from app.labels.engine import LABEL_CONFIG_VERSION, LabelingEngine
from app.quant.types import CandidateSignal
from app.services.fmp_pipeline import (
    DEFAULT_SEED_INTERVALS,
    DEFAULT_SEED_SYMBOLS,
    FMPLiveDataService,
)
from app.services.research import ResearchCycleService
from app.services.workflows import BacktestService, FeatureBuildService
from app.signals.candidates import NO_TRADE, CandidateSignalEngine
from app.utils.time import UTC

DEFAULT_RESEARCH_SYMBOLS = ["SPY", "QQQ", "AAPL", "NVDA"]
DEFAULT_FEATURE_INTERVALS = ["1min", "5min", "15min", "1day"]
DEFAULT_INTRADAY_INTERVALS = ["1min", "5min", "15min"]
PHASE19_EXPORT_PREFIX = "phase19"


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _parse_dt(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _iso(value: Any) -> str | None:
    parsed = _parse_dt(value)
    return parsed.isoformat() if parsed else None


def _text(value: Any) -> str:
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def _sanitize(payload: Any) -> Any:
    secret_values = {
        value
        for value in (os.environ.get("FMP_API_KEY"), os.environ.get("DATABASE_URL"))
        if value
    }
    if isinstance(payload, dict):
        output: dict[str, Any] = {}
        for key, value in payload.items():
            lowered = str(key).lower()
            if any(part in lowered for part in ("api_key", "secret", "password", "token", "credential", "database_url")):
                output[str(key)] = "[REDACTED]"
            else:
                output[str(key)] = _sanitize(value)
        return output
    if isinstance(payload, list):
        return [_sanitize(item) for item in payload]
    if isinstance(payload, tuple):
        return [_sanitize(item) for item in payload]
    if isinstance(payload, datetime):
        return payload.isoformat()
    if isinstance(payload, date):
        return payload.isoformat()
    if isinstance(payload, str) and payload in secret_values:
        return "[REDACTED]"
    return payload


class ArtifactReadinessService:
    def __init__(self, repos: RepositoryRegistry) -> None:
        self.repos = repos
        self.candidates = CandidateSignalEngine()
        self.labels = LabelingEngine(max_hold_bars=get_settings().max_hold_minutes, target_r=get_settings().target_r)

    def dirty_window_audit(
        self,
        *,
        symbols: list[str] | None = None,
        intervals: list[str] | None = None,
        export: bool = False,
        kind: str = "json",
    ) -> dict[str, Any]:
        selected_symbols, selected_intervals = self._scope(symbols=symbols, intervals=intervals, include_daily=True)
        dirty_rows = [
            self._audit_window(row)
            for row in self.repos.pipeline_windows.list_dirty(symbols=selected_symbols, intervals=selected_intervals)
        ]
        dirty_by_artifact = dict(Counter(str(row.get("artifact_type") or "unknown") for row in dirty_rows))
        report = {
            "status": "ok",
            "generated_at": _now(),
            "phase": "19",
            "symbols": selected_symbols,
            "intervals": selected_intervals,
            "dirty_window_count": len(dirty_rows),
            "dirty_by_artifact": dirty_by_artifact,
            "dirty_windows": dirty_rows,
            "artifact_summaries": self._artifact_summaries(selected_symbols, selected_intervals),
            "recommended_rebuild_order": self._recommended_rebuild_order(dirty_by_artifact),
            "persistence": self.repos.info(),
            "no_secrets": True,
            "no_broker_execution": True,
            "model_activation_unchanged": True,
        }
        if export:
            report["export"] = self.export_report("dirty_window_audit", report, dirty_rows, kind=kind)
        return report

    def rebuild_features(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = dict(payload or {})
        symbols, intervals = self._scope_from_payload(payload, include_daily=True)
        start = _parse_dt(payload.get("start"))
        end = _parse_dt(payload.get("end"))
        dirty_before = self.repos.pipeline_windows.list_dirty("features", symbols=symbols, intervals=intervals)
        bars = self.repos.bars.query(symbols=symbols, intervals=intervals, start=start, end=end)
        if not bars:
            return self._blocked("no_persisted_bars_for_feature_rebuild", symbols, intervals)
        build = FeatureBuildService(self.repos).build(symbols=symbols, intervals=intervals, start=start, end=end)
        cleaned = self._clean_windows(dirty_before, {"rebuild_step": "features", "features_written": build.get("features_written")})
        dirty_after = self.repos.pipeline_windows.list_dirty("features", symbols=symbols, intervals=intervals)
        report = {
            "status": "ok",
            "generated_at": _now(),
            "step": "rebuild_features",
            "symbols": symbols,
            "intervals": intervals,
            "start": start.isoformat() if start else None,
            "end": end.isoformat() if end else None,
            "bars_read": len(bars),
            "features_written": int(build.get("features_written") or 0),
            "dirty_windows_before": [self._audit_window(row) for row in dirty_before],
            "dirty_windows_cleared": len(cleaned),
            "dirty_windows_after_count": len(dirty_after),
            "feature_summary": self._feature_summary(self.repos.features.query(symbols=symbols, intervals=intervals, start=start, end=end)),
            "build_windows": cleaned,
            "no_fmp_calls": True,
            "no_secrets": True,
            "model_activation_unchanged": True,
        }
        if payload.get("export"):
            report["export"] = self.export_report("feature_rebuild_report", report, report["build_windows"], kind=str(payload.get("kind") or "json"))
        return report

    def rebuild_candidates(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = dict(payload or {})
        symbols, intervals = self._scope(
            symbols=payload.get("symbols"),
            intervals=payload.get("intervals") or DEFAULT_INTRADAY_INTERVALS,
            include_daily=True,
        )
        start = _parse_dt(payload.get("start"))
        end = _parse_dt(payload.get("end"))
        dirty_features = self.repos.pipeline_windows.list_dirty("features", symbols=symbols, intervals=intervals)
        if dirty_features and not bool(payload.get("allow_dirty_inputs", False)):
            return self._blocked("features_dirty_for_candidate_rebuild", symbols, intervals, dirty_features)
        dirty_before = self.repos.pipeline_windows.list_dirty("candidates", symbols=symbols, intervals=intervals)
        features = self.repos.features.query(symbols=symbols, intervals=intervals, start=start, end=end)
        candidates: list[Any] = []
        for feature in features:
            candidates.extend(self.candidates.detect(feature))
        written = self.repos.candidate_signals.upsert_many(candidates)
        cleaned = self._clean_windows(dirty_before, {"rebuild_step": "candidates", "candidates_written": written})
        persisted = self.repos.candidate_signals.query(symbols=symbols, intervals=intervals, start=start, end=end)
        dirty_after = self.repos.pipeline_windows.list_dirty("candidates", symbols=symbols, intervals=intervals)
        report = {
            "status": "ok",
            "generated_at": _now(),
            "step": "rebuild_candidates",
            "symbols": symbols,
            "intervals": intervals,
            "start": start.isoformat() if start else None,
            "end": end.isoformat() if end else None,
            "features_read": len(features),
            "candidates_written": int(written),
            "candidate_summary": self._candidate_summary(persisted),
            "dirty_windows_before": [self._audit_window(row) for row in dirty_before],
            "dirty_windows_cleared": len(cleaned),
            "dirty_windows_after_count": len(dirty_after),
            "build_windows": cleaned,
            "source": "persisted_features",
            "no_future_labels_used": True,
            "no_fmp_calls": True,
            "no_secrets": True,
            "model_activation_unchanged": True,
        }
        if payload.get("export"):
            report["export"] = self.export_report("candidate_rebuild_report", report, persisted, kind=str(payload.get("kind") or "json"))
        return report

    def rebuild_labels(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = dict(payload or {})
        symbols, intervals = self._scope(
            symbols=payload.get("symbols"),
            intervals=payload.get("intervals") or DEFAULT_INTRADAY_INTERVALS,
            include_daily=True,
        )
        start = _parse_dt(payload.get("start"))
        end = _parse_dt(payload.get("end"))
        dirty_inputs = self.repos.pipeline_windows.list_dirty("candidates", symbols=symbols, intervals=intervals)
        if dirty_inputs and not bool(payload.get("allow_dirty_inputs", False)):
            return self._blocked("candidates_dirty_for_label_rebuild", symbols, intervals, dirty_inputs)
        dirty_before = self.repos.pipeline_windows.list_dirty("labels", symbols=symbols, intervals=intervals)
        bars = self.repos.bars.query(symbols=symbols, intervals=intervals, start=start, end=end)
        features = self.repos.features.query(symbols=symbols, intervals=intervals, start=start, end=end)
        candidates = self.repos.candidate_signals.query(symbols=symbols, intervals=intervals, start=start, end=end)
        labels = self._labels_from_persisted_candidates(bars, features, candidates)
        written = self.repos.labels.upsert_many(labels)
        cleaned = self._clean_windows(dirty_before, {"rebuild_step": "labels", "labels_written": written})
        persisted = self.repos.labels.query(symbols=symbols, intervals=intervals, start=start, end=end)
        dirty_after = self.repos.pipeline_windows.list_dirty("labels", symbols=symbols, intervals=intervals)
        actionable_candidates = [row for row in candidates if str(row.get("side")) != NO_TRADE]
        report = {
            "status": "ok",
            "generated_at": _now(),
            "step": "rebuild_labels",
            "symbols": symbols,
            "intervals": intervals,
            "start": start.isoformat() if start else None,
            "end": end.isoformat() if end else None,
            "bars_read": len(bars),
            "features_read": len(features),
            "candidate_rows_read": len(candidates),
            "actionable_candidate_rows": len(actionable_candidates),
            "labels_written": int(written),
            "unobserved_or_skipped_candidates_not_labeled": max(0, len(actionable_candidates) - int(written)),
            "label_summary": self._label_summary(persisted),
            "dirty_windows_before": [self._audit_window(row) for row in dirty_before],
            "dirty_windows_cleared": len(cleaned),
            "dirty_windows_after_count": len(dirty_after),
            "build_windows": cleaned,
            "entry_assumption": "next_bar_open",
            "future_bars_used_only_for_outcomes": True,
            "no_skipped_or_unobserved_as_losses": True,
            "no_fmp_calls": True,
            "no_secrets": True,
            "model_activation_unchanged": True,
        }
        if payload.get("export"):
            report["export"] = self.export_report("label_rebuild_report", report, [_label_payload(label) for label in persisted], kind=str(payload.get("kind") or "json"))
        return report

    def rebuild_replay(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = dict(payload or {})
        symbols = normalize_symbols(payload.get("symbols") or DEFAULT_RESEARCH_SYMBOLS)
        intervals = [str(item) for item in payload.get("intervals") or ["1min"]]
        unsupported_intervals = [interval for interval in intervals if interval not in DEFAULT_INTRADAY_INTERVALS]
        not_applicable_cleaned: list[dict[str, Any]] = []
        if unsupported_intervals:
            not_applicable_cleaned = self._clean_windows(
                self.repos.pipeline_windows.list_dirty("replay", symbols=symbols, intervals=unsupported_intervals),
                {
                    "rebuild_step": "replay_not_applicable",
                    "reason": "candidate_market_replay_is_intraday_only",
                },
            )
        intervals = [interval for interval in intervals if interval in DEFAULT_INTRADAY_INTERVALS]
        if not intervals:
            report = {
                "status": "ok",
                "generated_at": _now(),
                "step": "run_replay",
                "symbols": symbols,
                "intervals": unsupported_intervals,
                "replay_skipped_not_applicable": True,
                "reason": "candidate_market_replay_is_intraday_only",
                "dirty_windows_cleared": len(not_applicable_cleaned),
                "dirty_windows_after_count": len(self.repos.pipeline_windows.list_dirty("replay", symbols=symbols, intervals=unsupported_intervals)),
                "build_windows": not_applicable_cleaned,
                "no_fmp_calls": True,
                "no_secrets": True,
                "model_activation_unchanged": True,
            }
            if payload.get("export"):
                report["export"] = self.export_report("replay_report", report, not_applicable_cleaned, kind=str(payload.get("kind") or "json"))
            return report
        start = _parse_dt(payload.get("start"))
        end = _parse_dt(payload.get("end"))
        if start is None or end is None:
            inferred = self._common_bar_window(symbols, intervals)
            start = start or inferred.get("start")
            end = end or inferred.get("end")
        if start is None or end is None:
            return self._blocked("no_persisted_bars_for_replay_window", symbols, intervals)
        dirty_inputs = self.repos.pipeline_windows.list_dirty("features", symbols=symbols, intervals=intervals)
        dirty_inputs += self.repos.pipeline_windows.list_dirty("candidates", symbols=symbols, intervals=intervals)
        if dirty_inputs and not bool(payload.get("allow_dirty_inputs", False)):
            return self._blocked("features_or_candidates_dirty_for_replay", symbols, intervals, dirty_inputs)
        dirty_before = self.repos.pipeline_windows.list_dirty("replay", symbols=symbols, intervals=intervals)
        base_payload = {
            "symbols": symbols,
            "intervals": intervals,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "session": str(payload.get("session") or "rth"),
            "max_hold_minutes": int(payload.get("max_hold_minutes") or 60),
            "target_2_r": float(payload.get("target_2_r") or 1.5),
            "allow_stale": False,
            "minimum_reward_risk": float(payload.get("minimum_reward_risk") or 1.0),
        }
        portfolio = BacktestService(self.repos).run_replay(
            base_payload
            | {
                "replay_purpose": "portfolio_execution",
                "simulation_type": SIMULATION_TYPE_REPLAY,
                "enforce_portfolio_constraints": True,
                "enforce_symbol_overlap": True,
            }
        )
        counterfactual = BacktestService(self.repos).run_replay(
            base_payload
            | {
                "replay_purpose": "model_training_counterfactual",
                "simulation_type": SIMULATION_TYPE_COUNTERFACTUAL,
                "allow_overlapping_trades": True,
                "enforce_portfolio_constraints": False,
                "enforce_symbol_overlap": False,
                "counterfactual_include_invalid_candidates": True,
            }
        )
        replay_runs = [row for row in (portfolio, counterfactual) if row.get("replay_run_id")]
        cleaned = []
        if replay_runs:
            cleaned = self._clean_windows(
                dirty_before,
                {
                    "rebuild_step": "replay",
                    "portfolio_replay_run_id": portfolio.get("replay_run_id"),
                    "counterfactual_replay_run_id": counterfactual.get("replay_run_id"),
                },
            )
        dirty_after = self.repos.pipeline_windows.list_dirty("replay", symbols=symbols, intervals=intervals)
        status = "ok" if replay_runs and not any(row.get("status") == "error" for row in (portfolio, counterfactual)) else "blocked"
        report = {
            "status": status,
            "generated_at": _now(),
            "step": "run_replay",
            "symbols": symbols,
            "intervals": intervals,
            "not_applicable_intervals": unsupported_intervals,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "portfolio_replay": self._compact_replay(portfolio),
            "counterfactual_replay": self._compact_replay(counterfactual),
            "replay_run_ids": [str(row["replay_run_id"]) for row in replay_runs],
            "dirty_windows_before": [self._audit_window(row) for row in dirty_before],
            "dirty_windows_cleared": len(cleaned) + len(not_applicable_cleaned),
            "dirty_windows_after_count": len(dirty_after),
            "build_windows": [*cleaned, *not_applicable_cleaned],
            "candidate_quality_evidence_only": bool(counterfactual.get("replay_run_id")),
            "no_fmp_calls": True,
            "no_secrets": True,
            "model_activation_unchanged": True,
        }
        if payload.get("export"):
            report["export"] = self.export_report("replay_report", report, replay_runs, kind=str(payload.get("kind") or "json"))
        return report

    def freshness_recheck(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = dict(payload or {})
        default_symbols = normalize_symbols(payload.get("default_symbols") or DEFAULT_SEED_SYMBOLS)
        default_intervals = [str(item) for item in payload.get("default_intervals") or DEFAULT_SEED_INTERVALS]
        research_symbols = normalize_symbols(payload.get("research_symbols") or payload.get("symbols") or DEFAULT_RESEARCH_SYMBOLS)
        research_intervals = [str(item) for item in payload.get("research_intervals") or payload.get("intervals") or ["1min"]]
        window = self._common_bar_window(research_symbols, research_intervals)
        service = FMPLiveDataService(self.repos)
        capability_ready = service.capability_review_summary().get("status") == "READY"
        default_report = service.freshness_check(
            symbols=default_symbols,
            intervals=default_intervals,
            include_quotes=bool(payload.get("include_quotes", True)),
            require_reviewed_capabilities=bool(payload.get("require_reviewed_capabilities", False)),
            persist=True,
        )
        research_report = service.freshness_check(
            symbols=research_symbols,
            intervals=research_intervals,
            include_quotes=bool(payload.get("require_quote_freshness", False)),
            require_reviewed_capabilities=capability_ready,
            persist=True,
            reference_time=window.get("end"),
        )
        report = {
            "status": "ok",
            "generated_at": _now(),
            "default_scope_freshness": default_report,
            "research_scope_freshness": research_report,
            "research_window": {key: value.isoformat() if isinstance(value, datetime) else value for key, value in window.items()},
            "capability_review_ready": capability_ready,
            "default_scope_uses_wall_clock": True,
            "research_scope_uses_window_end_reference_time": True,
            "no_secrets": True,
            "model_activation_unchanged": True,
        }
        if payload.get("export"):
            report["export"] = self.export_report("freshness_report", report, [default_report, research_report], kind=str(payload.get("kind") or "json"))
        return report

    def research_cycle_dry_run(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = dict(payload or {})
        symbols = normalize_symbols(payload.get("symbols") or DEFAULT_RESEARCH_SYMBOLS)
        intervals = [str(item) for item in payload.get("intervals") or ["1min"]]
        start = _parse_dt(payload.get("start"))
        end = _parse_dt(payload.get("end"))
        if start is None or end is None:
            inferred = self._common_bar_window(symbols, intervals)
            start = start or inferred.get("start")
            end = end or inferred.get("end")
        if start is None or end is None:
            return self._blocked("no_persisted_bars_for_research_cycle", symbols, intervals)
        capability_ready = FMPLiveDataService(self.repos).capability_review_summary().get("status") == "READY"
        cycle_payload = {
            "cycle_date": str(payload.get("cycle_date") or "2026-07-03"),
            "cycle_type": "phase19_real_data_dry_run",
            "symbols": symbols,
            "intervals": intervals,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "session": str(payload.get("session") or "rth"),
            "allow_stale": False,
            "refresh_data": False,
            "require_quote_freshness": bool(payload.get("require_quote_freshness", False)),
            "require_reviewed_capabilities_for_research": capability_ready,
            "train_challenger": False,
            "validate_challenger": False,
            "export_reports": False,
            "run_now": False,
        }
        service = ResearchCycleService(self.repos)
        created = service.create(cycle_payload)
        strict = service.dry_run(str(created["research_cycle_id"])) if created.get("research_cycle_id") else created
        report = {
            "status": "ok" if not strict.get("blocked") else "blocked",
            "generated_at": _now(),
            "strict": True,
            "allow_stale": False,
            "refresh_data": False,
            "created_cycle": created,
            "strict_dry_run": strict,
            "diagnostic_dry_run": None,
            "model_activation_unchanged": True,
            "no_broker_execution": True,
            "no_secrets": True,
        }
        if strict.get("blocked") and bool(payload.get("run_diagnostic_if_blocked", False)):
            diagnostic_created = service.create(cycle_payload | {"allow_stale": True, "cycle_type": "phase19_diagnostic_allow_stale"})
            diagnostic = service.dry_run(str(diagnostic_created["research_cycle_id"]))
            report["diagnostic_dry_run"] = {
                "label": "diagnostic_allow_stale_true",
                "created_cycle": diagnostic_created,
                "dry_run": diagnostic,
            }
        if payload.get("export"):
            report["export"] = self.export_report("research_cycle_dry_run_report", report, [strict], kind=str(payload.get("kind") or "json"))
        return report

    def run_readiness_sequence(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = dict(payload or {})
        symbols = normalize_symbols(payload.get("symbols") or DEFAULT_SEED_SYMBOLS)
        intraday_intervals = [str(item) for item in payload.get("intervals") or DEFAULT_INTRADAY_INTERVALS]
        feature_intervals = [*intraday_intervals, *([] if "1day" in intraday_intervals else ["1day"])]
        export = bool(payload.get("export", False))
        audit_before = self.dirty_window_audit(symbols=symbols, intervals=feature_intervals, export=export)
        features = self.rebuild_features({"symbols": symbols, "intervals": feature_intervals, "export": export})
        candidates = self.rebuild_candidates({"symbols": symbols, "intervals": feature_intervals, "export": export})
        labels = self.rebuild_labels({"symbols": symbols, "intervals": feature_intervals, "export": export})
        replay = self.rebuild_replay(
            {
                "symbols": payload.get("replay_symbols") or DEFAULT_RESEARCH_SYMBOLS,
                "intervals": payload.get("replay_intervals") or ["1min"],
                "export": export,
            }
        )
        freshness = self.freshness_recheck({"export": export})
        research = self.research_cycle_dry_run({"export": export, "run_diagnostic_if_blocked": bool(payload.get("run_diagnostic_if_blocked", False))})
        audit_after = self.dirty_window_audit(symbols=symbols, intervals=feature_intervals, export=export)
        return {
            "status": "ok",
            "generated_at": _now(),
            "audit_before": audit_before,
            "feature_rebuild": features,
            "candidate_rebuild": candidates,
            "label_rebuild": labels,
            "replay_report": replay,
            "freshness_report": freshness,
            "research_cycle_dry_run": research,
            "audit_after": audit_after,
            "no_fmp_calls_for_rebuilds": True,
            "model_activation_unchanged": True,
            "no_broker_execution": True,
            "no_secrets": True,
        }

    def export_report(
        self,
        export_type: str,
        payload: dict[str, Any],
        rows: list[Any] | None = None,
        *,
        kind: str = "json",
    ) -> dict[str, Any]:
        safe_payload = _sanitize(payload)
        safe_rows = _sanitize(rows or [])
        settings = get_settings()
        settings.exports_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
        digest = sha256(json.dumps(safe_payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:12]
        normalized_kind = "csv" if kind == "csv" else "json"
        path = settings.exports_dir / f"{PHASE19_EXPORT_PREFIX}_{export_type}_{timestamp}_{digest}.{normalized_kind}"
        if normalized_kind == "csv":
            self._write_csv(path, safe_rows)
        else:
            path.write_text(json.dumps(safe_payload, indent=2, sort_keys=True, default=str, allow_nan=False), encoding="utf-8")
        record = self.repos.exports.record(
            f"{PHASE19_EXPORT_PREFIX}_{export_type}",
            normalized_kind,
            path,
            len(safe_rows),
            payload.get("research_cycle_id") or payload.get("replay_run_id"),
            {"phase": "19", "no_secrets": True, "model_activation_unchanged": True},
        )
        return {"status": "ok", "path": str(path), "rows": len(safe_rows), "export": record}

    def _scope_from_payload(self, payload: dict[str, Any], *, include_daily: bool) -> tuple[list[str], list[str]]:
        return self._scope(
            symbols=payload.get("symbols"),
            intervals=payload.get("intervals"),
            include_daily=include_daily,
        )

    def _scope(
        self,
        *,
        symbols: Any = None,
        intervals: Any = None,
        include_daily: bool,
    ) -> tuple[list[str], list[str]]:
        symbol_values = [part.strip() for part in symbols.split(",")] if isinstance(symbols, str) else symbols
        interval_values = [part.strip() for part in intervals.split(",")] if isinstance(intervals, str) else intervals
        selected_symbols = normalize_symbols(symbol_values or DEFAULT_SEED_SYMBOLS)
        defaults = DEFAULT_FEATURE_INTERVALS if include_daily else DEFAULT_INTRADAY_INTERVALS
        selected_intervals = [str(item) for item in interval_values or defaults]
        if not include_daily:
            selected_intervals = [item for item in selected_intervals if item != "1day"]
        return selected_symbols, selected_intervals

    def _audit_window(self, row: dict[str, Any]) -> dict[str, Any]:
        artifact = str(row.get("artifact_type") or "unknown")
        return {
            "build_window_id": row.get("build_window_id"),
            "artifact_type": artifact,
            "symbol": row.get("symbol"),
            "interval": row.get("interval"),
            "session_date": row.get("session_date"),
            "status": "dirty" if row.get("dirty") else "clean",
            "dirty": bool(row.get("dirty")),
            "stale": bool(row.get("dirty")),
            "stale_reason": row.get("stale_reason"),
            "start": row.get("start"),
            "end": row.get("end"),
            "version": row.get("version"),
            "source": (row.get("payload") or {}).get("source") or "pipeline_build_windows",
            "recommended_rebuild": self._recommended_action(artifact),
            "updated_at": row.get("updated_at"),
        }

    def _recommended_action(self, artifact: str) -> str:
        return {
            "features": "rebuild_features",
            "candidates": "rebuild_candidates",
            "labels": "rebuild_labels",
            "replay": "run_replay",
        }.get(artifact, "inspect")

    def _recommended_rebuild_order(self, dirty_by_artifact: dict[str, int]) -> list[str]:
        order = []
        for artifact, action in (
            ("features", "rebuild_features"),
            ("candidates", "rebuild_candidates"),
            ("labels", "rebuild_labels"),
            ("replay", "run_replay"),
        ):
            if int(dirty_by_artifact.get(artifact) or 0) > 0:
                order.append(action)
        return order

    def _clean_windows(self, dirty_rows: list[dict[str, Any]], metadata: dict[str, Any]) -> list[dict[str, Any]]:
        cleaned = []
        for row in dirty_rows:
            cleaned.append(
                self.repos.pipeline_windows.mark_window_built(
                    artifact_type=str(row["artifact_type"]),
                    symbol=str(row["symbol"]),
                    interval=str(row["interval"]),
                    session_date=str(row.get("session_date") or ""),
                    version=str(row["version"]),
                    start=row.get("start"),
                    end=row.get("end"),
                    metadata=metadata,
                )
            )
        return cleaned

    def _artifact_summaries(self, symbols: list[str], intervals: list[str]) -> dict[str, Any]:
        bars = self.repos.bars.query(symbols=symbols, intervals=intervals)
        features = self.repos.features.query(symbols=symbols, intervals=intervals)
        candidates = self.repos.candidate_signals.query(symbols=symbols, intervals=intervals)
        labels = self.repos.labels.query(symbols=symbols, intervals=intervals)
        quotes = self.repos.quote_snapshots.list(symbols=symbols, limit=1000)
        freshness_reports = self.repos.data_freshness_reports.list(provider="fmp", limit=25)
        replay_runs = self.repos.replays.list_runs()
        research_cycles = self.repos.research_cycles.list(limit=25)
        return {
            "bars": self._bar_summary(bars),
            "quote_snapshots": self._quote_summary(quotes),
            "features": self._feature_summary(features),
            "candidate_signals": self._candidate_summary(candidates),
            "labels": self._label_summary(labels),
            "replay_runs": {
                "count": len(replay_runs),
                "latest_created_at": max((str(row.get("created_at") or "") for row in replay_runs), default=None),
                "simulation_types": dict(Counter(str(row.get("simulation_type") or "unknown") for row in replay_runs)),
            },
            "data_freshness_reports": {
                "count": len(freshness_reports),
                "latest_status": freshness_reports[0].get("status") if freshness_reports else None,
                "latest_generated_at": freshness_reports[0].get("generated_at") if freshness_reports else None,
            },
            "research_cycles": {
                "count": len(research_cycles),
                "latest_status": research_cycles[0].get("status") if research_cycles else None,
                "latest_created_at": research_cycles[0].get("created_at") if research_cycles else None,
            },
        }

    def _bar_summary(self, bars: list[Any]) -> dict[str, Any]:
        return {
            "count": len(bars),
            "first_timestamp_utc": min((bar.timestamp_utc.isoformat() for bar in bars), default=None),
            "last_timestamp_utc": max((bar.timestamp_utc.isoformat() for bar in bars), default=None),
            "by_interval": dict(Counter(str(bar.interval) for bar in bars)),
            "by_source": dict(Counter(str(bar.source) for bar in bars)),
        }

    def _quote_summary(self, quotes: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "count": len(quotes),
            "latest_timestamp_utc": max((str(row.get("timestamp_utc") or "") for row in quotes), default=None),
            "by_symbol": dict(Counter(str(row.get("symbol") or "unknown") for row in quotes)),
            "by_endpoint": dict(Counter(str(row.get("endpoint_key") or "unknown") for row in quotes)),
        }

    def _feature_summary(self, features: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "count": len(features),
            "first_timestamp_utc": min((_iso(row.get("timestamp_utc") or row.get("timestamp")) or "" for row in features), default=None),
            "last_timestamp_utc": max((_iso(row.get("timestamp_utc") or row.get("timestamp")) or "" for row in features), default=None),
            "by_interval": dict(Counter(str(row.get("interval") or "1min") for row in features)),
            "versions": dict(Counter(str(row.get("feature_set_version") or FEATURE_SET_VERSION) for row in features)),
        }

    def _candidate_summary(self, candidates: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "count": len(candidates),
            "actionable_count": len([row for row in candidates if str(row.get("side")) != NO_TRADE]),
            "by_side": dict(Counter(str(row.get("side") or "unknown") for row in candidates)),
            "by_setup_type": dict(Counter(str(row.get("setup_type") or "unknown") for row in candidates)),
            "version": CANDIDATE_CONFIG_VERSION,
        }

    def _label_summary(self, labels: list[Any]) -> dict[str, Any]:
        return {
            "count": len(labels),
            "by_outcome": dict(Counter(_text(label.outcome) for label in labels)),
            "by_side": dict(Counter(_text(label.side) for label in labels)),
            "by_setup_type": dict(Counter(str(label.setup_type) for label in labels)),
            "version": LABEL_CONFIG_VERSION,
        }

    def _labels_from_persisted_candidates(
        self,
        bars: list[Any],
        features: list[dict[str, Any]],
        candidates: list[dict[str, Any]],
    ) -> list[Any]:
        bars_by_group: dict[tuple[str, str], list[Any]] = {}
        for bar in sorted(bars, key=lambda item: (item.symbol, item.interval, item.timestamp_utc)):
            bars_by_group.setdefault((bar.symbol, bar.interval), []).append(bar)
        feature_by_key = {
            (
                str(feature["symbol"]),
                str(feature.get("interval") or "1min"),
                _parse_dt(feature.get("timestamp_utc") or feature.get("timestamp")),
            ): feature
            for feature in features
        }
        index_by_group = {
            key: {bar.timestamp_utc: index for index, bar in enumerate(group)}
            for key, group in bars_by_group.items()
        }
        labels = []
        blocked_until: dict[tuple[str, str], datetime] = {}
        for row in sorted(candidates, key=lambda item: (_iso(item.get("timestamp_utc") or item.get("timestamp")) or "", str(item.get("symbol") or ""))):
            if str(row.get("side")) == NO_TRADE:
                continue
            candidate = self._candidate_from_row(row)
            group_key = (candidate.symbol, candidate.interval)
            timestamp = candidate.timestamp_utc
            index = index_by_group.get(group_key, {}).get(timestamp)
            feature = feature_by_key.get((candidate.symbol, candidate.interval, timestamp))
            if index is None or feature is None:
                continue
            block_key = (candidate.symbol, candidate.setup_type)
            blocked_time = blocked_until.get(block_key, datetime.min.replace(tzinfo=timestamp.tzinfo))
            if timestamp <= blocked_time:
                continue
            label = self.labels._label_candidate(bars_by_group.get(group_key, []), index, feature, candidate)
            if label is None:
                continue
            labels.append(label)
            if label.exit_timestamp_utc is not None:
                blocked_until[block_key] = label.exit_timestamp_utc
        return labels

    def _candidate_from_row(self, row: dict[str, Any]) -> CandidateSignal:
        timestamp_utc = _parse_dt(row.get("timestamp_utc") or row.get("timestamp")) or datetime.now(UTC)
        timestamp_et = _parse_dt(row.get("timestamp_et")) or timestamp_utc
        session_date_value = row.get("session_date")
        if isinstance(session_date_value, date):
            session_date = session_date_value
        elif session_date_value:
            session_date = date.fromisoformat(str(session_date_value)[:10])
        else:
            session_date = timestamp_et.date()
        return CandidateSignal(
            symbol=str(row.get("symbol")),
            interval=str(row.get("interval") or "1min"),
            timestamp_utc=timestamp_utc,
            timestamp_et=timestamp_et,
            session_date=session_date,
            side=str(row.get("side")),
            setup_type=str(row.get("setup_type") or "unknown"),
            entry_context=dict(row.get("entry_context") or {}),
            invalidation_context=dict(row.get("invalidation_context") or {}),
            required_feature_names=tuple(str(item) for item in row.get("required_feature_names") or []),
            reason_codes=tuple(str(item) for item in row.get("reason_codes") or []),
            warning_codes=tuple(str(item) for item in row.get("warning_codes") or []),
        )

    def _common_bar_window(self, symbols: list[str], intervals: list[str]) -> dict[str, datetime | None]:
        starts = []
        ends = []
        for symbol in symbols:
            for interval in intervals:
                rows = self.repos.bars.query(symbols=[symbol], intervals=[interval])
                if not rows:
                    continue
                starts.append(min(row.timestamp_utc for row in rows))
                ends.append(max(row.timestamp_utc for row in rows))
        if not starts or not ends:
            return {"start": None, "end": None}
        start = max(starts)
        end = min(ends)
        if start >= end:
            all_rows = self.repos.bars.query(symbols=symbols, intervals=intervals)
            return {
                "start": min((row.timestamp_utc for row in all_rows), default=None),
                "end": max((row.timestamp_utc for row in all_rows), default=None),
            }
        return {"start": start, "end": end}

    def _compact_replay(self, replay: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": replay.get("status", "ok" if replay.get("replay_run_id") else "unknown"),
            "reason": replay.get("reason"),
            "replay_run_id": replay.get("replay_run_id"),
            "simulation_type": replay.get("simulation_type"),
            "start": replay.get("start"),
            "end": replay.get("end"),
            "symbols": replay.get("symbols"),
            "intervals": replay.get("intervals"),
            "summary_metrics": replay.get("summary_metrics") or replay.get("metrics"),
            "warnings": replay.get("warnings") or [],
            "stale_window_status": replay.get("stale_window_status"),
        }

    def _blocked(
        self,
        reason: str,
        symbols: list[str],
        intervals: list[str],
        dirty_rows: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return {
            "status": "blocked",
            "reason": reason,
            "symbols": symbols,
            "intervals": intervals,
            "dirty_windows": [self._audit_window(row) for row in dirty_rows or []],
            "no_fmp_calls": True,
            "no_secrets": True,
            "model_activation_unchanged": True,
        }

    def _write_csv(self, path: Path, rows: list[Any]) -> None:
        dict_rows = [row if isinstance(row, dict) else {"value": row} for row in rows]
        columns = sorted({key for row in dict_rows for key in row.keys()}) or ["value"]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            for row in dict_rows:
                writer.writerow({key: self._csv_cell(row.get(key)) for key in columns})

    def _csv_cell(self, value: Any) -> Any:
        if isinstance(value, (dict, list, tuple)):
            return json.dumps(value, default=str, sort_keys=True)
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        return value


def _label_payload(label: Any) -> dict[str, Any]:
    if hasattr(label, "model_dump"):
        return label.model_dump(mode="json")
    if hasattr(label, "__dict__"):
        payload = dict(label.__dict__)
        return _sanitize(payload)
    return {"value": str(label)}
