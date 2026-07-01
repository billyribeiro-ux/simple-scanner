from __future__ import annotations

from datetime import datetime
from statistics import mean
from typing import Any

from app.backtesting.audit import stable_hash
from app.utils.time import UTC


class CalibrationDriftEngine:
    def run(
        self,
        *,
        model_version: str,
        calibration_audits: list[dict[str, Any]],
        window_results: list[dict[str, Any]] | None = None,
        replay_runs: list[dict[str, Any]] | None = None,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        config = config or {}
        ordered_audits = sorted(calibration_audits, key=lambda row: str(row.get("created_at") or ""))
        ordered_windows = sorted(window_results or [], key=lambda row: int(row.get("window_index") or 0))
        replay_runs = replay_runs or []
        window_metrics = self._window_metrics(ordered_audits, ordered_windows, config)
        drift_flags = self._drift_flags(window_metrics, replay_runs, config)
        severity = self._severity(drift_flags)
        created_at = datetime.now(UTC).isoformat()
        report_id = "calibration_drift_" + stable_hash(
            {
                "model_version": model_version,
                "calibration_audit_ids": [row.get("calibration_audit_id") for row in ordered_audits],
                "window_result_ids": [row.get("window_result_id") for row in ordered_windows],
                "created_at": created_at,
            }
        )[:32]
        report = {
            "drift_report_id": report_id,
            "model_version": model_version,
            "calibration_audit_ids": [
                str(row.get("calibration_audit_id"))
                for row in ordered_audits
                if row.get("calibration_audit_id")
            ],
            "window_result_ids": [
                str(row.get("window_result_id"))
                for row in ordered_windows
                if row.get("window_result_id")
            ],
            "replay_run_ids": [
                str(row.get("replay_run_id"))
                for row in replay_runs
                if row.get("replay_run_id")
            ],
            "window_metrics": window_metrics,
            "score_bin_drift": self._bin_drift(ordered_audits, "score_bins"),
            "grade_bin_drift": self._bin_drift(ordered_audits, "grade_bins"),
            "action_bin_drift": self._bin_drift(ordered_audits, "action_bins"),
            "stability_metrics": self._stability_metrics(window_metrics),
            "drift_flags": drift_flags,
            "severity": severity,
            "summary": {
                "window_count": len(window_metrics),
                "calibration_audit_count": len(ordered_audits),
                "drift_flag_count": len(drift_flags),
                "severity": severity,
                "diagnostic_only": True,
            },
            "warnings": [
                "Calibration drift reports are research diagnostics and do not activate or trade a model."
            ],
            "config": config,
            "created_at": created_at,
        }
        return report

    def _window_metrics(
        self,
        audits: list[dict[str, Any]],
        window_results: list[dict[str, Any]],
        config: dict[str, Any],
    ) -> list[dict[str, Any]]:
        output = []
        max_count = max(len(audits), len(window_results))
        for index in range(max_count):
            audit = audits[index] if index < len(audits) else {}
            window = window_results[index] if index < len(window_results) else {}
            metrics = dict(window.get("metrics") or {})
            grade_bins = {str(row.get("bin_key")): row for row in audit.get("grade_bins") or []}
            action_bins = {str(row.get("bin_key")): row for row in audit.get("action_bins") or []}
            high_grade = grade_bins.get("A") or {}
            take = action_bins.get("TAKE") or {}
            watch = action_bins.get("WATCH") or {}
            row_metrics = {
                "rank_correlation_score": self._float(audit.get("rank_correlation_score")),
                "monotonicity_pass": bool(audit.get("monotonicity_pass")),
                "high_grade_average_r": self._float(high_grade.get("observed_average_r")),
                "high_grade_sample_size": int(high_grade.get("sample_size") or 0),
                "take_average_r": self._float(take.get("observed_average_r")),
                "watch_average_r": self._float(watch.get("observed_average_r")),
                "take_minus_watch_average_r": self._float((audit.get("separation_metrics") or {}).get("take_minus_watch_average_r")),
                "warning_count": len(audit.get("calibration_warnings") or audit.get("warnings") or []),
                "replay_average_r": self._float(metrics.get("average_r")),
                "replay_profit_factor": self._float(metrics.get("profit_factor")),
                "replay_max_drawdown_r": self._float(metrics.get("max_drawdown_r")),
                "replay_total_trades": int(metrics.get("total_trades") or metrics.get("candidates_taken") or 0),
            }
            flags = self._window_flags(row_metrics, window, config)
            output.append(
                {
                    "window_index": int(window.get("window_index") or index + 1),
                    "window_result_id": window.get("window_result_id"),
                    "calibration_audit_id": audit.get("calibration_audit_id"),
                    "created_at": audit.get("created_at") or window.get("created_at"),
                    "metrics": row_metrics,
                    "flags": flags,
                    "severity": self._severity(flags),
                }
            )
        return output

    def _window_flags(self, metrics: dict[str, Any], window: dict[str, Any], config: dict[str, Any]) -> list[str]:
        flags: list[str] = []
        minimum_recent_samples = int(config.get("minimum_recent_high_grade_samples") or config.get("minimum_high_grade_samples") or 5)
        if not metrics["monotonicity_pass"]:
            flags.append("monotonicity_failed")
        if float(metrics["high_grade_average_r"]) < 0:
            flags.append("high_grade_expectancy_negative")
        if float(metrics["take_minus_watch_average_r"]) <= 0 and (metrics["take_average_r"] or metrics["watch_average_r"]):
            flags.append("take_underperforms_watch")
        if int(metrics["high_grade_sample_size"]) < minimum_recent_samples:
            flags.append("too_few_recent_high_grade_samples")
        warnings = list(window.get("warnings") or [])
        stale_status = dict(window.get("stale_window_status") or {})
        if stale_status.get("status") not in {None, "", "clean"} or any("stale" in str(item) for item in warnings):
            flags.append("stale_window_contamination")
        return sorted(set(flags))

    def _drift_flags(
        self,
        window_metrics: list[dict[str, Any]],
        replay_runs: list[dict[str, Any]],
        config: dict[str, Any],
    ) -> list[str]:
        if not window_metrics:
            return ["no_calibration_windows_available"]
        flags: list[str] = []
        if len(window_metrics) < 2:
            flags.append("insufficient_history_for_drift")
        first = window_metrics[0]["metrics"]
        recent = window_metrics[-1]["metrics"]
        if float(recent["rank_correlation_score"]) < float(first["rank_correlation_score"]) - float(config.get("rank_correlation_drop_threshold") or 0.10):
            flags.append("rank_correlation_deteriorating")
        if not recent["monotonicity_pass"]:
            flags.append("monotonicity_failed_in_recent_window")
        if float(recent["high_grade_average_r"]) < 0:
            flags.append("high_grade_expectancy_turns_negative")
        if float(recent["take_minus_watch_average_r"]) <= 0:
            flags.append("take_underperforms_watch_recently")
        previous_warning_counts = [int(row["metrics"]["warning_count"]) for row in window_metrics[:-1]]
        if previous_warning_counts and int(recent["warning_count"]) > max(previous_warning_counts):
            flags.append("calibration_warning_spike")
        if any("stale_window_contamination" in row.get("flags", []) for row in window_metrics):
            flags.append("stale_window_contamination")
        if any(self._replay_is_stale(run) for run in replay_runs):
            flags.append("stale_replay_source_contamination")
        if "too_few_recent_high_grade_samples" in window_metrics[-1].get("flags", []):
            flags.append("too_few_recent_samples")
        return sorted(set(flags))

    def _bin_drift(self, audits: list[dict[str, Any]], key: str) -> dict[str, Any]:
        if not audits:
            return {"status": "no_audits"}
        first = {str(row.get("bin_key")): row for row in audits[0].get(key) or []}
        latest = {str(row.get("bin_key")): row for row in audits[-1].get(key) or []}
        output = {}
        for bin_key in sorted(set(first) | set(latest)):
            start_avg = self._float((first.get(bin_key) or {}).get("observed_average_r"))
            latest_avg = self._float((latest.get(bin_key) or {}).get("observed_average_r"))
            output[bin_key] = {
                "start_average_r": start_avg,
                "latest_average_r": latest_avg,
                "average_r_delta": latest_avg - start_avg,
                "start_sample_size": int((first.get(bin_key) or {}).get("sample_size") or 0),
                "latest_sample_size": int((latest.get(bin_key) or {}).get("sample_size") or 0),
            }
        return output

    def _stability_metrics(self, window_metrics: list[dict[str, Any]]) -> dict[str, Any]:
        ranks = [float(row["metrics"]["rank_correlation_score"]) for row in window_metrics]
        high_grade = [float(row["metrics"]["high_grade_average_r"]) for row in window_metrics]
        take_watch = [float(row["metrics"]["take_minus_watch_average_r"]) for row in window_metrics]
        return {
            "rank_correlation_series": ranks,
            "rank_correlation_average": mean(ranks) if ranks else 0.0,
            "rank_correlation_latest": ranks[-1] if ranks else 0.0,
            "high_grade_average_r_series": high_grade,
            "high_grade_latest": high_grade[-1] if high_grade else 0.0,
            "take_minus_watch_series": take_watch,
            "take_minus_watch_latest": take_watch[-1] if take_watch else 0.0,
            "monotonicity_pass_rate": (
                len([row for row in window_metrics if row["metrics"]["monotonicity_pass"]]) / len(window_metrics)
                if window_metrics
                else 0.0
            ),
        }

    def _severity(self, flags: list[str]) -> str:
        flag_set = set(flags)
        if {"stale_window_contamination", "stale_replay_source_contamination"} & flag_set:
            return "BLOCKING"
        if {"high_grade_expectancy_turns_negative", "take_underperforms_watch_recently"} <= flag_set:
            return "BLOCKING"
        if {"high_grade_expectancy_negative", "take_underperforms_watch"} <= flag_set:
            return "REVIEW"
        if flag_set & {
            "rank_correlation_deteriorating",
            "monotonicity_failed_in_recent_window",
            "high_grade_expectancy_turns_negative",
            "take_underperforms_watch_recently",
            "calibration_warning_spike",
        }:
            return "REVIEW"
        if flag_set:
            return "WATCH"
        return "INFO"

    def _replay_is_stale(self, replay: dict[str, Any]) -> bool:
        stale_status = dict(replay.get("stale_window_status") or {})
        warnings = list(replay.get("warnings") or [])
        return stale_status.get("status") not in {None, "", "clean"} or any("stale" in str(item) for item in warnings)

    def _float(self, value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
