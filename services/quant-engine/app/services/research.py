from __future__ import annotations

import builtins
import os
from datetime import date, datetime
from typing import Any

from app.backtesting.audit import git_commit, stable_hash
from app.config import get_settings
from app.data.symbols import normalize_symbols
from app.db.repositories import EXPECTED_ALEMBIC_REVISION, RepositoryRegistry
from app.models.replay_evidence import (
    REPLAY_AWARE_MODEL_TYPE,
    REPLAY_AWARE_VALIDATION_MODE,
    REPLAY_AWARE_VALIDATION_PURPOSE,
)
from app.services.fmp_pipeline import FMPLiveDataService
from app.services.workflows import (
    DataQualityService,
    ExportWorkflowService,
    ModelActivationService,
    ModelReviewReportService,
    ModelTrainingService,
    ReplayWindowOrchestrationService,
    ValidationWorkflowService,
)
from app.utils.time import UTC

PASSING_READINESS = {"PASS", "WATCH"}
BLOCKING_READINESS = {"BLOCK", "BLOCKING"}
NON_ACTIVATION_RECOMMENDATIONS = {"KEEP_CHAMPION", "REJECT_CHALLENGER", "BLOCK_ALL_CHANGES"}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _safe_config(payload: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, value in payload.items():
        lowered = key.lower()
        if any(part in lowered for part in ("api_key", "secret", "password", "token")):
            redacted[key] = "[REDACTED]"
        elif isinstance(value, dict):
            redacted[key] = _safe_config(value)
        elif isinstance(value, list):
            redacted[key] = [_safe_config(item) if isinstance(item, dict) else item for item in value]
        else:
            redacted[key] = value
    return redacted


class ChampionChallengerComparisonService:
    def __init__(self, repos: RepositoryRegistry) -> None:
        self.repos = repos

    def compare(
        self,
        champion_model_version: str | None,
        challenger_model_version: str | None,
        *,
        stale_window_status: dict[str, Any] | None = None,
        data_quality_summary: dict[str, Any] | None = None,
        comparison_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        champion = self.repos.model_runs.get(champion_model_version) if champion_model_version else None
        challenger = self.repos.model_runs.get(challenger_model_version) if challenger_model_version else None
        champion_metrics = self._model_metrics(champion)
        challenger_metrics = self._model_metrics(challenger)
        delta_metrics = {
            key: round(float(challenger_metrics.get(key) or 0.0) - float(champion_metrics.get(key) or 0.0), 6)
            for key in sorted(set(champion_metrics) | set(challenger_metrics))
            if isinstance(champion_metrics.get(key, 0), (int, float)) or isinstance(challenger_metrics.get(key, 0), (int, float))
        }
        better_flags = [f"{key}_improved" for key, value in delta_metrics.items() if value > 0 and key != "max_drawdown_r"]
        worse_flags = [f"{key}_deteriorated" for key, value in delta_metrics.items() if value < 0 and key != "max_drawdown_r"]
        if delta_metrics.get("max_drawdown_r", 0.0) < 0:
            better_flags.append("max_drawdown_improved")
        elif delta_metrics.get("max_drawdown_r", 0.0) > 0:
            worse_flags.append("max_drawdown_worse")

        gate_results = self._gate_results(challenger_model_version, stale_window_status, data_quality_summary, comparison_context)
        readiness_status = self._readiness(challenger, gate_results)
        recommended_action = self._recommended_action(champion, challenger, gate_results, better_flags, worse_flags, readiness_status)
        warnings = ["Champion/challenger comparison is diagnostic only and does not activate models."]
        if champion is None:
            warnings.append("champion_missing_minimum_gates_only")
        if challenger is None:
            warnings.append("challenger_missing")
        comparison = {
            "champion_model_version": champion_model_version,
            "challenger_model_version": challenger_model_version,
            "champion_metrics": champion_metrics,
            "challenger_metrics": challenger_metrics,
            "delta_metrics": delta_metrics,
            "challenger_better_flags": sorted(set(better_flags)),
            "challenger_worse_flags": sorted(set(worse_flags)),
            "gate_results": gate_results,
            "recommended_action": recommended_action,
            "readiness_status": readiness_status,
            "warnings": warnings,
            "comparison_context": comparison_context or {},
            "created_at": _now(),
        }
        saved = self.repos.champion_challenger_comparisons.save(comparison)
        return {"status": "ok", **saved}

    def get(self, comparison_id: str) -> dict[str, Any]:
        return self.repos.champion_challenger_comparisons.get(comparison_id) or {"status": "not_found", "comparison_id": comparison_id}

    def list(self, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        return {"comparisons": self.repos.champion_challenger_comparisons.list(limit=limit, offset=offset), "limit": limit, "offset": offset}

    def _model_metrics(self, model: dict[str, Any] | None) -> dict[str, Any]:
        if not model:
            return {}
        metrics = dict(model.get("metrics") or {})
        validation = dict(model.get("validation_metrics") or {})
        merged = {
            str(key): value
            for key, value in metrics.items()
            if isinstance(value, (int, float))
        } | {f"validation_{key}": value for key, value in validation.items() if isinstance(value, (int, float))}
        for key in ("average_r", "profit_factor", "max_drawdown_r", "observed_outcome_count", "total_trades"):
            merged.setdefault(key, 0.0)
        return merged

    def _gate_results(
        self,
        challenger_model_version: str | None,
        stale_window_status: dict[str, Any] | None,
        data_quality_summary: dict[str, Any] | None,
        comparison_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not challenger_model_version:
            return {"challenger_present": False, "all_passed": False}
        context = comparison_context or {}
        model = self.repos.model_runs.get(challenger_model_version)
        validation_ids = {str(value) for value in context.get("validation_report_ids") or [] if value}
        validations = self.repos.validation_reports.list_all()
        if validation_ids:
            validation_reports = [report for report in validations if str(report.get("report_id")) in validation_ids]
            latest_validation = validation_reports[0] if validation_reports else None
        else:
            latest_validation = (
                self.repos.validation_reports.latest(challenger_model_version, purpose=REPLAY_AWARE_VALIDATION_PURPOSE)
                or self.repos.validation_reports.latest(challenger_model_version)
            )
        calibration_ids = [str(value) for value in context.get("calibration_audit_ids") or [] if value]
        calibration = (
            self.repos.model_calibration_audits.get(calibration_ids[0])
            if calibration_ids
            else self.repos.model_calibration_audits.latest(challenger_model_version)
        )
        drift_ids = {str(value) for value in context.get("drift_report_ids") or [] if value}
        if drift_ids:
            drift = next(
                (report for report in self.repos.model_calibration_drift.list(challenger_model_version, limit=100) if str(report.get("drift_report_id")) in drift_ids),
                None,
            )
        else:
            drifts = self.repos.model_calibration_drift.list(challenger_model_version, limit=1)
            drift = drifts[0] if drifts else None
        review_ids = {str(value) for value in context.get("model_review_report_ids") or [] if value}
        if review_ids:
            review = next(
                (report for report in self.repos.model_review_reports.list(challenger_model_version, limit=100) if str(report.get("review_report_id")) in review_ids),
                None,
            )
        else:
            reviews = self.repos.model_review_reports.list(challenger_model_version, limit=1)
            review = reviews[0] if reviews else None
        gates = {
            "challenger_present": model is not None,
            "validation_pass": bool(latest_validation and latest_validation.get("activation_decision") == "accepted"),
            "calibration_pass": calibration is None or not calibration.get("rejection_reasons"),
            "drift_pass": drift is None or str(drift.get("severity") or "INFO") not in BLOCKING_READINESS,
            "model_review_pass": review is None or str(review.get("readiness_status") or "REVIEW") not in BLOCKING_READINESS,
            "stale_window_pass": not bool((stale_window_status or {}).get("dirty_window_count")),
            "data_quality_pass": not bool((data_quality_summary or {}).get("invalid_price_or_volume_count")),
            "validation_report_id": latest_validation.get("report_id") if latest_validation else None,
            "calibration_audit_id": calibration.get("calibration_audit_id") if calibration else None,
            "drift_report_id": drift.get("drift_report_id") if drift else None,
            "model_review_report_id": review.get("review_report_id") if review else None,
        }
        gates["all_passed"] = all(bool(gates[key]) for key in (
            "challenger_present",
            "validation_pass",
            "calibration_pass",
            "drift_pass",
            "model_review_pass",
            "stale_window_pass",
            "data_quality_pass",
        ))
        return gates

    def _readiness(self, challenger: dict[str, Any] | None, gates: dict[str, Any]) -> str:
        if challenger is None:
            return "REVIEW"
        if not gates.get("challenger_present") or not gates.get("validation_pass"):
            return "BLOCK"
        if not gates.get("calibration_pass") or not gates.get("drift_pass") or not gates.get("model_review_pass"):
            return "BLOCK"
        if not gates.get("stale_window_pass") or not gates.get("data_quality_pass"):
            return "REVIEW"
        return "PASS"

    def _recommended_action(
        self,
        champion: dict[str, Any] | None,
        challenger: dict[str, Any] | None,
        gates: dict[str, Any],
        better_flags: builtins.list[str],
        worse_flags: builtins.list[str],
        readiness_status: str,
    ) -> str:
        if challenger is None:
            return "KEEP_CHAMPION" if champion else "BLOCK_ALL_CHANGES"
        if readiness_status == "BLOCK":
            return "REJECT_CHALLENGER"
        if not gates.get("all_passed"):
            return "REVIEW_CHALLENGER"
        if champion is None:
            return "APPROVE_CHALLENGER_FOR_ACTIVATION"
        if worse_flags and len(worse_flags) >= len(better_flags):
            return "KEEP_CHAMPION"
        return "APPROVE_CHALLENGER_FOR_ACTIVATION"


class ModelProposalService:
    def __init__(self, repos: RepositoryRegistry) -> None:
        self.repos = repos

    def create_from_comparison(
        self,
        comparison: dict[str, Any],
        *,
        research_cycle_id: str | None = None,
        evidence_summary: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        readiness = str(comparison.get("readiness_status") or "REVIEW")
        recommended_action = str(comparison.get("recommended_action") or "REVIEW_CHALLENGER")
        if readiness in BLOCKING_READINESS or recommended_action == "REJECT_CHALLENGER":
            status = "REJECTED"
            rejection_reasons = ["comparison_gates_failed"]
        elif recommended_action == "APPROVE_CHALLENGER_FOR_ACTIVATION":
            status = "PROPOSED"
            rejection_reasons = []
        else:
            status = "REVIEW_REQUIRED"
            rejection_reasons = []
        proposal = {
            "research_cycle_id": research_cycle_id,
            "proposal_type": "challenger_model" if comparison.get("challenger_model_version") else "keep_champion",
            "status": status,
            "champion_model_version": comparison.get("champion_model_version"),
            "challenger_model_version": comparison.get("challenger_model_version"),
            "recommended_action": recommended_action,
            "readiness_status": readiness,
            "validation_report_ids": [comparison.get("gate_results", {}).get("validation_report_id")] if comparison.get("gate_results", {}).get("validation_report_id") else [],
            "calibration_audit_ids": [comparison.get("gate_results", {}).get("calibration_audit_id")] if comparison.get("gate_results", {}).get("calibration_audit_id") else [],
            "drift_report_ids": [comparison.get("gate_results", {}).get("drift_report_id")] if comparison.get("gate_results", {}).get("drift_report_id") else [],
            "model_review_report_ids": [comparison.get("gate_results", {}).get("model_review_report_id")] if comparison.get("gate_results", {}).get("model_review_report_id") else [],
            "comparison_ids": [comparison.get("comparison_id")] if comparison.get("comparison_id") else [],
            "evidence_summary": evidence_summary or {},
            "champion_metrics": comparison.get("champion_metrics") or {},
            "challenger_metrics": comparison.get("challenger_metrics") or {},
            "delta_metrics": comparison.get("delta_metrics") or {},
            "pass_fail_gates": comparison.get("gate_results") or {},
            "rejection_reasons": rejection_reasons,
            "approval_required": True,
            "created_at": _now(),
        }
        saved = self.repos.model_proposals.save(proposal)
        self._ledger(
            "PROPOSAL_CREATED",
            saved,
            "RECORDED",
            reason_codes=[recommended_action],
            evidence_refs=[{"comparison_id": comparison.get("comparison_id")}],
        )
        return {"status": "ok", **saved}

    def list(self, limit: int = 100, offset: int = 0, status: str | None = None) -> dict[str, Any]:
        return {"model_proposals": self.repos.model_proposals.list(limit=limit, offset=offset, status=status), "limit": limit, "offset": offset}

    def get(self, proposal_id: str) -> dict[str, Any]:
        return self.repos.model_proposals.get(proposal_id) or {"status": "not_found", "proposal_id": proposal_id}

    def approve(self, proposal_id: str, actor: str | None = None) -> dict[str, Any]:
        proposal = self.repos.model_proposals.get(proposal_id)
        if proposal is None:
            return {"status": "not_found", "proposal_id": proposal_id}
        if proposal.get("status") == "REJECTED":
            return self._blocked(proposal, "proposal_rejected", "PROPOSAL_APPROVED")
        if str(proposal.get("recommended_action")) in NON_ACTIVATION_RECOMMENDATIONS:
            return self._blocked(proposal, "proposal_not_recommended_for_activation", "PROPOSAL_APPROVED")
        if str(proposal.get("readiness_status")) in BLOCKING_READINESS:
            return self._blocked(proposal, "readiness_block", "PROPOSAL_APPROVED")
        saved = self.repos.model_proposals.save(
            proposal
            | {
                "status": "APPROVED_FOR_ACTIVATION",
                "approved_by": actor or "manual",
                "approved_at": _now(),
                "updated_at": _now(),
            }
        )
        self._ledger("PROPOSAL_APPROVED", saved, "APPROVED", actor=actor, reason_codes=["manual_approval_required"])
        return {"status": "ok", **saved}

    def reject(self, proposal_id: str, actor: str | None = None, reason_codes: builtins.list[str] | None = None) -> dict[str, Any]:
        proposal = self.repos.model_proposals.get(proposal_id)
        if proposal is None:
            return {"status": "not_found", "proposal_id": proposal_id}
        reasons = reason_codes or ["manual_rejection"]
        saved = self.repos.model_proposals.save(
            proposal
            | {
                "status": "REJECTED",
                "rejection_reasons": sorted(set(list(proposal.get("rejection_reasons") or []) + reasons)),
                "updated_at": _now(),
            }
        )
        self._ledger("PROPOSAL_REJECTED", saved, "REJECTED", actor=actor, reason_codes=reasons)
        return {"status": "ok", **saved}

    def activate(
        self,
        proposal_id: str,
        *,
        actor: str | None = None,
        confirm_manual_activation: bool = False,
        validation_mode: str | None = None,
        calibration_audit_required: bool = False,
    ) -> dict[str, Any]:
        proposal = self.repos.model_proposals.get(proposal_id)
        if proposal is None:
            return {"status": "not_found", "proposal_id": proposal_id}
        challenger = str(proposal.get("challenger_model_version") or "")
        active = self.repos.active_models.get_active(REPLAY_AWARE_MODEL_TYPE) or self.repos.active_models.get_active()
        self._ledger(
            "MODEL_ACTIVATION_REQUESTED",
            proposal,
            "REQUESTED",
            actor=actor,
            reason_codes=["explicit_proposal_activation"],
            evidence_refs=[{"proposal_id": proposal_id}],
            previous_model_version=active.get("model_version") if active else None,
        )
        if not confirm_manual_activation:
            return self._activation_blocked(proposal, "manual_confirmation_required", actor=actor)
        if proposal.get("status") == "REJECTED":
            return self._activation_blocked(proposal, "proposal_rejected", actor=actor)
        if str(proposal.get("recommended_action")) in NON_ACTIVATION_RECOMMENDATIONS:
            return self._activation_blocked(proposal, "proposal_not_recommended_for_activation", actor=actor)
        if proposal.get("status") != "APPROVED_FOR_ACTIVATION":
            return self._activation_blocked(proposal, "proposal_not_approved_for_activation", actor=actor)
        if str(proposal.get("readiness_status")) in BLOCKING_READINESS:
            return self._activation_blocked(proposal, "readiness_block", actor=actor)
        model = self.repos.model_runs.get(challenger)
        if model is None:
            return self._activation_blocked(proposal, "challenger_model_not_found", actor=actor)
        selected_validation_mode = validation_mode or (REPLAY_AWARE_VALIDATION_MODE if model.get("model_type") == REPLAY_AWARE_MODEL_TYPE else "label_derived")
        activation = ModelActivationService(self.repos).activate(
            challenger,
            validation_mode=selected_validation_mode,
            calibration_audit_required=calibration_audit_required,
        )
        if not activation.get("activated"):
            return self._activation_blocked(proposal, str(activation.get("reason") or "activation_gate_failed"), actor=actor, activation=activation)
        activation_id = stable_hash({"proposal_id": proposal_id, "model_version": challenger, "activated_at": _now()})[:24]
        saved = self.repos.model_proposals.save(
            proposal
            | {
                "status": "ACTIVATED",
                "activation_model_version": challenger,
                "activation_id": activation_id,
                "activation": activation,
                "updated_at": _now(),
            }
        )
        self._ledger(
            "MODEL_ACTIVATED",
            saved,
            "ACTIVATED",
            actor=actor,
            reason_codes=["explicit_manual_activation_confirmed"],
            evidence_refs=[{"activation_id": activation_id}, {"report_id": activation.get("report_id")}],
            previous_model_version=active.get("model_version") if active else None,
        )
        return saved | {"status": "ok", "proposal_status": saved.get("status"), "activation": activation}

    def _blocked(self, proposal: dict[str, Any], reason: str, decision_type: str) -> dict[str, Any]:
        self._ledger(decision_type, proposal, "BLOCKED", reason_codes=[reason])
        return {"status": "blocked", "reason": reason, "proposal_id": proposal.get("proposal_id")}

    def _activation_blocked(
        self,
        proposal: dict[str, Any],
        reason: str,
        *,
        actor: str | None = None,
        activation: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._ledger(
            "MODEL_ACTIVATION_BLOCKED",
            proposal,
            "BLOCKED",
            actor=actor,
            reason_codes=[reason],
            evidence_refs=[{"activation": activation}] if activation else [],
        )
        return {"status": "blocked", "reason": reason, "proposal_id": proposal.get("proposal_id"), "activation": activation}

    def _ledger(
        self,
        decision_type: str,
        proposal: dict[str, Any],
        decision_status: str,
        *,
        actor: str | None = None,
        reason_codes: builtins.list[str] | None = None,
        evidence_refs: builtins.list[dict[str, Any]] | None = None,
        previous_model_version: str | None = None,
    ) -> dict[str, Any]:
        return self.repos.model_decision_ledger.append(
            {
                "decision_type": decision_type,
                "research_cycle_id": proposal.get("research_cycle_id"),
                "proposal_id": proposal.get("proposal_id"),
                "model_version": proposal.get("challenger_model_version") or proposal.get("activation_model_version"),
                "previous_model_version": previous_model_version or proposal.get("champion_model_version"),
                "decision_status": decision_status,
                "reason_codes": reason_codes or [],
                "evidence_refs": evidence_refs or [],
                "actor": actor,
                "metadata": {"approval_required": proposal.get("approval_required", True)},
            }
        )


class ResearchCycleService:
    def __init__(self, repos: RepositoryRegistry) -> None:
        self.repos = repos
        self.settings = get_settings()

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        safe_payload = _safe_config(payload)
        selected_symbols = normalize_symbols(safe_payload.get("symbols") or self.settings.symbol_list)
        selected_intervals = [str(value) for value in safe_payload.get("intervals") or ["1min"]]
        cycle_date_value = safe_payload.get("cycle_date") or date.today().isoformat()
        cycle_date = date.fromisoformat(str(cycle_date_value)[:10])
        active = self.repos.active_models.get_active(REPLAY_AWARE_MODEL_TYPE) or self.repos.active_models.get_active()
        now = _now()
        cycle = {
            "cycle_date": cycle_date.isoformat(),
            "cycle_type": safe_payload.get("cycle_type") or "daily",
            "status": "CREATED",
            "symbols": selected_symbols,
            "intervals": selected_intervals,
            "start": safe_payload.get("start"),
            "end": safe_payload.get("end"),
            "session": safe_payload.get("session") or "rth",
            "data_cutoff_timestamp": safe_payload.get("data_cutoff_timestamp") or safe_payload.get("end"),
            "active_model_version": safe_payload.get("active_model_version") or (active or {}).get("model_version"),
            "challenger_model_version": safe_payload.get("challenger_model_version"),
            "window_set_ids": [],
            "replay_run_ids": safe_payload.get("replay_run_ids") or [],
            "counterfactual_replay_run_ids": safe_payload.get("counterfactual_replay_run_ids") or [],
            "portfolio_replay_run_ids": safe_payload.get("portfolio_replay_run_ids") or [],
            "sensitivity_run_ids": safe_payload.get("sensitivity_run_ids") or [],
            "calibration_audit_ids": safe_payload.get("calibration_audit_ids") or [],
            "drift_report_ids": safe_payload.get("drift_report_ids") or [],
            "model_review_report_ids": safe_payload.get("model_review_report_ids") or [],
            "comparison_ids": [],
            "proposal_ids": [],
            "summary": {"diagnostic_only": True, "model_activation_unchanged": True},
            "warnings": [],
            "config": safe_payload,
            "config_hash": stable_hash(safe_payload),
            "input_fingerprint": self._input_fingerprint(selected_symbols, selected_intervals, safe_payload.get("start"), safe_payload.get("end")),
            "git_commit": git_commit(),
            "database_revision": EXPECTED_ALEMBIC_REVISION,
            "persistence_backend": self.repos.info().get("persistence_backend"),
            "created_at": now,
            "updated_at": now,
        }
        saved = self.repos.research_cycles.save(cycle)
        self.repos.model_decision_ledger.append(
            {
                "decision_type": "CYCLE_CREATED",
                "research_cycle_id": saved["research_cycle_id"],
                "model_version": saved.get("active_model_version"),
                "decision_status": "CREATED",
                "reason_codes": ["controlled_research_cycle_created"],
                "evidence_refs": [{"config_hash": saved.get("config_hash")}],
                "metadata": {"cycle_type": saved.get("cycle_type")},
            }
        )
        if safe_payload.get("run_now"):
            return self.run(str(saved["research_cycle_id"]), safe_payload)
        return saved | {"status": "created", "cycle_status": saved.get("status")}

    def list(self, limit: int = 100, offset: int = 0, status: str | None = None) -> dict[str, Any]:
        return {"research_cycles": self.repos.research_cycles.list(limit=limit, offset=offset, status=status), "limit": limit, "offset": offset}

    def get(self, research_cycle_id: str) -> dict[str, Any]:
        return self.repos.research_cycles.get(research_cycle_id) or {"status": "not_found", "research_cycle_id": research_cycle_id}

    def dry_run(self, research_cycle_id: str) -> dict[str, Any]:
        cycle = self.repos.research_cycles.get(research_cycle_id)
        if cycle is None:
            return {"status": "not_found", "research_cycle_id": research_cycle_id}
        plan = self._plan(cycle)
        return {"status": "dry_run", "research_cycle_id": research_cycle_id, **plan}

    def run(self, research_cycle_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        cycle = self.repos.research_cycles.get(research_cycle_id)
        if cycle is None:
            return {"status": "not_found", "research_cycle_id": research_cycle_id}
        config = _safe_config((cycle.get("config") or {}) | (payload or {}))
        started = self.repos.research_cycles.save(cycle | {"status": "RUNNING", "started_at": _now(), "updated_at": _now()})
        plan = self._plan(started | {"config": config})
        if plan.get("blocked"):
            blocked = self.repos.research_cycles.save(
                started
                | {
                    "status": "BLOCKED",
                    "failed_reason": plan.get("block_reason"),
                    "summary": plan.get("summary") or {},
                    "warnings": plan.get("warnings") or [],
                    "stale_window_status": plan.get("stale_window_status") or {},
                    "completed_at": _now(),
                    "updated_at": _now(),
                }
            )
            self._cycle_ledger(blocked, "BLOCKED", [str(plan.get("block_reason") or "cycle_blocked")])
            return blocked | {"status": "blocked", "cycle_status": blocked.get("status"), "plan": plan}

        artifacts: builtins.list[dict[str, Any]] = []
        data_quality_report_id = stable_hash({"research_cycle_id": research_cycle_id, "type": "data_quality"})[:24]
        artifacts.append(
            self.repos.research_cycles.save_artifact(
                research_cycle_id,
                {
                    "artifact_type": "data_quality",
                    "source_id": data_quality_report_id,
                    "source_table": "inline_data_quality_report",
                    "payload": plan.get("data_quality_report"),
                },
            )
        )
        window_set_ids: builtins.list[str] = list(cycle.get("window_set_ids") or [])
        if config.get("window_set_config"):
            window_set = ReplayWindowOrchestrationService(self.repos).create(
                dict(config.get("window_set_config") or {})
                | {
                    "symbols": cycle.get("symbols") or [],
                    "intervals": cycle.get("intervals") or ["1min"],
                    "start": cycle.get("start"),
                    "end": cycle.get("end"),
                    "model_version": cycle.get("challenger_model_version") or cycle.get("active_model_version"),
                }
            )
            if window_set.get("window_set_id"):
                window_set_ids.append(str(window_set["window_set_id"]))
                artifacts.append(self.repos.research_cycles.save_artifact(research_cycle_id, {"artifact_type": "replay_window_set", "source_id": window_set["window_set_id"], "source_table": "replay_window_sets"}))

        challenger_model_version = str(config.get("challenger_model_version") or cycle.get("challenger_model_version") or "")
        if config.get("train_challenger") and not challenger_model_version:
            training = self._train_challenger(cycle, config)
            artifacts.append(self.repos.research_cycles.save_artifact(research_cycle_id, {"artifact_type": "challenger_training", "source_id": training.get("model_version"), "source_table": "model_runs", "payload": training}))
            if training.get("model_version"):
                challenger_model_version = str(training["model_version"])

        if challenger_model_version and config.get("validate_challenger"):
            validation = ValidationWorkflowService(self.repos).validate(
                model_version=challenger_model_version,
                validation_mode=config.get("validation_mode") or REPLAY_AWARE_VALIDATION_MODE,
                training_replay_run_ids=cycle.get("counterfactual_replay_run_ids") or cycle.get("replay_run_ids") or None,
                validation_replay_run_ids=cycle.get("counterfactual_replay_run_ids") or cycle.get("replay_run_ids") or None,
                calibration_audit_id=(cycle.get("calibration_audit_ids") or [None])[0],
            )
            artifacts.append(self.repos.research_cycles.save_artifact(research_cycle_id, {"artifact_type": "validation", "source_id": validation.get("report_id"), "source_table": "validation_reports", "payload": validation}))

        if challenger_model_version and config.get("require_model_review"):
            review = ModelReviewReportService(self.repos).create(
                challenger_model_version,
                {
                    "validation_report_ids": cycle.get("validation_report_ids") or [],
                    "calibration_audit_ids": cycle.get("calibration_audit_ids") or [],
                    "drift_report_ids": cycle.get("drift_report_ids") or [],
                    "window_set_id": window_set_ids[-1] if window_set_ids else None,
                },
            )
            if review.get("review_report_id"):
                cycle.setdefault("model_review_report_ids", []).append(review["review_report_id"])
                artifacts.append(self.repos.research_cycles.save_artifact(research_cycle_id, {"artifact_type": "model_review", "source_id": review["review_report_id"], "source_table": "model_review_reports"}))

        comparison = ChampionChallengerComparisonService(self.repos).compare(
            str(cycle.get("active_model_version") or "") or None,
            challenger_model_version or None,
            stale_window_status=plan.get("stale_window_status"),
            data_quality_summary=(plan.get("data_quality_report") or {}).get("summary"),
            comparison_context={
                "research_cycle_id": research_cycle_id,
                "validation_report_ids": config.get("validation_report_ids") or [],
                "calibration_audit_ids": cycle.get("calibration_audit_ids") or config.get("calibration_audit_ids") or [],
                "drift_report_ids": cycle.get("drift_report_ids") or config.get("drift_report_ids") or [],
                "model_review_report_ids": cycle.get("model_review_report_ids") or config.get("model_review_report_ids") or [],
                "replay_run_ids": cycle.get("replay_run_ids") or config.get("replay_run_ids") or [],
                "counterfactual_replay_run_ids": cycle.get("counterfactual_replay_run_ids") or config.get("counterfactual_replay_run_ids") or [],
                "portfolio_replay_run_ids": cycle.get("portfolio_replay_run_ids") or config.get("portfolio_replay_run_ids") or [],
            },
        )
        artifacts.append(self.repos.research_cycles.save_artifact(research_cycle_id, {"artifact_type": "champion_challenger_comparison", "source_id": comparison.get("comparison_id"), "source_table": "champion_challenger_comparisons"}))
        proposal = ModelProposalService(self.repos).create_from_comparison(
            comparison,
            research_cycle_id=research_cycle_id,
            evidence_summary={"plan": plan.get("summary"), "artifact_count": len(artifacts)},
        )
        artifacts.append(self.repos.research_cycles.save_artifact(research_cycle_id, {"artifact_type": "model_proposal", "source_id": proposal.get("proposal_id"), "source_table": "model_proposals"}))
        final_status = "COMPLETED" if proposal.get("status") != "REJECTED" else "BLOCKED"
        completed = self.repos.research_cycles.save(
            started
            | {
                "status": final_status,
                "challenger_model_version": challenger_model_version or None,
                "window_set_ids": window_set_ids,
                "comparison_ids": [comparison.get("comparison_id")] if comparison.get("comparison_id") else [],
                "proposal_ids": [proposal.get("proposal_id")] if proposal.get("proposal_id") else [],
                "data_quality_report_id": data_quality_report_id,
                "stale_window_status": plan.get("stale_window_status") or {},
                "summary": {
                    "status": final_status,
                    "diagnostic_only": True,
                    "model_activation_unchanged": True,
                    "artifact_count": len(artifacts),
                    "recommended_action": comparison.get("recommended_action"),
                    "proposal_status": proposal.get("status"),
                },
                "warnings": sorted(set(list(plan.get("warnings") or []) + ["Research cycle completed without model activation."])),
                "completed_at": _now(),
                "updated_at": _now(),
            }
        )
        self._cycle_ledger(completed, final_status, [str(comparison.get("recommended_action") or "cycle_completed")])
        if config.get("export_reports"):
            ExportWorkflowService(self.repos).export_research_cycle(research_cycle_id)
            if proposal.get("proposal_id"):
                ExportWorkflowService(self.repos).export_model_proposal(str(proposal["proposal_id"]), "xlsx")
        return completed | {
            "status": final_status.lower(),
            "cycle_status": completed.get("status"),
            "comparison": comparison,
            "proposal": proposal,
            "artifacts": artifacts,
        }

    def artifacts(self, research_cycle_id: str, limit: int = 500, offset: int = 0) -> dict[str, Any]:
        return {
            "research_cycle_id": research_cycle_id,
            "artifacts": self.repos.research_cycles.list_artifacts(research_cycle_id, limit=limit, offset=offset),
            "limit": limit,
            "offset": offset,
        }

    def export(self, research_cycle_id: str) -> dict[str, Any]:
        return ExportWorkflowService(self.repos).export_research_cycle(research_cycle_id)

    def _plan(self, cycle: dict[str, Any]) -> dict[str, Any]:
        config = cycle.get("config") or {}
        symbols = normalize_symbols(cycle.get("symbols") or config.get("symbols") or self.settings.symbol_list)
        intervals = [str(value) for value in cycle.get("intervals") or config.get("intervals") or ["1min"]]
        start = _parse_datetime(cycle.get("start"))
        end = _parse_datetime(cycle.get("end"))
        data_quality = DataQualityService(self.repos).report(symbols=symbols, intervals=intervals, start=start, end=end, session=str(cycle.get("session") or "rth"))
        stale_status = self.repos.pipeline_windows.status(symbols=symbols, intervals=intervals)
        freshness_report = FMPLiveDataService(self.repos).freshness_check(
            symbols=symbols,
            intervals=intervals,
            include_quotes=bool(config.get("require_quote_freshness", False)),
            require_reviewed_capabilities=bool(config.get("require_reviewed_capabilities_for_research", False)),
            persist=True,
            reference_time=end,
        )
        latest_bars = self._latest_bars(symbols, intervals)
        warnings = sorted(
            set(
                list(data_quality.get("warnings") or [])
                + [f"stale_{key}" for key in (stale_status.get("dirty_by_artifact") or {}).keys()]
                + [str(item) for item in (freshness_report.get("warnings") or [])]
            )
        )
        suggested_rebuild_steps = [
            f"rebuild_{artifact}"
            for artifact, count in sorted((stale_status.get("dirty_by_artifact") or {}).items())
            if int(count) > 0
        ]
        blocked = False
        block_reason = None
        if config.get("refresh_data") and not os.environ.get("FMP_API_KEY"):
            blocked = True
            block_reason = "fmp_api_key_required_for_refresh_data"
        elif stale_status.get("dirty_window_count") and not bool(config.get("allow_stale", False)):
            blocked = True
            block_reason = "stale_artifacts_present"
        elif freshness_report.get("status") in {"BLOCKED", "STALE"} and not bool(config.get("allow_stale", False)):
            blocked = True
            block_reason = f"data_freshness_{str(freshness_report.get('status')).lower()}"
        if freshness_report.get("status") in {"BLOCKED", "STALE"} and bool(config.get("allow_stale", False)):
            warnings.append(f"allow_stale_data_freshness_{str(freshness_report.get('status')).lower()}")
            warnings = sorted(set(warnings))
        summary = {
            "symbols": symbols,
            "intervals": intervals,
            "dirty_window_count": stale_status.get("dirty_window_count", 0),
            "missing_bar_window_count": (data_quality.get("summary") or {}).get("missing_bar_window_count", 0),
            "freshness_status": freshness_report.get("status"),
            "suggested_rebuild_step_count": len(suggested_rebuild_steps),
            "blocked": blocked,
            "block_reason": block_reason,
            "dry_run_only": True,
            "will_not_activate_model": True,
        }
        return {
            "summary": summary,
            "data_quality_report": data_quality,
            "freshness_report": freshness_report,
            "stale_window_status": stale_status,
            "latest_bars": latest_bars,
            "suggested_rebuild_steps": suggested_rebuild_steps,
            "warnings": warnings,
            "blocked": blocked,
            "block_reason": block_reason,
        }

    def _latest_bars(self, symbols: builtins.list[str], intervals: builtins.list[str]) -> builtins.list[dict[str, Any]]:
        rows = []
        for symbol in symbols:
            for interval in intervals:
                bars = self.repos.bars.query(symbols=[symbol], intervals=[interval])
                latest = max(bars, key=lambda bar: bar.timestamp_utc, default=None)
                rows.append(
                    {
                        "symbol": symbol,
                        "interval": interval,
                        "last_timestamp_utc": latest.timestamp_utc.isoformat() if latest else None,
                        "bar_count": len(bars),
                    }
                )
        return rows

    def _input_fingerprint(self, symbols: builtins.list[str], intervals: builtins.list[str], start: Any, end: Any) -> str:
        bars = self.repos.bars.query(symbols=symbols or None, intervals=intervals or None, start=_parse_datetime(start), end=_parse_datetime(end))
        return stable_hash(
            {
                "symbols": symbols,
                "intervals": intervals,
                "start": start,
                "end": end,
                "bar_count": len(bars),
                "latest_bar": max((bar.timestamp_utc.isoformat() for bar in bars), default=None),
            }
        )

    def _train_challenger(self, cycle: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        training = dict(config.get("challenger_training_config") or {})
        start = _parse_datetime(training.get("training_start") or cycle.get("start"))
        end = _parse_datetime(training.get("training_end") or cycle.get("end"))
        if start is None or end is None:
            return {"trained": False, "reason": "training_window_required"}
        return ModelTrainingService(self.repos).train(
            cycle.get("symbols") or None,
            start,
            end,
            int(training.get("min_samples") or 1),
            model_type=training.get("model_type") or REPLAY_AWARE_MODEL_TYPE,
            intervals=cycle.get("intervals") or ["1min"],
            replay_run_ids=cycle.get("replay_run_ids") or None,
            counterfactual_replay_run_ids=cycle.get("counterfactual_replay_run_ids") or None,
            portfolio_replay_run_ids=cycle.get("portfolio_replay_run_ids") or None,
            require_counterfactual=bool(training.get("require_counterfactual", False)),
            minimum_observed_outcomes=int(training.get("minimum_observed_outcomes") or 1),
            minimum_cell_sample_size=int(training.get("minimum_cell_sample_size") or 1),
            scoring_config=training.get("scoring_config") or {},
            activation_criteria=training.get("activation_criteria") or {},
            validation_mode=training.get("validation_mode") or REPLAY_AWARE_VALIDATION_MODE,
            allow_stale=bool(config.get("allow_stale", False)),
        )

    def _cycle_ledger(self, cycle: dict[str, Any], status: str, reason_codes: builtins.list[str]) -> dict[str, Any]:
        return self.repos.model_decision_ledger.append(
            {
                "decision_type": "CYCLE_COMPLETED",
                "research_cycle_id": cycle.get("research_cycle_id"),
                "model_version": cycle.get("challenger_model_version") or cycle.get("active_model_version"),
                "previous_model_version": cycle.get("active_model_version"),
                "decision_status": status,
                "reason_codes": reason_codes,
                "evidence_refs": [
                    {"comparison_ids": cycle.get("comparison_ids") or []},
                    {"proposal_ids": cycle.get("proposal_ids") or []},
                ],
                "metadata": {"model_activation_unchanged": True},
            }
        )


class ResearchStatusService:
    def __init__(self, repos: RepositoryRegistry) -> None:
        self.repos = repos

    def status(self) -> dict[str, Any]:
        latest_cycle = self.repos.research_cycles.latest()
        latest_proposal = self.repos.model_proposals.latest()
        active = self.repos.active_models.get_active(REPLAY_AWARE_MODEL_TYPE) or self.repos.active_models.get_active()
        active_version = active.get("model_version") if active else None
        review = None
        drift = None
        if active_version:
            reviews = self.repos.model_review_reports.list(str(active_version), limit=1)
            review = reviews[0] if reviews else None
            drifts = self.repos.model_calibration_drift.list(str(active_version), limit=1)
            drift = drifts[0] if drifts else None
        stale = self.repos.pipeline_windows.status()
        data_quality = DataQualityService(self.repos).report()
        proposals = self.repos.model_proposals.list(limit=100)
        pending = [proposal for proposal in proposals if proposal.get("status") in {"PROPOSED", "REVIEW_REQUIRED", "APPROVED_FOR_ACTIVATION"}]
        blocked = [proposal for proposal in proposals if proposal.get("status") in {"REJECTED"} or proposal.get("readiness_status") in BLOCKING_READINESS]
        scheduler = self.repos.scheduler_jobs.status_summary()
        return {
            "status": "ok",
            "latest_research_cycle": latest_cycle,
            "latest_model_proposal": latest_proposal,
            "latest_scheduler_job": scheduler.get("latest_job"),
            "queued_scheduler_jobs": scheduler.get("queued_jobs", 0),
            "failed_scheduler_jobs": scheduler.get("failed_jobs", 0),
            "active_model_version": active_version,
            "active_model_review_status": review.get("readiness_status") if review else None,
            "latest_calibration_drift_severity": drift.get("severity") if drift else None,
            "stale_windows_summary": {
                "status": stale.get("status"),
                "dirty_window_count": stale.get("dirty_window_count"),
                "dirty_by_artifact": stale.get("dirty_by_artifact"),
            },
            "data_quality_summary": data_quality.get("summary"),
            "pending_proposals": pending,
            "blocked_proposals": blocked,
            "last_successful_api_smoke_timestamp": None,
            "warnings": [
                "Research status is read-only and contains no secrets.",
                "No broker execution or order routing is available.",
            ],
        }
