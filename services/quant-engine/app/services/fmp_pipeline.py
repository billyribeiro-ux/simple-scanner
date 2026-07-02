from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from app.config import Settings, get_settings
from app.data.fmp import (
    CAPABILITY_SYMBOLS,
    ENDPOINTS,
    FMP_PROVIDER,
    SUPPORTED_INTRADAY_INTERVALS,
    FMPClientError,
    FMPMarketDataProvider,
    FMPResponse,
)
from app.data.symbols import normalize_symbols
from app.db.repositories import RepositoryRegistry
from app.exports.service import ExportService
from app.schemas.market import Bar, Quote
from app.utils.time import UTC

DEFAULT_MAX_FMP_SYMBOLS = 10
DEFAULT_MAX_INTRADAY_DAYS = 5
DEFAULT_FMP_ENDPOINT_KEYS = [
    "quote",
    "quote_short",
    "batch_quote",
    "batch_quote_short",
    "historical_eod_full",
    "intraday_1min",
    "intraday_5min",
    "intraday_15min",
]


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _parse_datetime(value: Any) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _redact(value: Any) -> Any:
    secret_values = {
        item for item in (os.environ.get("FMP_API_KEY"), os.environ.get("DATABASE_URL")) if item
    }
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(part in lowered for part in ("apikey", "api_key", "secret", "password", "token", "database_url", "credential")):
                redacted[str(key)] = "[REDACTED]"
            else:
                redacted[str(key)] = _redact(item)
        return redacted
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, str):
        text = value
        for secret in secret_values:
            text = text.replace(secret, "[REDACTED]")
        return text.replace("apikey=", "apikey=[REDACTED]&")
    return value


