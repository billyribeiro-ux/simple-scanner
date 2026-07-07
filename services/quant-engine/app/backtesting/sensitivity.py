from __future__ import annotations

import time
from dataclasses import dataclass, replace
from datetime import datetime
from statistics import median
from typing import Any

from app.backtesting.audit import stable_hash
from app.backtesting.replay import CandidateMarketReplayEngine, ReplayConfig
from app.schemas.market import Bar
from app.utils.time import UTC

DEFAULT_SLIPPAGE_BPS_GRID = (0.0, 1.0, 2.0, 5.0, 10.0)
DEFAULT_SPREAD_BPS_GRID = (0.0, 1.0, 2.0, 5.0, 10.0)
DEFAULT_INTRABAR_POLICIES = ("conservative", "open_high_low_close", "open_low_high_close")
DEFAULT_SAME_BAR_POLICIES = ("conservative_stop_first",)
DEFAULT_FULL_GRID_SCENARIO_COUNT = (
    len(DEFAULT_SLIPPAGE_BPS_GRID)
    * len(DEFAULT_SPREAD_BPS_GRID)
    * len(DEFAULT_INTRABAR_POLICIES)
    * len(DEFAULT_SAME_BAR_POLICIES)
)
FULL_GRID_VERSION = "replay_sensitivity.full_default_grid.v1"
FULL_GRID_COVERAGE = "FULL_GRID"
CHUNKED_FULL_GRID_COVERAGE = "CHUNKED_FULL_GRID"
TIERED_ESSENTIAL_COVERAGE = "TIERED_ESSENTIAL"
SAMPLED_COVERAGE = "SAMPLED"
PARTIAL_TIMEOUT_COVERAGE = "PARTIAL_TIMEOUT"
ACTIVATION_GRADE_COVERAGE_MODES = {FULL_GRID_COVERAGE, CHUNKED_FULL_GRID_COVERAGE}
PASSED_STATUS = "pass"  # noqa: S105 - scenario pass/fail status, not a password.


