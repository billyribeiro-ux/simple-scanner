from __future__ import annotations

from app.backtesting.replay import CandidateMarketReplayEngine, ReplayConfig
from app.schemas.market import Bar, Side


def _candidate(bar: Bar, side: str = Side.LONG.value, symbol: str | None = None, confidence: float = 0.75) -> dict[str, object]:
    symbol = symbol or bar.symbol
    return {
        "candidate_id": f"candidate-{symbol}-{bar.timestamp_utc.isoformat()}-{side}",
        "symbol": symbol,
        "interval": bar.interval,
        "timestamp_utc": bar.timestamp_utc,
        "side": side,
        "setup_type": "VWAP reclaim long" if side == Side.LONG.value else "VWAP loss short",
        "entry_context": {"vwap": 100.0, "atr_14": 1.0, "time_bucket": "opening_drive"},
        "invalidation_context": {
            "opening_range_low": 100.0,
            "opening_range_high": 100.0,
            "premarket_low": 99.5,
            "premarket_high": 100.5,
        },
        "reason_codes": ["test"],
        "warning_codes": [],
        "confidence_score": confidence,
        "expected_r": confidence * 0.5,
    }


def _feature(bar: Bar, side: str = Side.LONG.value) -> dict[str, object]:
    return {
        "symbol": bar.symbol,
        "interval": bar.interval,
        "timestamp": bar.timestamp_utc.isoformat(),
        "timestamp_utc": bar.timestamp_utc,
        "timestamp_et": bar.timestamp_et,
        "session_date": bar.timestamp_et.date().isoformat(),
        "feature_set_version": "test",
        "close": bar.close,
        "vwap": 100.0,
        "atr_14": 1.0,
        "atr_14_proxy": 1.0,
        "market_regime": "trend_long" if side == Side.LONG.value else "trend_short",
        "time_bucket": "opening_drive",
        "data_quality_flags": [],
    }


def _replay(bars: list[Bar], candidates: list[dict[str, object]], config: ReplayConfig | None = None):
    features = [_feature(bar, str(candidate.get("side", Side.LONG.value))) for candidate in candidates for bar in bars if bar.timestamp_utc == candidate["timestamp_utc"]]
    return CandidateMarketReplayEngine().replay(bars, features, candidates, config or ReplayConfig(symbols=("AAPL",), intervals=("1min",)))


def test_replay_long_target_hit(make_bar) -> None:
    bars = [
        make_bar(0, 100),
        make_bar(1, 100.5),
        make_bar(2, 101, open_=101, high=101.1, low=100.9),
        make_bar(3, 102.6, high=102.7, low=102.0),
    ]
    run = _replay(bars, [_candidate(bars[1])])
    trade = [trade for trade in run.trades if trade.status == "TAKEN"][0]
    assert trade.entry_price == 101
    assert trade.exit_reason == "target_2"
    assert trade.realized_r == 1.5
    assert run.metrics["target_2_hit_rate"] == 1


def test_replay_long_stop_hit(make_bar) -> None:
    bars = [
        make_bar(0, 100),
        make_bar(1, 100.5),
        make_bar(2, 101, open_=101, high=101.1, low=100.9),
        make_bar(3, 99.8, high=100.2, low=99.8),
    ]
    trade = [trade for trade in _replay(bars, [_candidate(bars[1])]).trades if trade.status == "TAKEN"][0]
    assert trade.exit_reason == "stop"
    assert trade.realized_r == -1


def test_replay_short_target_and_stop(make_bar) -> None:
    winner = [
        make_bar(0, 100),
        make_bar(1, 99.5),
        make_bar(2, 99, open_=99, high=99.1, low=98.9),
        make_bar(3, 97.4, high=98.0, low=97.4),
    ]
    loser = [
        make_bar(0, 100),
        make_bar(1, 99.5),
        make_bar(2, 99, open_=99, high=99.1, low=98.9),
        make_bar(3, 100.2, high=100.2, low=99.8),
    ]
    short_candidate = _candidate(winner[1], side=Side.SHORT.value)
    short_candidate["invalidation_context"] = {"opening_range_high": 100.0, "premarket_high": 100.5}
    winner_trade = [trade for trade in _replay(winner, [short_candidate]).trades if trade.status == "TAKEN"][0]
    loser_candidate = _candidate(loser[1], side=Side.SHORT.value)
    loser_candidate["invalidation_context"] = {"opening_range_high": 100.0, "premarket_high": 100.5}
    loser_trade = [trade for trade in _replay(loser, [loser_candidate]).trades if trade.status == "TAKEN"][0]
    assert winner_trade.exit_reason == "target_2"
    assert loser_trade.exit_reason == "stop"


