from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256
from math import isfinite, sqrt
from statistics import mean, median, pstdev
from typing import Any

from app.backtesting.audit import stable_hash
from app.backtesting.replay import SIMULATION_TYPE_REPLAY
from app.schemas.market import Side
from app.utils.time import UTC

REPLAY_AWARE_MODEL_TYPE = "replay_aware_baseline"
REPLAY_AWARE_SCHEMA_VERSION = "model.v3.replay_aware_baseline"
REPLAY_AWARE_VALIDATION_MODE = "replay_aware_walk_forward"
REPLAY_AWARE_VALIDATION_PURPOSE = "replay_aware_validation"
SCORING_CONFIG_VERSION = "replay_meta_scorer.v1"

UNOBSERVED_SKIP_REASONS = {
    "overlapping_trade",
    "portfolio_trade_limit",
    "cooldown_active",
    "duplicate_candidate",
    "missing_entry_bar",
    "no_future_bars",
    "stale_data",
}
SUPPRESSION_SKIP_REASONS = {
    "invalid_risk_plan",
    "insufficient_context",
    "insufficient_reward_risk",
    "regime_filter_block",
    "outside_session",
    "data_quality_block",
}
CRITICAL_DATA_QUALITY_FLAGS = {
    "zero_or_negative_price",
    "high_below_low",
    "timestamp_utc_missing_or_invalid",
    "timezone_missing_or_ambiguous",
}
SEVERE_DIVERGENCE_FLAGS = {
    "average_r_disagreement",
    "win_rate_disagreement",
    "trade_count_disagreement",
    "material_disagreement",
}

HIERARCHY: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("symbol_side_setup_regime_time", ("symbol", "side", "setup_type", "market_regime", "time_bucket")),
    ("symbol_side_setup_regime", ("symbol", "side", "setup_type", "market_regime")),
    ("symbol_side_setup", ("symbol", "side", "setup_type")),
    ("side_setup_regime", ("side", "setup_type", "market_regime")),
    ("side_setup", ("side", "setup_type")),
    ("side_global", ("side",)),
)


@dataclass(frozen=True)
class EvidenceCube:
    cells: tuple[dict[str, Any], ...]
    by_key: dict[str, dict[str, Any]] = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "by_key", {str(cell["cell_key"]): cell for cell in self.cells})

    def resolve(
        self,
        candidate: dict[str, Any],
        feature: dict[str, Any] | None = None,
        *,
        shrinkage_strength: float = 20.0,
    ) -> dict[str, Any]:
        candidate_dims = dimensions_for_candidate(candidate, feature)
        matched: list[dict[str, Any]] = []
        for hierarchy_level, dims in HIERARCHY:
            key = cell_key(hierarchy_level, {name: candidate_dims.get(name, "unknown") for name in dims})
            cell = self.by_key.get(key)
            if cell is not None:
                matched.append(cell)
        if not matched:
            return {
                "has_evidence": False,
                "metrics": {},
                "cells_used": [],
                "evidence_cell_keys_used": [],
                "candidate_dimensions": candidate_dims,
            }

        blended: dict[str, float] = {}
        # Blend from broadest to most specific so small exact cells shrink toward parent evidence.
        for cell in reversed(matched):
            metrics = dict(cell.get("metrics") or {})
            observed = float(cell.get("observed_outcome_count") or metrics.get("observed_outcome_count") or 0.0)
            weight = observed / (observed + max(shrinkage_strength, 0.0)) if observed > 0 else 0.0
            if not blended:
                weight = 1.0
            for key in (
                "average_r",
                "median_r",
                "expectancy_r",
                "profit_factor",
                "max_drawdown_r",
                "win_rate",
                "loss_rate",
                "same_bar_ambiguity_rate",
                "sensitivity_robustness_score",
                "lower_bound_r",
                "average_mfe_r",
                "average_mae_r",
            ):
                value = _finite_float(metrics.get(key), 0.0)
                if key not in blended:
                    blended[key] = value
                else:
                    blended[key] = blended[key] * (1.0 - weight) + value * weight
        max_observed = max(int(cell.get("observed_outcome_count") or 0) for cell in matched)
        max_sample = max(int(cell.get("sample_size") or 0) for cell in matched)
        fragility_flags = sorted(
            {
                str(flag)
                for cell in matched
                for flag in (cell.get("fragility_flags") or (cell.get("metrics") or {}).get("fragility_flags") or [])
            }
        )
        divergence_flags = sorted(
            {
                str(flag)
                for cell in matched
                for flag in (cell.get("metrics") or {}).get("label_vs_replay_divergence_flags") or []
            }
        )
        stale_warnings = sorted(
            {
                str(flag)
                for cell in matched
                for flag in (cell.get("metrics") or {}).get("stale_window_warnings") or []
            }
        )
        blended["observed_outcome_count"] = float(max_observed)
        blended["sample_size"] = float(max_sample)
        blended["confidence_sample_size"] = float(sum(int(cell.get("observed_outcome_count") or 0) for cell in matched))
        blended["sensitivity_robustness_score"] = min(
            [_finite_float((cell.get("metrics") or {}).get("sensitivity_robustness_score"), 1.0) for cell in matched]
            or [1.0]
        )
        return {
            "has_evidence": True,
            "metrics": blended,
            "fragility_flags": fragility_flags,
            "label_vs_replay_divergence_flags": divergence_flags,
            "stale_window_warnings": stale_warnings,
            "cells_used": matched,
            "evidence_cell_keys_used": [str(cell["cell_key"]) for cell in matched],
            "candidate_dimensions": candidate_dims,
        }


