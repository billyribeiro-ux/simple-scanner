from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from hashlib import sha256
from statistics import mean, median
from typing import Any
from zoneinfo import ZoneInfo

from app.data.symbols import normalize_symbols
from app.schemas.market import Bar, Side
from app.utils.time import UTC

ET = ZoneInfo("America/New_York")
RTH_START_MINUTE = 9 * 60 + 30
RTH_END_MINUTE = 16 * 60
SIMULATION_TYPE_REPLAY = "candidate_market_replay"
SIMULATION_TYPE_LABEL_DERIVED = "label_derived"


class ReplaySkipReason(str, Enum):
    MISSING_ENTRY_BAR = "missing_entry_bar"
    OUTSIDE_SESSION = "outside_session"
    INVALID_RISK_PLAN = "invalid_risk_plan"
    INSUFFICIENT_REWARD_RISK = "insufficient_reward_risk"
    OVERLAPPING_TRADE = "overlapping_trade"
    PORTFOLIO_TRADE_LIMIT = "portfolio_trade_limit"
    COOLDOWN_ACTIVE = "cooldown_active"
    INSUFFICIENT_CONTEXT = "insufficient_context"
    REGIME_FILTER_BLOCK = "regime_filter_block"
    DUPLICATE_CANDIDATE = "duplicate_candidate"
    NO_FUTURE_BARS = "no_future_bars"
    DATA_QUALITY_BLOCK = "data_quality_block"


class IntrabarPolicy(str, Enum):
    CONSERVATIVE = "conservative"
    OPEN_HIGH_LOW_CLOSE = "open_high_low_close"
    OPEN_LOW_HIGH_CLOSE = "open_low_high_close"
    UNKNOWN = "unknown"


class ExecutionAssumption(str, Enum):
    NEXT_BAR_OPEN = "next_bar_open"


