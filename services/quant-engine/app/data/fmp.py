from __future__ import annotations

import asyncio
import os
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.utils.time import UTC

try:
    import httpx
except ModuleNotFoundError:  # pragma: no cover - compatibility path for mocked pure tests
    httpx = None

from app.config import Settings, get_settings
from app.data.provider import MarketDataProvider
from app.data.symbols import normalize_symbol, normalize_symbols
from app.schemas.market import Bar, Quote
from app.utils.secrets import redact_url

FMP_PROVIDER = "fmp"
CAPABILITY_SYMBOLS = ["SPY", "QQQ", "AAPL", "NVDA"]
SUPPORTED_INTRADAY_INTERVALS = {"1min", "5min", "15min"}
OPTIONAL_INTRADAY_INTERVALS = {"30min", "1hour", "4hour"}
CAPABILITY_STATUSES = {
    "ACCESSIBLE",
    "DENIED",
    "RATE_LIMITED",
    "EMPTY",
    "ERROR",
    "SKIPPED_NO_KEY",
    "SKIPPED_MARKET_CLOSED",
    "UNKNOWN",
}


@dataclass(frozen=True)
class FMPEndpoint:
    key: str
    category: str
    path: str
    request_type: str = "REST"
    interval: str | None = None
    batch: bool = False
    optional: bool = False


@dataclass
class FMPResponse:
    request_id: str
    endpoint_key: str
    endpoint_category: str
    path: str
    status: str
    http_status: int | None
    data: Any
    started_at: datetime
    finished_at: datetime
    latency_ms: int
    sample_count: int
    response_shape: dict[str, Any]
    symbol: str | None = None
    interval: str | None = None
    error_code: str | None = None
    error_class: str | None = None
    error_message: str | None = None

    def provider_request_metadata(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "endpoint_key": self.endpoint_key,
            "endpoint_category": self.endpoint_category,
            "path": self.path,
            "latency_ms": self.latency_ms,
            "sample_count": self.sample_count,
            "response_shape": self.response_shape,
            "error_code": self.error_code,
            "error_class": self.error_class,
            "auth": "header",
            "secret_redacted": True,
        }

    def capability_payload(self, *, sample_symbol: str | None = None, symbol_scope: list[str] | None = None) -> dict[str, Any]:
        return {
            "provider": FMP_PROVIDER,
            "endpoint_key": self.endpoint_key,
            "endpoint_category": self.endpoint_category,
            "symbol_scope": symbol_scope or ([sample_symbol] if sample_symbol else []),
            "request_type": "REST",
            "status": self.status,
            "http_status": self.http_status,
            "error_code": self.error_code,
            "error_class": self.error_class,
            "response_shape": self.response_shape,
            "sample_symbol": sample_symbol or self.symbol,
            "sample_count": self.sample_count,
            "latency_ms": self.latency_ms,
            "entitlement_notes": {
                "auth_mode": "header",
                "path": self.path,
                "websocket_default": False,
                "error": self.error_message,
            },
            "checked_at": self.finished_at.isoformat(),
        }


class FMPClientError(RuntimeError):
    def __init__(self, message: str, response: FMPResponse | None = None) -> None:
        super().__init__(message)
        self.response = response


ENDPOINTS: dict[str, FMPEndpoint] = {
    "quote": FMPEndpoint("quote", "quote", "quote"),
    "quote_short": FMPEndpoint("quote_short", "quote", "quote-short"),
    "batch_quote": FMPEndpoint("batch_quote", "quote", "batch-quote", batch=True),
    "batch_quote_short": FMPEndpoint("batch_quote_short", "quote", "batch-quote-short", batch=True),
    "historical_eod_full": FMPEndpoint("historical_eod_full", "historical_eod", "historical-price-eod/full"),
    "intraday_1min": FMPEndpoint("intraday_1min", "intraday", "historical-chart/1min", interval="1min"),
    "intraday_5min": FMPEndpoint("intraday_5min", "intraday", "historical-chart/5min", interval="5min"),
    "intraday_15min": FMPEndpoint("intraday_15min", "intraday", "historical-chart/15min", interval="15min"),
    "intraday_30min": FMPEndpoint("intraday_30min", "intraday", "historical-chart/30min", interval="30min", optional=True),
    "intraday_1hour": FMPEndpoint("intraday_1hour", "intraday", "historical-chart/1hour", interval="1hour", optional=True),
    "intraday_4hour": FMPEndpoint("intraday_4hour", "intraday", "historical-chart/4hour", interval="4hour", optional=True),
    "websocket_us_stocks_probe": FMPEndpoint(
        "websocket_us_stocks_probe",
        "websocket",
        "wss://financialmodelingprep.com/ws/us-stocks",
        request_type="WebSocket",
        optional=True,
    ),
}


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


