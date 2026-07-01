from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.schemas.market import Bar, Side
from app.signals.engine import SignalEngine


def test_signal_suppresses_hostile_regime() -> None:
    timestamp = datetime(2026, 6, 1, 14, 0, tzinfo=UTC)
    bar = Bar(
        symbol="AAPL",
        interval="1min",
        timestamp_utc=timestamp,
        timestamp_et=timestamp.astimezone(ZoneInfo("America/New_York")),
        open=100,
        high=101,
        low=99.8,
        close=100.8,
        volume=2000,
    )
    feature = {
        "close": 100.8,
        "vwap": 100,
        "distance_from_vwap": 0.008,
        "relative_volume": 2.0,
        "trend_slope_5": 0.006,
        "market_regime": "chop",
        "ticker_regime": "chop",
        "atr_14_proxy": 0.5,
    }
    model = {
        "model_version": "test",
        "statistical_evidence": {
            "AAPL|VWAP reclaim long|chop": {
                "sample_size": 100,
                "win_rate": 0.65,
                "average_r": 0.4,
            }
        },
    }
    signal = SignalEngine().generate(bar, feature, model, confidence_threshold=0.7)
    assert signal.side == Side.NO_TRADE
    assert signal.warnings
