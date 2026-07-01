from __future__ import annotations

from datetime import date, datetime
from typing import Any

from app.quant.types import CandidateSignal
from app.utils.time import UTC


LONG = "LONG"
SHORT = "SHORT"
NO_TRADE = "NO_TRADE"


def _float(feature: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = feature.get(key)
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _bool(feature: dict[str, Any], key: str) -> bool:
    return bool(feature.get(key))


class CandidateSignalEngine:
    def detect(self, feature: dict[str, Any]) -> list[CandidateSignal]:
        candidates = self.detect_actionable(feature)
        if candidates:
            return candidates
        return [self._candidate(feature, NO_TRADE, "no qualified setup", ("no_setup_qualified",), ())]

    def detect_actionable(self, feature: dict[str, Any]) -> list[CandidateSignal]:
        close = _float(feature, "close")
        previous_close = feature.get("previous_close")
        previous_close_value = float(previous_close) if previous_close is not None else None
        vwap = _float(feature, "vwap")
        distance = _float(feature, "distance_from_vwap")
        rel_volume = _float(feature, "relative_volume")
        trend_5 = _float(feature, "trend_slope_5")
        trend_20 = _float(feature, "trend_slope_20")
        candidates: list[CandidateSignal] = []

        if vwap and close > vwap and distance > 0.0015 and trend_5 >= 0 and rel_volume >= 1.05:
            candidates.append(
                self._candidate(
                    feature,
                    LONG,
                    "VWAP reclaim long",
                    ("vwap_reclaim", "positive_short_term_slope"),
                    ("vwap", "distance_from_vwap", "trend_slope_5", "relative_volume"),
                )
            )
        if vwap and close < vwap and distance < -0.0015 and trend_5 <= 0 and rel_volume >= 1.05:
            candidates.append(
                self._candidate(
                    feature,
                    SHORT,
                    "VWAP loss short",
                    ("vwap_loss", "negative_short_term_slope"),
                    ("vwap", "distance_from_vwap", "trend_slope_5", "relative_volume"),
                )
            )

        if _bool(feature, "opening_range_breakout") and rel_volume >= 1.1:
            candidates.append(
                self._candidate(
                    feature,
                    LONG,
                    "opening range breakout long",
                    ("opening_range_breakout", "volume_confirmation"),
                    ("opening_range_high", "relative_volume"),
                )
            )
        if _bool(feature, "opening_range_breakdown") and rel_volume >= 1.1:
            candidates.append(
                self._candidate(
                    feature,
                    SHORT,
                    "opening range breakdown short",
                    ("opening_range_breakdown", "volume_confirmation"),
                    ("opening_range_low", "relative_volume"),
                )
            )

        if self._crossed_above(close, previous_close_value, feature.get("premarket_high")):
            candidates.append(
                self._candidate(
                    feature,
                    LONG,
                    "premarket high breakout long",
                    ("premarket_high_break",),
                    ("premarket_high",),
                )
            )
        if self._crossed_below(close, previous_close_value, feature.get("premarket_low")):
            candidates.append(
                self._candidate(
                    feature,
                    SHORT,
                    "premarket low breakdown short",
                    ("premarket_low_break",),
                    ("premarket_low",),
                )
            )
        if self._crossed_above(close, previous_close_value, feature.get("previous_day_high")):
            candidates.append(
                self._candidate(
                    feature,
                    LONG,
                    "previous day high reclaim long",
                    ("previous_day_high_reclaim",),
                    ("previous_day_high",),
                )
            )
        if self._crossed_below(close, previous_close_value, feature.get("previous_day_low")):
            candidates.append(
                self._candidate(
                    feature,
                    SHORT,
                    "previous day low loss short",
                    ("previous_day_low_loss",),
                    ("previous_day_low",),
                )
            )

        if _bool(feature, "sweep_below_previous_day_low") or _bool(feature, "sweep_below_premarket_low") or _bool(
            feature, "sweep_below_opening_range_low"
        ):
            candidates.append(
                self._candidate(
                    feature,
                    LONG,
                    "liquidity sweep reversal long",
                    ("liquidity_sweep_below_reversal",),
                    ("previous_day_low", "premarket_low", "opening_range_low"),
                )
            )
        if _bool(feature, "sweep_above_previous_day_high") or _bool(feature, "sweep_above_premarket_high") or _bool(
            feature, "sweep_above_opening_range_high"
        ):
            candidates.append(
                self._candidate(
                    feature,
                    SHORT,
                    "liquidity sweep reversal short",
                    ("liquidity_sweep_above_reversal",),
                    ("previous_day_high", "premarket_high", "opening_range_high"),
                )
            )

        if _bool(feature, "failed_breakout"):
            candidates.append(
                self._candidate(
                    feature,
                    SHORT,
                    "failed breakout short",
                    ("failed_breakout",),
                    ("previous_day_high", "premarket_high", "opening_range_high"),
                )
            )
        if _bool(feature, "failed_breakdown"):
            candidates.append(
                self._candidate(
                    feature,
                    LONG,
                    "failed breakdown long",
                    ("failed_breakdown",),
                    ("previous_day_low", "premarket_low", "opening_range_low"),
                )
            )

        if trend_5 > 0.004 and (trend_20 >= 0 or rel_volume >= 1.2):
            candidates.append(
                self._candidate(
                    feature,
                    LONG,
                    "trend continuation long",
                    ("trend_continuation_positive",),
                    ("trend_slope_5", "trend_slope_20", "relative_volume"),
                )
            )
        if trend_5 < -0.004 and (trend_20 <= 0 or rel_volume >= 1.2):
            candidates.append(
                self._candidate(
                    feature,
                    SHORT,
                    "trend continuation short",
                    ("trend_continuation_negative",),
                    ("trend_slope_5", "trend_slope_20", "relative_volume"),
                )
            )
        return candidates

    def _candidate(
        self,
        feature: dict[str, Any],
        side: str,
        setup_type: str,
        reason_codes: tuple[str, ...],
        required_feature_names: tuple[str, ...],
    ) -> CandidateSignal:
        timestamp_utc = feature.get("timestamp_utc")
        if not isinstance(timestamp_utc, datetime):
            timestamp_value = feature.get("timestamp")
            timestamp_utc = (
                datetime.fromisoformat(str(timestamp_value))
                if timestamp_value is not None
                else datetime.now(UTC)
            )
        timestamp_et = feature.get("timestamp_et")
        if not isinstance(timestamp_et, datetime):
            timestamp_et = timestamp_utc
        session_date_value = feature.get("session_date")
        if isinstance(session_date_value, date):
            session_date = session_date_value
        elif session_date_value is None:
            session_date = timestamp_et.date()
        else:
            session_date = date.fromisoformat(str(session_date_value))
        warnings = tuple(str(flag) for flag in feature.get("data_quality_flags", []) or [])
        return CandidateSignal(
            symbol=str(feature["symbol"]),
            interval=str(feature.get("interval") or "1min"),
            timestamp_utc=timestamp_utc,
            timestamp_et=timestamp_et,
            session_date=session_date,
            side=side,
            setup_type=setup_type,
            entry_context={
                "close": feature.get("close"),
                "vwap": feature.get("vwap"),
                "atr_14": feature.get("atr_14"),
                "time_bucket": feature.get("time_bucket"),
            },
            invalidation_context={
                "previous_day_high": feature.get("previous_day_high"),
                "previous_day_low": feature.get("previous_day_low"),
                "premarket_high": feature.get("premarket_high"),
                "premarket_low": feature.get("premarket_low"),
                "opening_range_high": feature.get("opening_range_high"),
                "opening_range_low": feature.get("opening_range_low"),
            },
            required_feature_names=required_feature_names,
            reason_codes=reason_codes,
            warning_codes=warnings,
        )

    def _crossed_above(self, close: float, previous_close: float | None, level: object) -> bool:
        if level is None:
            return False
        level_value = float(level)
        return close > level_value and (previous_close is None or previous_close <= level_value)

    def _crossed_below(self, close: float, previous_close: float | None, level: object) -> bool:
        if level is None:
            return False
        level_value = float(level)
        return close < level_value and (previous_close is None or previous_close >= level_value)