def test_replay_time_exit_and_mfe_mae(make_bar) -> None:
    bars = [
        make_bar(0, 100),
        make_bar(1, 100.5),
        make_bar(2, 101, open_=101, high=101.2, low=100.8),
        make_bar(3, 101.1, high=101.3, low=100.7),
    ]
    config = ReplayConfig(symbols=("AAPL",), intervals=("1min",), max_hold_minutes=1)
    trade = [trade for trade in _replay(bars, [_candidate(bars[1])], config).trades if trade.status == "TAKEN"][0]
    assert trade.exit_reason == "time_exit"
    assert trade.mfe_r > 0
    assert trade.mae_r < 0


def test_replay_same_bar_conservative_stop_first(make_bar) -> None:
    bars = [
        make_bar(0, 100),
        make_bar(1, 100.5),
        make_bar(2, 101, open_=101, high=103, low=99),
    ]
    trade = [trade for trade in _replay(bars, [_candidate(bars[1])]).trades if trade.status == "TAKEN"][0]
    assert trade.same_bar_ambiguous is True
    assert trade.ambiguity_policy == "conservative_stop_first"
    assert trade.exit_reason == "stop"


def test_replay_missing_entry_and_invalid_risk_skips(make_bar) -> None:
    bars = [make_bar(0, 100), make_bar(1, 100.5)]
    invalid = _candidate(bars[0])
    invalid["stop_price"] = 105
    run = _replay(bars, [_candidate(bars[-1]), invalid])
    skips = {trade.skip_reason for trade in run.trades if trade.status == "SKIPPED"}
    assert {"missing_entry_bar", "invalid_risk_plan"} <= skips


def test_replay_overlap_portfolio_limit_and_priority(make_bar) -> None:
    aapl = [make_bar(index, 100 + index * 0.1) for index in range(8)]
    msft = [make_bar(index, 200 + index * 0.1, symbol="MSFT") for index in range(8)]
    candidates = [
        _candidate(aapl[1], confidence=0.5),
        _candidate(aapl[2], confidence=0.9),
        _candidate(msft[1], symbol="MSFT", confidence=0.8),
    ]
    config = ReplayConfig(
        symbols=("AAPL", "MSFT"),
        intervals=("1min",),
        max_hold_minutes=4,
        max_open_trades_portfolio=1,
    )
    run = _replay([*aapl, *msft], candidates, config)
    skips = [trade.skip_reason for trade in run.trades if trade.status == "SKIPPED"]
    assert "portfolio_trade_limit" in skips

    overlap_run = _replay(
        aapl,
        [_candidate(aapl[1], confidence=0.5), _candidate(aapl[2], confidence=0.9)],
        ReplayConfig(symbols=("AAPL",), intervals=("1min",), max_hold_minutes=4, max_open_trades_portfolio=10),
    )
    assert "overlapping_trade" in [trade.skip_reason for trade in overlap_run.trades if trade.status == "SKIPPED"]


def test_replay_cooldown_after_loss(make_bar) -> None:
    bars = [
        make_bar(0, 100),
        make_bar(1, 100.5),
        make_bar(2, 101, open_=101, high=101.1, low=100.9),
        make_bar(3, 99.8, high=100.2, low=99.8),
        make_bar(4, 100.4),
        make_bar(5, 101, open_=101, high=101.1, low=100.9),
    ]
    config = ReplayConfig(symbols=("AAPL",), intervals=("1min",), cooldown_bars_after_loss=5)
    run = _replay(bars, [_candidate(bars[1]), _candidate(bars[4])], config)
    assert "cooldown_active" in {trade.skip_reason for trade in run.trades if trade.status == "SKIPPED"}


def test_replay_slippage_spread_adjustment(make_bar) -> None:
    bars = [
        make_bar(0, 100),
        make_bar(1, 100.5),
        make_bar(2, 101, open_=101, high=101.2, low=100.8),
        make_bar(3, 102.7, high=102.8, low=102.0),
    ]
    config = ReplayConfig(symbols=("AAPL",), intervals=("1min",), slippage_bps=10, spread_bps=10)
    trade = [trade for trade in _replay(bars, [_candidate(bars[1])], config).trades if trade.status == "TAKEN"][0]
    assert trade.entry_price and trade.entry_price > 101
    assert trade.slippage_bps == 10
    assert trade.spread_bps == 10


def test_replay_metrics_breakdowns_drawdown_daily_series(make_bar) -> None:
    bars = [make_bar(index, 100 + index * 0.1, high=101 + index, low=99 + index * 0.1) for index in range(8)]
    candidates = [_candidate(bars[1]), _candidate(bars[5])]
    candidates[1] = dict(candidates[1]) | {"candidate_id": "second-candidate"}
    config = ReplayConfig(symbols=("AAPL",), intervals=("1min",), allow_overlapping_trades=True)
    run = _replay(bars, candidates, config)
    assert run.metrics["profit_factor"] >= 0
    assert "AAPL" in run.metrics["per_symbol_metrics"]
    assert "VWAP reclaim long" in run.metrics["per_setup_metrics"]
    assert run.metrics["daily_r_series"]
    assert isinstance(run.metrics["drawdown_series"], list)
