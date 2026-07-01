from __future__ import annotations

from app.features.engine import FeatureEngine


def test_grouped_vwap_does_not_cross_symbols_or_sessions(make_bar) -> None:
    bars = [
        make_bar(0, 100, symbol="AAPL", day=1),
        make_bar(1, 102, symbol="AAPL", day=1),
        make_bar(0, 200, symbol="AAPL", day=2),
        make_bar(0, 50, symbol="TSLA", day=1),
    ]
    features = FeatureEngine().build_features(bars)
    by_key = {(row["symbol"], row["session_date"], row["timestamp"]): row for row in features}
    day2 = [row for row in by_key.values() if row["symbol"] == "AAPL" and row["session_date"] == "2026-06-02"][0]
    tsla = [row for row in by_key.values() if row["symbol"] == "TSLA"][0]
    assert abs(float(day2["vwap"]) - 200.0) < 0.25
    assert abs(float(tsla["vwap"]) - 50.0) < 0.25


def test_true_atr_uses_previous_close(make_bar) -> None:
    bars = [
        make_bar(0, 100, high=101, low=99),
        make_bar(1, 110, open_=109, high=112, low=108),
    ]
    features = FeatureEngine(atr_period=2).build_features(bars)
    assert features[1]["true_range"] == 12
    assert features[1]["atr_14"] == 7


def test_previous_day_levels_do_not_use_current_day_future(make_bar) -> None:
    bars = [
        make_bar(0, 100, day=1, high=110, low=90),
        make_bar(1, 105, day=1, high=111, low=95),
        make_bar(0, 101, day=2, high=130, low=100),
        make_bar(1, 120, day=2, high=140, low=119),
    ]
    day2_first = [
        row for row in FeatureEngine().build_features(bars) if row["session_date"] == "2026-06-02"
    ][0]
    assert day2_first["previous_day_high"] == 111
    assert day2_first["previous_day_high"] != 140


def test_same_time_relative_volume_uses_prior_sessions_only(make_bar) -> None:
    bars = [
        make_bar(0, 100, day=1, volume=100),
        make_bar(0, 101, day=2, volume=250),
    ]
    day2 = [row for row in FeatureEngine().build_features(bars) if row["session_date"] == "2026-06-02"][0]
    assert day2["same_time_relative_volume"] == 2.5


def test_opening_range_is_incomplete_until_window_finishes(make_bar) -> None:
    bars = [
        make_bar(0, 100, high=101, low=99),
        make_bar(14, 101, high=102, low=100),
        make_bar(15, 103, high=104, low=102),
    ]
    features = FeatureEngine(opening_range_minutes=15).build_features(bars)
    assert features[0]["opening_range_high"] is None
    assert "opening_range_incomplete" in features[0]["data_quality_flags"]
    assert features[-1]["opening_range_high"] == 102
    assert features[-1]["opening_range_breakout"] is True


def test_relative_strength_aligns_by_timestamp(make_bar) -> None:
    bars = [
        make_bar(0, 100, symbol="AAPL"),
        make_bar(1, 104, symbol="AAPL"),
        make_bar(0, 400, symbol="SPY"),
        make_bar(1, 404, symbol="SPY"),
        make_bar(0, 300, symbol="QQQ"),
        make_bar(1, 300, symbol="QQQ"),
    ]
    aapl_second = [
        row for row in FeatureEngine().build_features(bars) if row["symbol"] == "AAPL" and row["close"] == 104
    ][0]
    assert aapl_second["relative_strength_vs_spy"] > 0
    assert aapl_second["relative_strength_vs_qqq"] > 0


def test_data_quality_flags_duplicates_and_invalid_prices(make_bar) -> None:
    first = make_bar(0, 100)
    duplicate = make_bar(0, -1)
    features = FeatureEngine().build_features([first, duplicate])
    flags = [flag for row in features for flag in row["data_quality_flags"]]
    assert "duplicate_timestamp" in flags
    assert "zero_or_negative_price" in flags
