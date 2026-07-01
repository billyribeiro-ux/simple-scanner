from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from app.data.fmp import FMPMarketDataProvider
from app.jobs.scanner import ScannerState
from app.schemas.market import Bar, Quote, Side
from app.utils.secrets import redact_url
from app.utils.time import UTC


class FakeProvider:
    def __init__(self, bars: list[Bar]) -> None:
        self.bars = bars

    async def get_historical_bars(self, symbol, interval, start, end):
        return [bar for bar in self.bars if bar.symbol == symbol and bar.interval == interval]


class FakeClient:
    async def get(self, path, params=None):
        if path == "quote":
            return [{"symbol": "AAPL", "price": 101, "timestamp": 1_780_000_000, "volume": 1000}]
        if path == "batch-quote":
            return [{"symbol": "AAPL", "price": 101, "timestamp": 1_780_000_000, "volume": 1000}]
        if path.startswith("historical-chart"):
            return [
                {"date": "2026-06-01 09:30:00", "open": 100, "high": 101, "low": 99, "close": 100, "volume": 1000}
            ]
        if path == "historical-price-eod/full":
            return [
                {"date": "2026-05-31", "open": 98, "high": 102, "low": 97, "close": 100, "volume": 5000}
            ]
        return []


def test_scanner_suppresses_insufficient_context(make_bar) -> None:
    scanner = ScannerState()
    scanner.minimum_context_bars = 30
    signal = asyncio.run(
        scanner.score_quote(
            FakeProvider([make_bar(0, 100)]),
            Quote(symbol="AAPL", price=101, timestamp_utc=datetime(2026, 6, 1, 14, 0, tzinfo=UTC)),
            {"model_version": "test", "statistical_evidence": {}},
        )
    )
    assert signal.side == Side.NO_TRADE
    assert "minimum is 30" in signal.warnings[0]


def test_scanner_uses_historical_context(make_bar) -> None:
    bars = [make_bar(index, 100 + index * 0.05, volume=1000 + index * 10) for index in range(40)]
    scanner = ScannerState()
    scanner.minimum_context_bars = 30
    signal = asyncio.run(
        scanner.score_quote(
            FakeProvider(bars),
            Quote(symbol="AAPL", price=103, timestamp_utc=bars[-1].timestamp_utc + timedelta(minutes=1)),
            {
                "model_version": "test",
                "statistical_evidence": {
                    "AAPL|trend continuation long|trend_long": {
                        "sample_size": 100,
                        "win_rate": 0.65,
                        "average_r": 0.4,
                    }
                },
            },
        )
    )
    assert "scanner requires historical context" not in signal.reasons


def test_fmp_provider_mocked_quote_batch_intraday_daily() -> None:
    provider = FMPMarketDataProvider(client=FakeClient())
    quote = asyncio.run(provider.get_quote("AAPL"))
    batch = asyncio.run(provider.get_batch_quotes(["AAPL"]))
    intraday = asyncio.run(provider.get_historical_bars("AAPL", "1min", datetime.now(UTC), datetime.now(UTC)))
    daily = asyncio.run(provider.get_daily_bars("AAPL", datetime.now(UTC), datetime.now(UTC)))
    assert quote.symbol == "AAPL"
    assert batch[0].price == 101
    assert intraday[0].interval == "1min"
    assert daily[0].interval == "1day"


def test_secret_redaction() -> None:
    redacted = redact_url("https://example.test/stable/quote?symbol=AAPL&apikey=super-secret")
    assert "super-secret" not in redacted
