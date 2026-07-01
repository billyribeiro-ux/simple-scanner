from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import date, datetime
from math import isfinite
from statistics import mean, pstdev
from typing import Any
from zoneinfo import ZoneInfo

from app.utils.time import UTC


FEATURE_SET_VERSION = "features.v2.no_leakage"
ET = ZoneInfo("America/New_York")
RTH_START_MINUTE = 9 * 60 + 30
RTH_END_MINUTE = 16 * 60


@dataclass(frozen=True)
class _NormalizedBar:
    symbol: str
    interval: str
    timestamp_utc: datetime
    timestamp_et: datetime
    session_date: date
    session: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    source: str
    quality_flags: tuple[str, ...]


def _safe_div(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or abs(denominator) < 1e-12:
        return None
    return numerator / denominator


def _zero_safe(value: float | None) -> float:
    return 0.0 if value is None or not isfinite(value) else value


def _minute_of_day(timestamp_et: datetime) -> int:
    return timestamp_et.hour * 60 + timestamp_et.minute


def _session_for_minute(minute: int) -> str:
    if minute < RTH_START_MINUTE:
        return "premarket"
    if minute < RTH_END_MINUTE:
        return "rth"
    return "afterhours"


def _time_bucket(minute: int) -> str:
    if RTH_START_MINUTE <= minute < 10 * 60:
        return "opening_drive"
    if 10 * 60 <= minute < 10 * 60 + 30:
        return "ten_am_reversal_zone"
    if 11 * 60 + 30 <= minute < 13 * 60 + 30:
        return "lunch_window"
    if 13 * 60 + 30 <= minute < 15 * 60:
        return "afternoon_continuation"
    if 15 * 60 <= minute < RTH_END_MINUTE:
        return "power_hour"
    return "off_hours"


def _linear_regression_slope(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    n = len(values)
    x_mean = (n - 1) / 2
    y_mean = mean(values)
    numerator = sum((index - x_mean) * (value - y_mean) for index, value in enumerate(values))
    denominator = sum((index - x_mean) ** 2 for index in range(n))
    return _safe_div(numerator, denominator)


class FeatureEngine:
    def __init__(
        self,
        atr_period: int = 14,
        rolling_window: int = 20,
        opening_range_minutes: int = 15,
        same_time_lookback_sessions: int = 5,
    ) -> None:
        self.atr_period = atr_period
        self.rolling_window = rolling_window
        self.opening_range_minutes = opening_range_minutes
        self.same_time_lookback_sessions = same_time_lookback_sessions

    def build_features(self, bars: list[Any]) -> list[dict[str, object]]:
        normalized = [self._normalize_bar(bar) for bar in bars]
        sorted_bars = sorted(normalized, key=lambda bar: (bar.symbol, bar.interval, bar.timestamp_utc))
        if not sorted_bars:
            return []

        original_order = [(bar.symbol, bar.interval, bar.timestamp_utc) for bar in normalized]
        sorted_order = [(bar.symbol, bar.interval, bar.timestamp_utc) for bar in sorted_bars]
        globally_unsorted = original_order != sorted_order

        duplicate_keys = self._duplicate_keys(sorted_bars)
        grouped: dict[tuple[str, str, date], list[_NormalizedBar]] = defaultdict(list)
        for bar in sorted_bars:
            grouped[(bar.symbol, bar.interval, bar.session_date)].append(bar)

        same_time_volume_history: dict[tuple[str, str, int], deque[int]] = defaultdict(
            lambda: deque(maxlen=self.same_time_lookback_sessions)
        )
        previous_session_stats: dict[tuple[str, str], dict[str, float]] = {}
        output: list[dict[str, object]] = []

        sessions = sorted(grouped.items(), key=lambda item: (item[0][0], item[0][1], item[0][2]))
        for (symbol, interval, session_date), session_bars in sessions:
            previous_stats = previous_session_stats.get((symbol, interval))
            rows = self._build_session_features(
                session_bars,
                previous_stats,
                same_time_volume_history,
                duplicate_keys,
                globally_unsorted,
            )
            output.extend(rows)
            previous_session_stats[(symbol, interval)] = self._session_stats(session_bars)
            for bar in session_bars:
                same_time_volume_history[(bar.symbol, bar.interval, _minute_of_day(bar.timestamp_et))].append(
                    bar.volume
                )

        output.sort(key=lambda row: (str(row["symbol"]), str(row["interval"]), str(row["timestamp"])))
        self._attach_relative_strength(output)
        return output

    def _build_session_features(
        self,
        bars: list[_NormalizedBar],
        previous_stats: dict[str, float] | None,
        same_time_volume_history: dict[tuple[str, str, int], deque[int]],
        duplicate_keys: set[tuple[str, str, datetime]],
        globally_unsorted: bool,
    ) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        rolling_closes: deque[float] = deque(maxlen=self.rolling_window)
        rolling_highs: deque[float] = deque(maxlen=self.rolling_window)
        rolling_lows: deque[float] = deque(maxlen=self.rolling_window)
        rolling_volumes: deque[int] = deque(maxlen=self.rolling_window)
        rolling_true_ranges: deque[float] = deque(maxlen=self.atr_period)
        rolling_volume_changes: deque[float] = deque(maxlen=5)

        cumulative_pv = 0.0
        cumulative_volume = 0
        session_high = float("-inf")
        session_low = float("inf")
        premarket_high: float | None = None
        premarket_low: float | None = None
        opening_range_high: float | None = None
        opening_range_low: float | None = None
        opening_range_end = RTH_START_MINUTE + self.opening_range_minutes
        rth_open: float | None = None
        ema_9: float | None = None

        for index, bar in enumerate(bars):
            flags = set(bar.quality_flags)
            if globally_unsorted:
                flags.add("input_not_sorted_by_symbol_interval_timestamp")
            if (bar.symbol, bar.interval, bar.timestamp_utc) in duplicate_keys:
                flags.add("duplicate_timestamp")

            minute = _minute_of_day(bar.timestamp_et)
            in_premarket = bar.session == "premarket"
            in_rth = bar.session == "rth"
            in_opening_range = RTH_START_MINUTE <= minute < opening_range_end
            opening_range_complete = minute >= opening_range_end and opening_range_high is not None

            if in_rth and rth_open is None:
                rth_open = bar.open

            if in_premarket:
                premarket_high = bar.high if premarket_high is None else max(premarket_high, bar.high)
                premarket_low = bar.low if premarket_low is None else min(premarket_low, bar.low)
            if in_opening_range:
                opening_range_high = (
                    bar.high if opening_range_high is None else max(opening_range_high, bar.high)
                )
                opening_range_low = bar.low if opening_range_low is None else min(opening_range_low, bar.low)

            typical_price = (bar.high + bar.low + bar.close) / 3.0
            cumulative_pv += typical_price * max(bar.volume, 0)
            cumulative_volume += max(bar.volume, 0)
            vwap = _safe_div(cumulative_pv, float(cumulative_volume)) or bar.close

            previous_close = rolling_closes[-1] if rolling_closes else None
            true_range = self._true_range(bar, previous_close)
            rolling_true_ranges.append(true_range)
            atr = mean(rolling_true_ranges) if len(rolling_true_ranges) >= self.atr_period else None
            atr_proxy = atr if atr is not None else mean(rolling_true_ranges)
            if atr is None:
                flags.add("atr_insufficient_history")
            if previous_close is None:
                flags.add("atr_session_reset")

            session_high = max(session_high, bar.high)
            session_low = min(session_low, bar.low)
            candle_range = max(bar.high - bar.low, 0.0)
            body = abs(bar.close - bar.open)
            upper_wick = max(bar.high - max(bar.open, bar.close), 0.0)
            lower_wick = max(min(bar.open, bar.close) - bar.low, 0.0)
            close_location = _safe_div(bar.close - bar.low, candle_range)

            rolling_volume_avg = mean(rolling_volumes) if rolling_volumes else None
            rolling_relative_volume = _safe_div(float(bar.volume), rolling_volume_avg)
            if rolling_relative_volume is None:
                flags.add("rolling_relative_volume_insufficient_history")

            same_time_history = same_time_volume_history[(bar.symbol, bar.interval, minute)]
            same_time_relative_volume = (
                _safe_div(float(bar.volume), mean(same_time_history)) if same_time_history else None
            )
            if same_time_relative_volume is None:
                flags.add("same_time_rvol_insufficient_history")

            volume_std = pstdev(rolling_volumes) if len(rolling_volumes) > 1 else None
            volume_zscore = _safe_div(
                float(bar.volume) - (rolling_volume_avg or float(bar.volume)),
                volume_std,
            )
            prior_volume = rolling_volumes[-1] if rolling_volumes else None
            volume_change = None if prior_volume is None else float(bar.volume - prior_volume)
            if volume_change is not None:
                rolling_volume_changes.append(volume_change)
            volume_acceleration = (
                volume_change - mean(rolling_volume_changes)
                if volume_change is not None and len(rolling_volume_changes) > 1
                else None
            )

            ret_1 = _safe_div(bar.close - previous_close, previous_close) if previous_close else None
            ret_5 = self._rolling_return(bar.close, rolling_closes, 5)
            ret_20 = self._rolling_return(bar.close, rolling_closes, 20)
            trend_slope_5 = ret_5
            trend_slope_20 = ret_20
            regression_values = [*rolling_closes, bar.close][-20:]
            linear_slope_20 = _linear_regression_slope(regression_values)
            if ema_9 is None:
                ema_9 = bar.close
                ema_slope_9 = None
            else:
                previous_ema = ema_9
                alpha = 2 / (9 + 1)
                ema_9 = alpha * bar.close + (1 - alpha) * ema_9
                ema_slope_9 = _safe_div(ema_9 - previous_ema, previous_ema)

            abs_returns = [abs(_safe_div(rolling_closes[i] - rolling_closes[i - 1], rolling_closes[i - 1]) or 0.0) for i in range(1, len(rolling_closes))]
            trend_quality = _safe_div(abs(ret_5 or 0.0), mean(abs_returns)) if abs_returns else None

            previous_day_high = previous_stats.get("high") if previous_stats else None
            previous_day_low = previous_stats.get("low") if previous_stats else None
            previous_day_close = previous_stats.get("close") if previous_stats else None
            previous_day_range = (
                previous_day_high - previous_day_low
                if previous_day_high is not None and previous_day_low is not None
                else None
            )
            if previous_stats is None:
                flags.add("previous_day_levels_unavailable")

            if premarket_high is None or premarket_low is None:
                flags.add("premarket_levels_unavailable")
            premarket_range = (
                premarket_high - premarket_low if premarket_high is not None and premarket_low is not None else None
            )

            if not opening_range_complete:
                flags.add("opening_range_incomplete")
            opening_midpoint = (
                (opening_range_high + opening_range_low) / 2
                if opening_range_complete and opening_range_high is not None and opening_range_low is not None
                else None
            )
            opening_range = (
                opening_range_high - opening_range_low
                if opening_range_complete and opening_range_high is not None and opening_range_low is not None
                else None
            )
            position_vs_or = self._position_vs_range(bar.close, opening_range_low, opening_range_high)

            gap_pct = (
                _safe_div((rth_open or bar.open) - previous_day_close, previous_day_close)
                if previous_day_close is not None
                else None
            )
            gap_classification = self._gap_classification(gap_pct)
            gap_fill_percentage, gap_hold = self._gap_fill(
                bar, rth_open, previous_day_close, gap_classification
            )

            absorption_up = bool(
                (rolling_relative_volume or 0.0) >= 1.5
                and atr_proxy > 0
                and candle_range <= atr_proxy * 0.7
                and (close_location or 0.0) < 0.55
                and bar.close >= bar.open
            )
            absorption_down = bool(
                (rolling_relative_volume or 0.0) >= 1.5
                and atr_proxy > 0
                and candle_range <= atr_proxy * 0.7
                and (close_location or 1.0) > 0.45
                and bar.close <= bar.open
            )

            values = {
                "close": bar.close,
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "volume": bar.volume,
                "source": bar.source,
                "session": bar.session,
                "previous_close": previous_close,
                "return_1": _zero_safe(ret_1),
                "return_5": _zero_safe(ret_5),
                "rolling_return_1": ret_1,
                "rolling_return_5": ret_5,
                "rolling_return_20": ret_20,
                "range": candle_range,
                "candle_body": body,
                "upper_wick": upper_wick,
                "lower_wick": lower_wick,
                "candle_body_ratio": _zero_safe(_safe_div(body, candle_range)),
                "body_pct_range": _safe_div(body, candle_range),
                "upper_wick_ratio": _zero_safe(_safe_div(upper_wick, candle_range)),
                "upper_wick_percentage": _safe_div(upper_wick, candle_range),
                "lower_wick_ratio": _zero_safe(_safe_div(lower_wick, candle_range)),
                "lower_wick_percentage": _safe_div(lower_wick, candle_range),
                "close_location": close_location,
                "rolling_high_20": max([bar.high, *rolling_highs]),
                "rolling_low_20": min([bar.low, *rolling_lows]),
                "vwap": vwap,
                "distance_from_vwap": _zero_safe(_safe_div(bar.close - vwap, vwap)),
                "true_range": true_range,
                "atr_14": atr,
                "atr_14_proxy": atr_proxy,
                "distance_from_atr_band": _zero_safe(_safe_div(bar.close - vwap, atr_proxy)),
                "day_high": session_high,
                "day_low": session_low,
                "previous_day_high": previous_day_high,
                "previous_day_low": previous_day_low,
                "previous_day_close": previous_day_close,
                "previous_day_range": previous_day_range,
                "distance_to_previous_day_high": self._distance_to_level(bar.close, previous_day_high),
                "distance_to_previous_day_low": self._distance_to_level(bar.close, previous_day_low),
                "premarket_high": premarket_high,
                "premarket_low": premarket_low,
                "premarket_range": premarket_range,
                "distance_to_premarket_high": self._distance_to_level(bar.close, premarket_high),
                "distance_to_premarket_low": self._distance_to_level(bar.close, premarket_low),
                "opening_range_high": opening_range_high if opening_range_complete else None,
                "opening_range_low": opening_range_low if opening_range_complete else None,
                "opening_range_midpoint": opening_midpoint,
                "opening_range_range": opening_range,
                "position_relative_to_opening_range": position_vs_or if opening_range_complete else None,
                "opening_range_breakout": bool(opening_range_complete and opening_range_high and bar.close > opening_range_high),
                "opening_range_breakdown": bool(opening_range_complete and opening_range_low and bar.close < opening_range_low),
                "gap_percentage": gap_pct,
                "gap_classification": gap_classification,
                "gap_fill_percentage": gap_fill_percentage,
                "gap_hold": gap_hold,
                "relative_volume": rolling_relative_volume,
                "rolling_relative_volume": rolling_relative_volume,
                "same_time_relative_volume": same_time_relative_volume,
                "volume_zscore": volume_zscore,
                "volume_change": volume_change,
                "volume_acceleration": volume_acceleration,
                "trend_slope_5": _zero_safe(trend_slope_5),
                "trend_slope_20": trend_slope_20,
                "ema_9": ema_9,
                "ema_slope_9": ema_slope_9,
                "linear_regression_slope_20": linear_slope_20,
                "trend_quality_score": trend_quality,
                "absorption_up": absorption_up,
                "absorption_down": absorption_down,
                "sweep_above_previous_day_high": self._sweep_above(bar, previous_day_high),
                "sweep_below_previous_day_low": self._sweep_below(bar, previous_day_low),
                "sweep_above_premarket_high": self._sweep_above(bar, premarket_high),
                "sweep_below_premarket_low": self._sweep_below(bar, premarket_low),
                "sweep_above_opening_range_high": self._sweep_above(bar, opening_range_high if opening_range_complete else None),
                "sweep_below_opening_range_low": self._sweep_below(bar, opening_range_low if opening_range_complete else None),
                "reversal_confirmation": self._reversal_confirmation(bar, previous_close),
                "failed_breakout": self._failed_breakout(bar, previous_day_high, premarket_high, opening_range_high if opening_range_complete else None),
                "failed_breakdown": self._failed_breakdown(bar, previous_day_low, premarket_low, opening_range_low if opening_range_complete else None),
                "symbol_cumulative_intraday_return": self._session_return(bar.close, rows),
                "minute_of_day": minute,
                "time_of_day_minutes": minute,
                "time_bucket": _time_bucket(minute),
                "is_opening_drive": RTH_START_MINUTE <= minute < 10 * 60,
                "opening_drive": RTH_START_MINUTE <= minute < 10 * 60,
                "ten_am_reversal_zone": 10 * 60 <= minute < 10 * 60 + 30,
                "is_lunch_chop": 11 * 60 + 30 <= minute < 13 * 60 + 30,
                "lunch_window": 11 * 60 + 30 <= minute < 13 * 60 + 30,
                "afternoon_continuation": 13 * 60 + 30 <= minute < 15 * 60,
                "is_power_hour": 15 * 60 <= minute < RTH_END_MINUTE,
                "power_hour": 15 * 60 <= minute < RTH_END_MINUTE,
                "day_of_week": bar.timestamp_et.weekday(),
                "bar_index_in_session": index,
            }
            rows.append(
                {
                    "feature_set_version": FEATURE_SET_VERSION,
                    "symbol": bar.symbol,
                    "interval": bar.interval,
                    "timestamp": bar.timestamp_utc.isoformat(),
                    "timestamp_utc": bar.timestamp_utc,
                    "timestamp_et": bar.timestamp_et,
                    "session_date": bar.session_date.isoformat(),
                    "data_quality_flags": sorted(flags),
                    **values,
                }
            )
            rolling_closes.append(bar.close)
            rolling_highs.append(bar.high)
            rolling_lows.append(bar.low)
            rolling_volumes.append(bar.volume)
        return rows

    def _normalize_bar(self, bar: Any) -> _NormalizedBar:
        flags = set(getattr(bar, "quality_flags", []) or getattr(bar, "data_quality_flags", []) or [])
        timestamp_utc = getattr(bar, "timestamp_utc", None)
        timestamp_et = getattr(bar, "timestamp_et", None)
        if timestamp_utc is None or not isinstance(timestamp_utc, datetime):
            flags.add("timestamp_utc_missing_or_invalid")
            timestamp_utc = datetime.min.replace(tzinfo=UTC)
        if timestamp_utc.tzinfo is None:
            flags.add("timezone_missing_or_ambiguous")
            timestamp_utc = timestamp_utc.replace(tzinfo=UTC)
        timestamp_utc = timestamp_utc.astimezone(UTC)
        if timestamp_et is None or not isinstance(timestamp_et, datetime):
            timestamp_et = timestamp_utc.astimezone(ET)
        elif timestamp_et.tzinfo is None:
            flags.add("timezone_missing_or_ambiguous")
            timestamp_et = timestamp_et.replace(tzinfo=ET)
        timestamp_et = timestamp_et.astimezone(ET)

        raw_values = {
            "open": getattr(bar, "open", None),
            "high": getattr(bar, "high", None),
            "low": getattr(bar, "low", None),
            "close": getattr(bar, "close", None),
            "volume": getattr(bar, "volume", None),
        }
        for field_name, value in raw_values.items():
            if value is None:
                flags.add(f"{field_name}_missing")

        open_ = float(raw_values["open"] or 0.0)
        high = float(raw_values["high"] or 0.0)
        low = float(raw_values["low"] or 0.0)
        close = float(raw_values["close"] or 0.0)
        volume = int(raw_values["volume"] or 0)
        if min(open_, high, low, close) <= 0:
            flags.add("zero_or_negative_price")
        if high < low:
            flags.add("high_below_low")
        if volume < 0:
            flags.add("negative_volume")

        session_date = getattr(bar, "session_date", None) or timestamp_et.date()
        session = getattr(bar, "session", None) or _session_for_minute(_minute_of_day(timestamp_et))
        return _NormalizedBar(
            symbol=str(getattr(bar, "symbol", "")).upper(),
            interval=str(getattr(bar, "interval", "")),
            timestamp_utc=timestamp_utc,
            timestamp_et=timestamp_et,
            session_date=session_date,
            session=session,
            open=open_,
            high=high,
            low=low,
            close=close,
            volume=volume,
            source=str(getattr(bar, "source", "unknown")),
            quality_flags=tuple(sorted(flags)),
        )

    def _duplicate_keys(self, bars: list[_NormalizedBar]) -> set[tuple[str, str, datetime]]:
        counts: dict[tuple[str, str, datetime], int] = defaultdict(int)
        for bar in bars:
            counts[(bar.symbol, bar.interval, bar.timestamp_utc)] += 1
        return {key for key, count in counts.items() if count > 1}

    def _true_range(self, bar: _NormalizedBar, previous_close: float | None) -> float:
        if previous_close is None:
            return max(bar.high - bar.low, 0.0)
        return max(bar.high - bar.low, abs(bar.high - previous_close), abs(bar.low - previous_close))

    def _rolling_return(self, close: float, rolling_closes: deque[float], lookback: int) -> float | None:
        if len(rolling_closes) < lookback:
            return None
        base = list(rolling_closes)[-lookback]
        return _safe_div(close - base, base)

    def _session_stats(self, bars: list[_NormalizedBar]) -> dict[str, float]:
        return {
            "high": max(bar.high for bar in bars),
            "low": min(bar.low for bar in bars),
            "close": bars[-1].close,
        }

    def _position_vs_range(
        self, close: float, low: float | None, high: float | None
    ) -> str | None:
        if low is None or high is None:
            return None
        if close > high:
            return "above"
        if close < low:
            return "below"
        return "inside"

    def _distance_to_level(self, close: float, level: float | None) -> float | None:
        if level is None:
            return None
        return _safe_div(close - level, level)

    def _gap_classification(self, gap_pct: float | None) -> str:
        if gap_pct is None:
            return "unknown"
        if gap_pct > 0.001:
            return "gap_up"
        if gap_pct < -0.001:
            return "gap_down"
        return "flat"

    def _gap_fill(
        self,
        bar: _NormalizedBar,
        rth_open: float | None,
        previous_close: float | None,
        classification: str,
    ) -> tuple[float | None, bool | None]:
        if rth_open is None or previous_close is None or classification == "unknown":
            return None, None
        if classification == "gap_up":
            gap_size = rth_open - previous_close
            if gap_size <= 0:
                return None, None
            fill = min(max((rth_open - bar.low) / gap_size, 0.0), 1.0)
            return fill, bar.low > previous_close
        if classification == "gap_down":
            gap_size = previous_close - rth_open
            if gap_size <= 0:
                return None, None
            fill = min(max((bar.high - rth_open) / gap_size, 0.0), 1.0)
            return fill, bar.high < previous_close
        return 1.0, True

    def _sweep_above(self, bar: _NormalizedBar, level: float | None) -> bool:
        return bool(level is not None and bar.high > level and bar.close < level)

    def _sweep_below(self, bar: _NormalizedBar, level: float | None) -> bool:
        return bool(level is not None and bar.low < level and bar.close > level)

    def _reversal_confirmation(self, bar: _NormalizedBar, previous_close: float | None) -> bool:
        if previous_close is None:
            return False
        return (bar.close > bar.open and bar.close > previous_close) or (
            bar.close < bar.open and bar.close < previous_close
        )

    def _failed_breakout(self, bar: _NormalizedBar, *levels: float | None) -> bool:
        return any(level is not None and bar.high > level and bar.close < level for level in levels)

    def _failed_breakdown(self, bar: _NormalizedBar, *levels: float | None) -> bool:
        return any(level is not None and bar.low < level and bar.close > level for level in levels)

    def _session_return(self, close: float, rows: list[dict[str, object]]) -> float:
        if not rows:
            return 0.0
        first_close = float(rows[0]["close"])
        return _zero_safe(_safe_div(close - first_close, first_close))

    def _attach_relative_strength(self, rows: list[dict[str, object]]) -> None:
        by_timestamp: dict[tuple[str, str, str], dict[str, float]] = defaultdict(dict)
        for row in rows:
            key = (str(row["interval"]), str(row["session_date"]), str(row["timestamp"]))
            by_timestamp[key][str(row["symbol"])] = float(row["symbol_cumulative_intraday_return"])

        for row in rows:
            key = (str(row["interval"]), str(row["session_date"]), str(row["timestamp"]))
            returns = by_timestamp[key]
            symbol = str(row["symbol"])
            symbol_return = float(row["symbol_cumulative_intraday_return"])
            flags = set(row.get("data_quality_flags") or [])

            spy_return = returns.get("SPY")
            qqq_return = returns.get("QQQ")
            proxy_returns = [value for sym, value in returns.items() if sym != symbol]
            universe_median = sorted(proxy_returns)[len(proxy_returns) // 2] if proxy_returns else None
            iwm_return = returns.get("IWM")

            if symbol == "SPY":
                spy_benchmark = iwm_return if iwm_return is not None else universe_median
            else:
                spy_benchmark = spy_return
            if symbol == "QQQ":
                qqq_benchmark = iwm_return if iwm_return is not None else universe_median
            else:
                qqq_benchmark = qqq_return

            if spy_benchmark is None:
                flags.add("relative_strength_spy_unavailable")
            if qqq_benchmark is None:
                flags.add("relative_strength_qqq_unavailable")

            rs_vs_spy = symbol_return - spy_benchmark if spy_benchmark is not None else None
            rs_vs_qqq = symbol_return - qqq_benchmark if qqq_benchmark is not None else None
            row["spy_cumulative_intraday_return"] = spy_benchmark
            row["qqq_cumulative_intraday_return"] = qqq_benchmark
            row["relative_strength_vs_spy"] = rs_vs_spy
            row["relative_strength_vs_qqq"] = rs_vs_qqq
            row["leadership_score"] = mean(
                [value for value in [rs_vs_spy, rs_vs_qqq] if value is not None]
            ) if rs_vs_spy is not None or rs_vs_qqq is not None else None
            row["data_quality_flags"] = sorted(flags)