def _sample_count(payload: Any) -> int:
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        for key in ("historical", "data", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return len(value)
        return 1 if payload else 0
    return 0


def _response_shape(payload: Any) -> dict[str, Any]:
    if isinstance(payload, list):
        first = next((item for item in payload if isinstance(item, dict)), None)
        return {
            "type": "list",
            "count": len(payload),
            "first_keys": sorted(str(key) for key in first.keys())[:20] if first else [],
        }
    if isinstance(payload, dict):
        shape: dict[str, Any] = {"type": "dict", "keys": sorted(str(key) for key in payload.keys())[:20]}
        for key in ("historical", "data", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                shape[f"{key}_count"] = len(value)
        return shape
    return {"type": type(payload).__name__}


def _safe_error_message(exc: Exception | str | None) -> str | None:
    if exc is None:
        return None
    message = str(exc)
    for secret in (os.environ.get("FMP_API_KEY"), os.environ.get("DATABASE_URL")):
        if secret:
            message = message.replace(secret, "[REDACTED]")
    return message.replace("apikey=", "apikey=[REDACTED]&")


def _classify_http(status_code: int | None, payload: Any = None) -> tuple[str, str | None]:
    if status_code in {401, 403}:
        return "DENIED", "http_auth_or_entitlement_denied"
    if status_code == 429:
        return "RATE_LIMITED", "http_rate_limited"
    if status_code is not None and status_code >= 400:
        return "ERROR", f"http_{status_code}"
    if _sample_count(payload) == 0:
        return "EMPTY", "empty_response"
    return "ACCESSIBLE", None


class FMPClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._request_count = 0
        self._lock = asyncio.Lock()

    @property
    def request_count(self) -> int:
        return self._request_count

    @property
    def key_present(self) -> bool:
        return bool(self.settings.fmp_api_key)

    async def get(self, path: str, params: dict[str, object] | None = None) -> object:
        response = await self.request(endpoint_key=path.replace("/", "_").replace("-", "_"), path=path, params=params)
        if response.status not in {"ACCESSIBLE", "EMPTY"}:
            raise FMPClientError(response.error_message or "FMP request failed safely", response)
        return response.data

    async def request(
        self,
        *,
        endpoint_key: str,
        path: str,
        params: dict[str, object] | None = None,
        symbol: str | None = None,
        interval: str | None = None,
    ) -> FMPResponse:
        request_id = f"fmp_req_{uuid4().hex}"
        started = datetime.now(UTC)
        monotonic_start = time.perf_counter()
        endpoint = ENDPOINTS.get(endpoint_key) or FMPEndpoint(endpoint_key, "unknown", path)
        if not self.settings.fmp_api_key:
            finished = datetime.now(UTC)
            return FMPResponse(
                request_id=request_id,
                endpoint_key=endpoint_key,
                endpoint_category=endpoint.category,
                path=path,
                status="SKIPPED_NO_KEY",
                http_status=None,
                data=[],
                started_at=started,
                finished_at=finished,
                latency_ms=0,
                sample_count=0,
                response_shape={"type": "skipped"},
                symbol=symbol,
                interval=interval,
                error_code="fmp_api_key_required",
                error_class="MissingFMPCredential",
                error_message="FMP_API_KEY is not configured in the runtime environment.",
            )
        url = f"{self.settings.fmp_base_url.rstrip('/')}/{path.lstrip('/')}"
        safe_url = redact_url(url)
        request_params = dict(params or {})
        request_params.pop("apikey", None)
        last_response: FMPResponse | None = None
        last_exception: Exception | None = None
        for attempt in range(1, max(1, self.settings.max_retries) + 1):
            try:
                async with self._lock:
                    self._request_count += 1
                if httpx is None:
                    raise RuntimeError("httpx is not installed; install backend dependencies before live FMP calls")
                async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
                    response = await client.get(url, params=request_params, headers={"apikey": self.settings.fmp_api_key})
                try:
                    payload = response.json()
                except Exception as exc:
                    payload = []
                    last_exception = exc
                status, error_code = _classify_http(response.status_code, payload)
                finished = datetime.now(UTC)
                last_response = FMPResponse(
                    request_id=request_id,
                    endpoint_key=endpoint_key,
                    endpoint_category=endpoint.category,
                    path=path,
                    status=status,
                    http_status=response.status_code,
                    data=payload,
                    started_at=started,
                    finished_at=finished,
                    latency_ms=int((time.perf_counter() - monotonic_start) * 1000),
                    sample_count=_sample_count(payload),
                    response_shape=_response_shape(payload),
                    symbol=symbol,
                    interval=interval,
                    error_code=error_code,
                    error_class="HTTPStatusError" if status in {"DENIED", "RATE_LIMITED", "ERROR"} else None,
                    error_message=None if status in {"ACCESSIBLE", "EMPTY"} else f"FMP {status.lower()} for {path}",
                )
                if status == "RATE_LIMITED" and attempt < self.settings.max_retries:
                    await asyncio.sleep(min(2.0**attempt, 8.0))
                    continue
                return last_response
            except Exception as exc:  # pragma: no cover - retry timing is integration behavior
                last_exception = exc
                if attempt >= self.settings.max_retries:
                    break
                await asyncio.sleep(min(2.0**attempt, 8.0))
        finished = datetime.now(UTC)
        return FMPResponse(
            request_id=request_id,
            endpoint_key=endpoint_key,
            endpoint_category=endpoint.category,
            path=path,
            status=last_response.status if last_response is not None else "ERROR",
            http_status=last_response.http_status if last_response is not None else None,
            data=last_response.data if last_response is not None else [],
            started_at=started,
            finished_at=finished,
            latency_ms=int((time.perf_counter() - monotonic_start) * 1000),
            sample_count=last_response.sample_count if last_response is not None else 0,
            response_shape=last_response.response_shape if last_response is not None else {"type": "error"},
            symbol=symbol,
            interval=interval,
            error_code=last_response.error_code if last_response is not None else "transport_error",
            error_class=type(last_exception).__name__ if last_exception is not None else "FMPClientError",
            error_message=_safe_error_message(last_exception) or f"FMP request failed after retries: {safe_url}",
        )


class FMPMarketDataProvider(MarketDataProvider):
    def __init__(self, settings: Settings | None = None, client: FMPClient | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = client or FMPClient(self.settings)

    def capability_matrix(self) -> list[dict[str, object]]:
        return [
            {
                "endpoint_key": endpoint.key,
                "name": endpoint.path,
                "endpoint_category": endpoint.category,
                "transport": endpoint.request_type,
                "v1": endpoint.key in {
                    "quote",
                    "quote_short",
                    "batch_quote",
                    "batch_quote_short",
                    "historical_eod_full",
                    "intraday_1min",
                    "intraday_5min",
                    "intraday_15min",
                },
                "batch": endpoint.batch,
                "optional": endpoint.optional,
                "auth": "header",
            }
            for endpoint in ENDPOINTS.values()
        ]

    async def request_endpoint(
        self,
        endpoint_key: str,
        *,
        symbol: str | None = None,
        symbols: list[str] | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> FMPResponse:
        endpoint = ENDPOINTS[endpoint_key]
        if endpoint.request_type == "WebSocket":
            return await self.websocket_probe(symbols or CAPABILITY_SYMBOLS)
        params: dict[str, object] = {}
        normalized_symbols = normalize_symbols(symbols or [])
        normalized_symbol = normalize_symbol(symbol or (normalized_symbols[0] if normalized_symbols else CAPABILITY_SYMBOLS[0]))
        if endpoint.batch:
            params["symbols"] = ",".join(normalized_symbols or CAPABILITY_SYMBOLS)
        else:
            params["symbol"] = normalized_symbol
        if endpoint.category in {"historical_eod", "intraday"}:
            probe_end = end or datetime.now(UTC) - timedelta(days=1)
            probe_start = start or probe_end - timedelta(days=7)
            params["from"] = probe_start.date().isoformat()
            params["to"] = probe_end.date().isoformat()
        if not hasattr(self.client, "request"):
            started = datetime.now(UTC)
            payload = await self.client.get(endpoint.path, params)  # type: ignore[attr-defined]
            finished = datetime.now(UTC)
            return FMPResponse(
                request_id=f"fmp_req_{uuid4().hex}",
                endpoint_key=endpoint_key,
                endpoint_category=endpoint.category,
                path=endpoint.path,
                status="ACCESSIBLE" if _sample_count(payload) else "EMPTY",
                http_status=200,
                data=payload,
                started_at=started,
                finished_at=finished,
                latency_ms=0,
                sample_count=_sample_count(payload),
                response_shape=_response_shape(payload),
                symbol=normalized_symbol,
                interval=endpoint.interval,
            )
        return await self.client.request(
            endpoint_key=endpoint_key,
            path=endpoint.path,
            params=params,
            symbol=normalized_symbol,
            interval=endpoint.interval,
        )

    async def capability_check(self, endpoint_key: str, symbols: list[str] | None = None) -> dict[str, Any]:
        if endpoint_key not in ENDPOINTS:
            return {
                "provider": FMP_PROVIDER,
                "endpoint_key": endpoint_key,
                "endpoint_category": "unknown",
                "symbol_scope": normalize_symbols(symbols or []),
                "request_type": "REST",
                "status": "UNKNOWN",
                "http_status": None,
                "sample_count": 0,
                "response_shape": {"type": "unknown"},
                "entitlement_notes": {"reason": "unsupported_endpoint_key"},
                "checked_at": datetime.now(UTC).isoformat(),
            }
        response = await self.request_endpoint(endpoint_key, symbols=symbols or CAPABILITY_SYMBOLS)
        return response.capability_payload(
            sample_symbol=normalize_symbols(symbols or CAPABILITY_SYMBOLS)[0],
            symbol_scope=normalize_symbols(symbols or CAPABILITY_SYMBOLS),
        )

    async def get_quote(self, symbol: str) -> Quote:
        response = await self.request_endpoint("quote", symbol=symbol)
        self._raise_if_unusable(response, f"No quote returned for {symbol}")
        rows = response.data if isinstance(response.data, list) else []
        return self._quote_from_row(rows[0])

    async def get_quote_short(self, symbol: str) -> Quote:
        response = await self.request_endpoint("quote_short", symbol=symbol)
        self._raise_if_unusable(response, f"No quote-short returned for {symbol}")
        rows = response.data if isinstance(response.data, list) else []
        return self._quote_from_row(rows[0])

    async def get_batch_quotes(self, symbols: list[str]) -> list[Quote]:
        normalized = normalize_symbols(symbols)
        if not normalized:
            return []
        response = await self.request_endpoint("batch_quote", symbols=normalized)
        rows = response.data if isinstance(response.data, list) else []
        if rows:
            return [self._quote_from_row(row) for row in rows if isinstance(row, dict)]
        return [await self.get_quote(symbol) for symbol in normalized]

    async def get_batch_quote_short(self, symbols: list[str]) -> list[Quote]:
        normalized = normalize_symbols(symbols)
        if not normalized:
            return []
        response = await self.request_endpoint("batch_quote_short", symbols=normalized)
        rows = response.data if isinstance(response.data, list) else []
        if rows:
            return [self._quote_from_row(row) for row in rows if isinstance(row, dict)]
        return [await self.get_quote_short(symbol) for symbol in normalized]

    async def get_historical_bars(
        self, symbol: str, interval: str, start: datetime, end: datetime
    ) -> list[Bar]:
        return await self.get_intraday_bars(symbol, interval, start, end)

    async def get_intraday_bars(self, symbol: str, interval: str, start: datetime, end: datetime) -> list[Bar]:
        interval = str(interval)
        if interval not in SUPPORTED_INTRADAY_INTERVALS | OPTIONAL_INTRADAY_INTERVALS:
            raise ValueError(f"Unsupported FMP intraday interval: {interval}")
        endpoint_key = f"intraday_{interval}"
        response = await self.request_endpoint(endpoint_key, symbol=symbol, start=start, end=end)
        if response.status not in {"ACCESSIBLE", "EMPTY"}:
            raise FMPClientError(response.error_message or f"FMP intraday request failed for {interval}", response)
        rows = response.data if isinstance(response.data, list) else []
        bars = [self._bar_from_row(normalize_symbol(symbol), interval, row) for row in rows if isinstance(row, dict)]
        return sorted(bars, key=lambda bar: bar.timestamp_utc)

    async def get_daily_bars(self, symbol: str, start: datetime, end: datetime) -> list[Bar]:
        return await self.get_eod_bars(symbol, start, end)

    async def get_eod_bars(self, symbol: str, start: datetime, end: datetime) -> list[Bar]:
        response = await self.request_endpoint("historical_eod_full", symbol=symbol, start=start, end=end)
        if response.status not in {"ACCESSIBLE", "EMPTY"}:
            raise FMPClientError(response.error_message or "FMP EOD request failed", response)
        if isinstance(response.data, dict):
            rows = response.data.get("historical") or response.data.get("data") or []
        else:
            rows = response.data if isinstance(response.data, list) else []
        bars = [self._bar_from_row(normalize_symbol(symbol), "1day", row) for row in rows if isinstance(row, dict)]
        return sorted(bars, key=lambda bar: bar.timestamp_utc)

    async def stream_quotes(self, symbols: list[str]) -> AsyncIterator[Quote]:
        normalized = normalize_symbols(symbols)
        while True:
            for quote in await self.get_batch_quotes(normalized):
                yield quote
            await asyncio.sleep(self.settings.rest_poll_seconds)

    async def get_market_calendar_or_hours(self) -> dict[str, object]:
        response = await self.client.request(endpoint_key="market_hours", path="is-the-market-open", params={})
        return {
            "status": response.status.lower(),
            "payload": response.data if response.status in {"ACCESSIBLE", "EMPTY"} else {},
            "warning": response.error_message,
        }

    async def get_symbol_profile(self, symbol: str) -> dict[str, object]:
        payload = await self.client.get("profile", {"symbol": normalize_symbol(symbol)})
        return {"symbol": normalize_symbol(symbol), "payload": payload}

    async def health_check(self) -> dict[str, object]:
        if not self.settings.fmp_api_key:
            return {"status": "missing_api_key", "fmp_api_key_configured": False, "requests": self.client.request_count}
        result = await self.capability_check("quote", ["AAPL"])
        status = "ok" if result.get("status") == "ACCESSIBLE" else "limited"
        return {
            "status": status,
            "fmp_api_key_configured": True,
            "capability_status": result.get("status"),
            "requests": self.client.request_count,
            "warning": result.get("error_code"),
        }

    async def websocket_probe(self, symbols: list[str] | None = None) -> FMPResponse:
        endpoint = ENDPOINTS["websocket_us_stocks_probe"]
        started = datetime.now(UTC)
        enabled = os.environ.get("AMD_ENABLE_FMP_WS_PROBE", "").strip().lower() in {"1", "true", "yes", "on"}
        if not self.settings.fmp_api_key:
            status = "SKIPPED_NO_KEY"
            error_code = "fmp_api_key_required"
        elif not enabled:
            status = "UNKNOWN"
            error_code = "websocket_probe_disabled"
        else:
            status = "UNKNOWN"
            error_code = "websocket_probe_not_implemented_in_v1"
        finished = datetime.now(UTC)
        return FMPResponse(
            request_id=f"fmp_req_{uuid4().hex}",
            endpoint_key=endpoint.key,
            endpoint_category=endpoint.category,
            path=endpoint.path,
            status=status,
            http_status=None,
            data=[],
            started_at=started,
            finished_at=finished,
            latency_ms=0,
            sample_count=0,
            response_shape={"type": "websocket_probe", "symbols": normalize_symbols(symbols or [])},
            error_code=error_code,
            error_class="WebSocketProbe",
            error_message="WebSocket probe is disabled by default and not used for production ingestion.",
        )

    def _raise_if_unusable(self, response: FMPResponse, fallback: str) -> None:
        if response.status not in {"ACCESSIBLE", "EMPTY"}:
            raise FMPClientError(response.error_message or fallback, response)
        rows = response.data if isinstance(response.data, list) else []
        if not rows:
            raise FMPClientError(fallback, response)

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
            source=FMP_PROVIDER,
            raw={key: value for key, value in row.items() if str(key).lower() != "apikey"},
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
            vwap=float(row["vwap"]) if row.get("vwap") is not None else None,
            source=FMP_PROVIDER,
            ingestion_time=datetime.now(UTC),
            quality_flags=[],
        )