class CandidateOutcomeDatasetBuilder:
    def build(
        self,
        *,
        replay_runs: list[dict[str, Any]],
        trades_by_run: dict[str, list[dict[str, Any]]],
        features: list[dict[str, Any]] | None = None,
        candidates: list[dict[str, Any]] | None = None,
        sensitivities_by_run: dict[str, list[dict[str, Any]]] | None = None,
        comparisons_by_run: dict[str, list[dict[str, Any]]] | None = None,
        training_start: datetime | None = None,
        training_end: datetime | None = None,
        allow_stale: bool = False,
    ) -> list[dict[str, Any]]:
        features_by_key = {_feature_key(feature): feature for feature in features or []}
        candidates_by_id = {str(candidate.get("candidate_id")): candidate for candidate in candidates or [] if candidate.get("candidate_id")}
        sensitivities_by_run = sensitivities_by_run or {}
        comparisons_by_run = comparisons_by_run or {}
        rows: list[dict[str, Any]] = []
        for replay_run in replay_runs:
            replay_run_id = str(replay_run.get("replay_run_id") or "")
            if not replay_run_id or replay_run.get("simulation_type") != SIMULATION_TYPE_REPLAY:
                continue
            stale_status = _stale_status(replay_run)
            if stale_status.get("status") != "clean" and not allow_stale:
                raise ValueError(f"stale_replay_run:{replay_run_id}")
            sensitivity = (sensitivities_by_run.get(replay_run_id) or [None])[0]
            comparison_flags = _comparison_flags(comparisons_by_run.get(replay_run_id) or [])
            config = dict(replay_run.get("config") or {})
            for trade in trades_by_run.get(replay_run_id, []):
                timestamp = _parse_datetime(trade.get("signal_timestamp_utc"))
                if training_start and timestamp < training_start:
                    continue
                if training_end and timestamp > training_end:
                    continue
                symbol = str(trade.get("symbol") or "").upper()
                interval = str(trade.get("interval") or "1min")
                feature = features_by_key.get((symbol, interval, timestamp))
                candidate = candidates_by_id.get(str(trade.get("candidate_id") or "")) or {}
                skip_reason = trade.get("skip_reason")
                observed = self._is_observed(trade)
                suppression_eligible = str(skip_reason or "") in SUPPRESSION_SKIP_REASONS
                row = {
                    "candidate_id": trade.get("candidate_id"),
                    "replay_run_id": replay_run_id,
                    "symbol": symbol,
                    "interval": interval,
                    "side": str(trade.get("side") or candidate.get("side") or "UNKNOWN"),
                    "setup_type": str(trade.get("setup_type") or candidate.get("setup_type") or "unknown"),
                    "signal_timestamp_utc": timestamp.isoformat(),
                    "session_date": _session_date(trade, feature, timestamp),
                    "time_bucket": str(trade.get("time_bucket") or (feature or {}).get("time_bucket") or "unknown"),
                    "market_regime": str(trade.get("market_regime") or (feature or {}).get("market_regime") or "unknown"),
                    "ticker_regime": (feature or {}).get("ticker_regime"),
                    "feature_set_version": (feature or {}).get("feature_set_version") or replay_run.get("feature_set_version"),
                    "candidate_config_version": replay_run.get("candidate_config_version"),
                    "replay_config_hash": replay_run.get("config_hash"),
                    "input_fingerprint": replay_run.get("input_fingerprint"),
                    "entry_mode": config.get("entry_mode"),
                    "stop_mode": config.get("stop_mode"),
                    "target_mode": config.get("target_mode"),
                    "slippage_bps": _finite_float(trade.get("slippage_bps") or config.get("slippage_bps"), 0.0),
                    "spread_bps": _finite_float(trade.get("spread_bps") or config.get("spread_bps"), 0.0),
                    "same_bar_policy": config.get("same_bar_stop_target_policy") or trade.get("ambiguity_policy"),
                    "intrabar_policy": config.get("intrabar_path_policy"),
                    "status": str(trade.get("status") or "UNKNOWN"),
                    "skip_reason": skip_reason,
                    "observed_outcome": observed,
                    "not_observed_outcome": not observed,
                    "suppression_eligible_skip": suppression_eligible,
                    "entry_price": trade.get("entry_price"),
                    "stop_price": trade.get("stop_price"),
                    "target_1": trade.get("target_1"),
                    "target_2": trade.get("target_2"),
                    "target_3": trade.get("target_3"),
                    "exit_price": trade.get("exit_price"),
                    "exit_reason": trade.get("exit_reason"),
                    "realized_r": _finite_float(trade.get("realized_r"), 0.0) if observed else None,
                    "mfe_r": _finite_float(trade.get("mfe_r"), 0.0) if observed else None,
                    "mae_r": _finite_float(trade.get("mae_r"), 0.0) if observed else None,
                    "same_bar_ambiguous": bool(trade.get("same_bar_ambiguous")),
                    "bars_held": int(trade.get("bars_held") or 0),
                    "minutes_held": _finite_float(trade.get("minutes_held"), 0.0),
                    "signal_score_at_candidate_time": trade.get("signal_score"),
                    "expected_r_at_candidate_time": trade.get("expected_r"),
                    "feature_snapshot": _selected_feature_snapshot(feature or {}),
                    "sensitivity_run_id": (sensitivity or {}).get("sensitivity_run_id") if sensitivity else None,
                    "sensitivity_robustness_score": _finite_float((sensitivity or {}).get("robustness_score"), 1.0),
                    "sensitivity_fragility_flags": list((sensitivity or {}).get("fragility_flags") or []),
                    "label_vs_replay_divergence_flags": comparison_flags,
                    "stale_window_status": stale_status,
                    "data_quality_flags": list((feature or {}).get("data_quality_flags") or []),
                    "candidate_payload": candidate,
                }
                rows.append(row)
        return sorted(rows, key=lambda row: (str(row["signal_timestamp_utc"]), str(row["symbol"]), str(row["setup_type"])))

    def _is_observed(self, trade: dict[str, Any]) -> bool:
        status = str(trade.get("status") or "").upper()
        skip_reason = str(trade.get("skip_reason") or "")
        if status == "TAKEN":
            return True
        if status == "SKIPPED" and skip_reason in UNOBSERVED_SKIP_REASONS:
            return False
        if status == "SKIPPED":
            return False
        return False


