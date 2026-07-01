from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.config import get_settings
from app.data.fmp import FMPMarketDataProvider
from app.features.engine import FeatureEngine
from app.models.engine import ModelEngine
from app.regimes.classifier import RegimeClassifier
from app.schemas.market import Bar, Quote, Signal, Side
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

    def status(self) -> dict[str, object]:
        return {
            "running": self.running,
            "started_at": self.started_at,
            "latest_count": len(self.latest_signals),
            "last_error": self.last_error,
            "context_symbols": sorted({key[0] for key in self.context_bars}),
        }

    async def start(self, symbols: list[str] | None = None, confidence_threshold: float | None = None) -> None:
        if self.running:
            return
        self.running = True
        self.started_at = datetime.now(UTC)
        self._queue = asyncio.Queue(maxsize=500)
        self._task = asyncio.create_task(self._run(symbols, confidence_threshold))

    async def stop(self) -> None:
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def stream(self):
        while True:
            if self._queue is None:
                self._queue = asyncio.Queue(maxsize=500)
            signal = await self._queue.get()
            yield signal

    async def _run(self, symbols: list[str] | None, confidence_threshold: float | None) -> None:
        settings = get_settings()
        provider = FMPMarketDataProvider(settings)
        model = ModelEngine().load()
        selected = symbols or settings.symbol_list
        threshold = confidence_threshold or settings.min_confidence
        if not settings.fmp_api_key:
            self.last_error = "FMP_API_KEY is not configured; scanner requires a provider for live quotes"
            self.running = False
            return
        while self.running:
            try:
                quotes = await provider.get_batch_quotes(selected)
                for quote in quotes:
                    signal = await self.score_quote(provider, quote, model, threshold)
                    self.latest_signals = [signal, *self.latest_signals][:250]
                    if self._queue is not None and not self._queue.full():
                        await self._queue.put(signal)
                await asyncio.sleep(settings.rest_poll_seconds)
            except Exception as exc:  # pragma: no cover - live loop behavior
                self.last_error = str(exc)
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
        if "atr_insufficient_history" in latest_feature.get("data_quality_flags", []):
            signal.warnings.append("context has insufficient ATR history")
        return signal

    async def _hydrate_context(self, provider: FMPMarketDataProvider, symbol: str, now: datetime) -> None:
        key = (symbol, "1min")
        existing = self.context_bars.get(key, [])
        if len(existing) >= self.minimum_context_bars:
            return
        start = now - timedelta(days=max(self.context_lookback_sessions + 2, 7))
        bars = await provider.get_historical_bars(symbol, "1min", start, now)
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