class FMPLiveDataService:
    def __init__(
        self,
        repos: RepositoryRegistry,
        provider: FMPMarketDataProvider | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.repos = repos
        self.settings = settings or get_settings()
        self.provider = provider or FMPMarketDataProvider(self.settings)
        self.exporter = ExportService()

    def key_status(self) -> dict[str, Any]:
        return {
            "provider": FMP_PROVIDER,
            "fmp_api_key_configured": bool(self.settings.fmp_api_key),
            "key_status": "present" if self.settings.fmp_api_key else "missing",
            "websocket_probe_enabled": os.environ.get("AMD_ENABLE_FMP_WS_PROBE", "").strip().lower()
            in {"1", "true", "yes", "on"},
            "rest_polling_default": True,
            "no_broker_execution": True,
        }

    async def capability_check(
        self,
        *,
        endpoint_keys: list[str] | None = None,
        symbols: list[str] | None = None,
        include_websocket: bool = False,
    ) -> dict[str, Any]:
        selected_symbols = normalize_symbols(symbols or CAPABILITY_SYMBOLS)[:DEFAULT_MAX_FMP_SYMBOLS]
        keys = list(endpoint_keys or DEFAULT_FMP_ENDPOINT_KEYS)
        if include_websocket and "websocket_us_stocks_probe" not in keys:
            keys.append("websocket_us_stocks_probe")
        records = []
        request_ids = []
        for endpoint_key in keys:
            if endpoint_key not in ENDPOINTS:
                record = self.repos.provider_capabilities.save(
                    {
                        "provider": FMP_PROVIDER,
                        "endpoint_key": endpoint_key,
                        "endpoint_category": "unknown",
                        "symbol_scope": selected_symbols,
                        "request_type": "REST",
                        "status": "UNKNOWN",
                        "response_shape": {"type": "unsupported"},
                        "entitlement_notes": {"reason": "unsupported_endpoint_key"},
                        "checked_at": _now().isoformat(),
                    }
                )
                records.append(record)
                continue
            response = await self.provider.request_endpoint(endpoint_key, symbols=selected_symbols)
            provider_request_id = self._record_provider_response(response)
            request_ids.append(provider_request_id)
            record = self.repos.provider_capabilities.save(
                response.capability_payload(sample_symbol=selected_symbols[0], symbol_scope=selected_symbols)
                | {"provider_request_id": provider_request_id}
            )
            records.append(record | {"provider_request_id": provider_request_id})
        return {
            "status": "ok",
            "provider": FMP_PROVIDER,
            "key_status": self.key_status(),
            "symbols": selected_symbols,
            "endpoint_count": len(records),
            "capabilities": records,
            "provider_request_ids": request_ids,
            "warnings": self._capability_warnings(records),
            "no_secrets": True,
        }

    async def smoke(self, *, include_websocket: bool | None = None) -> dict[str, Any]:
        include = (
            os.environ.get("AMD_ENABLE_FMP_WS_PROBE", "").strip().lower() in {"1", "true", "yes", "on"}
            if include_websocket is None
            else include_websocket
        )
        result = await self.capability_check(endpoint_keys=DEFAULT_FMP_ENDPOINT_KEYS, symbols=CAPABILITY_SYMBOLS, include_websocket=include)
        result["smoke"] = True
        result["status"] = "skipped" if not self.settings.fmp_api_key else result["status"]
        if not self.settings.fmp_api_key:
            result["warnings"] = sorted(set(result.get("warnings") or []) | {"fmp_api_key_missing_live_smoke_skipped"})
        return result

    async def ingest_quotes(self, symbols: list[str] | None = None) -> dict[str, Any]:
        selected_symbols = self._bounded_symbols(symbols)
        if not self.settings.fmp_api_key:
            return self._blocked_run("quote_snapshot", selected_symbols, [])
        response = await self.provider.request_endpoint("batch_quote", symbols=selected_symbols)
        provider_request_id = self._record_provider_response(response)
        quotes = self._quotes_from_response(response)
        warnings = ["quote_snapshot_persisted_as_provider_request_no_quote_table"]
        return self._save_run(
            ingestion_type="quote_snapshot",
            symbols=selected_symbols,
            intervals=[],
            records_fetched=len(quotes),
            records_inserted=0,
            provider_request_ids=[provider_request_id],
            warnings=warnings,
            errors=self._response_errors(response),
            status="COMPLETED" if response.status in {"ACCESSIBLE", "EMPTY"} else "FAILED",
        ) | {"quotes": [quote.model_dump(mode="json") for quote in quotes]}

    async def ingest_eod(self, symbols: list[str] | None, start: datetime, end: datetime) -> dict[str, Any]:
        selected_symbols = self._bounded_symbols(symbols)
        if not self.settings.fmp_api_key:
            return self._blocked_run("eod_bars", selected_symbols, ["1day"], start=start, end=end)
        return await self._ingest_bars("eod_bars", selected_symbols, ["1day"], start, end)

    async def ingest_intraday(
        self,
        symbols: list[str] | None,
        intervals: list[str] | None,
        start: datetime,
        end: datetime,
    ) -> dict[str, Any]:
        selected_symbols = self._bounded_symbols(symbols)
        selected_intervals = self._bounded_intervals(intervals)
        self._guard_intraday_span(start, end)
        if not self.settings.fmp_api_key:
            return self._blocked_run("intraday_bars", selected_symbols, selected_intervals, start=start, end=end)
        return await self._ingest_bars("intraday_bars", selected_symbols, selected_intervals, start, end)

    async def incremental_intraday(
        self,
        symbols: list[str] | None,
        intervals: list[str] | None,
        end: datetime | None = None,
    ) -> dict[str, Any]:
        selected_symbols = self._bounded_symbols(symbols)
        selected_intervals = self._bounded_intervals(intervals)
        refresh_end = end or _now()
        earliest = refresh_end - timedelta(days=DEFAULT_MAX_INTRADAY_DAYS)
        start_candidates = [self._last_bar_start(symbol, interval, earliest) for symbol in selected_symbols for interval in selected_intervals]
        refresh_start = min(start_candidates) if start_candidates else earliest
        if not self.settings.fmp_api_key:
            return self._blocked_run(
                "incremental_intraday_refresh",
                selected_symbols,
                selected_intervals,
                start=refresh_start,
                end=refresh_end,
            )
        return await self._ingest_bars("incremental_intraday_refresh", selected_symbols, selected_intervals, refresh_start, refresh_end)

    def list_ingestion_runs(self, *, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        return {
            "ingestion_runs": self.repos.ingestion_runs.list(provider=FMP_PROVIDER, limit=limit, offset=offset),
            "limit": limit,
            "offset": offset,
        }

    def get_ingestion_run(self, ingestion_run_id: str) -> dict[str, Any]:
        return self.repos.ingestion_runs.get(ingestion_run_id) or {
            "status": "not_found",
            "ingestion_run_id": ingestion_run_id,
        }

    def provider_status(self) -> dict[str, Any]:
        latest_matrix = self.repos.provider_capabilities.latest_matrix(provider=FMP_PROVIDER)
        latest_ingestion = self.repos.ingestion_runs.latest(provider=FMP_PROVIDER)
        provider_requests = self.repos.provider_requests.list_all()
        provider_errors = [
            row for row in provider_requests if str(row.get("status") or "").upper() not in {"ACCESSIBLE", "OK", "SUCCESS", "EMPTY"}
        ][:20]
        return {
            "status": "ok",
            **self.key_status(),
            "latest_capabilities": latest_matrix,
            "latest_ingestion_run": latest_ingestion,
            "latest_provider_errors": provider_errors,
            "warnings": self._capability_warnings(latest_matrix)
            + (latest_ingestion.get("warnings") if isinstance(latest_ingestion, dict) else []),
            "no_secrets": True,
        }

    def coverage_report(
        self,
        *,
        symbols: list[str] | None = None,
        intervals: list[str] | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> dict[str, Any]:
        selected_symbols = normalize_symbols(symbols or [])
        bars = self.repos.bars.query(symbols=selected_symbols or None, intervals=intervals, start=start, end=end)
        by_key: dict[tuple[str, str], list[Bar]] = {}
        source_breakdown: dict[str, int] = {}
        for bar in bars:
            by_key.setdefault((bar.symbol, bar.interval), []).append(bar)
            source_breakdown[bar.source] = source_breakdown.get(bar.source, 0) + 1
        latest = [
            {
                "symbol": symbol,
                "interval": interval,
                "latest_bar_timestamp_utc": max(row.timestamp_utc for row in rows).isoformat(),
                "bar_count": len(rows),
            }
            for (symbol, interval), rows in sorted(by_key.items())
        ]
        provider_requests = self.repos.provider_requests.list_all()
        ingestion_runs = self.repos.ingestion_runs.list(provider=FMP_PROVIDER, limit=25)
        capability_warnings = self._capability_warnings(self.repos.provider_capabilities.latest_matrix(provider=FMP_PROVIDER))
        return {
            "status": "ok",
            "generated_at": _now().isoformat(),
            "symbols": selected_symbols or sorted({bar.symbol for bar in bars}),
            "intervals": intervals or sorted({bar.interval for bar in bars}),
            "start": _iso(start),
            "end": _iso(end),
            "summary": {
                "bar_count": len(bars),
                "source_breakdown": source_breakdown,
                "latest_bar_group_count": len(latest),
                "provider_request_count": len(provider_requests),
                "ingestion_run_count": len(ingestion_runs),
                "capability_warning_count": len(capability_warnings),
            },
            "latest_bars": latest,
            "provider_request_summary": provider_requests[:50],
            "ingestion_run_summary": ingestion_runs,
            "capability_warnings": capability_warnings,
            "recommended_refresh_steps": self._recommended_refresh_steps(latest, capability_warnings),
            "warnings": capability_warnings,
            "no_secrets": True,
        }

    def export_capabilities(self, kind: str = "json") -> dict[str, Any]:
        rows = self.repos.provider_capabilities.latest_matrix(provider=FMP_PROVIDER)
        return self._export_rows("fmp_capability_matrix", kind, rows, source_id="fmp")

    def export_ingestion_runs(self, kind: str = "json") -> dict[str, Any]:
        rows = self.repos.ingestion_runs.list(provider=FMP_PROVIDER, limit=1000)
        return self._export_rows("fmp_ingestion_runs", kind, rows, source_id="fmp")

    def export_coverage(self, kind: str = "json") -> dict[str, Any]:
        report = self.coverage_report()
        rows = report.get("latest_bars") or []
        return self._export_payload("fmp_data_coverage", kind, report, rows, source_id="fmp")

    def export_provider_requests(self, kind: str = "csv") -> dict[str, Any]:
        rows = self.repos.provider_requests.list_all()
        return self._export_rows("fmp_provider_requests", kind, rows, source_id="fmp")

    async def _ingest_bars(
        self,
        ingestion_type: str,
        symbols: list[str],
        intervals: list[str],
        start: datetime,
        end: datetime,
    ) -> dict[str, Any]:
        fetched = 0
        inserted = 0
        errors: list[dict[str, Any]] = []
        provider_request_ids: list[str] = []
        warnings: list[str] = []
        for symbol in symbols:
            selected_intervals = ["1day"] if intervals == ["1day"] else intervals
            for interval in selected_intervals:
                endpoint_key = "historical_eod_full" if interval == "1day" else f"intraday_{interval}"
                try:
                    response = await self.provider.request_endpoint(endpoint_key, symbol=symbol, start=start, end=end)
                    provider_request_ids.append(self._record_provider_response(response))
                    response_errors = self._response_errors(response)
                    if response_errors:
                        errors.extend(response_errors)
                    bars = self._bars_from_response(response, symbol, interval)
                    fetched += len(bars)
                    inserted += self.repos.bars.upsert_many(bars)
                except (FMPClientError, ValueError) as exc:
                    errors.append({"symbol": symbol, "interval": interval, "error": str(_redact(str(exc)))})
        dirty = self.repos.pipeline_windows.list_dirty(symbols=symbols, intervals=None if intervals == ["1day"] else intervals)
        status = "COMPLETED" if not errors else ("PARTIAL" if fetched else "FAILED")
        return self._save_run(
            ingestion_type=ingestion_type,
            symbols=symbols,
            intervals=intervals,
            start=start,
            end=end,
            records_fetched=fetched,
            records_inserted=inserted,
            provider_request_ids=provider_request_ids,
            dirty_windows=dirty,
            errors=errors,
            warnings=warnings,
            status=status,
        )

    def _record_provider_response(self, response: FMPResponse) -> str:
        return self.repos.provider_requests.record(
            provider=FMP_PROVIDER,
            endpoint=response.endpoint_key,
            status=response.status,
            symbol=response.symbol,
            interval=response.interval,
            row_count=response.sample_count,
            error_message=response.error_message,
            metadata=response.provider_request_metadata(),
            request_id=response.request_id,
            response_status=response.http_status,
            started_at=response.started_at,
            finished_at=response.finished_at,
        )

    def _save_run(
        self,
        *,
        ingestion_type: str,
        symbols: list[str],
        intervals: list[str],
        records_fetched: int,
        records_inserted: int,
        provider_request_ids: list[str],
        status: str,
        start: datetime | None = None,
        end: datetime | None = None,
        records_updated: int = 0,
        records_skipped: int = 0,
        dirty_windows: list[dict[str, Any]] | None = None,
        errors: list[dict[str, Any]] | None = None,
        warnings: list[str] | None = None,
    ) -> dict[str, Any]:
        return self.repos.ingestion_runs.save(
            {
                "provider": FMP_PROVIDER,
                "ingestion_type": ingestion_type,
                "symbols": symbols,
                "intervals": intervals,
                "start": start,
                "end": end,
                "status": status,
                "records_fetched": records_fetched,
                "records_inserted": records_inserted,
                "records_updated": records_updated,
                "records_skipped": records_skipped,
                "provider_request_ids": provider_request_ids,
                "dirty_windows": dirty_windows or [],
                "errors": errors or [],
                "warnings": warnings or [],
                "completed_at": _now(),
            }
        )

    def _blocked_run(
        self,
        ingestion_type: str,
        symbols: list[str],
        intervals: list[str],
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> dict[str, Any]:
        return self._save_run(
            ingestion_type=ingestion_type,
            symbols=symbols,
            intervals=intervals,
            start=start,
            end=end,
            records_fetched=0,
            records_inserted=0,
            provider_request_ids=[],
            status="BLOCKED",
            errors=[{"reason": "fmp_api_key_required"}],
            warnings=["FMP_API_KEY is missing; live FMP ingestion skipped."],
        )

    def _quotes_from_response(self, response: FMPResponse) -> list[Quote]:
        if response.status not in {"ACCESSIBLE", "EMPTY"}:
            return []
        rows = response.data if isinstance(response.data, list) else []
        return [self.provider._quote_from_row(row) for row in rows if isinstance(row, dict)]  # noqa: SLF001

    def _bars_from_response(self, response: FMPResponse, symbol: str, interval: str) -> list[Bar]:
        if response.status not in {"ACCESSIBLE", "EMPTY"}:
            return []
        if isinstance(response.data, dict):
            rows = response.data.get("historical") or response.data.get("data") or []
        else:
            rows = response.data if isinstance(response.data, list) else []
        actual_interval = "1day" if interval == "1day" else interval
        return [
            self.provider._bar_from_row(symbol, actual_interval, row)  # noqa: SLF001
            for row in rows
            if isinstance(row, dict)
        ]

    def _response_errors(self, response: FMPResponse) -> list[dict[str, Any]]:
        if response.status in {"ACCESSIBLE", "EMPTY"}:
            return []
        return [
            {
                "endpoint_key": response.endpoint_key,
                "status": response.status,
                "http_status": response.http_status,
                "error_code": response.error_code,
                "error_class": response.error_class,
            }
        ]

    def _bounded_symbols(self, symbols: list[str] | None) -> list[str]:
        selected = normalize_symbols(symbols or self.settings.symbol_list)
        if len(selected) > DEFAULT_MAX_FMP_SYMBOLS:
            raise ValueError(f"FMP ingestion is bounded to {DEFAULT_MAX_FMP_SYMBOLS} symbols per job")
        return selected

    def _bounded_intervals(self, intervals: list[str] | None) -> list[str]:
        selected = [str(interval) for interval in (intervals or ["1min", "5min", "15min"])]
        invalid = sorted(set(selected) - SUPPORTED_INTRADAY_INTERVALS)
        if invalid:
            raise ValueError(f"Unsupported FMP intraday intervals: {','.join(invalid)}")
        return selected

    def _guard_intraday_span(self, start: datetime, end: datetime) -> None:
        if end < start:
            raise ValueError("FMP intraday end must be after start")
        if (end - start).days > DEFAULT_MAX_INTRADAY_DAYS:
            raise ValueError(f"FMP intraday ingestion is bounded to {DEFAULT_MAX_INTRADAY_DAYS} days")

    def _last_bar_start(self, symbol: str, interval: str, fallback: datetime) -> datetime:
        bars = self.repos.bars.query(symbols=[symbol], intervals=[interval])
        if not bars:
            return fallback
        return max(bar.timestamp_utc for bar in bars) - timedelta(minutes=15)

    def _capability_warnings(self, records: list[dict[str, Any]]) -> list[str]:
        warnings = []
        if not self.settings.fmp_api_key:
            warnings.append("fmp_api_key_missing")
        for record in records:
            status = str(record.get("status") or "")
            if status in {"DENIED", "RATE_LIMITED", "ERROR", "UNKNOWN"}:
                warnings.append(f"{record.get('endpoint_key')}_{status.lower()}")
        return sorted(set(warnings))

    def _recommended_refresh_steps(self, latest: list[dict[str, Any]], warnings: list[str]) -> list[str]:
        steps = []
        if warnings:
            steps.append("Run a provider capability check before ingestion.")
        if not latest:
            steps.append("Run bounded EOD or intraday FMP ingestion.")
        if self.settings.fmp_api_key:
            steps.append("Use REST polling and keep WebSocket disabled unless explicitly probing entitlement.")
        else:
            steps.append("Set FMP_API_KEY in the runtime environment before live ingestion.")
        return steps

    def _export_rows(self, export_type: str, kind: str, rows: list[dict[str, Any]], *, source_id: str) -> dict[str, Any]:
        payload = {"rows": rows, "created_at": _now().isoformat(), "no_secrets": True}
        return self._export_payload(export_type, kind, payload, rows, source_id=source_id)

    def _export_payload(
        self,
        export_type: str,
        kind: str,
        payload: dict[str, Any],
        rows: list[dict[str, Any]],
        *,
        source_id: str,
    ) -> dict[str, Any]:
        kind = kind.lower()
        self.settings.exports_dir.mkdir(parents=True, exist_ok=True)
        timestamp = _now().strftime("%Y%m%dT%H%M%S")
        path = self.settings.exports_dir / f"{export_type}_{timestamp}.{kind}"
        safe_payload = _redact(payload)
        if kind == "json":
            path.write_text(json.dumps(safe_payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
        elif kind == "csv":
            self._write_csv(path, rows)
        elif kind == "xlsx":
            table_rows = self._table(rows)
            self.exporter._write_workbook(path, {export_type[:31]: table_rows})  # noqa: SLF001
        else:
            raise ValueError("export kind must be json, csv, or xlsx")
        record = self.repos.exports.record(export_type, kind, path, len(rows), source_id, {"no_secrets": True})
        return {"status": "ok", "kind": kind, "path": str(path), "rows": len(rows), "export": record}

    def _write_csv(self, path: Path, rows: list[dict[str, Any]]) -> None:
        columns = sorted({str(key) for row in rows for key in row.keys()}) or ["status"]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            for row in rows:
                writer.writerow({column: json.dumps(_redact(row.get(column)), default=str) for column in columns})

    def _table(self, rows: list[dict[str, Any]]) -> list[list[object]]:
        if not rows:
            return [["status", "message"], ["empty", "No rows available."]]
        columns = sorted({str(key) for row in rows for key in row.keys()})
        return [columns, *[[json.dumps(_redact(row.get(column)), default=str) for column in columns] for row in rows]]
