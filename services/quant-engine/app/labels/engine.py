from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256

from app.quant.types import CandidateSignal, LabelRow
from app.schemas.market import Bar, Label, Outcome, Side
from app.signals.candidates import CandidateSignalEngine

LABEL_CONFIG_VERSION = "labels.v2.no_leakage"


@dataclass(frozen=True)
class LabelSettings:
    max_hold_minutes: int = 60
    entry_mode: str = "next_bar_open"
    target_r: float = 1.5
    stop_mode: str = "structure_plus_atr"
    atr_stop_multiplier: float = 1.0
    slippage_bps: float = 0.0
    spread_bps: float = 0.0
    same_bar_stop_target_policy: str = "conservative_stop_first"
    allow_overlapping_trades: bool = False
    minimum_bars_before_label: int = 1
    recent_swing_lookback: int = 10


class LabelingEngine:
    def __init__(
        self,
        max_hold_bars: int | None = None,
        target_r: float = 1.5,
        settings: LabelSettings | None = None,
    ) -> None:
        if settings is None:
            settings = LabelSettings(
                max_hold_minutes=max_hold_bars if max_hold_bars is not None else 60,
                target_r=target_r,
            )
        self.settings = settings
        self.candidates = CandidateSignalEngine()

    def build_labels(self, bars: list[Bar], features: list[dict[str, object]]) -> list[Label]:
        return [self._to_schema_label(row) for row in self.build_label_rows(bars, features)]

    def build_label_rows(self, bars: list[Bar], features: list[dict[str, object]]) -> list[LabelRow]:
        bars_by_group: dict[tuple[str, str], list[Bar]] = {}
        for bar in sorted(bars, key=lambda item: (item.symbol, item.interval, item.timestamp_utc)):
            bars_by_group.setdefault((bar.symbol, bar.interval), []).append(bar)

        features_by_key: dict[tuple[str, str, datetime], dict[str, object]] = {}
        for feature in features:
            timestamp = self._feature_timestamp(feature)
            features_by_key[(str(feature["symbol"]), str(feature.get("interval") or "1min"), timestamp)] = feature

        labels: list[LabelRow] = []
        blocked_until: dict[tuple[str, str], datetime] = {}
        for group_key, group_bars in bars_by_group.items():
            index_by_timestamp = {bar.timestamp_utc: index for index, bar in enumerate(group_bars)}
            group_features = [
                feature
                for key, feature in features_by_key.items()
                if key[0] == group_key[0] and key[1] == group_key[1]
            ]
            group_features.sort(key=self._feature_timestamp)
            for feature in group_features:
                timestamp = self._feature_timestamp(feature)
                index = index_by_timestamp.get(timestamp)
                if index is None or index < self.settings.minimum_bars_before_label:
                    continue
                if index + 1 >= len(group_bars):
                    continue
                for candidate in self.candidates.detect_actionable(feature):
                    block_key = (candidate.symbol, candidate.setup_type)
                    if not self.settings.allow_overlapping_trades and timestamp <= blocked_until.get(
                        block_key, datetime.min.replace(tzinfo=timestamp.tzinfo)
                    ):
                        continue
                    label = self._label_candidate(group_bars, index, feature, candidate)
                    if label is None:
                        continue
                    labels.append(label)
                    if label.exit_timestamp_utc is not None:
                        blocked_until[block_key] = label.exit_timestamp_utc
                    break
        return labels

    def _label_candidate(
        self,
        bars: list[Bar],
        candidate_index: int,
        feature: dict[str, object],
        candidate: CandidateSignal,
    ) -> LabelRow | None:
        entry_bar_index = candidate_index + 1
        if entry_bar_index >= len(bars):
            return None
        candidate_bar = bars[candidate_index]
        entry_bar = bars[entry_bar_index]
        future = self._future_window(bars, entry_bar_index)
        if not future:
            return None

        side = candidate.side
        entry = self._entry_price(entry_bar.open, side)
        stop = self._stop_price(bars, candidate_index, feature, entry, side)
        risk = entry - stop if side == Side.LONG.value else stop - entry
        if risk <= 0:
            return None
        targets = self._targets(entry, risk, side)
        mfe = 0.0
        mae = 0.0
        hit_targets = [False, False, False]
        hit_stop = False
        time_to_target: int | None = None
        time_to_stop: int | None = None
        realized_r = 0.0
        outcome = Outcome.NEUTRAL.value
        exit_timestamp = future[-1].timestamp_utc

        for offset, bar in enumerate(future, start=1):
            if side == Side.LONG.value:
                mfe = max(mfe, (bar.high - entry) / risk)
                mae = min(mae, (bar.low - entry) / risk)
                stop_hit_now = bar.low <= stop
                target_hits_now = [bar.high >= target for target in targets]
            else:
                mfe = max(mfe, (entry - bar.low) / risk)
                mae = min(mae, (entry - bar.high) / risk)
                stop_hit_now = bar.high >= stop
                target_hits_now = [bar.low <= target for target in targets]

            hit_targets = [
                old or new for old, new in zip(hit_targets, target_hits_now, strict=True)
            ]
            target_2_hit_now = target_hits_now[1]
            if stop_hit_now and (
                target_2_hit_now
                or self.settings.same_bar_stop_target_policy == "conservative_stop_first"
            ):
                hit_stop = True
                time_to_stop = offset
                realized_r = -1.0
                outcome = Outcome.LOSS.value
                exit_timestamp = bar.timestamp_utc
                break
            if target_2_hit_now:
                time_to_target = offset
                realized_r = self.settings.target_r
                outcome = Outcome.WIN.value
                exit_timestamp = bar.timestamp_utc
                break
            if stop_hit_now:
                hit_stop = True
                time_to_stop = offset
                realized_r = -1.0
                outcome = Outcome.LOSS.value
                exit_timestamp = bar.timestamp_utc
                break

        if outcome == Outcome.NEUTRAL.value:
            final_close = future[-1].close
            realized_r = (final_close - entry) / risk if side == Side.LONG.value else (entry - final_close) / risk

        return LabelRow(
            symbol=candidate.symbol,
            interval=candidate.interval,
            timestamp_utc=candidate_bar.timestamp_utc,
            side=side,
            setup_type=candidate.setup_type,
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
            label_config_version=LABEL_CONFIG_VERSION,
            market_regime=str(feature.get("market_regime") or "mixed_uncertain"),
            exit_timestamp_utc=exit_timestamp,
            warning_codes=candidate.warning_codes,
        )

    def _feature_timestamp(self, feature: dict[str, object]) -> datetime:
        value = feature.get("timestamp_utc")
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(feature["timestamp"]))

    def _future_window(self, bars: list[Bar], entry_index: int) -> list[Bar]:
        entry_time = bars[entry_index].timestamp_utc
        max_exit = entry_time + timedelta(minutes=self.settings.max_hold_minutes)
        return [bar for bar in bars[entry_index:] if entry_time <= bar.timestamp_utc <= max_exit]

    def _entry_price(self, raw_open: float, side: str) -> float:
        cost_bps = (self.settings.slippage_bps + self.settings.spread_bps / 2) / 10_000
        return raw_open * (1 + cost_bps) if side == Side.LONG.value else raw_open * (1 - cost_bps)

    def _stop_price(
        self,
        bars: list[Bar],
        candidate_index: int,
        feature: dict[str, object],
        entry: float,
        side: str,
    ) -> float:
        past = bars[max(0, candidate_index - self.settings.recent_swing_lookback + 1) : candidate_index + 1]
        atr = float(feature.get("atr_14") or feature.get("atr_14_proxy") or entry * 0.002)
        atr = max(atr, entry * 0.001)
        if side == Side.LONG.value:
            candidates = [
                min(bar.low for bar in past),
                self._float_or_none(feature.get("vwap")),
                self._float_or_none(feature.get("opening_range_low")),
                entry - atr * self.settings.atr_stop_multiplier,
            ]
            valid = [value for value in candidates if value is not None and value < entry]
            return max(valid) if valid else entry - atr
        candidates = [
            max(bar.high for bar in past),
            self._float_or_none(feature.get("vwap")),
            self._float_or_none(feature.get("opening_range_high")),
            entry + atr * self.settings.atr_stop_multiplier,
        ]
        valid = [value for value in candidates if value is not None and value > entry]
        return min(valid) if valid else entry + atr

    def _targets(self, entry: float, risk: float, side: str) -> list[float]:
        multiples = (1.0, self.settings.target_r, 2.5)
        if side == Side.LONG.value:
            return [entry + risk * multiple for multiple in multiples]
        return [entry - risk * multiple for multiple in multiples]

    def _float_or_none(self, value: object) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _to_schema_label(self, row: LabelRow) -> Label:
        label_id = sha256(f"{row.symbol}:{row.timestamp_utc.isoformat()}:{row.side}:{row.setup_type}".encode()).hexdigest()[:32]
        return Label(
            label_id=label_id,
            symbol=row.symbol,
            timestamp=row.timestamp_utc,
            side=Side(row.side),
            entry_price=row.entry_price,
            stop_price=row.stop_price,
            target_1=row.target_1,
            target_2=row.target_2,
            target_3=row.target_3,
            max_favorable_excursion=row.max_favorable_excursion,
            max_adverse_excursion=row.max_adverse_excursion,
            hit_target_1=row.hit_target_1,
            hit_target_2=row.hit_target_2,
            hit_target_3=row.hit_target_3,
            hit_stop=row.hit_stop,
            time_to_target=row.time_to_target,
            time_to_stop=row.time_to_stop,
            realized_r=row.realized_r,
            outcome=Outcome(row.outcome),
            setup_type=row.setup_type,
            market_regime=row.market_regime,
        )