@dataclass(frozen=True)
class ReplayConfig:
    symbols: tuple[str, ...] = ()
    intervals: tuple[str, ...] = ("1min",)
    start: datetime | None = None
    end: datetime | None = None
    session: str = "rth"
    candidate_setup_types: tuple[str, ...] = ()
    sides: tuple[str, ...] = (Side.LONG.value, Side.SHORT.value)
    max_hold_minutes: int = 60
    entry_mode: str = ExecutionAssumption.NEXT_BAR_OPEN.value
    stop_mode: str = "candidate_context"
    target_mode: str = "candidate_targets"
    target_1_r: float = 1.0
    target_2_r: float = 1.5
    target_3_r: float = 2.5
    partial_exit_mode: str = "none"
    same_bar_stop_target_policy: str = "conservative_stop_first"
    intrabar_path_policy: str = IntrabarPolicy.CONSERVATIVE.value
    slippage_bps: float = 0.0
    spread_bps: float = 0.0
    commission_per_share: float = 0.0
    minimum_reward_risk: float = 1.0
    minimum_confidence: float | None = None
    allow_overlapping_trades: bool = False
    max_open_trades_per_symbol: int = 1
    max_open_trades_portfolio: int = 10
    cooldown_bars_after_loss: int = 0
    cooldown_bars_after_trade: int = 0
    one_trade_per_setup_per_symbol_until_exit: bool = True
    no_trade_on_insufficient_context: bool = True
    market_regime_filter: tuple[str, ...] = ()
    time_bucket_filter: tuple[str, ...] = ()
    close_at_session_end: bool = True
    feature_warmup_bars: int = 1
    allow_stale: bool = False

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> ReplayConfig:
        data = dict(payload)
        symbols = tuple(normalize_symbols(list(data.get("symbols") or [])))
        intervals = tuple(str(value) for value in data.get("intervals") or ("1min",))
        sides_payload = data.get("sides") or (Side.LONG.value, Side.SHORT.value)
        if isinstance(sides_payload, str):
            sides = (Side.LONG.value, Side.SHORT.value) if sides_payload.upper() == "BOTH" else (sides_payload.upper(),)
        else:
            sides = tuple(str(value).upper() for value in sides_payload)
        for key in ("start", "end"):
            if isinstance(data.get(key), str):
                data[key] = _parse_datetime(data[key])
        return cls(
            symbols=symbols,
            intervals=intervals,
            start=data.get("start"),
            end=data.get("end"),
            session=str(data.get("session") or "rth"),
            candidate_setup_types=tuple(str(value) for value in data.get("candidate_setup_types") or ()),
            sides=sides,
            max_hold_minutes=int(data.get("max_hold_minutes") or 60),
            entry_mode=str(data.get("entry_mode") or ExecutionAssumption.NEXT_BAR_OPEN.value),
            stop_mode=str(data.get("stop_mode") or "candidate_context"),
            target_mode=str(data.get("target_mode") or "candidate_targets"),
            target_1_r=float(data.get("target_1_r") or 1.0),
            target_2_r=float(data.get("target_2_r") or 1.5),
            target_3_r=float(data.get("target_3_r") or 2.5),
            partial_exit_mode=str(data.get("partial_exit_mode") or "none"),
            same_bar_stop_target_policy=str(data.get("same_bar_stop_target_policy") or "conservative_stop_first"),
            intrabar_path_policy=str(data.get("intrabar_path_policy") or IntrabarPolicy.CONSERVATIVE.value),
            slippage_bps=float(data.get("slippage_bps") or 0.0),
            spread_bps=float(data.get("spread_bps") or 0.0),
            commission_per_share=float(data.get("commission_per_share") or 0.0),
            minimum_reward_risk=float(data.get("minimum_reward_risk") or 1.0),
            minimum_confidence=(
                None if data.get("minimum_confidence") is None else float(data.get("minimum_confidence"))
            ),
            allow_overlapping_trades=bool(data.get("allow_overlapping_trades", False)),
            max_open_trades_per_symbol=int(data.get("max_open_trades_per_symbol") or 1),
            max_open_trades_portfolio=int(data.get("max_open_trades_portfolio") or 10),
            cooldown_bars_after_loss=int(data.get("cooldown_bars_after_loss") or 0),
            cooldown_bars_after_trade=int(data.get("cooldown_bars_after_trade") or 0),
            one_trade_per_setup_per_symbol_until_exit=bool(
                data.get("one_trade_per_setup_per_symbol_until_exit", True)
            ),
            no_trade_on_insufficient_context=bool(data.get("no_trade_on_insufficient_context", True)),
            market_regime_filter=tuple(str(value) for value in data.get("market_regime_filter") or ()),
            time_bucket_filter=tuple(str(value) for value in data.get("time_bucket_filter") or ()),
            close_at_session_end=bool(data.get("close_at_session_end", True)),
            feature_warmup_bars=int(data.get("feature_warmup_bars") or 1),
            allow_stale=bool(data.get("allow_stale", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["symbols"] = list(self.symbols)
        payload["intervals"] = list(self.intervals)
        payload["candidate_setup_types"] = list(self.candidate_setup_types)
        payload["sides"] = list(self.sides)
        payload["market_regime_filter"] = list(self.market_regime_filter)
        payload["time_bucket_filter"] = list(self.time_bucket_filter)
        payload["start"] = self.start.isoformat() if self.start else None
        payload["end"] = self.end.isoformat() if self.end else None
        return payload


@dataclass(frozen=True)
class ReplayDecision:
    candidate_id: str
    status: str
    skip_reason: str | None = None
    trade_id: str | None = None


@dataclass(frozen=True)
class SimulatedTrade:
    trade_id: str
    replay_run_id: str
    candidate_id: str | None
    symbol: str
    interval: str
    side: str
    setup_type: str
    signal_timestamp_utc: datetime
    entry_timestamp_utc: datetime | None
    exit_timestamp_utc: datetime | None
    entry_price: float | None
    stop_price: float | None
    target_1: float | None
    target_2: float | None
    target_3: float | None
    exit_price: float | None
    exit_reason: str | None
    realized_r: float
    mfe_r: float
    mae_r: float
    bars_held: int
    minutes_held: float
    same_bar_ambiguous: bool
    ambiguity_policy: str | None
    slippage_bps: float
    spread_bps: float
    commission: float
    market_regime: str | None
    time_bucket: str | None
    signal_score: float | None
    expected_r: float | None
    status: str
    skip_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in ("signal_timestamp_utc", "entry_timestamp_utc", "exit_timestamp_utc"):
            if isinstance(payload.get(key), datetime):
                payload[key] = payload[key].isoformat()
        return payload


@dataclass(frozen=True)
class ReplayMetrics:
    replay_run_id: str
    simulation_type: str
    start: datetime | None
    end: datetime | None
    symbols: tuple[str, ...]
    intervals: tuple[str, ...]
    config_summary: dict[str, Any]
    metrics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "replay_run_id": self.replay_run_id,
            "simulation_type": self.simulation_type,
            "start": self.start.isoformat() if self.start else None,
            "end": self.end.isoformat() if self.end else None,
            "symbols": list(self.symbols),
            "intervals": list(self.intervals),
            "config_summary": self.config_summary,
            **self.metrics,
        }


@dataclass(frozen=True)
class ReplayRun:
    replay_run_id: str
    simulation_type: str
    config: ReplayConfig
    metrics: dict[str, Any]
    trades: tuple[SimulatedTrade, ...]
    decisions: tuple[ReplayDecision, ...]
    warnings: tuple[str, ...] = ()
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def to_dict(self) -> dict[str, Any]:
        return {
            "replay_run_id": self.replay_run_id,
            "simulation_type": self.simulation_type,
            "start": self.config.start.isoformat() if self.config.start else None,
            "end": self.config.end.isoformat() if self.config.end else None,
            "symbols": list(self.config.symbols),
            "intervals": list(self.config.intervals),
            "config": self.config.to_dict(),
            "summary_metrics": self.metrics,
            "warnings": list(self.warnings),
            "created_at": self.created_at.isoformat(),
        }


class CandidateMarketReplayEngine:
    def replay(
        self,
        bars: list[Bar],
        features: list[dict[str, Any]],
        candidates: list[dict[str, Any]],
        config: ReplayConfig,
        replay_run_id: str | None = None,
    ) -> ReplayRun:
        run_id = replay_run_id or self._run_id(config)
        bars_by_key = self._bars_by_key(bars)
        features_by_key = self._features_by_key(features)
        selected_candidates = self._filter_candidates(candidates, config)
        selected_candidates.sort(key=self._candidate_priority)

        trades: list[SimulatedTrade] = []
        decisions: list[ReplayDecision] = []
        seen_keys: set[tuple[str, str, str, str, str]] = set()
        open_until_symbol: dict[str, list[datetime]] = {}
        open_until_setup: dict[tuple[str, str], datetime] = {}
        cooldown_until: dict[str, datetime] = {}

        for candidate in selected_candidates:
            timestamp = _candidate_timestamp(candidate)
            symbol = str(candidate["symbol"])
            interval = str(candidate.get("interval") or "1min")
            side = str(candidate["side"])
            setup_type = str(candidate["setup_type"])
            candidate_id = str(candidate.get("candidate_id") or self._candidate_id(candidate))
            market_regime = self._candidate_market_regime(candidate, features_by_key)
            time_bucket = self._candidate_time_bucket(candidate, features_by_key)
            duplicate_key = (symbol, interval, timestamp.isoformat(), side, setup_type)
            if duplicate_key in seen_keys:
                trade = self._skip(run_id, candidate, ReplaySkipReason.DUPLICATE_CANDIDATE, market_regime, time_bucket)
                trades.append(trade)
                decisions.append(ReplayDecision(candidate_id, "SKIPPED", ReplaySkipReason.DUPLICATE_CANDIDATE.value))
                continue
            seen_keys.add(duplicate_key)

            skip_reason = self._preflight_skip(
                candidate,
                config,
                market_regime,
                time_bucket,
                open_until_symbol,
                open_until_setup,
                cooldown_until,
                timestamp,
                trades,
            )
            if skip_reason is not None:
                trade = self._skip(run_id, candidate, skip_reason, market_regime, time_bucket)
                trades.append(trade)
                decisions.append(ReplayDecision(candidate_id, "SKIPPED", skip_reason.value))
                continue

            group_bars = bars_by_key.get((symbol, interval), [])
            feature = features_by_key.get((symbol, interval, timestamp))
            trade = self._simulate_candidate(run_id, candidate, group_bars, feature, config, market_regime, time_bucket)
            trades.append(trade)
            if trade.status == "SKIPPED":
                decisions.append(ReplayDecision(candidate_id, "SKIPPED", trade.skip_reason))
                continue
            decisions.append(ReplayDecision(candidate_id, "TAKEN", trade_id=trade.trade_id))
            if trade.exit_timestamp_utc:
                open_until_symbol.setdefault(symbol, []).append(trade.exit_timestamp_utc)
                open_until_setup[(symbol, setup_type)] = trade.exit_timestamp_utc
                interval_minutes = self._interval_minutes(interval)
                cooldown_bars = (
                    config.cooldown_bars_after_loss
                    if trade.realized_r < 0
                    else config.cooldown_bars_after_trade
                )
                if cooldown_bars > 0:
                    cooldown_until[symbol] = trade.exit_timestamp_utc + timedelta(minutes=interval_minutes * cooldown_bars)

        metrics = self.metrics(run_id, trades, config)
        return ReplayRun(
            replay_run_id=run_id,
            simulation_type=SIMULATION_TYPE_REPLAY,
            config=config,
            metrics=metrics,
            trades=tuple(trades),
            decisions=tuple(decisions),
            warnings=tuple(metrics.get("warnings") or []),
        )

    def metrics(self, replay_run_id: str, trades: list[SimulatedTrade], config: ReplayConfig) -> dict[str, Any]:
        taken = [trade for trade in trades if trade.status == "TAKEN"]
        skipped = [trade for trade in trades if trade.status == "SKIPPED"]
        returns = [trade.realized_r for trade in taken]
        winners = [trade for trade in taken if trade.realized_r > 0]
        losers = [trade for trade in taken if trade.realized_r < 0]
        breakeven = [trade for trade in taken if trade.realized_r == 0]
        equity = []
        running = 0.0
        for value in returns:
            running += value
            equity.append(running)
        drawdown_series = self._drawdown_series(equity)
        skip_breakdown = dict(Counter(trade.skip_reason or "unknown" for trade in skipped))
        daily_r = self._daily_r(taken)
        return {
            "replay_run_id": replay_run_id,
            "simulation_type": SIMULATION_TYPE_REPLAY,
            "start": config.start.isoformat() if config.start else None,
            "end": config.end.isoformat() if config.end else None,
            "symbols": list(config.symbols),
            "intervals": list(config.intervals),
            "config_summary": config.to_dict(),
            "total_candidates": len(trades),
            "candidates_taken": len(taken),
            "candidates_skipped": len(skipped),
            "skip_rate": len(skipped) / len(trades) if trades else 0.0,
            "skip_breakdown": skip_breakdown,
            "total_trades": len(taken),
            "long_trades": len([trade for trade in taken if trade.side == Side.LONG.value]),
            "short_trades": len([trade for trade in taken if trade.side == Side.SHORT.value]),
            "winners": len(winners),
            "losers": len(losers),
            "breakeven": len(breakeven),
            "win_rate": len(winners) / len(taken) if taken else 0.0,
            "loss_rate": len(losers) / len(taken) if taken else 0.0,
            "average_r": mean(returns) if returns else 0.0,
            "median_r": median(returns) if returns else 0.0,
            "expectancy_r": mean(returns) if returns else 0.0,
            "total_r": sum(returns),
            "gross_profit_r": sum(value for value in returns if value > 0),
            "gross_loss_r": sum(value for value in returns if value < 0),
            "profit_factor": self._profit_factor(returns),
            "max_drawdown_r": min(drawdown_series) if drawdown_series else 0.0,
            "max_consecutive_wins": self._max_consecutive(taken, positive=True),
            "max_consecutive_losses": self._max_consecutive(taken, positive=False),
            "average_mfe_r": mean([trade.mfe_r for trade in taken]) if taken else 0.0,
            "average_mae_r": mean([trade.mae_r for trade in taken]) if taken else 0.0,
            "median_mfe_r": median([trade.mfe_r for trade in taken]) if taken else 0.0,
            "median_mae_r": median([trade.mae_r for trade in taken]) if taken else 0.0,
            "target_1_hit_rate": len([trade for trade in taken if trade.mfe_r >= config.target_1_r]) / len(taken) if taken else 0.0,
            "target_2_hit_rate": len([trade for trade in taken if trade.mfe_r >= config.target_2_r]) / len(taken) if taken else 0.0,
            "target_3_hit_rate": len([trade for trade in taken if trade.mfe_r >= config.target_3_r]) / len(taken) if taken else 0.0,
            "stop_hit_rate": len([trade for trade in taken if trade.exit_reason == "stop"]) / len(taken) if taken else 0.0,
            "time_exit_rate": len([trade for trade in taken if trade.exit_reason == "time_exit"]) / len(taken) if taken else 0.0,
            "session_exit_rate": len([trade for trade in taken if trade.exit_reason == "session_exit"]) / len(taken) if taken else 0.0,
            "same_bar_ambiguity_count": len([trade for trade in taken if trade.same_bar_ambiguous]),
            "average_time_in_trade_minutes": mean([trade.minutes_held for trade in taken]) if taken else 0.0,
            "median_time_in_trade_minutes": median([trade.minutes_held for trade in taken]) if taken else 0.0,
            "per_symbol_metrics": self._breakdown(taken, "symbol"),
            "per_setup_metrics": self._breakdown(taken, "setup_type"),
            "per_regime_metrics": self._breakdown(taken, "market_regime"),
            "per_time_bucket_metrics": self._breakdown(taken, "time_bucket"),
            "per_side_metrics": self._breakdown(taken, "side"),
            "daily_r_series": daily_r,
            "trade_r_series": returns,
            "drawdown_series": drawdown_series,
            "warnings": [],
            "data_quality_summary": self._data_quality_summary(trades),
        }

    def _simulate_candidate(
        self,
        run_id: str,
        candidate: dict[str, Any],
        bars: list[Bar],
        feature: dict[str, Any] | None,
        config: ReplayConfig,
        market_regime: str | None,
        time_bucket: str | None,
    ) -> SimulatedTrade:
        timestamp = _candidate_timestamp(candidate)
        candidate_id = str(candidate.get("candidate_id") or self._candidate_id(candidate))
        side = str(candidate["side"])
        if config.no_trade_on_insufficient_context and feature is not None:
            flags = list(feature.get("data_quality_flags") or [])
            if len([flag for flag in flags if "insufficient" in str(flag)]) > 3:
                return self._skip(run_id, candidate, ReplaySkipReason.INSUFFICIENT_CONTEXT, market_regime, time_bucket)
        index = next((idx for idx, bar in enumerate(bars) if bar.timestamp_utc == timestamp), None)
        if index is None:
            return self._skip(run_id, candidate, ReplaySkipReason.MISSING_ENTRY_BAR, market_regime, time_bucket)
        entry_index = index + 1
        if entry_index >= len(bars):
            return self._skip(run_id, candidate, ReplaySkipReason.MISSING_ENTRY_BAR, market_regime, time_bucket)
        entry_bar = bars[entry_index]
        future = [
            bar
            for bar in bars[entry_index:]
            if bar.timestamp_utc <= entry_bar.timestamp_utc + timedelta(minutes=config.max_hold_minutes)
        ]
        if not future:
            return self._skip(run_id, candidate, ReplaySkipReason.NO_FUTURE_BARS, market_regime, time_bucket)
        entry = self._entry_price(entry_bar.open, side, config)
        stop = self._stop_price(candidate, feature, bars[: entry_index + 1], entry, side, config)
        if stop is None:
            return self._skip(run_id, candidate, ReplaySkipReason.INVALID_RISK_PLAN, market_regime, time_bucket)
        risk = entry - stop if side == Side.LONG.value else stop - entry
        if risk <= 0:
            return self._skip(run_id, candidate, ReplaySkipReason.INVALID_RISK_PLAN, market_regime, time_bucket)
        targets = self._targets(candidate, entry, risk, side, config)
        reward_risk = self._reward_risk(entry, targets[1], risk, side)
        if reward_risk < config.minimum_reward_risk:
            return self._skip(run_id, candidate, ReplaySkipReason.INSUFFICIENT_REWARD_RISK, market_regime, time_bucket)

        mfe = 0.0
        mae = 0.0
        exit_bar = future[-1]
        exit_price = self._time_exit_price(exit_bar.close, side, config)
        exit_reason = "end_of_data"
        same_bar_ambiguous = False
        bars_held = len(future)

        for offset, bar in enumerate(future, start=1):
            if side == Side.LONG.value:
                mfe = max(mfe, (bar.high - entry) / risk)
                mae = min(mae, (bar.low - entry) / risk)
                stop_hit = bar.low <= stop
                target_hits = [bar.high >= target for target in targets]
            else:
                mfe = max(mfe, (entry - bar.low) / risk)
                mae = min(mae, (entry - bar.high) / risk)
                stop_hit = bar.high >= stop
                target_hits = [bar.low <= target for target in targets]
            target_hit = target_hits[1]
            if stop_hit and target_hit:
                same_bar_ambiguous = True
                exit_bar = bar
                bars_held = offset
                if config.same_bar_stop_target_policy == "conservative_stop_first":
                    exit_price = stop
                    exit_reason = "stop"
                else:
                    exit_price = targets[1]
                    exit_reason = "target_2"
                break
            if stop_hit:
                exit_bar = bar
                exit_price = stop
                exit_reason = "stop"
                bars_held = offset
                break
            if target_hit:
                exit_bar = bar
                exit_price = targets[1]
                exit_reason = "target_2"
                bars_held = offset
                break
            if self._session_exit(bar, side, config):
                exit_bar = bar
                exit_price = self._time_exit_price(bar.close, side, config)
                exit_reason = "session_exit"
                bars_held = offset
                break
            if bar.timestamp_utc >= entry_bar.timestamp_utc + timedelta(minutes=config.max_hold_minutes):
                exit_bar = bar
                exit_price = self._time_exit_price(bar.close, side, config)
                exit_reason = "time_exit"
                bars_held = offset
                break

        commission = config.commission_per_share * 2
        realized_r = (
            (exit_price - entry) / risk
            if side == Side.LONG.value
            else (entry - exit_price) / risk
        )
        if commission:
            realized_r -= commission / risk
        minutes_held = max((exit_bar.timestamp_utc - entry_bar.timestamp_utc).total_seconds() / 60.0, 0.0)
        trade_id = self._trade_id(run_id, candidate_id, entry_bar.timestamp_utc)
        return SimulatedTrade(
            trade_id=trade_id,
            replay_run_id=run_id,
            candidate_id=candidate_id,
            symbol=str(candidate["symbol"]),
            interval=str(candidate.get("interval") or "1min"),
            side=side,
            setup_type=str(candidate["setup_type"]),
            signal_timestamp_utc=timestamp,
            entry_timestamp_utc=entry_bar.timestamp_utc,
            exit_timestamp_utc=exit_bar.timestamp_utc,
            entry_price=entry,
            stop_price=stop,
            target_1=targets[0],
            target_2=targets[1],
            target_3=targets[2],
            exit_price=exit_price,
            exit_reason=exit_reason,
            realized_r=realized_r,
            mfe_r=mfe,
            mae_r=mae,
            bars_held=bars_held,
            minutes_held=minutes_held,
            same_bar_ambiguous=same_bar_ambiguous,
            ambiguity_policy=config.same_bar_stop_target_policy if same_bar_ambiguous else None,
            slippage_bps=config.slippage_bps,
            spread_bps=config.spread_bps,
            commission=commission,
            market_regime=market_regime,
            time_bucket=time_bucket,
            signal_score=self._float_or_none(candidate.get("confidence_score") or candidate.get("signal_score")),
            expected_r=self._float_or_none(candidate.get("expected_r")),
            status="TAKEN",
            metadata={
                "entry_mode": config.entry_mode,
                "stop_mode": config.stop_mode,
                "target_mode": config.target_mode,
                "execution_assumption": ExecutionAssumption.NEXT_BAR_OPEN.value,
                "intrabar_path_policy": config.intrabar_path_policy,
                "same_bar_ambiguous": same_bar_ambiguous,
            },
        )

    def _preflight_skip(
        self,
        candidate: dict[str, Any],
        config: ReplayConfig,
        market_regime: str | None,
        time_bucket: str | None,
        open_until_symbol: dict[str, list[datetime]],
        open_until_setup: dict[tuple[str, str], datetime],
        cooldown_until: dict[str, datetime],
        timestamp: datetime,
        trades: list[SimulatedTrade],
    ) -> ReplaySkipReason | None:
        symbol = str(candidate["symbol"])
        setup_type = str(candidate["setup_type"])
        side = str(candidate["side"])
        if side not in {Side.LONG.value, Side.SHORT.value}:
            return ReplaySkipReason.DATA_QUALITY_BLOCK
        if config.session == "rth" and not _is_rth(timestamp):
            return ReplaySkipReason.OUTSIDE_SESSION
        if config.market_regime_filter and market_regime not in config.market_regime_filter:
            return ReplaySkipReason.REGIME_FILTER_BLOCK
        if config.time_bucket_filter and time_bucket not in config.time_bucket_filter:
            return ReplaySkipReason.REGIME_FILTER_BLOCK
        confidence = self._float_or_none(candidate.get("confidence_score") or candidate.get("signal_score"))
        if config.minimum_confidence is not None and confidence is not None and confidence < config.minimum_confidence:
            return ReplaySkipReason.DATA_QUALITY_BLOCK
        if timestamp <= cooldown_until.get(symbol, datetime.min.replace(tzinfo=UTC)):
            return ReplaySkipReason.COOLDOWN_ACTIVE
        active_symbol = [value for value in open_until_symbol.get(symbol, []) if value > timestamp]
        active_portfolio = [
            trade for trade in trades if trade.status == "TAKEN" and trade.exit_timestamp_utc and trade.exit_timestamp_utc > timestamp
        ]
        if not config.allow_overlapping_trades and len(active_symbol) >= config.max_open_trades_per_symbol:
            return ReplaySkipReason.OVERLAPPING_TRADE
        if len(active_portfolio) >= config.max_open_trades_portfolio:
            return ReplaySkipReason.PORTFOLIO_TRADE_LIMIT
        if config.one_trade_per_setup_per_symbol_until_exit and timestamp <= open_until_setup.get(
            (symbol, setup_type),
            datetime.min.replace(tzinfo=UTC),
        ):
            return ReplaySkipReason.OVERLAPPING_TRADE
        return None

    def _skip(
        self,
        run_id: str,
        candidate: dict[str, Any],
        reason: ReplaySkipReason,
        market_regime: str | None,
        time_bucket: str | None,
    ) -> SimulatedTrade:
        timestamp = _candidate_timestamp(candidate)
        candidate_id = str(candidate.get("candidate_id") or self._candidate_id(candidate))
        return SimulatedTrade(
            trade_id=self._trade_id(run_id, candidate_id, timestamp, "skip"),
            replay_run_id=run_id,
            candidate_id=candidate_id,
            symbol=str(candidate["symbol"]),
            interval=str(candidate.get("interval") or "1min"),
            side=str(candidate.get("side") or "UNKNOWN"),
            setup_type=str(candidate.get("setup_type") or "unknown"),
            signal_timestamp_utc=timestamp,
            entry_timestamp_utc=None,
            exit_timestamp_utc=None,
            entry_price=None,
            stop_price=None,
            target_1=None,
            target_2=None,
            target_3=None,
            exit_price=None,
            exit_reason=None,
            realized_r=0.0,
            mfe_r=0.0,
            mae_r=0.0,
            bars_held=0,
            minutes_held=0.0,
            same_bar_ambiguous=False,
            ambiguity_policy=None,
            slippage_bps=0.0,
            spread_bps=0.0,
            commission=0.0,
            market_regime=market_regime,
            time_bucket=time_bucket,
            signal_score=self._float_or_none(candidate.get("confidence_score") or candidate.get("signal_score")),
            expected_r=self._float_or_none(candidate.get("expected_r")),
            status="SKIPPED",
            skip_reason=reason.value,
            metadata={"reason_codes": candidate.get("reason_codes") or [], "warning_codes": candidate.get("warning_codes") or []},
        )

    def _filter_candidates(self, candidates: list[dict[str, Any]], config: ReplayConfig) -> list[dict[str, Any]]:
        selected = []
        symbols = set(config.symbols)
        intervals = set(config.intervals)
        setups = set(config.candidate_setup_types)
        sides = set(config.sides)
        for candidate in candidates:
            timestamp = _candidate_timestamp(candidate)
            if symbols and str(candidate.get("symbol")) not in symbols:
                continue
            if intervals and str(candidate.get("interval") or "1min") not in intervals:
                continue
            if setups and str(candidate.get("setup_type")) not in setups:
                continue
            if sides and str(candidate.get("side")) not in sides:
                continue
            if config.start and timestamp < config.start:
                continue
            if config.end and timestamp > config.end:
                continue
            selected.append(candidate)
        return selected

    def _candidate_priority(self, candidate: dict[str, Any]) -> tuple[Any, ...]:
        confidence = self._float_or_none(candidate.get("confidence_score") or candidate.get("signal_score")) or 0.0
        expected_r = self._float_or_none(candidate.get("expected_r")) or 0.0
        return (
            _candidate_timestamp(candidate),
            -confidence,
            -expected_r,
            str(candidate.get("symbol") or ""),
            str(candidate.get("setup_type") or ""),
        )

    def _bars_by_key(self, bars: list[Bar]) -> dict[tuple[str, str], list[Bar]]:
        grouped: dict[tuple[str, str], list[Bar]] = {}
        for bar in bars:
            grouped.setdefault((bar.symbol, bar.interval), []).append(bar)
        for rows in grouped.values():
            rows.sort(key=lambda bar: bar.timestamp_utc)
        return grouped

    def _features_by_key(self, features: list[dict[str, Any]]) -> dict[tuple[str, str, datetime], dict[str, Any]]:
        output = {}
        for feature in features:
            timestamp = _parse_datetime(feature.get("timestamp_utc") or feature.get("timestamp"))
            output[(str(feature["symbol"]), str(feature.get("interval") or "1min"), timestamp)] = feature
        return output

    def _candidate_market_regime(self, candidate: dict[str, Any], features: dict[tuple[str, str, datetime], dict[str, Any]]) -> str | None:
        timestamp = _candidate_timestamp(candidate)
        feature = features.get((str(candidate["symbol"]), str(candidate.get("interval") or "1min"), timestamp))
        return str(candidate.get("market_regime") or (feature or {}).get("market_regime") or "unknown")

    def _candidate_time_bucket(self, candidate: dict[str, Any], features: dict[tuple[str, str, datetime], dict[str, Any]]) -> str | None:
        timestamp = _candidate_timestamp(candidate)
        feature = features.get((str(candidate["symbol"]), str(candidate.get("interval") or "1min"), timestamp))
        return str(candidate.get("time_bucket") or (feature or {}).get("time_bucket") or "unknown")

    def _entry_price(self, raw_open: float, side: str, config: ReplayConfig) -> float:
        cost = (config.slippage_bps + config.spread_bps / 2) / 10_000
        return raw_open * (1 + cost) if side == Side.LONG.value else raw_open * (1 - cost)

    def _time_exit_price(self, raw_close: float, side: str, config: ReplayConfig) -> float:
        cost = (config.slippage_bps + config.spread_bps / 2) / 10_000
        return raw_close * (1 - cost) if side == Side.LONG.value else raw_close * (1 + cost)

    def _stop_price(
        self,
        candidate: dict[str, Any],
        feature: dict[str, Any] | None,
        past_bars: list[Bar],
        entry: float,
        side: str,
        config: ReplayConfig,
    ) -> float | None:
        explicit = self._float_or_none(candidate.get("stop_price"))
        if explicit is not None:
            return explicit
        if config.stop_mode == "fixed_risk":
            risk = entry * 0.005
            return entry - risk if side == Side.LONG.value else entry + risk
        context = dict(candidate.get("invalidation_context") or {})
        entry_context = dict(candidate.get("entry_context") or {})
        feature = feature or {}
        atr = (
            self._float_or_none(feature.get("atr_14"))
            or self._float_or_none(feature.get("atr_14_proxy"))
            or self._float_or_none(entry_context.get("atr_14"))
            or entry * 0.002
        )
        atr = max(float(atr), entry * 0.001)
        if side == Side.LONG.value:
            candidates = [
                self._float_or_none(context.get("opening_range_low")),
                self._float_or_none(context.get("premarket_low")),
                self._float_or_none(context.get("previous_day_low")),
                self._float_or_none(entry_context.get("vwap")),
                entry - atr,
            ]
            if past_bars:
                candidates.append(min(bar.low for bar in past_bars[-10:]))
            valid = [value for value in candidates if value is not None and value < entry]
            return max(valid) if valid else None
        candidates = [
            self._float_or_none(context.get("opening_range_high")),
            self._float_or_none(context.get("premarket_high")),
            self._float_or_none(context.get("previous_day_high")),
            self._float_or_none(entry_context.get("vwap")),
            entry + atr,
        ]
        if past_bars:
            candidates.append(max(bar.high for bar in past_bars[-10:]))
        valid = [value for value in candidates if value is not None and value > entry]
        return min(valid) if valid else None

    def _targets(self, candidate: dict[str, Any], entry: float, risk: float, side: str, config: ReplayConfig) -> tuple[float, float, float]:
        explicit = [self._float_or_none(candidate.get(key)) for key in ("target_1", "target_2", "target_3")]
        if config.target_mode == "candidate_targets" and all(value is not None for value in explicit):
            return explicit[0], explicit[1], explicit[2]  # type: ignore[return-value]
        multiples = (config.target_1_r, config.target_2_r, config.target_3_r)
        if side == Side.LONG.value:
            return tuple(entry + risk * multiple for multiple in multiples)  # type: ignore[return-value]
        return tuple(entry - risk * multiple for multiple in multiples)  # type: ignore[return-value]

    def _reward_risk(self, entry: float, target: float, risk: float, side: str) -> float:
        return (target - entry) / risk if side == Side.LONG.value else (entry - target) / risk

    def _session_exit(self, bar: Bar, side: str, config: ReplayConfig) -> bool:
        if not config.close_at_session_end or config.session != "rth":
            return False
        timestamp_et = bar.timestamp_et.astimezone(ET)
        return _minute_of_day(timestamp_et) >= RTH_END_MINUTE - self._interval_minutes(bar.interval)

    def _breakdown(self, trades: list[SimulatedTrade], field: str) -> dict[str, dict[str, Any]]:
        buckets: dict[str, list[SimulatedTrade]] = {}
        for trade in trades:
            buckets.setdefault(str(getattr(trade, field) or "unknown"), []).append(trade)
        output = {}
        for key, rows in buckets.items():
            returns = [trade.realized_r for trade in rows]
            output[key] = {
                "total_trades": len(rows),
                "average_r": mean(returns) if returns else 0.0,
                "median_r": median(returns) if returns else 0.0,
                "win_rate": len([value for value in returns if value > 0]) / len(rows) if rows else 0.0,
                "total_r": sum(returns),
                "profit_factor": self._profit_factor(returns),
            }
        return output

    def _daily_r(self, trades: list[SimulatedTrade]) -> list[dict[str, Any]]:
        buckets: dict[date, float] = {}
        for trade in trades:
            if trade.exit_timestamp_utc is None:
                continue
            key = trade.exit_timestamp_utc.astimezone(UTC).date()
            buckets[key] = buckets.get(key, 0.0) + trade.realized_r
        return [{"date": key.isoformat(), "r": value} for key, value in sorted(buckets.items())]

    def _drawdown_series(self, equity: list[float]) -> list[float]:
        peak = 0.0
        series = []
        for value in equity:
            peak = max(peak, value)
            series.append(value - peak)
        return series

    def _profit_factor(self, returns: list[float]) -> float:
        gains = sum(value for value in returns if value > 0)
        losses = abs(sum(value for value in returns if value < 0))
        if losses == 0:
            return float("inf") if gains > 0 else 0.0
        return gains / losses

    def _max_consecutive(self, trades: list[SimulatedTrade], positive: bool) -> int:
        best = 0
        current = 0
        for trade in trades:
            matched = trade.realized_r > 0 if positive else trade.realized_r < 0
            current = current + 1 if matched else 0
            best = max(best, current)
        return best

    def _data_quality_summary(self, trades: list[SimulatedTrade]) -> dict[str, Any]:
        return {"skipped": dict(Counter(trade.skip_reason or "none" for trade in trades if trade.status == "SKIPPED"))}

    def _run_id(self, config: ReplayConfig) -> str:
        digest = sha256(str(config.to_dict()).encode("utf-8")).hexdigest()[:24]
        return f"replay_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}_{digest}"

    def _candidate_id(self, candidate: dict[str, Any]) -> str:
        return "candidate_" + sha256(
            f"{candidate.get('symbol')}:{candidate.get('interval')}:{candidate.get('timestamp_utc')}:{candidate.get('side')}:{candidate.get('setup_type')}".encode()
        ).hexdigest()[:32]

    def _trade_id(self, *parts: Any) -> str:
        return "simtrade_" + sha256("|".join(str(part) for part in parts).encode()).hexdigest()[:32]

    def _interval_minutes(self, interval: str) -> int:
        if interval.endswith("min"):
            return int(interval.removesuffix("min"))
        return 1

    def _float_or_none(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None


def _candidate_timestamp(candidate: dict[str, Any]) -> datetime:
    return _parse_datetime(candidate.get("timestamp_utc") or candidate.get("timestamp"))


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)
    parsed = datetime.fromisoformat(str(value))
    return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _minute_of_day(timestamp_et: datetime) -> int:
    return timestamp_et.hour * 60 + timestamp_et.minute


def _is_rth(timestamp: datetime) -> bool:
    timestamp_et = timestamp.astimezone(ET)
    minute = _minute_of_day(timestamp_et)
    return RTH_START_MINUTE <= minute < RTH_END_MINUTE