class EvidenceCubeBuilder:
    def build(
        self,
        rows: list[dict[str, Any]],
        *,
        minimum_cell_sample_size: int = 5,
    ) -> EvidenceCube:
        buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
        dimensions_by_key: dict[str, dict[str, str]] = {}
        level_by_key: dict[str, str] = {}
        for row in rows:
            dims_all = dimensions_for_candidate(row, row.get("feature_snapshot") if isinstance(row.get("feature_snapshot"), dict) else None)
            for hierarchy_level, dims in HIERARCHY:
                dimensions = {name: str(dims_all.get(name) or "unknown") for name in dims}
                key = cell_key(hierarchy_level, dimensions)
                buckets[key].append(row)
                dimensions_by_key[key] = dimensions
                level_by_key[key] = hierarchy_level
        cells = []
        for key, bucket in sorted(buckets.items()):
            metrics = summarize_outcome_rows(bucket, minimum_cell_sample_size=minimum_cell_sample_size)
            cells.append(
                {
                    "cell_key": key,
                    "dimensions": dimensions_by_key[key],
                    "hierarchy_level": level_by_key[key],
                    "parent_cell_key": self._parent_key(level_by_key[key], dimensions_by_key[key]),
                    "metrics": metrics,
                    "sample_size": metrics["sample_size"],
                    "observed_outcome_count": metrics["observed_outcome_count"],
                    "average_r": metrics["average_r"],
                    "median_r": metrics["median_r"],
                    "profit_factor": metrics["profit_factor"],
                    "max_drawdown_r": metrics["max_drawdown_r"],
                    "robustness_score": metrics["sensitivity_robustness_score"],
                    "fragility_flags": metrics["fragility_flags"],
                    "evidence_quality_grade": metrics["evidence_quality_grade"],
                    "created_at": datetime.now(UTC).isoformat(),
                }
            )
        return EvidenceCube(tuple(cells))

    def _parent_key(self, hierarchy_level: str, dimensions: dict[str, str]) -> str | None:
        levels = [level for level, _dims in HIERARCHY]
        index = levels.index(hierarchy_level)
        if index + 1 >= len(HIERARCHY):
            return None
        parent_level, parent_dims = HIERARCHY[index + 1]
        return cell_key(parent_level, {name: dimensions.get(name, "unknown") for name in parent_dims})


