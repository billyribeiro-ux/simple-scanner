from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import datetime

from app.schemas.market import Bar, Quote


class MarketDataProvider(ABC):
    @abstractmethod
    async def get_quote(self, symbol: str) -> Quote:
        raise NotImplementedError

    @abstractmethod
    async def get_batch_quotes(self, symbols: list[str]) -> list[Quote]:
        raise NotImplementedError

    @abstractmethod
    async def get_historical_bars(
        self, symbol: str, interval: str, start: datetime, end: datetime
    ) -> list[Bar]:
        raise NotImplementedError

    @abstractmethod
    async def stream_quotes(self, symbols: list[str]) -> AsyncIterator[Quote]:
        raise NotImplementedError

    @abstractmethod
    async def get_market_calendar_or_hours(self) -> dict[str, object]:
        raise NotImplementedError

    @abstractmethod
    async def get_symbol_profile(self, symbol: str) -> dict[str, object]:
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> dict[str, object]:
        raise NotImplementedError

    @abstractmethod
    def capability_matrix(self) -> list[dict[str, object]]:
        raise NotImplementedError
