from __future__ import annotations

from datetime import datetime

from app.utils.time import UTC
from typing import Any

from app.regimes.classifier import RegimeClassifier
from app.schemas.market import Bar, Signal, Side
from app.signals.rules import SetupRuleEngine


HOSTILE_REGIMES = {"chop", "liquidity_trap", "mixed_uncertain"}


class SignalEngine:
    def __init__(self) -> None:
        self.rules = SetupRuleEngine()
        self.regimes = RegimeClassifier()

    def generate(
        self,
        latest_bar: Bar,
        features: dict[str, object],
        model: dict[str, Any],
        confidence_threshold: float = 0.70,
    ) -> Signal:
        features = dict(features)
        features.setdefault("symbol", latest_bar.symbol)
        features.setdefault("interval", latest_bar.interval)
        features.setdefault("timestamp_utc", latest_bar.timestamp_utc)
        features.setdefault("timestamp_et", latest_bar.timestamp_et)
        features.setdefault("session_date", latest_bar.timestamp_et.date())
        side, setup_type, reasons = self.rules.detect(features)
        market_regime = str(features.get("market_regime") or "mixed_uncertain")
        ticker_regime = str(features.get("ticker_regime") or self.regimes.classify_ticker(features))
        evidence = self._evidence_for(model, latest_bar.symbol, setup_type, market_regime)
        warnings: list[str] = []
        score = self._score(features, evidence, market_regime, side)
        if evidence["sample_size"] < 20:
            warnings.append("historical sample size is below V1 action threshold")
            score *= 0.85
        if market_regime in HOSTILE_REGIMES:
            warnings.append(f"market regime is hostile or uncertain: {market_regime}")
            score *= 0.55
        if score < confidence_threshold:
            side = Side.NO_TRADE
            setup_type = "no trade suppression"
            reasons.append("confidence below configured threshold")
        entry, stop, targets, risk = self._plan_prices(latest_bar, features, side)
        expected_r = float(evidence["average_r"]) * score
        return Signal(
            timestamp=datetime.now(UTC),
            ticker=latest_bar.symbol,
            side=side,
            entry_price=entry,
            stop_price=stop,
            target_1=targets[0] if targets else None,
            target_2=targets[1] if targets else None,
            target_3=targets[2] if targets else None,
            risk_per_share=risk,
            reward_risk_to_t1=1.0 if risk else None,
            reward_risk_to_t2=1.5 if risk else None,
            reward_risk_to_t3=2.5 if risk else None,
            expected_r=expected_r,
            confidence_score=round(score, 4),
            signal_grade=self._grade(score),
            setup_type=setup_type,
            market_regime=market_regime,
            ticker_regime=ticker_regime,
            reasons=reasons,
            warnings=warnings,
            historical_sample_size=int(evidence["sample_size"]),
            historical_win_rate=float(evidence["win_rate"]),
            historical_average_r=float(evidence["average_r"]),
            model_version=str(model.get("model_version", "untrained-baseline")),
            training_start=self._maybe_dt(model.get("training_start")),
            training_end=self._maybe_dt(model.get("training_end")),
            data_source="fmp",
        )

    def _evidence_for(self, model: dict[str, Any], symbol: str, setup_type: str, regime: str) -> dict[str, float]:
        key = f"{symbol}|{setup_type}|{regime}"
        evidence = (model.get("statistical_evidence") or {}).get(key) or {}
        return {
            "sample_size": float(evidence.get("sample_size", 0)),
            "win_rate": float(evidence.get("win_rate", 0.0)),
            "average_r": float(evidence.get("average_r", 0.0)),
        }

    def _score(self, features: dict[str, object], evidence: dict[str, float], regime: str, side: Side) -> float:
        if side == Side.NO_TRADE:
            return 0.0
        base = 0.45
        base += min(float(features.get("relative_volume") or 0.0), 3.0) * 0.06
        base += min(abs(float(features.get("distance_from_vwap") or 0.0)) * 20.0, 0.12)
        base += max(evidence["win_rate"] - 0.45, 0.0) * 0.35
        base += max(evidence["average_r"], 0.0) * 0.08
        if regime in {"trend_long", "trend_short", "opening_drive", "single_stock_momentum"}:
            base += 0.08
        return max(0.0, min(base, 0.99))

    def _plan_prices(
        self, latest_bar: Bar, features: dict[str, object], side: Side
    ) -> tuple[float | None, float | None, list[float], float | None]:
        if side == Side.NO_TRADE:
            return None, None, [], None
        entry = latest_bar.close
        atr = max(float(features.get("atr_14_proxy") or 0.0), entry * 0.002)
        if side == Side.LONG:
            stop = min(latest_bar.low, entry - atr)
            risk = max(entry - stop, entry * 0.001)
            targets = [entry + risk * r for r in (1.0, 1.5, 2.5)]
        else:
            stop = max(latest_bar.high, entry + atr)
            risk = max(stop - entry, entry * 0.001)
            targets = [entry - risk * r for r in (1.0, 1.5, 2.5)]
        return entry, stop, targets, risk

    def _grade(self, score: float) -> str:
        if score >= 0.9:
            return "A+"
        if score >= 0.82:
            return "A"
        if score >= 0.76:
            return "A-"
        if score >= 0.70:
            return "B+"
        if score >= 0.64:
            return "B"
        if score >= 0.55:
            return "C"
        return "NO_TRADE"

    def _maybe_dt(self, value: object) -> datetime | None:
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return None
