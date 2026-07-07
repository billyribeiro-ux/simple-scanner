from __future__ import annotations

import asyncio
import json
import sys
from collections import defaultdict
from datetime import date, datetime, time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVICE_ROOT = REPO_ROOT / "services" / "quant-engine"
sys.path.insert(0, str(SERVICE_ROOT))

from app.config import get_settings  # noqa: E402
from app.data.fmp import FMPMarketDataProvider  # noqa: E402
from app.db.repositories import RepositoryRegistry  # noqa: E402
from app.services.fmp_pipeline import FMPLiveDataService  # noqa: E402
from app.utils.time import UTC  # noqa: E402

ET = ZoneInfo("America/New_York")
SYMBOLS = ["SPY", "QQQ", "AAPL", "NVDA"]
INTERVALS = ["1day", "1min", "5min", "15min"]
EXPECTED_DATES = [
    "2026-06-18",
    "2026-06-22",
    "2026-06-23",
    "2026-06-24",
    "2026-06-25",
    "2026-06-26",
    "2026-06-29",
    "2026-06-30",
    "2026-07-01",
    "2026-07-02",
]
KNOWN_SUCCESS_DATES = ["2026-06-30", "2026-07-01", "2026-07-02"]
MISSING_1MIN_DATES = ["2026-06-18", "2026-06-23", "2026-06-24", "2026-06-29"]
ONE_DAY_PROBE_DATES = sorted(set(KNOWN_SUCCESS_DATES + MISSING_1MIN_DATES))
ROLLING_WINDOWS = [
    ("2026-06-18", "2026-07-02"),
    ("2026-06-23", "2026-06-29"),
]


def _start_of_day(day: str) -> datetime:
    return datetime.fromisoformat(day).replace(tzinfo=UTC)


def _end_of_day(day: str) -> datetime:
    return datetime.fromisoformat(day).replace(hour=23, minute=59, second=59, tzinfo=UTC)


def _endpoint_key(interval: str) -> str:
    return "historical_eod_full" if interval == "1day" else f"intraday_{interval}"


