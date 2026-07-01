from __future__ import annotations

from app.labels.engine import LabelSettings, LabelingEngine
from app.schemas.market import Outcome, Side


def build_label(bars, feature_for_bar, overrides=None, settings=None):
    feature = feature_for_bar(bars[1], **(overrides or {}))
    return LabelingEngine(settings=settings or LabelSettings(minimum_bars_before_label=0)).build_labels(
        bars, [feature]
    )[0]


def test_long_winner_next_bar_open(make_bar, feature_for_bar) -> None:
    bars = [
        make_bar(0, 100),
        make_bar(1, 100.5),
        make_bar(2, 101, open_=101, high=101.2, low=100.8),
        make_bar(3, 103, high=103.5, low=102.5),
    ]
    label = build_label(bars, feature_for_bar)
    assert label.side == Side.LONG
    assert label.entry_price == 101
    assert label.outcome == Outcome.WIN


def test_long_loser(make_bar, feature_for_bar) -> None:
    bars = [
        make_bar(0, 100),
        make_bar(1, 100.5),
        make_bar(2, 101, open_=101, high=101.2, low=100.8),
        make_bar(3, 99, high=100, low=99),
    ]
    label = build_label(bars, feature_for_bar)
    assert label.outcome == Outcome.LOSS
    assert label.hit_stop is True


def test_short_winner(make_bar, feature_for_bar) -> None:
    bars = [
        make_bar(0, 100),
        make_bar(1, 99.5),
        make_bar(2, 99, open_=99, high=99.2, low=98.8),
        make_bar(3, 97, high=97.5, low=96.5),
    ]
    label = build_label(
        bars,
        feature_for_bar,
        {"vwap": 100, "distance_from_vwap": -0.006, "trend_slope_5": -0.006},
    )
    assert label.side == Side.SHORT
    assert label.outcome == Outcome.WIN


def test_short_loser(make_bar, feature_for_bar) -> None:
    bars = [
        make_bar(0, 100),
        make_bar(1, 99.5),
        make_bar(2, 99, open_=99, high=99.2, low=98.8),
        make_bar(3, 101, high=101, low=100),
    ]
    label = build_label(
        bars,
        feature_for_bar,
        {"vwap": 100, "distance_from_vwap": -0.006, "trend_slope_5": -0.006},
    )
    assert label.outcome == Outcome.LOSS


def test_neutral_time_exit(make_bar, feature_for_bar) -> None:
    bars = [
        make_bar(0, 100),
        make_bar(1, 100.5),
        make_bar(2, 101, open_=101, high=101.2, low=100.8),
        make_bar(3, 101.1, high=101.2, low=100.9),
    ]
    label = build_label(bars, feature_for_bar)
    assert label.outcome == Outcome.NEUTRAL


def test_same_bar_stop_target_conservative_stop_first(make_bar, feature_for_bar) -> None:
    bars = [
        make_bar(0, 100),
        make_bar(1, 100.5),
        make_bar(2, 101, open_=101, high=103, low=99),
    ]
    label = build_label(bars, feature_for_bar)
    assert label.outcome == Outcome.LOSS
    assert label.hit_stop is True


def test_no_label_when_next_bar_missing(make_bar, feature_for_bar) -> None:
    bars = [make_bar(0, 100), make_bar(1, 100.5)]
    feature = feature_for_bar(bars[1])
    labels = LabelingEngine(settings=LabelSettings(minimum_bars_before_label=0)).build_labels(bars, [feature])
    assert labels == []


def test_stop_does_not_use_future_bars(make_bar, feature_for_bar) -> None:
    bars = [
        make_bar(0, 100, low=99.8),
        make_bar(1, 100.5, low=100.0),
        make_bar(2, 101, open_=101, high=101.2, low=100.8),
        make_bar(3, 90, high=91, low=89),
    ]
    label = build_label(bars, feature_for_bar)
    assert label.stop_price > 89


def test_no_overlapping_trades_when_disabled(make_bar, feature_for_bar) -> None:
    bars = [
        make_bar(0, 100),
        make_bar(1, 100.5),
        make_bar(2, 101, open_=101, high=101.2, low=100.8),
        make_bar(3, 101.2),
        make_bar(4, 103, high=103.5, low=102.5),
    ]
    features = [
        feature_for_bar(bars[1]),
        feature_for_bar(bars[2], trend_slope_5=0.001, trend_slope_20=0.0),
    ]
    labels = LabelingEngine(settings=LabelSettings(minimum_bars_before_label=0)).build_labels(bars, features)
    assert len(labels) == 1
