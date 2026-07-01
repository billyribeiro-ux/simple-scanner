from __future__ import annotations

from statistics import mean

from app.schemas.market import Bar


class RegimeClassifier:
    def classify_market(self, bars: list[Bar]) -> str:
        if len(bars) < 5:
            return "mixed_uncertain"
        ordered = sorted(bars, key=lambda bar: bar.timestamp_utc)
        closes = [bar.close for bar in ordered[-20:]]
        ranges = [max(bar.high - bar.low, 0.0) for bar in ordered[-20:]]
        start = closes[0]
        end = closes[-1]
        slope = (end - start) / start if start else 0.0
        avg_range = mean(ranges) if ranges else 0.0
        range_pct = avg_range / end if end else 0.0
        minute = ordered[-1].timestamp_et.hour * 60 + ordered[-1].timestamp_et.minute
        if 570 <= minute < 600 and abs(slope) > 0.002:
            return "opening_drive"
        if range_pct > 0.01:
            return "high_volatility"
        if slope > 0.004:
            return "trend_long"
        if slope < -0.004:
            return "trend_short"
        if range_pct < 0.002:
            return "chop"
        return "mean_reversion"

    def classify_ticker(self, features: dict[str, object]) -> str:
        rel_volume = float(features.get("relative_volume") or 0.0)
        trend = float(features.get("trend_slope_5") or 0.0)
        distance = float(features.get("distance_from_vwap") or 0.0)
        if rel_volume > 2.0 and abs(trend) > 0.004:
            return "single_stock_momentum"
        if abs(distance) < 0.001 and rel_volume < 0.8:
            return "chop"
        if trend > 0.003:
            return "trend_long"
        if trend < -0.003:
            return "trend_short"
        return "mixed_uncertain"
