from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from app.backtesting.engine import BacktestEngine
from app.quant.types import SimulatedTrade, ValidationReport, ValidationSplit, WalkForwardWindow


@dataclass(frozen=True)
class ActivationCriteria:
    minimum_trades: int = 30
    minimum_average_r: float = 0.0
    minimum_profit_factor: float = 1.10
    maximum_drawdown_r: float = -10.0
    maximum_symbol_profit_share: float = 0.70
    maximum_setup_profit_share: float = 0.80


@dataclass(frozen=True)
class WalkForwardSettings:
    train_window_days: int = 20
    validation_window_days: int = 5
    test_window_days: int = 5
    step_days: int = 5
    embargo_minutes: int = 0


class ValidationEngine:
    def __init__(self, criteria: ActivationCriteria | None = None) -> None:
        self.criteria = criteria or ActivationCriteria()
        self.backtest = BacktestEngine()

    def chronological_split(
        self,
        start: datetime,
        end: datetime,
        train_fraction: float = 0.60,
        validation_fraction: float = 0.20,
        embargo_minutes: int = 0,
    ) -> ValidationSplit:
        if start >= end:
            raise ValueError("start must be before end")
        total_seconds = (end - start).total_seconds()
        train_end = start + timedelta(seconds=total_seconds * train_fraction)
        validation_start = train_end + timedelta(minutes=embargo_minutes)
        validation_end = validation_start + timedelta(seconds=total_seconds * validation_fraction)
        test_start = validation_end + timedelta(minutes=embargo_minutes)
        if test_start >= end:
            raise ValueError("chronological split leaves no test window")
        return ValidationSplit(
            train_start=start,
            train_end=train_end,
            validation_start=validation_start,
            validation_end=validation_end,
            test_start=test_start,
            test_end=end,
            embargo_minutes=embargo_minutes,
        )

    def walk_forward_windows(
        self,
        start: datetime,
        end: datetime,
        settings: WalkForwardSettings | None = None,
    ) -> list[ValidationSplit]:
        settings = settings or WalkForwardSettings()
        windows: list[ValidationSplit] = []
        cursor = start
        index = 1
        while True:
            train_start = cursor
            train_end = train_start + timedelta(days=settings.train_window_days)
            validation_start = train_end + timedelta(minutes=settings.embargo_minutes)
            validation_end = validation_start + timedelta(days=settings.validation_window_days)
            test_start = validation_end + timedelta(minutes=settings.embargo_minutes)
            test_end = test_start + timedelta(days=settings.test_window_days)
            if test_end > end:
                break
            windows.append(
                ValidationSplit(
                    train_start=train_start,
                    train_end=train_end,
                    validation_start=validation_start,
                    validation_end=validation_end,
                    test_start=test_start,
                    test_end=test_end,
                    embargo_minutes=settings.embargo_minutes,
                )
            )
            cursor = start + timedelta(days=settings.step_days * index)
            index += 1
        return windows

    def leakage_warnings(
        self,
        features: list[dict[str, Any]] | None = None,
        labels: list[Any] | None = None,
        splits: list[ValidationSplit] | None = None,
    ) -> list[str]:
        warnings: list[str] = []
        for feature in features or []:
            timestamp = self._timestamp(feature.get("timestamp_utc") or feature.get("timestamp"))
            for key in ("previous_day_high", "previous_day_low", "previous_day_close"):
                if feature.get(key) is not None and "previous_day_levels_unavailable" in (
                    feature.get("data_quality_flags") or []
                ):
                    warnings.append(f"{key}_present_with_unavailable_flag_at_{timestamp.isoformat()}")
            if feature.get("current_day_final_high") is not None or feature.get("current_day_final_low") is not None:
                warnings.append(f"future_final_day_value_present_at_{timestamp.isoformat()}")
        for label in labels or []:
            entry_timestamp = getattr(label, "timestamp", getattr(label, "timestamp_utc", None))
            exit_timestamp = getattr(label, "exit_timestamp_utc", None)
            if exit_timestamp is not None and entry_timestamp is not None and exit_timestamp <= entry_timestamp:
                warnings.append(f"label_exit_not_after_entry_{entry_timestamp.isoformat()}")
        for split in splits or []:
            if split.train_end >= split.validation_start:
                warnings.append("train_validation_overlap_or_embargo_violation")
            if split.validation_end >= split.test_start:
                warnings.append("validation_test_overlap_or_embargo_violation")
        return sorted(set(warnings))

    def validate_trades(
        self,
        trades: list[SimulatedTrade],
        splits: list[ValidationSplit],
        leakage_warnings: list[str] | None = None,
    ) -> ValidationReport:
        leakage_warnings = leakage_warnings or []
        windows: list[WalkForwardWindow] = []
        test_trades_all: list[SimulatedTrade] = []
        for index, split in enumerate(splits, start=1):
            test_trades = [
                trade
                for trade in trades
                if split.test_start <= trade.entry_timestamp_utc <= split.test_end
            ]
            test_trades_all.extend(test_trades)
            metrics = self.backtest.summarize_trades(test_trades)
            decision = self.activation_decision(metrics, leakage_warnings, test_trades)
            windows.append(
                WalkForwardWindow(
                    window_id=f"wf-{index:03d}",
                    split=split,
                    metrics=metrics,
                    accepted=decision["activation_decision"] == "accepted",
                    rejection_reasons=tuple(decision["rejection_reasons"]),
                )
            )
        summary = self.backtest.summarize_trades(test_trades_all)
        final_decision = self.activation_decision(summary, leakage_warnings, test_trades_all)
        return ValidationReport(
            summary=summary,
            windows=tuple(windows),
            per_symbol=self._breakdown_dict(test_trades_all, "symbol"),
            per_setup=self._breakdown_dict(test_trades_all, "setup_type"),
            per_regime=self._breakdown_dict(test_trades_all, "market_regime"),
            per_time_bucket=self._breakdown_dict(test_trades_all, "time_bucket"),
            leakage_warnings=tuple(leakage_warnings),
            activation_decision=str(final_decision["activation_decision"]),
            rejection_reasons=tuple(final_decision["rejection_reasons"]),
        )

    def activation_decision(
        self,
        metrics: dict[str, Any],
        leakage_warnings: list[str] | None = None,
        trades: list[SimulatedTrade] | None = None,
    ) -> dict[str, Any]:
        leakage_warnings = leakage_warnings or []
        trades = trades or []
        reasons: list[str] = []
        if int(metrics.get("total_trades") or metrics.get("number_of_trades") or 0) < self.criteria.minimum_trades:
            reasons.append("minimum_trades_not_met")
        if float(metrics.get("average_r") or 0.0) <= self.criteria.minimum_average_r:
            reasons.append("average_r_not_positive")
        if float(metrics.get("profit_factor") or 0.0) <= self.criteria.minimum_profit_factor:
            reasons.append("profit_factor_below_threshold")
        if float(metrics.get("max_drawdown_r") or metrics.get("max_drawdown") or 0.0) < self.criteria.maximum_drawdown_r:
            reasons.append("max_drawdown_too_large")
        if leakage_warnings:
            reasons.append("critical_leakage_warnings_present")
        if self._profit_concentration(trades, "symbol") > self.criteria.maximum_symbol_profit_share:
            reasons.append("single_symbol_profit_concentration_too_high")
        if self._profit_concentration(trades, "setup_type") > self.criteria.maximum_setup_profit_share:
            reasons.append("single_setup_profit_concentration_too_high")
        return {
            "activation_decision": "rejected" if reasons else "accepted",
            "rejection_reasons": reasons,
        }

    def _breakdown_dict(self, trades: list[SimulatedTrade], field: str) -> dict[str, dict[str, Any]]:
        return {
            str(item["group"]): {key: value for key, value in item.items() if key != "group"}
            for item in self.backtest.breakdown_trades(trades, field)
        }

    def _profit_concentration(self, trades: list[SimulatedTrade], field: str) -> float:
        gross_profit = sum(max(trade.realized_r, 0.0) for trade in trades)
        if gross_profit <= 0:
            return 0.0
        buckets: dict[str, float] = {}
        for trade in trades:
            buckets[str(getattr(trade, field))] = buckets.get(str(getattr(trade, field)), 0.0) + max(
                trade.realized_r, 0.0
            )
        return max(buckets.values()) / gross_profit if buckets else 0.0

    def _timestamp(self, value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value))