@dataclass(frozen=True)
class SensitivityConfig:
    slippage_bps_grid: tuple[float, ...] = DEFAULT_SLIPPAGE_BPS_GRID
    spread_bps_grid: tuple[float, ...] = DEFAULT_SPREAD_BPS_GRID
    intrabar_path_policies: tuple[str, ...] = DEFAULT_INTRABAR_POLICIES
    same_bar_stop_target_policies: tuple[str, ...] = DEFAULT_SAME_BAR_POLICIES
    minimum_robustness_score: float = 0.70
    minimum_total_trades: int = 5
    minimum_average_r: float = 0.0
    minimum_profit_factor: float = 1.0
    maximum_drawdown_r: float = -10.0
    coverage_mode: str = FULL_GRID_COVERAGE
    max_scenarios: int | None = None
    max_scenarios_per_invocation: int | None = None
    max_runtime_seconds: float | None = None
    scenario_group: str | None = None
    full_default_grid_required: bool = False

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None = None) -> SensitivityConfig:
        data = payload or {}
        coverage_mode = str(data.get("coverage_mode") or FULL_GRID_COVERAGE).upper()
        default_slippage_grid = (0.0, 2.0) if coverage_mode == TIERED_ESSENTIAL_COVERAGE else DEFAULT_SLIPPAGE_BPS_GRID
        default_spread_grid = (0.0, 2.0) if coverage_mode == TIERED_ESSENTIAL_COVERAGE else DEFAULT_SPREAD_BPS_GRID
        default_intrabar_policies = (
            ("conservative",) if coverage_mode == TIERED_ESSENTIAL_COVERAGE else DEFAULT_INTRABAR_POLICIES
        )
        max_scenarios = data.get("max_scenarios")
        max_scenarios_per_invocation = data.get("max_scenarios_per_invocation")
        if max_scenarios_per_invocation is None:
            max_scenarios_per_invocation = data.get("chunk_size")
        max_runtime_seconds = data.get("max_runtime_seconds")
        return cls(
            slippage_bps_grid=tuple(float(value) for value in data.get("slippage_bps_grid") or default_slippage_grid),
            spread_bps_grid=tuple(float(value) for value in data.get("spread_bps_grid") or default_spread_grid),
            intrabar_path_policies=tuple(str(value) for value in data.get("intrabar_path_policies") or default_intrabar_policies),
            same_bar_stop_target_policies=tuple(
                str(value) for value in data.get("same_bar_stop_target_policies") or DEFAULT_SAME_BAR_POLICIES
            ),
            minimum_robustness_score=float(data.get("minimum_robustness_score") or 0.70),
            minimum_total_trades=int(data.get("minimum_total_trades") or 5),
            minimum_average_r=float(data.get("minimum_average_r") or 0.0),
            minimum_profit_factor=float(data.get("minimum_profit_factor") or 1.0),
            maximum_drawdown_r=float(data.get("maximum_drawdown_r") or -10.0),
            coverage_mode=coverage_mode,
            max_scenarios=None if max_scenarios is None else max(int(max_scenarios), 0),
            max_scenarios_per_invocation=(
                None if max_scenarios_per_invocation is None else max(int(max_scenarios_per_invocation), 0)
            ),
            max_runtime_seconds=None if max_runtime_seconds is None else max(float(max_runtime_seconds), 0.0),
            scenario_group=str(data.get("scenario_group")) if data.get("scenario_group") else None,
            full_default_grid_required=bool(data.get("full_default_grid_required")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "slippage_bps_grid": list(self.slippage_bps_grid),
            "spread_bps_grid": list(self.spread_bps_grid),
            "intrabar_path_policies": list(self.intrabar_path_policies),
            "same_bar_stop_target_policies": list(self.same_bar_stop_target_policies),
            "minimum_robustness_score": self.minimum_robustness_score,
            "minimum_total_trades": self.minimum_total_trades,
            "minimum_average_r": self.minimum_average_r,
            "minimum_profit_factor": self.minimum_profit_factor,
            "maximum_drawdown_r": self.maximum_drawdown_r,
            "coverage_mode": self.coverage_mode,
            "max_scenarios": self.max_scenarios,
            "max_scenarios_per_invocation": self.max_scenarios_per_invocation,
            "max_runtime_seconds": self.max_runtime_seconds,
            "scenario_group": self.scenario_group,
            "full_default_grid_required": self.full_default_grid_required,
        }

    def identity_payload(self) -> dict[str, Any]:
        payload = self.to_dict()
        payload.pop("max_scenarios_per_invocation", None)
        payload.pop("max_runtime_seconds", None)
        payload.pop("scenario_group", None)
        return payload

    def grid_payload(self) -> dict[str, Any]:
        return {
            "slippage_bps_grid": list(self.slippage_bps_grid),
            "spread_bps_grid": list(self.spread_bps_grid),
            "intrabar_path_policies": list(self.intrabar_path_policies),
            "same_bar_stop_target_policies": list(self.same_bar_stop_target_policies),
        }


class ReplaySensitivityEngine:
    def __init__(self, replay_engine: CandidateMarketReplayEngine | None = None) -> None:
        self.replay_engine = replay_engine or CandidateMarketReplayEngine()

    def full_grid_spec(self, config: SensitivityConfig | None = None) -> dict[str, Any]:
        config = config or SensitivityConfig()
        return {
            "grid_version": FULL_GRID_VERSION,
            "grid_hash": self.grid_hash(config),
            "slippage_bps_grid": list(config.slippage_bps_grid),
            "spread_bps_grid": list(config.spread_bps_grid),
            "intrabar_path_policies": list(config.intrabar_path_policies),
            "same_bar_stop_target_policies": list(config.same_bar_stop_target_policies),
            "scenario_count": len(self._planned_scenarios(ReplayConfig(), config)),
            "default_full_grid_scenario_count": DEFAULT_FULL_GRID_SCENARIO_COUNT,
        }

    def grid_hash(self, config: SensitivityConfig) -> str:
        return stable_hash({"grid_version": FULL_GRID_VERSION, "grid": config.grid_payload()})

    def sensitivity_run_id(
        self,
        replay_run_id: str,
        base_config: ReplayConfig,
        sensitivity_config: SensitivityConfig,
    ) -> str:
        return "sensitivity_" + stable_hash(
            {
                "replay_run_id": replay_run_id,
                "base_config": base_config.to_dict(),
                "sensitivity_config": sensitivity_config.identity_payload(),
                "grid_version": FULL_GRID_VERSION,
                "grid_hash": self.grid_hash(sensitivity_config),
            }
        )[:32]

    def run(
        self,
        replay_run_id: str,
        bars: list[Bar],
        features: list[dict[str, Any]],
        candidates: list[dict[str, Any]],
        base_config: ReplayConfig,
        sensitivity_config: SensitivityConfig | None = None,
        *,
        sensitivity_run_id: str | None = None,
        existing_scenarios: list[dict[str, Any]] | None = None,
        previous_run: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        sensitivity_config = sensitivity_config or SensitivityConfig()
        sensitivity_run_id = sensitivity_run_id or self.sensitivity_run_id(replay_run_id, base_config, sensitivity_config)
        created_at = str((previous_run or {}).get("created_at") or datetime.now(UTC).isoformat())
        started = time.perf_counter()
        planned_scenarios = self._planned_scenarios(base_config, sensitivity_config)
        planned_rows = self._planned_rows(sensitivity_run_id, replay_run_id, planned_scenarios)
        selected_rows, selection_warnings = self._select_scenarios(planned_rows, sensitivity_config)
        selected_ids = {str(row["scenario_id"]) for row in selected_rows}
        existing_by_id = self._dedupe_existing_scenarios(existing_scenarios or [], selected_ids)
        scenarios: list[dict[str, Any]] = []
        partial_reason = None
        run_rows = [
            row
            for row in selected_rows
            if str(row["scenario_id"]) not in existing_by_id and self._scenario_group_matches(row, sensitivity_config.scenario_group)
        ]
        if sensitivity_config.max_scenarios_per_invocation is not None and sensitivity_config.max_scenarios_per_invocation < len(run_rows):
            run_rows = run_rows[: sensitivity_config.max_scenarios_per_invocation]
            partial_reason = "max_scenarios_per_invocation_limited"
        for row in run_rows:
            if (
                scenarios
                and sensitivity_config.max_runtime_seconds is not None
                and (time.perf_counter() - started) >= sensitivity_config.max_runtime_seconds
            ):
                partial_reason = "max_runtime_seconds_exhausted"
                break
            scenario_started = time.perf_counter()
            scenario_config = row["config"]
            scenario_id = str(row["scenario_id"])
            run = self.replay_engine.replay(
                bars,
                features,
                candidates,
                scenario_config,
                replay_run_id=scenario_id,
            )
            gate_results = self._gate_results(run.metrics, sensitivity_config)
            scenarios.append(
                {
                    "scenario_id": scenario_id,
                    "sensitivity_run_id": sensitivity_run_id,
                    "replay_run_id": replay_run_id,
                    "grid_version": FULL_GRID_VERSION,
                    "grid_hash": self.grid_hash(sensitivity_config),
                    "scenario_index": row["scenario_index"],
                    "scenario_key": self._scenario_key(sensitivity_run_id, scenario_id, replay_run_id),
                    "slippage_bps": scenario_config.slippage_bps,
                    "spread_bps": scenario_config.spread_bps,
                    "intrabar_path_policy": scenario_config.intrabar_path_policy,
                    "same_bar_stop_target_policy": scenario_config.same_bar_stop_target_policy,
                    "config_hash": row["config_hash"],
                    "summary_metrics": run.metrics,
                    "gate_results": gate_results,
                    "pass_fail": PASSED_STATUS if all(gate_results.values()) else "fail",
                    "runtime_seconds": round(time.perf_counter() - scenario_started, 6),
                }
            )
        scenario_by_id = {scenario_id: scenario for scenario_id, scenario in existing_by_id.items()}
        scenario_by_id.update({str(scenario["scenario_id"]): scenario for scenario in scenarios})
        all_scenarios = sorted(scenario_by_id.values(), key=lambda scenario: int(scenario.get("scenario_index") or 0))
        completed_scenario_ids = {str(scenario.get("scenario_id")) for scenario in all_scenarios}
        remaining_rows = [row for row in selected_rows if str(row["scenario_id"]) not in completed_scenario_ids]
        if partial_reason is None and sensitivity_config.scenario_group and remaining_rows:
            partial_reason = "scenario_group_limited"
        if partial_reason is None and len(selected_rows) < len(planned_rows):
            partial_reason = "max_scenarios_limited"
        if partial_reason is None and remaining_rows:
            partial_reason = "chunked_sensitivity_grid_not_complete"
        configured_grid_complete = len(all_scenarios) == len(planned_rows)
        default_grid = self._is_default_full_grid(sensitivity_config, len(planned_rows))
        full_default_grid_complete = (
            configured_grid_complete
            and default_grid
            and sensitivity_config.coverage_mode in ACTIVATION_GRADE_COVERAGE_MODES
            and len(planned_rows) >= DEFAULT_FULL_GRID_SCENARIO_COUNT
        )
        coverage_warnings = [
            *selection_warnings,
            *(["partial_sensitivity_grid_not_complete"] if not configured_grid_complete else []),
            *(["bounded_sensitivity_not_full_default_grid"] if not full_default_grid_complete else []),
            *(["full_default_grid_required_but_incomplete"] if sensitivity_config.full_default_grid_required and not full_default_grid_complete else []),
        ]
        completion_status = (
            "COMPLETE"
            if full_default_grid_complete
            else (
                PARTIAL_TIMEOUT_COVERAGE
                if partial_reason == "max_runtime_seconds_exhausted" or sensitivity_config.coverage_mode == PARTIAL_TIMEOUT_COVERAGE
                else ("PARTIAL" if not configured_grid_complete else "BOUNDED_COMPLETE")
            )
        )
        sorted_scenarios = sorted(all_scenarios, key=self._quality_key)
        pass_count = len([scenario for scenario in all_scenarios if scenario["pass_fail"] == PASSED_STATUS])
        robustness_score = pass_count / len(all_scenarios) if all_scenarios else 0.0
        fragility_flags = self._fragility_flags(all_scenarios, sensitivity_config)
        next_scenario_index = int(remaining_rows[0]["scenario_index"]) if remaining_rows else None
        resume_token = stable_hash(
            {
                "sensitivity_run_id": sensitivity_run_id,
                "completed_scenario_count": len(all_scenarios),
                "next_scenario_index": next_scenario_index,
                "grid_hash": self.grid_hash(sensitivity_config),
            }
        )[:24]
        gate_results = {
            "scenario_count_positive": bool(all_scenarios),
            "configured_grid_complete": configured_grid_complete,
            "full_default_grid_complete": full_default_grid_complete,
            "activation_grade_sensitivity": full_default_grid_complete and completion_status == "COMPLETE",
            "robustness_score_met": robustness_score >= sensitivity_config.minimum_robustness_score,
            "no_fragility_flags": not fragility_flags,
            "worst_case_passed": sorted_scenarios[0]["pass_fail"] == PASSED_STATUS if sorted_scenarios else False,
        }
        pass_fail = PASSED_STATUS if all(gate_results.values()) else "fail"
        return {
            "sensitivity_run_id": sensitivity_run_id,
            "replay_run_id": replay_run_id,
            "created_at": created_at,
            "config": sensitivity_config.to_dict(),
            "grid_version": FULL_GRID_VERSION,
            "grid_hash": self.grid_hash(sensitivity_config),
            "coverage_mode": sensitivity_config.coverage_mode,
            "completion_status": completion_status,
            "activation_grade_sensitivity": full_default_grid_complete and completion_status == "COMPLETE",
            "sensitivity_classification": "activation_grade" if full_default_grid_complete and completion_status == "COMPLETE" else "diagnostic",
            "configured_grid_complete": configured_grid_complete,
            "full_default_grid_complete": full_default_grid_complete,
            "partial_grid_disclosure": not full_default_grid_complete,
            "partial_reason": partial_reason,
            "planned_scenario_count": len(planned_rows),
            "selected_scenario_count": len(selected_rows),
            "completed_scenario_count": len(all_scenarios),
            "remaining_scenario_count": max(len(planned_rows) - len(all_scenarios), 0),
            "failed_required_scenario_count": len(all_scenarios) - pass_count,
            "next_scenario_index": next_scenario_index,
            "resume_token": resume_token,
            "scenario_group": sensitivity_config.scenario_group,
            "default_full_grid_scenario_count": DEFAULT_FULL_GRID_SCENARIO_COUNT,
            "coverage_warnings": sorted(set(coverage_warnings)),
            "runtime_seconds": round(time.perf_counter() - started, 6),
            "scenario_count": len(all_scenarios),
            "passed_scenario_count": pass_count,
            "failed_scenario_count": len(all_scenarios) - pass_count,
            "robustness_score": robustness_score,
            "pass_fail": pass_fail,
            "worst_case": sorted_scenarios[0] if sorted_scenarios else None,
            "median_case": sorted_scenarios[len(sorted_scenarios) // 2] if sorted_scenarios else None,
            "best_case": sorted_scenarios[-1] if sorted_scenarios else None,
            "fragility_flags": fragility_flags,
            "gate_results": gate_results,
            "scenarios": all_scenarios,
        }

    def _planned_scenarios(self, base_config: ReplayConfig, config: SensitivityConfig) -> list[ReplayConfig]:
        scenarios = []
        for slippage_bps in config.slippage_bps_grid:
            for spread_bps in config.spread_bps_grid:
                for intrabar_policy in config.intrabar_path_policies:
                    for same_bar_policy in config.same_bar_stop_target_policies:
                        scenarios.append(
                            replace(
                                base_config,
                                slippage_bps=slippage_bps,
                                spread_bps=spread_bps,
                                intrabar_path_policy=intrabar_policy,
                                same_bar_stop_target_policy=same_bar_policy,
                            )
                        )
        return scenarios

    def _planned_rows(
        self,
        sensitivity_run_id: str,
        replay_run_id: str,
        scenarios: list[ReplayConfig],
    ) -> list[dict[str, Any]]:
        rows = []
        for index, scenario_config in enumerate(scenarios, start=1):
            config_hash = stable_hash(scenario_config.to_dict())
            scenario_id = self._scenario_id(sensitivity_run_id, replay_run_id, scenario_config)
            rows.append(
                {
                    "scenario_index": index,
                    "scenario_id": scenario_id,
                    "scenario_key": self._scenario_key(sensitivity_run_id, scenario_id, replay_run_id),
                    "config_hash": config_hash,
                    "config": scenario_config,
                }
            )
        return rows

    def _select_scenarios(
        self,
        scenarios: list[dict[str, Any]],
        config: SensitivityConfig,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        warnings = []
        selected = list(scenarios)
        if config.coverage_mode == SAMPLED_COVERAGE:
            selected = sorted(selected, key=lambda scenario: str(scenario["config_hash"]))
            warnings.append("sampled_sensitivity_selection")
        if config.max_scenarios is not None and config.max_scenarios < len(selected):
            selected = selected[: config.max_scenarios]
            warnings.append("sensitivity_scenario_count_limited")
        if config.coverage_mode == TIERED_ESSENTIAL_COVERAGE:
            warnings.append("tiered_essential_sensitivity_scope")
        if config.coverage_mode == CHUNKED_FULL_GRID_COVERAGE:
            warnings.append("chunked_full_grid_sensitivity_scope")
        if config.coverage_mode == PARTIAL_TIMEOUT_COVERAGE:
            warnings.append("partial_timeout_sensitivity_scope")
        if config.scenario_group:
            warnings.append("scenario_group_invocation_scope")
        return selected, warnings

    def _scenario_id(self, sensitivity_run_id: str, replay_run_id: str, config: ReplayConfig) -> str:
        return "scenario_" + stable_hash(
            {
                "sensitivity_run_id": sensitivity_run_id,
                "replay_run_id": replay_run_id,
                "grid_version": FULL_GRID_VERSION,
                "config": config.to_dict(),
            }
        )[:32]

    def _scenario_key(self, sensitivity_run_id: str, scenario_id: str, replay_run_id: str) -> str:
        return stable_hash(
            {
                "sensitivity_run_id": sensitivity_run_id,
                "scenario_id": scenario_id,
                "replay_run_id": replay_run_id,
                "grid_version": FULL_GRID_VERSION,
            }
        )

    def _dedupe_existing_scenarios(
        self,
        scenarios: list[dict[str, Any]],
        selected_ids: set[str],
    ) -> dict[str, dict[str, Any]]:
        deduped: dict[str, dict[str, Any]] = {}
        for scenario in scenarios:
            scenario_id = str(scenario.get("scenario_id") or "")
            if scenario_id and scenario_id in selected_ids and scenario_id not in deduped:
                deduped[scenario_id] = dict(scenario)
        return deduped

    def _scenario_group_matches(self, row: dict[str, Any], scenario_group: str | None) -> bool:
        if not scenario_group or scenario_group.lower() == "all":
            return True
        config = row["config"]
        group = scenario_group.lower()
        if group == "low_costs":
            return float(config.slippage_bps) <= 2.0 and float(config.spread_bps) <= 2.0
        if group == "high_costs":
            return float(config.slippage_bps) >= 5.0 or float(config.spread_bps) >= 5.0
        if group.startswith("intrabar:"):
            return str(config.intrabar_path_policy) == scenario_group.split(":", 1)[1]
        if group.startswith("same_bar:"):
            return str(config.same_bar_stop_target_policy) == scenario_group.split(":", 1)[1]
        if group.startswith("slippage:"):
            return float(config.slippage_bps) == float(scenario_group.split(":", 1)[1])
        if group.startswith("spread:"):
            return float(config.spread_bps) == float(scenario_group.split(":", 1)[1])
        return True

    def _is_default_full_grid(self, config: SensitivityConfig, scenario_count: int) -> bool:
        return (
            tuple(config.slippage_bps_grid) == DEFAULT_SLIPPAGE_BPS_GRID
            and tuple(config.spread_bps_grid) == DEFAULT_SPREAD_BPS_GRID
            and tuple(config.intrabar_path_policies) == DEFAULT_INTRABAR_POLICIES
            and tuple(config.same_bar_stop_target_policies) == DEFAULT_SAME_BAR_POLICIES
            and scenario_count == DEFAULT_FULL_GRID_SCENARIO_COUNT
            and config.max_scenarios is None
        )

    def _gate_results(self, metrics: dict[str, Any], config: SensitivityConfig) -> dict[str, bool]:
        return {
            "minimum_total_trades_met": int(metrics.get("total_trades") or 0) >= config.minimum_total_trades,
            "average_r_positive": float(metrics.get("average_r") or 0.0) > config.minimum_average_r,
            "profit_factor_met": float(metrics.get("profit_factor") or 0.0) >= config.minimum_profit_factor,
            "drawdown_within_limit": float(metrics.get("max_drawdown_r") or 0.0) >= config.maximum_drawdown_r,
        }

    def _quality_key(self, scenario: dict[str, Any]) -> tuple[float, float, float, float]:
        metrics = dict(scenario.get("summary_metrics") or {})
        return (
            float(metrics.get("average_r") or 0.0),
            float(metrics.get("profit_factor") or 0.0),
            float(metrics.get("total_r") or 0.0),
            -float(metrics.get("max_drawdown_r") or 0.0),
        )

    def _fragility_flags(self, scenarios: list[dict[str, Any]], config: SensitivityConfig) -> list[str]:
        flags: list[str] = []
        if not scenarios:
            return ["no_sensitivity_scenarios"]
        small_costs = [
            scenario
            for scenario in scenarios
            if float(scenario["slippage_bps"]) <= 2.0 and float(scenario["spread_bps"]) <= 2.0
        ]
        if any(float((scenario.get("summary_metrics") or {}).get("average_r") or 0.0) <= 0 for scenario in small_costs):
            flags.append("expectancy_turns_non_positive_under_small_costs")
        if any(float((scenario.get("summary_metrics") or {}).get("profit_factor") or 0.0) <= 1.0 for scenario in small_costs):
            flags.append("profit_factor_not_robust_under_small_costs")
        total_trades = [int((scenario.get("summary_metrics") or {}).get("total_trades") or 0) for scenario in scenarios]
        if total_trades and median(total_trades) < config.minimum_total_trades:
            flags.append("median_scenario_trade_count_too_low")
        skip_rates = [float((scenario.get("summary_metrics") or {}).get("skip_rate") or 0.0) for scenario in scenarios]
        if skip_rates and median(skip_rates) >= 0.75:
            flags.append("median_scenario_skip_rate_high")
        same_bar_counts = [int((scenario.get("summary_metrics") or {}).get("same_bar_ambiguity_count") or 0) for scenario in scenarios]
        if same_bar_counts and max(same_bar_counts) > 0:
            flags.append("same_bar_path_assumption_affects_results")
        if (
            len([scenario for scenario in scenarios if scenario["pass_fail"] == PASSED_STATUS]) / len(scenarios)
            < config.minimum_robustness_score
        ):
            flags.append("robustness_score_below_threshold")
        return sorted(set(flags))
