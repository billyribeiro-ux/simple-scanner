from __future__ import annotations

from hashlib import sha256

from app.schemas.market import Bar, Label, Outcome, Side
from app.signals.rules import SetupRuleEngine


class LabelingEngine:
    def __init__(self, max_hold_bars: int = 60, target_r: float = 1.5) -> None:
        self.max_hold_bars = max_hold_bars
        self.target_r = target_r
        self.rules = SetupRuleEngine()

    def build_labels(self, bars: list[Bar], features: list[dict[str, object]]) -> list[Label]:
        ordered = sorted(bars, key=lambda bar: bar.timestamp_utc)
        by_timestamp = {bar.timestamp_utc.isoformat(): i for i, bar in enumerate(ordered)}
        labels: list[Label] = []
        for feature in features:
            index = by_timestamp.get(str(feature["timestamp"]))
            if index is None or index + 1 >= len(ordered):
                continue
            side, setup_type, _reasons = self.rules.detect(feature)
            if side == Side.NO_TRADE:
                continue
            future = ordered[index + 1 : index + 1 + self.max_hold_bars]
            if not future:
                continue
            labels.append(self._label_candidate(ordered[index], future, feature, side, setup_type))
        return labels

    def _label_candidate(
        self,
        candidate: Bar,
        future: list[Bar],
        feature: dict[str, object],
        side: Side,
        setup_type: str,
    ) -> Label:
        entry = future[0].open
        atr = max(float(feature.get("atr_14_proxy") or 0.0), entry * 0.002)
        if side == Side.LONG:
            structural_stop = min(candidate.low, float(feature.get("vwap") or candidate.low))
            stop = min(entry - atr, structural_stop)
            risk = max(entry - stop, entry * 0.001)
            targets = [entry + risk * r for r in (1.0, self.target_r, 2.5)]
        else:
            structural_stop = max(candidate.high, float(feature.get("vwap") or candidate.high))
            stop = max(entry + atr, structural_stop)
            risk = max(stop - entry, entry * 0.001)
            targets = [entry - risk * r for r in (1.0, self.target_r, 2.5)]

        hit_stop = False
        hit_targets = [False, False, False]
        time_to_target: int | None = None
        time_to_stop: int | None = None
        mfe = 0.0
        mae = 0.0
        realized_r = 0.0
        outcome = Outcome.NEUTRAL

        for offset, bar in enumerate(future, start=1):
            if side == Side.LONG:
                mfe = max(mfe, (bar.high - entry) / risk)
                mae = min(mae, (bar.low - entry) / risk)
                stop_hit_now = bar.low <= stop
                target_hits_now = [bar.high >= target for target in targets]
            else:
                mfe = max(mfe, (entry - bar.low) / risk)
                mae = min(mae, (entry - bar.high) / risk)
                stop_hit_now = bar.high >= stop
                target_hits_now = [bar.low <= target for target in targets]
            for target_index, hit in enumerate(target_hits_now):
                hit_targets[target_index] = hit_targets[target_index] or hit
            if target_hits_now[1] and not stop_hit_now:
                time_to_target = offset
                realized_r = self.target_r
                outcome = Outcome.WIN
                break
            if stop_hit_now:
                hit_stop = True
                time_to_stop = offset
                realized_r = -1.0
                outcome = Outcome.LOSS
                break

        if outcome == Outcome.NEUTRAL:
            final_close = future[-1].close
            realized_r = (final_close - entry) / risk if side == Side.LONG else (entry - final_close) / risk

        label_id = sha256(f"{candidate.symbol}:{candidate.timestamp_utc.isoformat()}:{side}".encode()).hexdigest()[:32]
        return Label(
            label_id=label_id,
            symbol=candidate.symbol,
            timestamp=candidate.timestamp_utc,
            side=side,
            entry_price=entry,
            stop_price=stop,
            target_1=targets[0],
            target_2=targets[1],
            target_3=targets[2],
            max_favorable_excursion=mfe,
            max_adverse_excursion=mae,
            hit_target_1=hit_targets[0],
            hit_target_2=hit_targets[1],
            hit_target_3=hit_targets[2],
            hit_stop=hit_stop,
            time_to_target=time_to_target,
            time_to_stop=time_to_stop,
            realized_r=realized_r,
            outcome=outcome,
            setup_type=setup_type,
            market_regime=str(feature.get("market_regime") or "mixed_uncertain"),
        )