class ReplayAwareMetaScorer:
    def __init__(self, evidence_cube: EvidenceCube, config: dict[str, Any] | None = None) -> None:
        self.evidence_cube = evidence_cube
        self.config = default_scoring_config(config)

    def score(
        self,
        candidate: dict[str, Any],
        feature: dict[str, Any] | None = None,
        *,
        model_version: str = "unversioned-replay-aware",
    ) -> dict[str, Any]:
        resolution = self.evidence_cube.resolve(
            candidate,
            feature,
            shrinkage_strength=float(self.config["shrinkage_strength"]),
        )
        suppression_reasons: list[str] = []
        positive_reason_codes: list[str] = []
        warning_codes: list[str] = []
        penalties = {
            "fragility_penalty": 0.0,
            "stale_data_penalty": 0.0,
            "label_vs_replay_divergence_penalty": 0.0,
            "ambiguity_penalty": 0.0,
        }
        if not resolution["has_evidence"]:
            suppression_reasons.append("no_evidence")
            return self._output(
                candidate,
                model_version,
                score=0.0,
                expected_r=0.0,
                grade="NO_TRADE",
                action="SUPPRESS",
                components=self._empty_components(),
                penalties=penalties,
                suppression_reasons=suppression_reasons,
                positive_reason_codes=positive_reason_codes,
                warning_codes=warning_codes,
                evidence_cell_keys_used=[],
            )

        metrics = dict(resolution["metrics"])
        observed = int(metrics.get("observed_outcome_count") or 0)
        sample_size = int(metrics.get("sample_size") or 0)
        average_r = _finite_float(metrics.get("average_r"), 0.0)
        lower_bound = _finite_float(metrics.get("lower_bound_r"), average_r)
        profit_factor = _finite_float(metrics.get("profit_factor"), 0.0)
        robustness = _finite_float(metrics.get("sensitivity_robustness_score"), 1.0)
        ambiguity_rate = _finite_float(metrics.get("same_bar_ambiguity_rate"), 0.0)
        fragility_flags = list(resolution.get("fragility_flags") or [])
        divergence_flags = list(resolution.get("label_vs_replay_divergence_flags") or [])
        stale_warnings = list(resolution.get("stale_window_warnings") or [])
        data_quality_flags = list((feature or candidate).get("data_quality_flags") or [])
        reward_risk = reward_risk_to_target(candidate)

        if observed < int(self.config["minimum_observed_outcomes"]):
            suppression_reasons.append("insufficient_observed_outcomes")
        if sample_size < int(self.config["minimum_cell_sample_size"]):
            warning_codes.append("evidence_sample_size_below_cell_minimum")
        if lower_bound <= float(self.config["minimum_expectancy_lower_bound"]):
            suppression_reasons.append("negative_expectancy_after_shrinkage")
        if profit_factor < float(self.config["minimum_profit_factor"]):
            suppression_reasons.append("profit_factor_below_threshold")
        if robustness < float(self.config["minimum_robustness_score"]):
            suppression_reasons.append("sensitivity_robustness_too_low")
        if fragility_flags:
            penalties["fragility_penalty"] = min(25.0, 8.0 + len(fragility_flags) * 4.0)
            warning_codes.extend(f"fragility:{flag}" for flag in fragility_flags)
            if self.config["suppress_on_fragility"]:
                suppression_reasons.append("sensitivity_fragility_present")
        if stale_warnings:
            penalties["stale_data_penalty"] = 40.0
            warning_codes.extend(f"stale:{warning}" for warning in stale_warnings)
            if self.config["block_stale_evidence"]:
                suppression_reasons.append("stale_replay_evidence")
        severe_divergence = sorted(SEVERE_DIVERGENCE_FLAGS.intersection(set(divergence_flags)))
        if divergence_flags:
            penalties["label_vs_replay_divergence_penalty"] = 20.0 if severe_divergence else 8.0
            warning_codes.extend(f"divergence:{flag}" for flag in divergence_flags)
        if severe_divergence:
            suppression_reasons.append("severe_label_vs_replay_divergence")
        if ambiguity_rate > float(self.config["maximum_same_bar_ambiguity_rate"]):
            penalties["ambiguity_penalty"] = min(25.0, ambiguity_rate * 40.0)
            suppression_reasons.append("same_bar_ambiguity_dependency_too_high")
        if CRITICAL_DATA_QUALITY_FLAGS.intersection(set(data_quality_flags)):
            suppression_reasons.append("critical_data_quality_flag")
        if invalid_risk_plan(candidate):
            suppression_reasons.append("invalid_risk_plan")
        if reward_risk is not None and reward_risk < float(self.config["minimum_reward_risk"]):
            suppression_reasons.append("reward_risk_below_threshold")
        if self.config["allowed_setup_types"] and str(candidate.get("setup_type")) not in self.config["allowed_setup_types"]:
            suppression_reasons.append("setup_not_allowed_by_active_model")
        if str((feature or candidate).get("market_regime") or candidate.get("market_regime") or "unknown") in self.config["blocked_regimes"]:
            suppression_reasons.append("regime_blocked_by_active_model")

        sample_confidence_score = min(observed / max(float(self.config["minimum_observed_outcomes"]) * 4.0, 1.0), 1.0) * 100.0
        evidence_quality_score = _clamp((lower_bound + 0.5) / 2.0, 0.0, 1.0) * 55.0 + _clamp((profit_factor - 1.0) / 2.0, 0.0, 1.0) * 45.0
        robustness_score = robustness * 100.0
        drawdown_score = _clamp(1.0 + (_finite_float(metrics.get("max_drawdown_r"), 0.0) / 10.0), 0.0, 1.0) * 100.0
        risk_quality_score = 100.0 if reward_risk is None else _clamp(reward_risk / max(float(self.config["minimum_reward_risk"]), 0.01), 0.0, 1.0) * 100.0
        regime_alignment_score = 75.0 if str((feature or {}).get("market_regime") or candidate.get("market_regime") or "unknown") != "unknown" else 50.0
        ticker_personality_score = min(_finite_float(metrics.get("win_rate"), 0.0) * 120.0, 100.0)
        time_bucket_score = _clamp((average_r + 0.4) / 1.6, 0.0, 1.0) * 100.0
        raw_score = (
            evidence_quality_score * 0.32
            + sample_confidence_score * 0.18
            + robustness_score * 0.16
            + drawdown_score * 0.10
            + risk_quality_score * 0.10
            + regime_alignment_score * 0.06
            + ticker_personality_score * 0.04
            + time_bucket_score * 0.04
        )
        score = _clamp(raw_score - sum(penalties.values()), 0.0, 100.0)
        if average_r > 0 and lower_bound > 0:
            positive_reason_codes.append("positive_shrunk_expectancy")
        if profit_factor >= float(self.config["minimum_profit_factor"]):
            positive_reason_codes.append("profit_factor_above_threshold")
        if robustness >= float(self.config["minimum_robustness_score"]):
            positive_reason_codes.append("sensitivity_robustness_met")
        grade = grade_for_score(score)
        action = "SUPPRESS" if suppression_reasons else ("TAKE" if score >= float(self.config["take_score_threshold"]) else "WATCH")
        if action == "SUPPRESS":
            grade = "NO_TRADE"
            score = min(score, float(self.config["suppressed_score_ceiling"]))
        return self._output(
            candidate,
            model_version,
            score=score,
            expected_r=lower_bound,
            grade=grade,
            action=action,
            components={
                "risk_quality_score": risk_quality_score,
                "evidence_quality_score": evidence_quality_score,
                "robustness_score": robustness_score,
                "regime_alignment_score": regime_alignment_score,
                "ticker_personality_score": ticker_personality_score,
                "time_bucket_score": time_bucket_score,
                "sample_confidence_score": sample_confidence_score,
            },
            penalties=penalties,
            suppression_reasons=sorted(set(suppression_reasons)),
            positive_reason_codes=sorted(set(positive_reason_codes)),
            warning_codes=sorted(set(warning_codes)),
            evidence_cell_keys_used=resolution["evidence_cell_keys_used"],
        )

    def _output(
        self,
        candidate: dict[str, Any],
        model_version: str,
        *,
        score: float,
        expected_r: float,
        grade: str,
        action: str,
        components: dict[str, float],
        penalties: dict[str, float],
        suppression_reasons: list[str],
        positive_reason_codes: list[str],
        warning_codes: list[str],
        evidence_cell_keys_used: list[str],
    ) -> dict[str, Any]:
        score_id = "score_" + stable_hash(
            {
                "model_version": model_version,
                "candidate_id": candidate.get("candidate_id"),
                "symbol": candidate.get("symbol"),
                "interval": candidate.get("interval"),
                "timestamp": str(candidate.get("timestamp_utc") or candidate.get("signal_timestamp_utc")),
                "side": candidate.get("side"),
                "setup_type": candidate.get("setup_type"),
                "score": round(score, 6),
            }
        )[:32]
        return {
            "score_id": score_id,
            "candidate_id": candidate.get("candidate_id"),
            "symbol": str(candidate.get("symbol") or "").upper(),
            "interval": str(candidate.get("interval") or "1min"),
            "timestamp_utc": _timestamp_text(candidate.get("timestamp_utc") or candidate.get("signal_timestamp_utc")),
            "side": str(candidate.get("side") or Side.NO_TRADE.value),
            "setup_type": str(candidate.get("setup_type") or "unknown"),
            "signal_quality_score": round(score, 4),
            "meta_score": round(score, 4),
            "grade": grade,
            "action": action,
            "expected_r_estimate": round(expected_r, 6),
            **{key: round(value, 4) for key, value in components.items()},
            **{key: round(value, 4) for key, value in penalties.items()},
            "score_components": {key: round(value, 4) for key, value in components.items()},
            "suppression_reasons": suppression_reasons,
            "positive_reason_codes": positive_reason_codes,
            "warning_codes": warning_codes,
            "warnings": warning_codes,
            "evidence_cell_keys_used": evidence_cell_keys_used,
            "model_version": model_version,
            "scoring_config_version": SCORING_CONFIG_VERSION,
            "created_at": datetime.now(UTC).isoformat(),
        }

    def _empty_components(self) -> dict[str, float]:
        return {
            "risk_quality_score": 0.0,
            "evidence_quality_score": 0.0,
            "robustness_score": 0.0,
            "regime_alignment_score": 0.0,
            "ticker_personality_score": 0.0,
            "time_bucket_score": 0.0,
            "sample_confidence_score": 0.0,
        }


