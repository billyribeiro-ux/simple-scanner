from __future__ import annotations

from itertools import accumulate
from statistics import mean, median

from app.schemas.market import Label, Outcome


class BacktestEngine:
    def summarize_labels(self, labels: list[Label]) -> dict[str, object]:
        returns = [label.realized_r for label in labels]
        wins = [label for label in labels if label.outcome == Outcome.WIN]
        losses = [label for label in labels if label.outcome == Outcome.LOSS]
        equity = list(accumulate(returns))
        max_drawdown = self._max_drawdown(equity)
        return {
            "number_of_trades": len(labels),
            "win_rate": len(wins) / len(labels) if labels else 0.0,
            "precision": len(wins) / len(labels) if labels else 0.0,
            "average_r": mean(returns) if returns else 0.0,
            "median_r": median(returns) if returns else 0.0,
            "expectancy": mean(returns) if returns else 0.0,
            "profit_factor": self._profit_factor(returns),
            "max_drawdown": max_drawdown,
            "average_mfe": mean([label.max_favorable_excursion for label in labels]) if labels else 0.0,
            "average_mae": mean([label.max_adverse_excursion for label in labels]) if labels else 0.0,
            "target_hit_rate": len([label for label in labels if label.hit_target_2]) / len(labels) if labels else 0.0,
            "stop_hit_rate": len(losses) / len(labels) if labels else 0.0,
            "no_trade_suppression_rate": 0.0,
            "equity_curve_r": equity,
        }

    def breakdown(self, labels: list[Label], field: str) -> list[dict[str, object]]:
        groups: dict[str, list[Label]] = {}
        for label in labels:
            key = str(getattr(label, field))
            groups.setdefault(key, []).append(label)
        return [{"group": key, **self.summarize_labels(bucket)} for key, bucket in sorted(groups.items())]

    def _profit_factor(self, returns: list[float]) -> float:
        gains = sum(value for value in returns if value > 0)
        losses = abs(sum(value for value in returns if value < 0))
        if losses == 0:
            return float(gains > 0)
        return gains / losses

    def _max_drawdown(self, equity: list[float]) -> float:
        peak = 0.0
        max_dd = 0.0
        for value in equity:
            peak = max(peak, value)
            max_dd = min(max_dd, value - peak)
        return max_dd
