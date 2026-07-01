from __future__ import annotations

import asyncio
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.config import get_settings
from app.data.fmp import FMPMarketDataProvider
from app.data.symbols import normalize_symbols
from app.db.repositories import get_repository_registry
from app.features.engine import FeatureEngine
from app.models.engine import ModelEngine
from app.models.replay_evidence import (
    REPLAY_AWARE_MODEL_TYPE,
    EvidenceCube,
    ReplayAwareMetaScorer,
    score_audit_from_score,
)
from app.regimes.classifier import RegimeClassifier
from app.schemas.market import Bar, Quote, Side, Signal
from app.signals.candidates import CandidateSignalEngine
from app.signals.engine import SignalEngine
from app.utils.time import UTC


class ScannerState:
    def __init__(self) -> None:
        self.running = False
        self.started_at: datetime | None = None
        self.last_error: str | None = None
        self.latest_signals: list[Signal] = []
        self.context_bars: dict[tuple[str, str], list[Bar]] = {}
        self.context_lookback_sessions = 5
        self.minimum_context_bars = 30
        self._task: asyncio.Task[None] | None = None
        self._queue: asyncio.Queue[Signal] | None = None
        self.scanner_run_id: str | None = None
        self._replay_model_cache: dict[str, Any] = {}

    def status(self) -> dict[str, object]:
        return {
            "running": self.running,
            "started_at": self.started_at,
            "latest_count": len(self.latest_signals),
            "last_error": self.last_error,
            "context_symbols": sorted({key[0] for key in self.context_bars}),
            "scanner_run_id": self.scanner_run_id,
        }

    async def start(self, symbols: list[str] | None = None, confidence_threshold: float | None = None) -> None:
        if self.running:
            return
        settings = get_settings()
        selected = normalize_symbols(symbols or settings.symbol_list)
        repository = get_repository_registry()
        model = (
            repository.active_models.get_active(model_type=REPLAY_AWARE_MODEL_TYPE)
            or repository.active_models.get_active()
            or ModelEngine().load()
        )
        threshold = confidence_threshold or settings.min_confidence
        self.running = True
        self.started_at = datetime.now(UTC)
        self._queue = asyncio.Queue(maxsize=500)
        self.scanner_run_id = get_repository_registry().scanner_runs.start(
            selected,
            threshold,
            str(model.get("model_version", "untrained-baseline")),
        )
        self._task = asyncio.create_task(self._run(selected, threshold, model))

    async def stop(self) -> None:
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self.scanner_run_id:
            get_repository_registry().scanner_runs.finish(
                self.scanner_run_id,
                status="stopped",
                latest_error=self.last_error,
                stats={"latest_count": len(self.latest_signals)},
            )

    async def stream(self):
        while True:
            if self._queue is None:
                self._queue = asyncio.Queue(maxsize=500)
            signal = await self._queue.get()
            yield signal

    async def _run(self, symbols: list[str] | None, confidence_threshold: float | None, model: dict[str, Any] | None = None) -> None:
        settings = get_settings()
        provider = FMPMarketDataProvider(settings)
        selected = symbols or settings.symbol_list
        threshold = confidence_threshold or settings.min_confidence
        if not settings.fmp_api_key:
            self.last_error = "FMP_API_KEY is not configured; scanner requires a provider for live quotes"
            self.running = False
            if self.scanner_run_id:
                get_repository_registry().scanner_runs.finish(
                    self.scanner_run_id,
                    status="error",
                    latest_error=self.last_error,
                )
            return
        while self.running:
            try:
                quotes = await provider.get_batch_quotes(selected)
                get_repository_registry().provider_requests.record(
                    provider="fmp",
                    endpoint="batch-quote",
                    status="ok",
                    row_count=len(quotes),
                    metadata={"symbols": selected},
                )
                for quote in quotes:
                    signal = await self.score_quote(provider, quote, model, threshold)
                    self.latest_signals = [signal, *self.latest_signals][:250]
                    get_repository_registry().live_signals.upsert_many([signal], scanner_run_id=self.scanner_run_id)
                    if self._queue is not None and not self._queue.full():
                        await self._queue.put(signal)
                await asyncio.sleep(settings.rest_poll_seconds)
            except Exception as exc:  # pragma: no cover - live loop behavior
                self.last_error = str(exc)
                get_repository_registry().provider_requests.record(
                    provider="fmp",
                    endpoint="batch-quote",
                    status="error",
                    error_message=str(exc),
                    metadata={"symbols": selected},
                )
                await asyncio.sleep(settings.rest_poll_seconds)

    async def score_quote(
        self,
        provider: FMPMarketDataProvider,
        quote: Quote,
        model: dict[str, Any] | None = None,
        confidence_threshold: float = 0.70,
    ) -> Signal:
        model = model or ModelEngine().load()
        now = quote.timestamp_utc or datetime.now(UTC)
        await self._hydrate_context(provider, quote.symbol, now)
        provisional_bar = self._quote_to_bar(quote, now)
        key = (quote.symbol, "1min")
        context = [*self.context_bars.get(key, []), provisional_bar]
        context = sorted(context, key=lambda bar: bar.timestamp_utc)
        if len(context) < self.minimum_context_bars:
            return self._insufficient_context_signal(quote, model, len(context))

        feature_engine = FeatureEngine()
        features = feature_engine.build_features(context)
        latest_feature = features[-1]
        classifier = RegimeClassifier()
        latest_feature["market_regime"] = classifier.classify_market(context)
        latest_feature["ticker_regime"] = classifier.classify_ticker(latest_feature)
        signal = SignalEngine().generate(provisional_bar, latest_feature, model, confidence_threshold)
        if model.get("model_type") == REPLAY_AWARE_MODEL_TYPE:
            signal = self._score_replay_aware(provisional_bar, latest_feature, model, quote.source)
        elif "no_replay_aware_model_active" not in signal.warnings:
            signal.warnings.append("no_replay_aware_model_active")
        if "atr_insufficient_history" in latest_feature.get("data_quality_flags", []):
            signal.warnings.append("context has insufficient ATR history")
        return signal

    def _score_replay_aware(
        self,
        latest_bar: Bar,
        latest_feature: dict[str, Any],
        model: dict[str, Any],
        data_source: str,
    ) -> Signal:
        model_version = str(model.get("model_version") or "unversioned-replay-aware")
        candidates = CandidateSignalEngine().detect_actionable(latest_feature)
        if not candidates:
            return self._no_trade_from_replay_model(
                latest_bar,
                latest_feature,
                model,
                data_source,
                ["no actionable candidate generated"],
                ["no_setup_qualified"],
            )
        cells = self._replay_evidence_cells(model_version)
        if not cells:
            return self._no_trade_from_replay_model(
                latest_bar,
                latest_feature,
                model,
                data_source,
                ["active replay-aware model has no persisted evidence cells"],
                ["no_replay_aware_evidence_cells"],
            )
        cube = EvidenceCube(tuple(cells))
        scorer = ReplayAwareMetaScorer(cube, dict(model.get("scoring_config") or {}))
        scored: list[tuple[dict[str, Any], dict[str, Any]]] = []
        signal_engine = SignalEngine()
        for candidate in candidates:
            payload = asdict(candidate)
            payload["timestamp_utc"] = latest_bar.timestamp_utc
            payload["timestamp"] = latest_bar.timestamp_utc
            side = Side(payload["side"]) if payload["side"] in {Side.LONG.value, Side.SHORT.value} else Side.NO_TRADE
            entry, stop, targets, risk = signal_engine._plan_prices(latest_bar, latest_feature, side)
            payload.update(
                {
                    "entry_price": entry,
                    "stop_price": stop,
                    "target_1": targets[0] if targets else None,
                    "target_2": targets[1] if targets else None,
                    "target_3": targets[2] if targets else None,
                }
            )
            score = scorer.score(payload, latest_feature, model_version=model_version)
            scored.append((payload, score))
        candidate_payload, best_score = max(scored, key=lambda item: float(item[1].get("signal_quality_score") or 0.0))
        get_repository_registry().candidate_score_audits.save(score_audit_from_score(best_score))
        side_value = candidate_payload["side"] if best_score["action"] == "TAKE" else Side.NO_TRADE.value
        side = Side(side_value) if side_value in {Side.LONG.value, Side.SHORT.value} else Side.NO_TRADE
        entry = candidate_payload.get("entry_price") if side != Side.NO_TRADE else None
        stop = candidate_payload.get("stop_price") if side != Side.NO_TRADE else None
        target_1 = candidate_payload.get("target_1") if side != Side.NO_TRADE else None
        target_2 = candidate_payload.get("target_2") if side != Side.NO_TRADE else None
        target_3 = candidate_payload.get("target_3") if side != Side.NO_TRADE else None
        risk = abs(float(entry) - float(stop)) if entry is not None and stop is not None else None
        reasons = [
            f"replay-aware action: {best_score['action']}",
            *list(best_score.get("positive_reason_codes") or []),
            *list(best_score.get("suppression_reasons") or []),
        ]
        warnings = list(best_score.get("warning_codes") or [])
        if best_score["action"] != "TAKE":
            reasons.append("replay-aware meta-scorer did not approve TAKE")
        return Signal(
            timestamp=datetime.now(UTC),
            ticker=latest_bar.symbol,
            side=side,
            entry_price=entry,
            stop_price=stop,
            target_1=target_1,
            target_2=target_2,
            target_3=target_3,
            risk_per_share=risk,
            reward_risk_to_t1=1.0 if risk and target_1 is not None else None,
            reward_risk_to_t2=1.5 if risk and target_2 is not None else None,
            reward_risk_to_t3=2.5 if risk and target_3 is not None else None,
            expected_r=float(best_score.get("expected_r_estimate") or 0.0),
            confidence_score=round(float(best_score.get("signal_quality_score") or 0.0) / 100.0, 4),
            signal_grade=str(best_score.get("grade") or "NO_TRADE"),
            setup_type=str(candidate_payload.get("setup_type") or "no trade suppression"),
            market_regime=str(latest_feature.get("market_regime") or "mixed_uncertain"),
            ticker_regime=str(latest_feature.get("ticker_regime") or "mixed_uncertain"),
            reasons=reasons,
            warnings=warnings,
            historical_sample_size=int(float(best_score.get("sample_confidence_score") or 0.0)),
            historical_win_rate=0.0,
            historical_average_r=float(best_score.get("expected_r_estimate") or 0.0),
            model_version=model_version,
            training_start=self._maybe_dt(model.get("training_start")),
            training_end=self._maybe_dt(model.get("training_end")),
            data_source=data_source,
        )

    def _replay_evidence_cells(self, model_version: str) -> list[dict[str, Any]]:
        cached = self._replay_model_cache.get(model_version)
        if cached is not None:
            return list(cached)
        cells = get_repository_registry().model_evidence_cells.list(model_version, limit=100_000)
        self._replay_model_cache = {model_version: cells}
        return cells

    def _no_trade_from_replay_model(
        self,
        latest_bar: Bar,
        latest_feature: dict[str, Any],
        model: dict[str, Any],
        data_source: str,
        reasons: list[str],
        warnings: list[str],
    ) -> Signal:
        return Signal(
            timestamp=datetime.now(UTC),
            ticker=latest_bar.symbol,
            side=Side.NO_TRADE,
            entry_price=None,
            stop_price=None,
            target_1=None,
            target_2=None,
            target_3=None,
            risk_per_share=None,
            reward_risk_to_t1=None,
            reward_risk_to_t2=None,
            reward_risk_to_t3=None,
            expected_r=0.0,
            confidence_score=0.0,
            signal_grade="NO_TRADE",
            setup_type="replay-aware no trade",
            market_regime=str(latest_feature.get("market_regime") or "mixed_uncertain"),
            ticker_regime=str(latest_feature.get("ticker_regime") or "mixed_uncertain"),
            reasons=reasons,
            warnings=warnings,
            historical_sample_size=0,
            historical_win_rate=0.0,
            historical_average_r=0.0,
            model_version=str(model.get("model_version") or "unversioned-replay-aware"),
            training_start=self._maybe_dt(model.get("training_start")),
            training_end=self._maybe_dt(model.get("training_end")),
            data_source=data_source,
        )

    def _maybe_dt(self, value: object) -> datetime | None:
        if isinstance(value, str):
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return None

    async def _hydrate_context(self, provider: FMPMarketDataProvider, symbol: str, now: datetime) -> None:
        key = (symbol, "1min")
        existing = self.context_bars.get(key, [])
        if len(existing) >= self.minimum_context_bars:
            return
        start = now - timedelta(days=max(self.context_lookback_sessions + 2, 7))
        if self.scanner_run_id is not None:
            persisted = get_repository_registry().bars.query(symbols=[symbol], intervals=["1min"], start=start, end=now)
            if len(persisted) >= self.minimum_context_bars:
                self.context_bars[key] = sorted(persisted, key=lambda bar: bar.timestamp_utc)[-2000:]
                return
        bars = await provider.get_historical_bars(symbol, "1min", start, now)
        if self.scanner_run_id is not None:
            get_repository_registry().bars.upsert_many(bars)
            get_repository_registry().provider_requests.record(
                provider="fmp",
                endpoint="historical-chart/1min",
                status="ok",
                symbol=symbol,
                interval="1min",
                row_count=len(bars),
            )
        self.context_bars[key] = sorted(bars, key=lambda bar: bar.timestamp_utc)[-2000:]

    def _quote_to_bar(self, quote: Quote, timestamp: datetime) -> Bar:
        timestamp = timestamp.astimezone(UTC)
        timestamp_et = timestamp.astimezone(ZoneInfo(get_settings().timezone))
        return Bar(
            symbol=quote.symbol,
            interval="1min",
            timestamp_utc=timestamp,
            timestamp_et=timestamp_et,
            open=quote.price,
            high=quote.price,
            low=quote.price,
            close=quote.price,
            volume=quote.volume or 0,
            source=f"{quote.source}:provisional_quote",
            quality_flags=["provisional_quote_bar"],
        )

    def _insufficient_context_signal(self, quote: Quote, model: dict[str, Any], context_count: int) -> Signal:
        now = quote.timestamp_utc or datetime.now(UTC)
        return Signal(
            timestamp=now,
            ticker=quote.symbol,
            side=Side.NO_TRADE,
            entry_price=None,
            stop_price=None,
            target_1=None,
            target_2=None,
            target_3=None,
            risk_per_share=None,
            reward_risk_to_t1=None,
            reward_risk_to_t2=None,
            reward_risk_to_t3=None,
            expected_r=0.0,
            confidence_score=0.0,
            signal_grade="NO_TRADE",
            setup_type="insufficient context",
            market_regime="mixed_uncertain",
            ticker_regime="mixed_uncertain",
            reasons=["scanner requires historical context before scoring live quotes"],
            warnings=[f"only {context_count} context bars available; minimum is {self.minimum_context_bars}"],
            historical_sample_size=0,
            historical_win_rate=0.0,
            historical_average_r=0.0,
            model_version=str(model.get("model_version", "untrained-baseline")),
            data_source=quote.source,
        )


scanner_state = ScannerState()