def default_scoring_config(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    config = {
        "minimum_observed_outcomes": 5,
        "minimum_cell_sample_size": 5,
        "shrinkage_strength": 20.0,
        "minimum_profit_factor": 1.05,
        "minimum_expectancy_lower_bound": 0.0,
        "minimum_robustness_score": 0.70,
        "minimum_reward_risk": 1.0,
        "maximum_same_bar_ambiguity_rate": 0.35,
        "take_score_threshold": 70.0,
        "suppressed_score_ceiling": 35.0,
        "block_stale_evidence": True,
        "suppress_on_fragility": False,
        "allowed_setup_types": [],
        "blocked_regimes": [],
    }
    if overrides:
        config.update(overrides)
    config["allowed_setup_types"] = list(config.get("allowed_setup_types") or [])
    config["blocked_regimes"] = list(config.get("blocked_regimes") or [])
    return config


def summarize_outcome_rows(rows: list[dict[str, Any]], *, minimum_cell_sample_size: int = 5) -> dict[str, Any]:
    observed = [row for row in rows if row.get("observed_outcome")]
    taken = [row for row in rows if str(row.get("status") or "").upper() == "TAKEN"]
    skipped = [row for row in rows if str(row.get("status") or "").upper() == "SKIPPED"]
    returns = [_finite_float(row.get("realized_r"), 0.0) for row in observed]
    wins = [value for value in returns if value > 0]
    losses = [value for value in returns if value < 0]
    equity: list[float] = []
    running = 0.0
    for value in returns:
        running += value
        equity.append(running)
    drawdown = _drawdown(equity)
    ambiguity_count = len([row for row in observed if row.get("same_bar_ambiguous")])
    fragility_flags = sorted({str(flag) for row in rows for flag in row.get("sensitivity_fragility_flags") or []})
    divergence_flags = sorted({str(flag) for row in rows for flag in row.get("label_vs_replay_divergence_flags") or []})
    stale_warnings = sorted(
        {
            str((row.get("stale_window_status") or {}).get("status"))
            for row in rows
            if isinstance(row.get("stale_window_status"), dict)
            and (row.get("stale_window_status") or {}).get("status")
            and (row.get("stale_window_status") or {}).get("status") != "clean"
        }
    )
    robustness_scores = [_finite_float(row.get("sensitivity_robustness_score"), 1.0) for row in rows if row.get("sensitivity_robustness_score") is not None]
    lower_bound = _lower_bound(returns)
    profit_factor = _profit_factor(returns)
    sample_size = len(rows)
    observed_count = len(observed)
    return {
        "sample_size": sample_size,
        "taken_count": len(taken),
        "skipped_count": len(skipped),
        "observed_outcome_count": observed_count,
        "suppression_skip_count": len([row for row in skipped if row.get("suppression_eligible_skip")]),
        "win_rate": len(wins) / observed_count if observed_count else 0.0,
        "loss_rate": len(losses) / observed_count if observed_count else 0.0,
        "average_r": mean(returns) if returns else 0.0,
        "median_r": median(returns) if returns else 0.0,
        "expectancy_r": mean(returns) if returns else 0.0,
        "total_r": sum(returns),
        "profit_factor": profit_factor,
        "max_drawdown_r": drawdown,
        "average_mfe_r": mean([_finite_float(row.get("mfe_r"), 0.0) for row in observed]) if observed else 0.0,
        "average_mae_r": mean([_finite_float(row.get("mae_r"), 0.0) for row in observed]) if observed else 0.0,
        "median_mfe_r": median([_finite_float(row.get("mfe_r"), 0.0) for row in observed]) if observed else 0.0,
        "median_mae_r": median([_finite_float(row.get("mae_r"), 0.0) for row in observed]) if observed else 0.0,
        "target_1_hit_rate": len([row for row in observed if _finite_float(row.get("mfe_r"), 0.0) >= 1.0]) / observed_count if observed_count else 0.0,
        "target_2_hit_rate": len([row for row in observed if _finite_float(row.get("mfe_r"), 0.0) >= 1.5]) / observed_count if observed_count else 0.0,
        "target_3_hit_rate": len([row for row in observed if _finite_float(row.get("mfe_r"), 0.0) >= 2.5]) / observed_count if observed_count else 0.0,
        "stop_hit_rate": len([row for row in observed if row.get("exit_reason") == "stop" or _finite_float(row.get("realized_r"), 0.0) <= -1.0]) / observed_count if observed_count else 0.0,
        "same_bar_ambiguity_rate": ambiguity_count / observed_count if observed_count else 0.0,
        "average_time_in_trade_minutes": mean([_finite_float(row.get("minutes_held"), 0.0) for row in observed]) if observed else 0.0,
        "sensitivity_robustness_score": min(robustness_scores) if robustness_scores else 1.0,
        "fragility_flags": fragility_flags,
        "label_vs_replay_divergence_flags": divergence_flags,
        "stale_window_warnings": stale_warnings,
        "lower_bound_r": lower_bound,
        "evidence_quality_grade": evidence_quality_grade(observed_count, lower_bound, profit_factor, fragility_flags, minimum_cell_sample_size),
        "skip_breakdown": dict(Counter(str(row.get("skip_reason") or "none") for row in skipped)),
    }


def evidence_quality_grade(
    observed_count: int,
    lower_bound: float,
    profit_factor: float,
    fragility_flags: list[str],
    minimum_cell_sample_size: int,
) -> str:
    if observed_count <= 0:
        return "NO_EVIDENCE"
    if observed_count < minimum_cell_sample_size:
        return "LOW_SAMPLE"
    if fragility_flags:
        return "FRAGILE"
    if lower_bound > 0.25 and profit_factor >= 1.5:
        return "A"
    if lower_bound > 0.0 and profit_factor >= 1.1:
        return "B"
    if lower_bound <= 0.0:
        return "NEGATIVE"
    return "C"


def dimensions_for_candidate(candidate: dict[str, Any], feature: dict[str, Any] | None = None) -> dict[str, str]:
    feature = feature or {}
    timestamp = _maybe_parse_datetime(candidate.get("signal_timestamp_utc") or candidate.get("timestamp_utc") or feature.get("timestamp_utc"))
    return {
        "symbol": str(candidate.get("symbol") or feature.get("symbol") or "").upper(),
        "interval": str(candidate.get("interval") or feature.get("interval") or "1min"),
        "side": str(candidate.get("side") or Side.NO_TRADE.value),
        "setup_type": str(candidate.get("setup_type") or "unknown"),
        "market_regime": str(candidate.get("market_regime") or feature.get("market_regime") or "unknown"),
        "time_bucket": str(candidate.get("time_bucket") or feature.get("time_bucket") or "unknown"),
        "day_of_week": str(timestamp.weekday()) if timestamp else "unknown",
        "relative_strength_bucket": _bucket(feature.get("leadership_score"), (-0.005, 0.0, 0.005), ("weak", "neutral", "strong", "leader")),
        "relative_volume_bucket": _bucket(feature.get("relative_volume"), (0.8, 1.2, 2.0), ("dry", "normal", "active", "hot")),
        "vwap_state": "above" if _finite_float(feature.get("distance_from_vwap"), 0.0) > 0 else "below",
        "opening_range_state": str(feature.get("position_relative_to_opening_range") or "unknown"),
        "gap_bucket": str(feature.get("gap_classification") or "unknown"),
        "trend_quality_bucket": _bucket(feature.get("trend_quality_score"), (0.8, 1.5, 3.0), ("low", "normal", "strong", "extreme")),
        "liquidity_sweep_flag": str(bool(feature.get("sweep_above_previous_day_high") or feature.get("sweep_below_previous_day_low"))),
        "failed_breakout_flag": str(bool(feature.get("failed_breakout"))),
        "failed_breakdown_flag": str(bool(feature.get("failed_breakdown"))),
        "same_bar_ambiguity_flag": str(bool(candidate.get("same_bar_ambiguous"))),
    }


def cell_key(hierarchy_level: str, dimensions: dict[str, Any]) -> str:
    dimension_text = "|".join(f"{key}={dimensions.get(key, 'unknown')}" for key in sorted(dimensions))
    return f"{hierarchy_level}:{dimension_text}"


def grade_for_score(score: float) -> str:
    if score >= 90:
        return "A+"
    if score >= 82:
        return "A"
    if score >= 76:
        return "A-"
    if score >= 70:
        return "B+"
    if score >= 64:
        return "B"
    if score >= 55:
        return "C"
    return "NO_TRADE"


def invalid_risk_plan(candidate: dict[str, Any]) -> bool:
    entry = _maybe_float(candidate.get("entry_price"))
    stop = _maybe_float(candidate.get("stop_price"))
    side = str(candidate.get("side") or "")
    if entry is None or stop is None or side not in {Side.LONG.value, Side.SHORT.value}:
        return False
    return stop >= entry if side == Side.LONG.value else stop <= entry


def reward_risk_to_target(candidate: dict[str, Any]) -> float | None:
    entry = _maybe_float(candidate.get("entry_price"))
    stop = _maybe_float(candidate.get("stop_price"))
    target = _maybe_float(candidate.get("target_2") or candidate.get("target_1"))
    side = str(candidate.get("side") or "")
    if entry is None or stop is None or target is None:
        return None
    if side == Side.LONG.value:
        risk = entry - stop
        reward = target - entry
    elif side == Side.SHORT.value:
        risk = stop - entry
        reward = entry - target
    else:
        return None
    if risk <= 0:
        return 0.0
    return reward / risk


def score_audit_from_score(score: dict[str, Any]) -> dict[str, Any]:
    return {
        "score_id": score["score_id"],
        "model_version": score["model_version"],
        "candidate_id": score.get("candidate_id"),
        "symbol": score["symbol"],
        "interval": score["interval"],
        "timestamp_utc": score["timestamp_utc"],
        "side": score["side"],
        "setup_type": score["setup_type"],
        "signal_quality_score": score["signal_quality_score"],
        "grade": score["grade"],
        "action": score["action"],
        "expected_r_estimate": score["expected_r_estimate"],
        "score_components": score.get("score_components") or {},
        "suppression_reasons": score.get("suppression_reasons") or [],
        "evidence_cell_keys_used": score.get("evidence_cell_keys_used") or [],
        "warnings": score.get("warning_codes") or [],
        "created_at": score.get("created_at") or datetime.now(UTC).isoformat(),
    }


def training_summary(rows: list[dict[str, Any]], cells: list[dict[str, Any]]) -> dict[str, Any]:
    observed = [row for row in rows if row.get("observed_outcome")]
    returns = [_finite_float(row.get("realized_r"), 0.0) for row in observed]
    return {
        "candidate_outcome_rows": len(rows),
        "observed_outcome_count": len(observed),
        "taken_count": len([row for row in rows if row.get("status") == "TAKEN"]),
        "skipped_count": len([row for row in rows if row.get("status") == "SKIPPED"]),
        "evidence_cell_count": len(cells),
        "average_r": mean(returns) if returns else 0.0,
        "median_r": median(returns) if returns else 0.0,
        "profit_factor": _profit_factor(returns),
        "total_r": sum(returns),
        "win_rate": len([value for value in returns if value > 0]) / len(returns) if returns else 0.0,
    }


def model_config_hash(config: dict[str, Any]) -> str:
    return sha256(str(stable_hash(config)).encode("utf-8")).hexdigest()


def _feature_key(feature: dict[str, Any]) -> tuple[str, str, datetime]:
    return (
        str(feature.get("symbol") or "").upper(),
        str(feature.get("interval") or "1min"),
        _parse_datetime(feature.get("timestamp_utc") or feature.get("timestamp")),
    )


def _selected_feature_snapshot(feature: dict[str, Any]) -> dict[str, Any]:
    if not feature:
        return {}
    keys = {
        "feature_set_version",
        "market_regime",
        "ticker_regime",
        "time_bucket",
        "relative_volume",
        "leadership_score",
        "distance_from_vwap",
        "position_relative_to_opening_range",
        "gap_classification",
        "trend_quality_score",
        "failed_breakout",
        "failed_breakdown",
        "sweep_above_previous_day_high",
        "sweep_below_previous_day_low",
        "data_quality_flags",
    }
    return {key: feature.get(key) for key in sorted(keys) if key in feature}


def _comparison_flags(comparisons: list[dict[str, Any]]) -> list[str]:
    flags: set[str] = set()
    for comparison in comparisons:
        summary = dict(comparison.get("summary") or {})
        flags.update(str(flag) for flag in summary.get("material_disagreements") or [])
        if summary.get("status") == "material_disagreement":
            flags.add("material_disagreement")
    return sorted(flags)


def _stale_status(replay_run: dict[str, Any]) -> dict[str, Any]:
    status = replay_run.get("stale_window_status")
    if isinstance(status, dict) and status:
        return status
    return {"status": "clean", "stale_window_ids": []}


def _session_date(trade: dict[str, Any], feature: dict[str, Any] | None, timestamp: datetime) -> str:
    value = trade.get("session_date") or (feature or {}).get("session_date")
    return str(value) if value else timestamp.date().isoformat()


def _timestamp_text(value: Any) -> str:
    try:
        return _parse_datetime(value).isoformat()
    except Exception:
        return datetime.now(UTC).isoformat()


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _maybe_parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        return _parse_datetime(value)
    except Exception:
        return None


def _maybe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if isfinite(parsed) else None


def _finite_float(value: Any, default: float) -> float:
    parsed = _maybe_float(value)
    return default if parsed is None else parsed


def _profit_factor(returns: list[float]) -> float:
    gains = sum(value for value in returns if value > 0)
    losses = abs(sum(value for value in returns if value < 0))
    if losses == 0:
        return 99.0 if gains > 0 else 0.0
    return gains / losses


def _drawdown(equity: list[float]) -> float:
    peak = 0.0
    max_drawdown = 0.0
    for value in equity:
        peak = max(peak, value)
        max_drawdown = min(max_drawdown, value - peak)
    return max_drawdown


def _lower_bound(returns: list[float]) -> float:
    if not returns:
        return 0.0
    avg = mean(returns)
    if len(returns) == 1:
        return avg - 1.0
    return avg - pstdev(returns) / sqrt(len(returns))


def _bucket(value: Any, thresholds: tuple[float, ...], names: tuple[str, ...]) -> str:
    parsed = _maybe_float(value)
    if parsed is None:
        return "unknown"
    for threshold, name in zip(thresholds, names, strict=False):
        if parsed < threshold:
            return name
    return names[-1]


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))
