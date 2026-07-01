from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import httpx

from app.config import Settings, get_settings
from app.data.provider import MarketDataProvider
from app.data.symbols import normalize_symbol, normalize_symbols
from app.schemas.market import Bar, Quote
from app.utils.secrets import redact_url


class FMPClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._request_count = 0
        self._lock = asyncio.Lock()

    @property
    def request_count(self) -> int:
        return self._request_count

    async def get(self, path: str, params: dict[str, object] | None = None) -> object:
        if not self.settings.fmp_api_key:
            raise RuntimeError("FMP_API_KEY is not configured")
        params = dict(params or {})
        params["apikey"] = self.settings.fmp_api_key
        url = f"{self.settings.fmp_base_url.rstrip('/')}/{path.lstrip('/')}"
        last_error: Exception | None = None
        for attempt in range(1, self.settings.max_retries + 1):
            try:
                async with self._lock:
                    self._request_count += 1
                async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
                    response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
            except Exception as exc:  # pragma: no cover - retry timing is integration behavior
                last_error = exc
                if attempt >= self.settings.max_retries:
                    break
                await asyncio.sleep(min(2.0**attempt, 8.0))
        safe_url = redact_url(str(httpx.URL(url, params=params)))
        raise RuntimeError(f"FMP request failed after retries: {safe_url}") from last_error


def _parse_timestamp(value: object, tz_name: str) -> tuple[datetime, datetime]:
    tz = ZoneInfo(tz_name)
    if isinstance(value, (int, float)):
        timestamp_utc = datetime.fromtimestamp(float(value), tz=UTC)
        return timestamp_utc, timestamp_utc.astimezone(tz)
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            timestamp_et = parsed.replace(tzinfo=tz)
            return timestamp_et.astimezone(UTC), timestamp_et
        return parsed.astimezone(UTC), parsed.astimezone(tz)
    now = datetime.now(UTC)
    return now, now.astimezone(tz)


class FMPMarketDataProvider(MarketDataProvider):
    def __init__(self, settings: Settings | None = None, client: FMPClient | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = client or FMPClient(self.settings)

    def capability_matrix(self) -> list[dict[str, object]]:
        return [
            {"name": "quote", "transport": "REST", "v1": True, "batch": False},
            {"name": "quote-short", "transport": "REST", "v1": True, "batch": False},
            {"name": "batch-quote", "transport": "REST", "v1": True, "batch": True},
            {"name": "historical-chart/1min", "transport": "REST", "v1": True, "batch": False},
            {"name": "historical-chart/5min", "transport": "REST", "v1": True, "batch": False},
            {"name": "historical-chart/15min", "transport": "REST", "v1": True, "batch": False},
            {"name": "historical-price-eod/full", "transport": "REST", "v1": True, "batch": False},
            {"name": "websocket-us-stocks", "transport": "WebSocket", "v1": "optional", "batch": True},
            {"name": "options-opra-gamma-l2", "transport": "future-adapter", "v1": False, "gap": True},
        ]

    async def get_quote(self, symbol: str) -> Quote:
        symbol = normalize_symbol(symbol)
        payload = await self.client.get("quote", {"symbol": symbol})
        rows = payload if isinstance(payload, list) else []
        if not rows:
            raise RuntimeError(f"No quote returned for {symbol}")
        return self._quote_from_row(rows[0])

    async def get_batch_quotes(self, symbols: list[str]) -> list[Quote]:
        normalized = normalize_symbols(symbols)
        if not normalized:
            return []
        payload = await self.client.get("batch-quote", {"symbols": ",".join(normalized)})
        rows = payload if isinstance(payload, list) else []
        if rows:
            return [self._quote_from_row(row) for row in rows if isinstance(row, dict)]
        return [await self.get_quote(symbol) for symbol in normalized]

    async def get_historical_bars(
        self, symbol: str, interval: str, start: datetime, end: datetime
    ) -> list[Bar]:
        symbol = normalize_symbol(symbol)
        payload = await self.client.get(
            f"historical-chart/{interval}",
            {"symbol": symbol, "from": start.date().isoformat(), "to": end.date().isoformat()},
        )
        rows = payload if isinstance(payload, list) else []
        bars = [self._bar_from_row(symbol, interval, row) for row in rows if isinstance(row, dict)]
        return sorted(bars, key=lambda bar: bar.timestamp_utc)

    async def stream_quotes(self, symbols: list[str]) -> AsyncIterator[Quote]:
        # V1 keeps WebSocket entitlement optional and uses REST polling as the safe default.
        normalized = normalize_symbols(symbols)
        while True:
            for quote in await self.get_batch_quotes(normalized):
                yield quote
            await asyncio.sleep(self.settings.rest_poll_seconds)

    async def get_market_calendar_or_hours(self) -> dict[str, object]:
        try:
            payload = await self.client.get("is-the-market-open", {})
            return {"status": "available", "payload": payload}
        except Exception as exc:
            return {"status": "unknown", "warning": str(exc)}

    async def get_symbol_profile(self, symbol: str) -> dict[str, object]:
        payload = await self.client.get("profile", {"symbol": normalize_symbol(symbol)})
        return {"symbol": normalize_symbol(symbol), "payload": payload}

    async def health_check(self) -> dict[str, object]:
        if not self.settings.fmp_api_key:
            return {"status": "missing_api_key", "requests": self.client.request_count}
        try:
            await self.get_quote("AAPL")
            return {"status": "ok", "requests": self.client.request_count}
        except Exception as exc:
            return {"status": "limited", "warning": str(exc), "requests": self.client.request_count}

    def _quote_from_row(self, row: dict[str, object]) -> Quote:
        symbol = normalize_symbol(str(row.get("symbol", "")))
        price = float(row.get("price") or row.get("priceAvg50") or 0.0)
        timestamp_value = row.get("timestamp")
        timestamp_utc = None
        if timestamp_value is not None:
            timestamp_utc, _timestamp_et = _parse_timestamp(timestamp_value, self.settings.timezone)
        return Quote(
            symbol=symbol,
            price=price,
            timestamp_utc=timestamp_utc,
            volume=int(row.get("volume") or 0) or None,
            source="fmp",
            raw=row,
        )

    def _bar_from_row(self, symbol: str, interval: str, row: dict[str, object]) -> Bar:
        timestamp_utc, timestamp_et = _parse_timestamp(row.get("date"), self.settings.timezone)
        return Bar(
            symbol=symbol,
            interval=interval,
            timestamp_utc=timestamp_utc,
            timestamp_et=timestamp_et,
            open=float(row.get("open") or 0.0),
            high=float(row.get("high") or 0.0),
            low=float(row.get("low") or 0.0),
            close=float(row.get("close") or 0.0),
            volume=int(row.get("volume") or 0),
            source="fmp",
            ingestion_time=datetime.now(UTC),
            quality_flags=[],
        )
