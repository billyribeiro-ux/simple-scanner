from __future__ import annotations

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

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None = None) -> SensitivityConfig:
        data = payload or {}
        return cls(
            slippage_bps_grid=tuple(float(value) for value in data.get("slippage_bps_grid") or DEFAULT_SLIPPAGE_BPS_GRID),
            spread_bps_grid=tuple(float(value) for value in data.get("spread_bps_grid") or DEFAULT_SPREAD_BPS_GRID),
            intrabar_path_policies=tuple(str(value) for value in data.get("intrabar_path_policies") or DEFAULT_INTRABAR_POLICIES),
            same_bar_stop_target_policies=tuple(
                str(value) for value in data.get("same_bar_stop_target_policies") or DEFAULT_SAME_BAR_POLICIES
            ),
            minimum_robustness_score=float(data.get("minimum_robustness_score") or 0.70),
            minimum_total_trades=int(data.get("minimum_total_trades") or 5),
            minimum_average_r=float(data.get("minimum_average_r") or 0.0),
            minimum_profit_factor=float(data.get("minimum_profit_factor") or 1.0),
            maximum_drawdown_r=float(data.get("maximum_drawdown_r") or -10.0),
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
        }


class ReplaySensitivityEngine:
    def __init__(self, replay_engine: CandidateMarketReplayEngine | None = None) -> None:
        self.replay_engine = replay_engine or CandidateMarketReplayEngine()

    def run(
        self,
        replay_run_id: str,
        bars: list[Bar],
        features: list[dict[str, Any]],
        candidates: list[dict[str, Any]],
        base_config: ReplayConfig,
        sensitivity_config: SensitivityConfig | None = None,
    ) -> dict[str, Any]:
        sensitivity_config = sensitivity_config or SensitivityConfig()
        created_at = datetime.now(UTC).isoformat()
        scenarios = []
        for slippage_bps in sensitivity_config.slippage_bps_grid:
            for spread_bps in sensitivity_config.spread_bps_grid:
                for intrabar_policy in sensitivity_config.intrabar_path_policies:
                    for same_bar_policy in sensitivity_config.same_bar_stop_target_policies:
                        scenario_config = replace(
                            base_config,
                            slippage_bps=slippage_bps,
                            spread_bps=spread_bps,
                            intrabar_path_policy=intrabar_policy,
                            same_bar_stop_target_policy=same_bar_policy,
                        )
                        scenario_id = self._scenario_id(replay_run_id, scenario_config)
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
                                "replay_run_id": replay_run_id,
                                "slippage_bps": slippage_bps,
                                "spread_bps": spread_bps,
                                "intrabar_path_policy": intrabar_policy,
                                "same_bar_stop_target_policy": same_bar_policy,
                                "config_hash": stable_hash(scenario_config.to_dict()),
                                "summary_metrics": run.metrics,
                                "gate_results": gate_results,
                                "pass_fail": PASSED_STATUS if all(gate_results.values()) else "fail",
                            }
                        )
        sorted_scenarios = sorted(scenarios, key=self._quality_key)
        pass_count = len([scenario for scenario in scenarios if scenario["pass_fail"] == PASSED_STATUS])
        robustness_score = pass_count / len(scenarios) if scenarios else 0.0
        fragility_flags = self._fragility_flags(scenarios, sensitivity_config)
        gate_results = {
            "scenario_count_positive": bool(scenarios),
            "robustness_score_met": robustness_score >= sensitivity_config.minimum_robustness_score,
            "no_fragility_flags": not fragility_flags,
            "worst_case_passed": sorted_scenarios[0]["pass_fail"] == PASSED_STATUS if sorted_scenarios else False,
        }
        pass_fail = PASSED_STATUS if all(gate_results.values()) else "fail"
        sensitivity_run_id = "sensitivity_" + stable_hash(
            {
                "replay_run_id": replay_run_id,
                "config": sensitivity_config.to_dict(),
                "scenario_hashes": [scenario["config_hash"] for scenario in scenarios],
            }
        )[:32]
        return {
            "sensitivity_run_id": sensitivity_run_id,
            "replay_run_id": replay_run_id,
            "created_at": created_at,
            "config": sensitivity_config.to_dict(),
            "scenario_count": len(scenarios),
            "passed_scenario_count": pass_count,
            "failed_scenario_count": len(scenarios) - pass_count,
            "robustness_score": robustness_score,
            "pass_fail": pass_fail,
            "worst_case": sorted_scenarios[0] if sorted_scenarios else None,
            "median_case": sorted_scenarios[len(sorted_scenarios) // 2] if sorted_scenarios else None,
            "best_case": sorted_scenarios[-1] if sorted_scenarios else None,
            "fragility_flags": fragility_flags,
            "gate_results": gate_results,
            "scenarios": scenarios,
        }

    def _scenario_id(self, replay_run_id: str, config: ReplayConfig) -> str:
        return "scenario_" + stable_hash({"replay_run_id": replay_run_id, "config": config.to_dict()})[:32]

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
