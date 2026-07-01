from __future__ import annotations

from datetime import timedelta
from hashlib import sha256
from itertools import accumulate
from statistics import mean, median
from typing import Any

from app.quant.types import SimulatedTrade
from app.schemas.market import Label, Outcome, Side


class BacktestEngine:
    def simulate_labels(
        self,
        labels: list[Label],
        one_open_trade_per_symbol: bool = True,
        max_hold_bars: int = 60,
    ) -> list[SimulatedTrade]:
        trades: list[SimulatedTrade] = []
        open_until: dict[str, Any] = {}
        for label in sorted(labels, key=lambda item: item.timestamp):
            if one_open_trade_per_symbol and label.timestamp <= open_until.get(label.symbol, label.timestamp.replace(year=1900)):
                continue
            duration = label.time_to_target or label.time_to_stop or max_hold_bars
            exit_timestamp = getattr(label, "exit_timestamp_utc", None) or label.timestamp + timedelta(minutes=duration)
            exit_reason = self._exit_reason(label)
            if label.side == Side.LONG:
                exit_price = label.entry_price + (label.realized_r * (label.entry_price - label.stop_price))
            else:
                exit_price = label.entry_price - (label.realized_r * (label.stop_price - label.entry_price))
            trade_id = sha256(
                f"{label.symbol}:{label.timestamp.isoformat()}:{label.side}:{label.setup_type}".encode()
            ).hexdigest()[:32]
            trades.append(
                SimulatedTrade(
                    trade_id=trade_id,
                    symbol=label.symbol,
                    interval=getattr(label, "interval", "1min"),
                    side=label.side.value,
                    setup_type=label.setup_type,
                    entry_timestamp_utc=label.timestamp,
                    exit_timestamp_utc=exit_timestamp,
                    entry_price=label.entry_price,
                    exit_price=exit_price,
                    stop_price=label.stop_price,
                    target_1=label.target_1,
                    target_2=label.target_2,
                    target_3=label.target_3,
                    realized_r=label.realized_r,
                    max_favorable_excursion=label.max_favorable_excursion,
                    max_adverse_excursion=label.max_adverse_excursion,
                    outcome=label.outcome.value,
                    market_regime=label.market_regime,
                    time_bucket=getattr(label, "time_bucket", "unknown"),
                    exit_reason=exit_reason,
                    duration_bars=duration,
                )
            )
            open_until[label.symbol] = exit_timestamp
        return trades

    def summarize_labels(self, labels: list[Label]) -> dict[str, object]:
        return self.summarize_trades(self.simulate_labels(labels))

    def summarize_trades(
        self,
        trades: list[SimulatedTrade],
        no_trade_candidates: int = 0,
    ) -> dict[str, object]:
        returns = [trade.realized_r for trade in trades]
        wins = [trade for trade in trades if trade.outcome == Outcome.WIN.value or trade.realized_r > 0]
        losses = [trade for trade in trades if trade.outcome == Outcome.LOSS.value or trade.realized_r < 0]
        equity = list(accumulate(returns))
        target_1_hits = [trade for trade in trades if trade.realized_r >= 1.0]
        target_2_hits = [trade for trade in trades if trade.realized_r >= 1.5]
        target_3_hits = [trade for trade in trades if trade.realized_r >= 2.5]
        total_candidates = len(trades) + no_trade_candidates
        return {
            "total_trades": len(trades),
            "number_of_trades": len(trades),
            "long_trades": len([trade for trade in trades if trade.side == Side.LONG.value]),
            "short_trades": len([trade for trade in trades if trade.side == Side.SHORT.value]),
            "win_rate": len(wins) / len(trades) if trades else 0.0,
            "precision": len(wins) / len(trades) if trades else 0.0,
            "precision_by_side": self._precision_by_side(trades),
            "average_r": mean(returns) if returns else 0.0,
            "median_r": median(returns) if returns else 0.0,
            "expectancy": mean(returns) if returns else 0.0,
            "profit_factor": self._profit_factor(returns),
            "gross_r": sum(returns),
            "max_drawdown": self._max_drawdown(equity),
            "max_drawdown_r": self._max_drawdown(equity),
            "average_mfe": mean([trade.max_favorable_excursion for trade in trades]) if trades else 0.0,
            "average_mae": mean([trade.max_adverse_excursion for trade in trades]) if trades else 0.0,
            "target_1_hit_rate": len(target_1_hits) / len(trades) if trades else 0.0,
            "target_2_hit_rate": len(target_2_hits) / len(trades) if trades else 0.0,
            "target_3_hit_rate": len(target_3_hits) / len(trades) if trades else 0.0,
            "target_hit_rate": len(target_2_hits) / len(trades) if trades else 0.0,
            "stop_hit_rate": len(losses) / len(trades) if trades else 0.0,
            "average_time_in_trade": mean([trade.duration_bars for trade in trades]) if trades else 0.0,
            "no_trade_suppression_rate": no_trade_candidates / total_candidates if total_candidates else 0.0,
            "equity_curve_r": equity,
        }

    def breakdown(self, labels: list[Label], field: str) -> list[dict[str, object]]:
        trades = self.simulate_labels(labels)
        return self.breakdown_trades(trades, field)

    def breakdown_trades(self, trades: list[SimulatedTrade], field: str) -> list[dict[str, object]]:
        groups: dict[str, list[SimulatedTrade]] = {}
        for trade in trades:
            key = str(getattr(trade, field))
            groups.setdefault(key, []).append(trade)
        return [{"group": key, **self.summarize_trades(bucket)} for key, bucket in sorted(groups.items())]

    def _exit_reason(self, label: Label) -> str:
        if label.outcome == Outcome.WIN:
            return "target"
        if label.outcome == Outcome.LOSS:
            return "stop"
        return "time_exit"

    def _precision_by_side(self, trades: list[SimulatedTrade]) -> dict[str, float]:
        output: dict[str, float] = {}
        for side in (Side.LONG.value, Side.SHORT.value):
            side_trades = [trade for trade in trades if trade.side == side]
            wins = [trade for trade in side_trades if trade.realized_r > 0]
            output[side] = len(wins) / len(side_trades) if side_trades else 0.0
        return output

    def _profit_factor(self, returns: list[float]) -> float:
        gains = sum(value for value in returns if value > 0)
        losses = abs(sum(value for value in returns if value < 0))
        if losses == 0:
            return float("inf") if gains > 0 else 0.0
        return gains / losses

    def _max_drawdown(self, equity: list[float]) -> float:
        peak = 0.0
        max_dd = 0.0
        for value in equity:
            peak = max(peak, value)
            max_dd = min(max_dd, value - peak)
        return max_dd
