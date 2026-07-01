from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta

from app.config import get_settings
from app.data.fmp import FMPMarketDataProvider
from app.utils.time import UTC


async def _run() -> int:
    settings = get_settings()
    if not settings.fmp_api_key:
        print("FMP_API_KEY not configured; skipping live FMP REST smoke.")
        return 0
    provider = FMPMarketDataProvider(settings)
    end = datetime.now(UTC)
    start = end - timedelta(days=5)
    quote = await provider.get_quote("AAPL")
    batch = await provider.get_batch_quotes(["AAPL", "SPY"])
    bars = await provider.get_historical_bars("AAPL", "1min", start, end)
    print(
        "FMP live REST smoke ok: "
        f"quote={quote.symbol} batch_rows={len(batch)} intraday_rows={len(bars)} requests={provider.client.request_count}"
    )
    return 0


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        print(f"FMP live REST smoke failed without exposing credentials: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
