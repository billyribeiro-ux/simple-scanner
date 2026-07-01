from __future__ import annotations

from datetime import datetime, timedelta

from app.backtesting.engine import BacktestEngine
from app.models.engine import StatisticalEvidenceEngine
from app.schemas.market import Outcome, Side
from app.utils.time import UTC
from app.validation.engine import ActivationCriteria, ValidationEngine, WalkForwardSettings


def test_backtest_profit_factor_drawdown_and_side_precision(make_label) -> None:
    labels = [
        make_label(0, 1.5, Outcome.WIN),
        make_label(10, -1.0, Outcome.LOSS),
        make_label(20, 0.5, Outcome.NEUTRAL),
    ]
    summary = BacktestEngine().summarize_labels(labels)
    assert summary["total_trades"] == 3
    assert summary["profit_factor"] == 2.0
    assert summary["max_drawdown_r"] == -1.0
    assert summary["precision_by_side"][Side.LONG.value] > 0


def test_one_open_trade_per_symbol(make_label) -> None:
    labels = [
        make_label(0, 1.5, Outcome.WIN),
        make_label(1, 1.5, Outcome.WIN),
    ]
    trades = BacktestEngine().simulate_labels(labels, one_open_trade_per_symbol=True, max_hold_bars=60)
    assert len(trades) == 1


def test_chronological_split_and_walk_forward_embargo() -> None:
    engine = ValidationEngine()
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = datetime(2026, 3, 1, tzinfo=UTC)
    split = engine.chronological_split(start, end, embargo_minutes=30)
    assert split.train_end < split.validation_start
    windows = engine.walk_forward_windows(
        start,
        end,
        WalkForwardSettings(train_window_days=20, validation_window_days=5, test_window_days=5, step_days=5, embargo_minutes=30),
    )
    assert windows
    assert all(window.validation_end < window.test_start for window in windows)


def test_activation_reject_and_accept(make_label) -> None:
    labels = [make_label(index * 10, 1.5, Outcome.WIN, symbol=f"S{index % 4}") for index in range(12)]
    trades = BacktestEngine().simulate_labels(labels, one_open_trade_per_symbol=False)
    reject = ValidationEngine().activation_decision({"total_trades": 2, "average_r": -0.1, "profit_factor": 0.5, "max_drawdown_r": -1}, [], [])
    assert reject["activation_decision"] == "rejected"
    criteria = ActivationCriteria(
        minimum_trades=10,
        minimum_profit_factor=1.1,
        maximum_symbol_profit_share=1.0,
        maximum_setup_profit_share=1.0,
    )
    metrics = BacktestEngine().summarize_trades(trades)
    accept = ValidationEngine(criteria).activation_decision(metrics, [], trades)
    assert accept["activation_decision"] == "accepted"


def test_statistical_evidence_model_shape(make_label) -> None:
    labels = [
        make_label(0, 1.5, Outcome.WIN),
        make_label(10, -1.0, Outcome.LOSS),
    ]
    evidence = StatisticalEvidenceEngine().summarize(labels)
    assert evidence
    assert any("VWAP reclaim long" in key for key in evidence)
