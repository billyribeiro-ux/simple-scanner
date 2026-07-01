from __future__ import annotations

from collections import deque
from statistics import mean, pstdev

from app.schemas.market import Bar


FEATURE_SET_VERSION = "features.v1"


def _safe_div(numerator: float, denominator: float) -> float:
    if abs(denominator) < 1e-12:
        return 0.0
    return numerator / denominator


class FeatureEngine:
    def build_features(self, bars: list[Bar]) -> list[dict[str, object]]:
        ordered = sorted(bars, key=lambda bar: bar.timestamp_utc)
        output: list[dict[str, object]] = []
        rolling_closes: deque[float] = deque(maxlen=20)
        rolling_highs: deque[float] = deque(maxlen=20)
        rolling_lows: deque[float] = deque(maxlen=20)
        rolling_volumes: deque[int] = deque(maxlen=20)
        rolling_ranges: deque[float] = deque(maxlen=14)
        cumulative_pv = 0.0
        cumulative_volume = 0
        day_high = float("-inf")
        day_low = float("inf")
        opening_range_high: float | None = None
        opening_range_low: float | None = None
        premarket_high: float | None = None
        premarket_low: float | None = None

        for index, bar in enumerate(ordered):
            minute = bar.timestamp_et.hour * 60 + bar.timestamp_et.minute
            in_premarket = minute < 9 * 60 + 30
            in_opening_range = 9 * 60 + 30 <= minute < 9 * 60 + 45

            if in_premarket:
                premarket_high = bar.high if premarket_high is None else max(premarket_high, bar.high)
                premarket_low = bar.low if premarket_low is None else min(premarket_low, bar.low)
            if in_opening_range:
                opening_range_high = (
                    bar.high if opening_range_high is None else max(opening_range_high, bar.high)
                )
                opening_range_low = (
                    bar.low if opening_range_low is None else min(opening_range_low, bar.low)
                )

            typical_price = (bar.high + bar.low + bar.close) / 3.0
            cumulative_pv += typical_price * max(bar.volume, 0)
            cumulative_volume += max(bar.volume, 0)
            vwap = _safe_div(cumulative_pv, cumulative_volume) if cumulative_volume else bar.close
            day_high = max(day_high, bar.high)
            day_low = min(day_low, bar.low)
            candle_range = max(bar.high - bar.low, 0.0)
            body = abs(bar.close - bar.open)
            upper_wick = max(bar.high - max(bar.open, bar.close), 0.0)
            lower_wick = max(min(bar.open, bar.close) - bar.low, 0.0)
            rolling_ranges.append(candle_range)
            avg_range = mean(rolling_ranges) if rolling_ranges else candle_range
            rolling_volume_avg = mean(rolling_volumes) if rolling_volumes else float(bar.volume)
            volume_std = pstdev(rolling_volumes) if len(rolling_volumes) > 1 else 0.0
            previous_close = rolling_closes[-1] if rolling_closes else bar.open
            ret_1 = _safe_div(bar.close - previous_close, previous_close)
            ret_5 = 0.0
            if len(rolling_closes) >= 5:
                ret_5 = _safe_div(bar.close - list(rolling_closes)[-5], list(rolling_closes)[-5])

            feature = {
                "feature_set_version": FEATURE_SET_VERSION,
                "symbol": bar.symbol,
                "timestamp": bar.timestamp_utc.isoformat(),
                "close": bar.close,
                "return_1": ret_1,
                "return_5": ret_5,
                "candle_body_ratio": _safe_div(body, candle_range),
                "upper_wick_ratio": _safe_div(upper_wick, candle_range),
                "lower_wick_ratio": _safe_div(lower_wick, candle_range),
                "rolling_high_20": max([bar.high, *rolling_highs]),
                "rolling_low_20": min([bar.low, *rolling_lows]),
                "vwap": vwap,
                "distance_from_vwap": _safe_div(bar.close - vwap, vwap),
                "atr_14_proxy": avg_range,
                "distance_from_atr_band": _safe_div(bar.close - vwap, avg_range),
                "day_high": day_high,
                "day_low": day_low,
                "opening_range_high": opening_range_high,
                "opening_range_low": opening_range_low,
                "premarket_high": premarket_high,
                "premarket_low": premarket_low,
                "volume": bar.volume,
                "relative_volume": _safe_div(float(bar.volume), rolling_volume_avg),
                "volume_zscore": _safe_div(float(bar.volume) - rolling_volume_avg, volume_std),
                "trend_slope_5": ret_5,
                "time_of_day_minutes": minute,
                "is_opening_drive": 570 <= minute < 600,
                "is_lunch_chop": 690 <= minute < 810,
                "is_power_hour": minute >= 900,
                "day_of_week": bar.timestamp_et.weekday(),
            }
            output.append(feature)
            rolling_closes.append(bar.close)
            rolling_highs.append(bar.high)
            rolling_lows.append(bar.low)
            rolling_volumes.append(bar.volume)
        return output
