from __future__ import annotations

import asyncio
import sys

from app.config import get_settings
from app.db.repositories import get_repository_registry
from app.services.fmp_pipeline import FMPLiveDataService


async def _run() -> int:
    settings = get_settings()
    service = FMPLiveDataService(get_repository_registry(), settings=settings)
    result = await service.smoke()
    if not settings.fmp_api_key:
        print("FMP_API_KEY not configured; live FMP REST smoke skipped safely.")
    else:
        print("FMP live REST smoke completed with redacted provider metadata.")
    print("endpoint_key,status,http_status,sample_count,latency_ms,note")
    for row in result.get("capabilities") or []:
        notes = row.get("entitlement_notes") or {}
        note = notes.get("error") or row.get("error_code") or ""
        print(
            ",".join(
                [
                    str(row.get("endpoint_key") or ""),
                    str(row.get("status") or ""),
                    str(row.get("http_status") or ""),
                    str(row.get("sample_count") or 0),
                    str(row.get("latency_ms") or 0),
                    str(note).replace(",", ";"),
                ]
            )
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
