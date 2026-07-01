from __future__ import annotations

import pytest

from app.signals.candidates import CandidateSignalEngine


@pytest.mark.parametrize(
    ("overrides", "setup"),
    [
        ({"close": 101, "vwap": 100, "distance_from_vwap": 0.01, "trend_slope_5": 0.01}, "VWAP reclaim long"),
        ({"close": 99, "vwap": 100, "distance_from_vwap": -0.01, "trend_slope_5": -0.01}, "VWAP loss short"),
        ({"opening_range_breakout": True}, "opening range breakout long"),
        ({"opening_range_breakdown": True}, "opening range breakdown short"),
        ({"close": 105, "previous_close": 99, "premarket_high": 104}, "premarket high breakout long"),
        ({"close": 95, "previous_close": 100, "premarket_low": 96}, "premarket low breakdown short"),
        ({"close": 105, "previous_close": 100, "previous_day_high": 104}, "previous day high reclaim long"),
        ({"close": 95, "previous_close": 100, "previous_day_low": 96}, "previous day low loss short"),
        ({"sweep_below_previous_day_low": True}, "liquidity sweep reversal long"),
        ({"sweep_above_previous_day_high": True}, "liquidity sweep reversal short"),
        ({"failed_breakout": True}, "failed breakout short"),
        ({"failed_breakdown": True}, "failed breakdown long"),
        ({"trend_slope_5": 0.01, "trend_slope_20": 0.004}, "trend continuation long"),
        ({"trend_slope_5": -0.01, "trend_slope_20": -0.004}, "trend continuation short"),
    ],
)
def test_candidate_setup_types(feature_for_bar, make_bar, overrides, setup) -> None:
    feature = feature_for_bar(make_bar(1, 100), **overrides)
    candidates = CandidateSignalEngine().detect_actionable(feature)
    assert setup in {candidate.setup_type for candidate in candidates}


def test_candidate_no_trade_is_deterministic(feature_for_bar, make_bar) -> None:
    feature = feature_for_bar(
        make_bar(1, 100),
        distance_from_vwap=0,
        relative_volume=0.5,
        trend_slope_5=0,
        opening_range_breakout=False,
    )
    candidate = CandidateSignalEngine().detect(feature)[0]
    assert candidate.side == "NO_TRADE"
    assert candidate.reason_codes == ("no_setup_qualified",)
