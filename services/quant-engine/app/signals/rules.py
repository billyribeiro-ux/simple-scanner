from __future__ import annotations

from app.schemas.market import Side


class SetupRuleEngine:
    def detect(self, features: dict[str, object]) -> tuple[Side, str, list[str]]:
        close = float(features.get("close") or 0.0)
        vwap = float(features.get("vwap") or 0.0)
        distance = float(features.get("distance_from_vwap") or 0.0)
        rel_volume = float(features.get("relative_volume") or 0.0)
        trend = float(features.get("trend_slope_5") or 0.0)
        upper_wick = float(features.get("upper_wick_ratio") or 0.0)
        lower_wick = float(features.get("lower_wick_ratio") or 0.0)
        opening_high = features.get("opening_range_high")
        opening_low = features.get("opening_range_low")
        premarket_high = features.get("premarket_high")
        premarket_low = features.get("premarket_low")
        day_high = float(features.get("day_high") or close)
        day_low = float(features.get("day_low") or close)
        reasons: list[str] = []

        if vwap and distance > 0.0015 and trend > 0 and rel_volume >= 1.1:
            reasons.append("price reclaimed and held above VWAP with positive short-term slope")
            return Side.LONG, "VWAP reclaim long", reasons
        if vwap and distance < -0.0015 and trend < 0 and rel_volume >= 1.1:
            reasons.append("price lost VWAP with negative short-term slope")
            return Side.SHORT, "VWAP loss short", reasons
        if opening_high and close > float(opening_high) and rel_volume >= 1.2:
            reasons.append("price broke above opening range on above-average volume")
            return Side.LONG, "opening range breakout long", reasons
        if opening_low and close < float(opening_low) and rel_volume >= 1.2:
            reasons.append("price broke below opening range on above-average volume")
            return Side.SHORT, "opening range breakdown short", reasons
        if premarket_high and close > float(premarket_high):
            reasons.append("price cleared premarket high")
            return Side.LONG, "premarket high breakout long", reasons
        if premarket_low and close < float(premarket_low):
            reasons.append("price broke premarket low")
            return Side.SHORT, "premarket low breakdown short", reasons
        if close >= day_high * 0.999 and upper_wick > 0.55 and rel_volume > 1.4:
            reasons.append("high-volume rejection near day high")
            return Side.SHORT, "failed breakout short", reasons
        if close <= day_low * 1.001 and lower_wick > 0.55 and rel_volume > 1.4:
            reasons.append("high-volume rejection near day low")
            return Side.LONG, "failed breakdown long", reasons
        if trend > 0.004 and rel_volume > 1.0:
            reasons.append("trend continuation pressure is positive")
            return Side.LONG, "trend continuation long", reasons
        if trend < -0.004 and rel_volume > 1.0:
            reasons.append("trend continuation pressure is negative")
            return Side.SHORT, "trend continuation short", reasons
        return Side.NO_TRADE, "no qualified setup", ["no setup met the V1 evidence threshold"]
