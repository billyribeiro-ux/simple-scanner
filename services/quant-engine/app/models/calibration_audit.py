from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from math import isfinite, sqrt
from statistics import mean
from typing import Any

from app.backtesting.audit import stable_hash
from app.utils.time import UTC

DEFAULT_SCORE_BIN_EDGES = [0, 20, 40, 60, 75, 85, 100]


class ScoreCalibrationAuditEngine:
    def run(
        self,
        *,
        model_version: str,
        score_audits: list[dict[str, Any]],
        outcome_rows: list[dict[str, Any]],
        replay_run_ids: list[str] | None = None,
        validation_report_id: str | None = None,
        outcome_source: str = "counterfactual_preferred",
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        config = config or {}
        joined = self._join(score_audits, outcome_rows)
        score_edges = list(config.get("score_bins") or DEFAULT_SCORE_BIN_EDGES)
        score_bins = self._score_bins(joined, score_edges)
        grade_bins = self._categorical_bins(joined, "grade", order=["A", "B", "C", "NO_TRADE"])
        action_bins = self._categorical_bins(joined, "action", order=["TAKE", "WATCH", "SUPPRESS"])
        stability_metrics = {
            "by_symbol": self._stability(joined, "symbol"),
            "by_setup": self._stability(joined, "setup_type"),
            "by_regime": self._stability(joined, "market_regime"),
            "by_time_bucket": self._stability(joined, "time_bucket"),
        }
        rank_correlation = self._rank_correlation(
            [float(row["score"]) for row in joined],
            [float(row["realized_r"]) for row in joined],
        )
        monotonicity_pass = self._monotonic_score_bins(score_bins)
        separation_metrics = self._separation_metrics(grade_bins, action_bins)
        warnings = self._warnings(
            joined,
            score_bins,
            grade_bins,
            action_bins,
            stability_metrics,
            minimum_high_grade_samples=int(config.get("minimum_high_grade_samples") or 5),
        )
        rejection_reasons = self._rejection_reasons(
            warnings,
            monotonicity_pass=monotonicity_pass,
            separation_metrics=separation_metrics,
            rank_correlation=rank_correlation,
            high_grade_samples=sum(int(bin_row["sample_size"]) for bin_row in grade_bins if str(bin_row["bin_key"]).startswith("A")),
            config=config,
        )
        created_at = datetime.now(UTC).isoformat()
        audit_id = "calibration_" + stable_hash(
            {
                "model_version": model_version,
                "validation_report_id": validation_report_id,
                "replay_run_ids": replay_run_ids or [],
                "outcome_source": outcome_source,
                "joined_count": len(joined),
                "created_at": created_at,
            }
        )[:32]
        return {
            "calibration_audit_id": audit_id,
            "model_version": model_version,
            "validation_report_id": validation_report_id,
            "replay_run_ids": replay_run_ids or [],
            "outcome_source": outcome_source,
            "scored_outcome_count": len(joined),
            "score_bins": score_bins,
            "grade_bins": grade_bins,
            "action_bins": action_bins,
            "rank_correlation_score": rank_correlation,
            "monotonicity_pass": monotonicity_pass,
            "separation_metrics": separation_metrics,
            "stability_metrics": stability_metrics,
            "calibration_warnings": warnings,
            "warnings": warnings,
            "rejection_reasons": rejection_reasons,
            "config": config,
            "provenance": {
                "score_audit_count": len(score_audits),
                "outcome_row_count": len(outcome_rows),
                "joined_count": len(joined),
                "method": "score_audit_replay_outcome_join",
                "not_probability_calibration": True,
            },
            "created_at": created_at,
        }

    def _join(self, score_audits: list[dict[str, Any]], outcome_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_candidate = {
            str(row.get("candidate_id")): row
            for row in outcome_rows
            if row.get("candidate_id") and row.get("observed_outcome")
        }
        by_key = {
            self._join_key(row): row
            for row in outcome_rows
            if row.get("observed_outcome")
        }
        joined = []
        for audit in score_audits:
            payload = dict(audit.get("payload") or {})
            candidate_id = str(audit.get("candidate_id") or payload.get("candidate_id") or "")
            outcome = by_candidate.get(candidate_id) if candidate_id else None
            if outcome is None:
                outcome = by_key.get(self._join_key(audit | payload))
            if outcome is None:
                continue
            realized_r = self._outcome_r(outcome)
            if realized_r is None:
                continue
            score = self._finite(audit.get("signal_quality_score") or payload.get("signal_quality_score") or payload.get("meta_score"), None)
            if score is None:
                continue
            joined.append(
                {
                    "candidate_id": candidate_id or outcome.get("candidate_id"),
                    "symbol": str(audit.get("symbol") or outcome.get("symbol") or "").upper(),
                    "setup_type": str(audit.get("setup_type") or outcome.get("setup_type") or "unknown"),
                    "market_regime": str(outcome.get("market_regime") or "unknown"),
                    "time_bucket": str(outcome.get("time_bucket") or "unknown"),
                    "score": float(score),
                    "grade": self._grade_family(str(audit.get("grade") or payload.get("grade") or "NO_TRADE")),
                    "action": str(audit.get("action") or payload.get("action") or "SUPPRESS"),
                    "realized_r": realized_r,
                    "same_bar_ambiguous": bool(outcome.get("same_bar_ambiguous")),
                    "sensitivity_fragility_flags": list(outcome.get("sensitivity_fragility_flags") or []),
                }
            )
        return joined

    def _score_bins(self, rows: list[dict[str, Any]], edges: list[float]) -> list[dict[str, Any]]:
        output = []
        for start, end in zip(edges, edges[1:], strict=False):
            bucket = [
                row for row in rows if float(row["score"]) >= float(start) and (float(row["score"]) < float(end) or end == edges[-1] and float(row["score"]) <= float(end))
            ]
            output.append(self._bin_metrics(bucket, f"{start:g}-{end:g}") | {"bin_type": "score", "lower": start, "upper": end})
        return output

    def _categorical_bins(self, rows: list[dict[str, Any]], field: str, *, order: list[str]) -> list[dict[str, Any]]:
        keys = [key for key in order if any(str(row.get(field)) == key for row in rows)]
        keys.extend(sorted({str(row.get(field) or "unknown") for row in rows} - set(keys)))
        return [self._bin_metrics([row for row in rows if str(row.get(field)) == key], key) | {"bin_type": field} for key in keys]

    def _stability(self, rows: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
        buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            buckets[str(row.get(field) or "unknown")].append(row)
        return [self._bin_metrics(bucket, key) for key, bucket in sorted(buckets.items())]

    def _bin_metrics(self, rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
        returns = [float(row["realized_r"]) for row in rows]
        wins = [value for value in returns if value > 0]
        equity = []
        running = 0.0
        for value in returns:
            running += value
            equity.append(running)
        return {
            "bin_key": key,
            "sample_size": len(rows),
            "observed_average_r": mean(returns) if returns else 0.0,
            "observed_win_rate": len(wins) / len(returns) if returns else 0.0,
            "profit_factor": self._profit_factor(returns),
            "max_drawdown_r": self._drawdown(equity),
            "same_bar_ambiguity_rate": len([row for row in rows if row.get("same_bar_ambiguous")]) / len(rows) if rows else 0.0,
            "fragility_flag_rate": len([row for row in rows if row.get("sensitivity_fragility_flags")]) / len(rows) if rows else 0.0,
        }

    def _warnings(
        self,
        rows: list[dict[str, Any]],
        score_bins: list[dict[str, Any]],
        grade_bins: list[dict[str, Any]],
        action_bins: list[dict[str, Any]],
        stability_metrics: dict[str, Any],
        *,
        minimum_high_grade_samples: int,
    ) -> list[str]:
        warnings: list[str] = []
        high_score_rows = [row for row in rows if float(row["score"]) >= 75.0]
        if high_score_rows and mean([float(row["realized_r"]) for row in high_score_rows]) <= 0:
            warnings.append("high_score_negative_expectancy")
        if not self._monotonic_grade_bins(grade_bins):
            warnings.append("grade_order_not_monotonic")
        action_by_key = {row["bin_key"]: row for row in action_bins}
        if action_by_key.get("TAKE") and action_by_key.get("WATCH"):
            if float(action_by_key["TAKE"]["observed_average_r"]) <= float(action_by_key["WATCH"]["observed_average_r"]):
                warnings.append("take_bucket_underperforms_watch")
        high_grade_samples = sum(int(row["sample_size"]) for row in grade_bins if str(row["bin_key"]).startswith("A"))
        if high_grade_samples < minimum_high_grade_samples:
            warnings.append("too_few_high_grade_samples")
        if score_bins and rows and max(int(row["sample_size"]) for row in score_bins) / len(rows) > 0.80:
            warnings.append("score_concentrated_in_one_bucket")
        if self._top_bucket_concentration(high_score_rows, "symbol") > 0.70:
            warnings.append("high_score_depends_on_one_symbol")
        if self._top_bucket_concentration(high_score_rows, "setup_type") > 0.70:
            warnings.append("high_score_depends_on_one_setup")
        regime_rows = list(stability_metrics.get("by_regime") or [])
        if len([row for row in regime_rows if int(row["sample_size"]) > 0]) >= 2:
            avgs = [float(row["observed_average_r"]) for row in regime_rows if int(row["sample_size"]) > 0]
            if max(avgs) > 0 and min(avgs) < 0:
                warnings.append("severe_regime_instability")
        top_bin = score_bins[-1] if score_bins else {}
        if float(top_bin.get("same_bar_ambiguity_rate") or 0.0) > 0.35:
            warnings.append("high_same_bar_ambiguity_in_top_bucket")
        if float(top_bin.get("fragility_flag_rate") or 0.0) > 0.0:
            warnings.append("sensitivity_fragility_in_top_bucket")
        return sorted(set(warnings))

    def _rejection_reasons(
        self,
        warnings: list[str],
        *,
        monotonicity_pass: bool,
        separation_metrics: dict[str, Any],
        rank_correlation: float,
        high_grade_samples: int,
        config: dict[str, Any],
    ) -> list[str]:
        reasons: list[str] = []
        if config.get("require_monotonic_score_bins") and not monotonicity_pass:
            reasons.append("score_bins_not_monotonic")
        if config.get("require_take_outperforms_watch") and float(separation_metrics.get("take_minus_watch_average_r") or 0.0) <= 0:
            reasons.append("take_does_not_outperform_watch")
        minimum_high_grade_samples = config.get("minimum_high_grade_samples")
        if minimum_high_grade_samples is not None and high_grade_samples < int(minimum_high_grade_samples):
            reasons.append("minimum_high_grade_samples_not_met")
        minimum_rank = config.get("minimum_rank_correlation_score")
        if minimum_rank is not None and rank_correlation < float(minimum_rank):
            reasons.append("rank_correlation_below_threshold")
        max_warnings = config.get("max_allowed_calibration_warnings")
        if max_warnings is not None and len(warnings) > int(max_warnings):
            reasons.append("too_many_calibration_warnings")
        return sorted(set(reasons))

    def _separation_metrics(self, grade_bins: list[dict[str, Any]], action_bins: list[dict[str, Any]]) -> dict[str, Any]:
        grade = {row["bin_key"]: row for row in grade_bins}
        action = {row["bin_key"]: row for row in action_bins}
        return {
            "a_minus_b_average_r": float((grade.get("A") or {}).get("observed_average_r") or 0.0) - float((grade.get("B") or {}).get("observed_average_r") or 0.0),
            "b_minus_c_average_r": float((grade.get("B") or {}).get("observed_average_r") or 0.0) - float((grade.get("C") or {}).get("observed_average_r") or 0.0),
            "take_minus_watch_average_r": float((action.get("TAKE") or {}).get("observed_average_r") or 0.0) - float((action.get("WATCH") or {}).get("observed_average_r") or 0.0),
            "watch_minus_suppress_average_r": float((action.get("WATCH") or {}).get("observed_average_r") or 0.0) - float((action.get("SUPPRESS") or {}).get("observed_average_r") or 0.0),
        }

    def _monotonic_score_bins(self, bins: list[dict[str, Any]]) -> bool:
        values = [float(row["observed_average_r"]) for row in bins if int(row["sample_size"]) > 0]
        return all(right >= left for left, right in zip(values, values[1:], strict=False))

    def _monotonic_grade_bins(self, bins: list[dict[str, Any]]) -> bool:
        by_key = {row["bin_key"]: row for row in bins}
        ordered = [by_key[key] for key in ("A", "B", "C", "NO_TRADE") if key in by_key and int(by_key[key]["sample_size"]) > 0]
        values = [float(row["observed_average_r"]) for row in ordered]
        return all(left >= right for left, right in zip(values, values[1:], strict=False))

    def _rank_correlation(self, scores: list[float], returns: list[float]) -> float:
        if len(scores) < 2 or len(scores) != len(returns):
            return 0.0
        score_ranks = self._ranks(scores)
        return_ranks = self._ranks(returns)
        mean_x = mean(score_ranks)
        mean_y = mean(return_ranks)
        numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(score_ranks, return_ranks, strict=True))
        denom_x = sqrt(sum((x - mean_x) ** 2 for x in score_ranks))
        denom_y = sqrt(sum((y - mean_y) ** 2 for y in return_ranks))
        if denom_x == 0 or denom_y == 0:
            return 0.0
        return numerator / (denom_x * denom_y)

    def _ranks(self, values: list[float]) -> list[float]:
        sorted_values = sorted((value, index) for index, value in enumerate(values))
        ranks = [0.0] * len(values)
        position = 0
        while position < len(sorted_values):
            end = position
            while end + 1 < len(sorted_values) and sorted_values[end + 1][0] == sorted_values[position][0]:
                end += 1
            rank = (position + end) / 2.0 + 1.0
            for _, index in sorted_values[position : end + 1]:
                ranks[index] = rank
            position = end + 1
        return ranks

    def _top_bucket_concentration(self, rows: list[dict[str, Any]], field: str) -> float:
        if not rows:
            return 0.0
        counts = Counter(str(row.get(field) or "unknown") for row in rows)
        return max(counts.values()) / len(rows)

    def _join_key(self, row: dict[str, Any]) -> tuple[str, str, str, str]:
        return (
            str(row.get("symbol") or "").upper(),
            str(row.get("timestamp_utc") or row.get("signal_timestamp_utc") or ""),
            str(row.get("side") or ""),
            str(row.get("setup_type") or ""),
        )

    def _outcome_r(self, row: dict[str, Any]) -> float | None:
        for key in ("counterfactual_realized_r", "realized_r", "portfolio_realized_r"):
            value = row.get(key)
            parsed = self._finite(value, None)
            if parsed is not None:
                return parsed
        return None

    def _grade_family(self, grade: str) -> str:
        if grade.startswith("A"):
            return "A"
        if grade.startswith("B"):
            return "B"
        if grade.startswith("C"):
            return "C"
        return "NO_TRADE"

    def _profit_factor(self, returns: list[float]) -> float:
        gains = sum(value for value in returns if value > 0)
        losses = abs(sum(value for value in returns if value < 0))
        if losses == 0:
            return 99.0 if gains > 0 else 0.0
        return gains / losses

    def _drawdown(self, equity: list[float]) -> float:
        peak = 0.0
        max_drawdown = 0.0
        for value in equity:
            peak = max(peak, value)
            max_drawdown = min(max_drawdown, value - peak)
        return max_drawdown

    def _finite(self, value: Any, default: float | None) -> float | None:
        if value is None:
            return default
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return default
        return parsed if isfinite(parsed) else default
