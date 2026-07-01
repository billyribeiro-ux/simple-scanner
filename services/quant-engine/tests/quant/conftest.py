from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.schemas.market import Bar, Label, Outcome, Side
from app.utils.time import UTC

ET = ZoneInfo("America/New_York")


def _make_bar(
    minute_index: int,
    close: float,
    symbol: str = "AAPL",
    day: int = 1,
    interval: str = "1min",
    volume: int = 1000,
    open_: float | None = None,
    high: float | None = None,
    low: float | None = None,
    hour: int = 9,
    minute: int = 30,
) -> Bar:
    timestamp_et = datetime(2026, 6, day, hour, minute, tzinfo=ET) + timedelta(minutes=minute_index)
    timestamp_utc = timestamp_et.astimezone(UTC)
    open_value = close if open_ is None else open_
    return Bar(
        symbol=symbol,
        interval=interval,
        timestamp_utc=timestamp_utc,
        timestamp_et=timestamp_et,
        open=open_value,
        high=close + 0.2 if high is None else high,
        low=close - 0.2 if low is None else low,
        close=close,
        volume=volume,
        source="synthetic",
    )


def _feature_for_bar(bar: Bar, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "feature_set_version": "test",
        "symbol": bar.symbol,
        "interval": bar.interval,
        "timestamp": bar.timestamp_utc.isoformat(),
        "timestamp_utc": bar.timestamp_utc,
        "timestamp_et": bar.timestamp_et,
        "session_date": bar.timestamp_et.date().isoformat(),
        "close": bar.close,
        "previous_close": bar.open,
        "vwap": bar.close - 0.5,
        "distance_from_vwap": 0.005,
        "relative_volume": 1.5,
        "trend_slope_5": 0.006,
        "trend_slope_20": 0.002,
        "atr_14": 1.0,
        "atr_14_proxy": 1.0,
        "opening_range_low": bar.close - 1.0,
        "opening_range_high": bar.close + 1.0,
        "market_regime": "trend_long",
        "time_bucket": "opening_drive",
        "data_quality_flags": [],
    }
    payload.update(overrides)
    return payload


def _make_label(
    index: int,
    realized_r: float,
    outcome: Outcome,
    symbol: str = "AAPL",
    setup_type: str = "VWAP reclaim long",
    side: Side = Side.LONG,
) -> Label:
    timestamp = datetime(2026, 6, 1, 13, 30, tzinfo=UTC) + timedelta(minutes=index)
    return Label(
        label_id=f"label-{symbol}-{index}",
        symbol=symbol,
        timestamp=timestamp,
        side=side,
        entry_price=100,
        stop_price=99 if side == Side.LONG else 101,
        target_1=101 if side == Side.LONG else 99,
        target_2=101.5 if side == Side.LONG else 98.5,
        target_3=102.5 if side == Side.LONG else 97.5,
        max_favorable_excursion=max(realized_r, 0),
        max_adverse_excursion=min(realized_r, 0),
        hit_target_1=realized_r >= 1,
        hit_target_2=realized_r >= 1.5,
        hit_target_3=realized_r >= 2.5,
        hit_stop=realized_r < 0,
        time_to_target=2 if realized_r > 0 else None,
        time_to_stop=1 if realized_r < 0 else None,
        realized_r=realized_r,
        outcome=outcome,
        setup_type=setup_type,
        market_regime="trend_long",
    )


@pytest.fixture
def make_bar():
    return _make_bar


@pytest.fixture
def feature_for_bar():
    return _feature_for_bar


@pytest.fixture
def make_label():
    return _make_label