def _rows_from_response(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        rows = data.get("historical") or data.get("data") or data.get("results") or []
    else:
        rows = data if isinstance(data, list) else []
    return [row for row in rows if isinstance(row, dict)]


def _is_rth(timestamp_et: datetime, interval: str) -> bool:
    if interval == "1day":
        return True
    local_time = timestamp_et.time()
    return time(9, 30) <= local_time <= time(16, 0)


def _summarize_response(
    *,
    provider: FMPMarketDataProvider,
    response: Any,
    provider_request_id: str,
    probe_type: str,
    requested_start: str,
    requested_end: str,
    symbol: str,
    interval: str,
) -> dict[str, Any]:
    rows = _rows_from_response(response.data)
    parsed_bars = []
    parser_error_count = 0
    for row in rows:
        try:
            parsed_bars.append(provider._bar_from_row(symbol, interval, row))  # noqa: SLF001
        except Exception:
            parser_error_count += 1

    by_date: dict[str, int] = defaultdict(int)
    rth_by_date: dict[str, int] = defaultdict(int)
    earliest_utc = None
    latest_utc = None
    earliest_et = None
    latest_et = None
    for bar in parsed_bars:
        timestamp_utc = bar.timestamp_utc.astimezone(UTC)
        timestamp_et = bar.timestamp_et.astimezone(ET) if bar.timestamp_et else timestamp_utc.astimezone(ET)
        day = timestamp_et.date().isoformat()
        by_date[day] += 1
        if _is_rth(timestamp_et, interval):
            rth_by_date[day] += 1
        earliest_utc = timestamp_utc if earliest_utc is None else min(earliest_utc, timestamp_utc)
        latest_utc = timestamp_utc if latest_utc is None else max(latest_utc, timestamp_utc)
        earliest_et = timestamp_et if earliest_et is None else min(earliest_et, timestamp_et)
        latest_et = timestamp_et if latest_et is None else max(latest_et, timestamp_et)

    requested_dates = [
        item.isoformat()
        for item in _date_range(date.fromisoformat(requested_start), date.fromisoformat(requested_end))
    ]
    requested_rth_dates_present = [day for day in requested_dates if rth_by_date.get(day, 0) > 0]
    requested_any_dates_present = [day for day in requested_dates if by_date.get(day, 0) > 0]
    unexpected_dates = sorted(set(by_date) - set(requested_dates))

    return {
        "probe_type": probe_type,
        "provider_request_id": provider_request_id,
        "request_id": response.request_id,
        "endpoint_key": response.endpoint_key,
        "path": response.path,
        "symbol": symbol,
        "interval": interval,
        "status": response.status,
        "http_status": response.http_status,
        "sample_count": response.sample_count,
        "raw_row_count": len(rows),
        "parsed_bar_count": len(parsed_bars),
        "parser_error_count": parser_error_count,
        "requested_start": requested_start,
        "requested_end": requested_end,
        "requested_any_dates_present": requested_any_dates_present,
        "requested_rth_dates_present": requested_rth_dates_present,
        "unexpected_dates": unexpected_dates,
        "all_dates_present": sorted(by_date),
        "rth_dates_present": sorted(rth_by_date),
        "rows_by_date": dict(sorted(by_date.items())),
        "rth_rows_by_date": dict(sorted(rth_by_date.items())),
        "earliest_timestamp_utc": earliest_utc.isoformat() if earliest_utc else None,
        "latest_timestamp_utc": latest_utc.isoformat() if latest_utc else None,
        "earliest_timestamp_et": earliest_et.isoformat() if earliest_et else None,
        "latest_timestamp_et": latest_et.isoformat() if latest_et else None,
        "response_shape": response.response_shape,
        "error_code": response.error_code,
        "error_class": response.error_class,
    }


def _date_range(start: date, end: date) -> list[date]:
    days = []
    current = start
    while current <= end:
        days.append(current)
        current = date.fromordinal(current.toordinal() + 1)
    return days


def _coverage_matrix(probes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    one_day = [probe for probe in probes if probe["probe_type"] == "one_day"]
    output = []
    for day in EXPECTED_DATES:
        row = {"session_date": day}
        for interval in INTERVALS:
            interval_probes = [probe for probe in one_day if probe["requested_start"] == day and probe["interval"] == interval]
            row[f"{interval}_symbols_with_rth"] = sorted(
                probe["symbol"]
                for probe in interval_probes
                if day in set(probe["requested_rth_dates_present"])
            )
            row[f"{interval}_total_rth_rows"] = sum(
                int((probe.get("rth_rows_by_date") or {}).get(day) or 0)
                for probe in interval_probes
            )
        output.append(row)
    return output


def _classify(probes: list[dict[str, Any]]) -> dict[str, Any]:
    one_day = [probe for probe in probes if probe["probe_type"] == "one_day"]
    by_key = {
        (probe["requested_start"], probe["symbol"], probe["interval"]): probe
        for probe in one_day
    }
    missing_diagnostics = []
    parser_drop = False
    request_window_signal = False
    provider_depth_signal = False
    for day in MISSING_1MIN_DATES:
        for symbol in SYMBOLS:
            one_min = by_key.get((day, symbol, "1min"))
            five_min = by_key.get((day, symbol, "5min"))
            fifteen_min = by_key.get((day, symbol, "15min"))
            daily = by_key.get((day, symbol, "1day"))
            if not one_min:
                continue
            has_1min_requested = day in set(one_min.get("requested_rth_dates_present") or [])
            has_any_requested = day in set(one_min.get("requested_any_dates_present") or [])
            support_intervals_present = [
                interval
                for interval, probe in (("5min", five_min), ("15min", fifteen_min), ("1day", daily))
                if probe and day in set(probe.get("requested_rth_dates_present") or probe.get("requested_any_dates_present") or [])
            ]
            if has_any_requested and not has_1min_requested and one_min.get("parser_error_count"):
                parser_drop = True
            if not has_1min_requested and support_intervals_present:
                if one_min.get("raw_row_count", 0) > 0 and one_min.get("unexpected_dates"):
                    provider_depth_signal = True
                elif one_min.get("raw_row_count", 0) == 0:
                    provider_depth_signal = True
            missing_diagnostics.append(
                {
                    "session_date": day,
                    "symbol": symbol,
                    "1min_status": one_min.get("status"),
                    "1min_raw_rows": one_min.get("raw_row_count"),
                    "1min_requested_rth_present": has_1min_requested,
                    "1min_unexpected_dates": one_min.get("unexpected_dates") or [],
                    "support_intervals_present": support_intervals_present,
                }
            )

    for start, end in ROLLING_WINDOWS:
        rolling = [
            probe
            for probe in probes
            if probe["probe_type"] == "rolling_window"
            and probe["requested_start"] == start
            and probe["requested_end"] == end
            and probe["interval"] == "1min"
        ]
        one_day_has_requested = {
            (probe["requested_start"], probe["symbol"])
            for probe in one_day
            if probe["interval"] == "1min"
            and probe["requested_start"] in MISSING_1MIN_DATES
            and probe["requested_start"] in set(probe.get("requested_rth_dates_present") or [])
        }
        requested_missing_dates = {
            day
            for day in MISSING_1MIN_DATES
            if date.fromisoformat(start) <= date.fromisoformat(day) <= date.fromisoformat(end)
        }
        rolling_missing_recovered_one_day = any(
            day not in set(probe.get("rth_dates_present") or [])
            and (day, probe["symbol"]) in one_day_has_requested
            for probe in rolling
            for day in requested_missing_dates
        )
        if rolling_missing_recovered_one_day:
            request_window_signal = True

    if parser_drop:
        classification = "PARSER_DROP_BUG"
    elif request_window_signal:
        classification = "REQUEST_WINDOW_LIMIT"
    elif provider_depth_signal:
        classification = "PROVIDER_DEPTH_LIMIT"
    else:
        classification = "UNKNOWN_PROVIDER_BEHAVIOR"
    return {
        "blocker_classification": classification,
        "missing_1min_diagnostics": missing_diagnostics,
        "classification_basis": {
            "parser_drop_signal": parser_drop,
            "request_window_signal": request_window_signal,
            "provider_depth_signal": provider_depth_signal,
        },
    }


async def main() -> None:
    settings = get_settings()
    repos = RepositoryRegistry(settings=settings)
    provider = FMPMarketDataProvider(settings)
    service = FMPLiveDataService(repos, provider=provider, settings=settings)
    probes: list[dict[str, Any]] = []

    for day in ONE_DAY_PROBE_DATES:
        for symbol in SYMBOLS:
            for interval in INTERVALS:
                response = await provider.request_endpoint(
                    _endpoint_key(interval),
                    symbol=symbol,
                    start=_start_of_day(day),
                    end=_end_of_day(day),
                )
                provider_request_id = service._record_provider_response(response)  # noqa: SLF001
                probes.append(
                    _summarize_response(
                        provider=provider,
                        response=response,
                        provider_request_id=provider_request_id,
                        probe_type="one_day",
                        requested_start=day,
                        requested_end=day,
                        symbol=symbol,
                        interval=interval,
                    )
                )

    for start, end in ROLLING_WINDOWS:
        for symbol in SYMBOLS:
            for interval in INTERVALS:
                response = await provider.request_endpoint(
                    _endpoint_key(interval),
                    symbol=symbol,
                    start=_start_of_day(start),
                    end=_end_of_day(end),
                )
                provider_request_id = service._record_provider_response(response)  # noqa: SLF001
                probes.append(
                    _summarize_response(
                        provider=provider,
                        response=response,
                        provider_request_id=provider_request_id,
                        probe_type="rolling_window",
                        requested_start=start,
                        requested_end=end,
                        symbol=symbol,
                        interval=interval,
                    )
                )

    coverage = _coverage_matrix(probes)
    classification = _classify(probes)
    payload = {
        "phase": "21U",
        "generated_at": datetime.now(UTC).isoformat(),
        "provider": "fmp",
        "auth_mode": "header",
        "no_secrets": True,
        "symbols": SYMBOLS,
        "intervals": INTERVALS,
        "expected_dates": EXPECTED_DATES,
        "known_success_dates": KNOWN_SUCCESS_DATES,
        "missing_1min_dates": MISSING_1MIN_DATES,
        "coverage_matrix": coverage,
        "classification": classification,
        "probe_count": len(probes),
        "provider_request_ids": [probe["provider_request_id"] for probe in probes],
        "probes": probes,
    }
    output_path = REPO_ROOT / "work" / "phase21u_fmp_coverage_diagnostic.json"
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "ok",
                "output_path": str(output_path),
                "probe_count": len(probes),
                "blocker_classification": classification["blocker_classification"],
                "no_secrets": True,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
