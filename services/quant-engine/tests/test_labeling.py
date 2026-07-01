from datetime import datetime, timedelta

from app.utils.time import UTC
from zoneinfo import ZoneInfo

from app.features.engine import FeatureEngine
from app.labels.engine import LabelingEngine
from app.schemas.market import Bar, Outcome, Side


def bar(index: int, close: float, volume: int = 1000) -> Bar:
    timestamp = datetime(2026, 6, 1, 13, 30, tzinfo=UTC) + timedelta(minutes=index)
    et = timestamp.astimezone(ZoneInfo("America/New_York"))
    return Bar(
        symbol="AAPL",
        interval="1min",
        timestamp_utc=timestamp,
        timestamp_et=et,
        open=close - 0.05,
        high=close + 0.25,
        low=close - 0.15,
        close=close,
        volume=volume,
    )


def test_label_uses_future_after_candidate() -> None:
    bars = [bar(0, 100.0), bar(1, 100.8, 2500), bar(2, 102.2, 2600), bar(3, 102.8, 2600)]
    features = FeatureEngine().build_features(bars)
    for feature in features:
        feature["market_regime"] = "trend_long"
    labels = LabelingEngine(max_hold_bars=3, target_r=1.5).build_labels(bars, features)
    assert labels
    assert all(label.timestamp < bars[-1].timestamp_utc for label in labels)
    assert labels[0].side in {Side.LONG, Side.SHORT}
    assert labels[0].outcome in {Outcome.WIN, Outcome.LOSS, Outcome.NEUTRAL}
