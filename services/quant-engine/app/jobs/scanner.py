from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from app.config import get_settings
from app.data.fmp import FMPMarketDataProvider
from app.features.engine import FeatureEngine
from app.models.engine import ModelEngine
from app.schemas.market import Bar, Signal
from app.signals.engine import SignalEngine


class ScannerState:
    def __init__(self) -> None:
        self.running = False
        self.started_at: datetime | None = None
        self.last_error: str | None = None
        self.latest_signals: list[Signal] = []
        self._task: asyncio.Task[None] | None = None
        self._queue: asyncio.Queue[Signal] = asyncio.Queue(maxsize=500)

    def status(self) -> dict[str, object]:
        return {
            "running": self.running,
            "started_at": self.started_at,
            "latest_count": len(self.latest_signals),
            "last_error": self.last_error,
        }

    async def start(self, symbols: list[str] | None = None, confidence_threshold: float | None = None) -> None:
        if self.running:
            return
        self.running = True
        self.started_at = datetime.now(UTC)
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
            signal = await self._queue.get()
            yield signal

    async def _run(self, symbols: list[str] | None, confidence_threshold: float | None) -> None:
        settings = get_settings()
        provider = FMPMarketDataProvider(settings)
        model = ModelEngine().load()
        signal_engine = SignalEngine()
        feature_engine = FeatureEngine()
        selected = symbols or settings.symbol_list
        threshold = confidence_threshold or settings.min_confidence
        while self.running:
            try:
                quotes = await provider.get_batch_quotes(selected)
                now = datetime.now(UTC)
                for quote in quotes:
                    bar = Bar(
                        symbol=quote.symbol,
                        interval="live",
                        timestamp_utc=quote.timestamp_utc or now,
                        timestamp_et=(quote.timestamp_utc or now).astimezone(),
                        open=quote.price,
                        high=quote.price,
                        low=quote.price,
                        close=quote.price,
                        volume=quote.volume or 0,
                        source=quote.source,
                    )
                    feature = feature_engine.build_features([bar])[-1]
                    feature["market_regime"] = "mixed_uncertain"
                    signal = signal_engine.generate(bar, feature, model, threshold)
                    self.latest_signals = [signal, *self.latest_signals][:250]
                    if not self._queue.full():
                        await self._queue.put(signal)
                await asyncio.sleep(settings.rest_poll_seconds)
            except Exception as exc:  # pragma: no cover - live loop behavior
                self.last_error = str(exc)
                await asyncio.sleep(settings.rest_poll_seconds)


scanner_state = ScannerState()
