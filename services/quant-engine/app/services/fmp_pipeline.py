from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

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
from app.data.symbols import normalize_symbol, normalize_symbols
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
DEFAULT_SEED_SYMBOLS = ["AMZN", "AAPL", "TSLA", "SPY", "QQQ", "IWM", "NVDA", "GOOGL", "BABA", "SHOP"]
DEFAULT_SEED_INTERVALS = ["1day", "1min", "5min", "15min"]
DEFAULT_BAR_FRESHNESS_MINUTES = {"1day": 2880, "1min": 30, "5min": 90, "15min": 180}
DEFAULT_QUOTE_FRESHNESS_SECONDS = 900
ACCESSIBLE_REVIEW_STATUS = "REVIEWED_ACCESSIBLE"
BLOCKING_REVIEW_STATUSES = {"REVIEWED_BLOCKED", "REVIEWED_RATE_LIMITED", "REVIEWED_UNUSABLE"}


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
        ingestion_run_id = f"ingestion_{uuid4().hex}"
        snapshot_rows = self._quote_snapshots_from_response(
            response,
            provider_request_id=provider_request_id,
            ingestion_run_id=ingestion_run_id,
        )
        snapshot_counts = self.repos.quote_snapshots.upsert_many(snapshot_rows)
        warnings: list[str] = []
        return self._save_run(
            ingestion_run_id=ingestion_run_id,
            ingestion_type="quote_snapshot",
            symbols=selected_symbols,
            intervals=[],
            records_fetched=len(quotes),
            records_inserted=int(snapshot_counts.get("records_inserted") or 0),
            records_updated=int(snapshot_counts.get("records_updated") or 0),
            provider_request_ids=[provider_request_id],
            warnings=warnings,
            errors=self._response_errors(response),
            status="COMPLETED" if response.status in {"ACCESSIBLE", "EMPTY"} else "FAILED",
        ) | {
            "quotes": [quote.model_dump(mode="json") for quote in quotes],
            "quote_snapshot_ids": snapshot_counts.get("quote_snapshot_ids") or [],
            "quote_snapshot_status": "persisted",
        }

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

    def review_capability(
        self,
        check_id: str,
        *,
        operator_review_status: str,
        reviewed_by: str | None = None,
        review_notes: str | None = None,
    ) -> dict[str, Any]:
        reviewed = self.repos.provider_capabilities.review(
            check_id,
            operator_review_status=operator_review_status,
            reviewed_by=reviewed_by,
            review_notes=review_notes,
            reviewed_at=_now(),
        )
        if reviewed is None:
            return {"status": "not_found", "check_id": check_id}
        return {
            "status": "ok",
            "capability": reviewed,
            "review_summary": self.capability_review_summary(),
            "no_secrets": True,
        }

    def capability_review_summary(
        self,
        *,
        required_endpoints: list[str] | None = None,
    ) -> dict[str, Any]:
        required = list(required_endpoints or DEFAULT_FMP_ENDPOINT_KEYS)
        latest_rows = self.repos.provider_capabilities.latest_matrix(provider=FMP_PROVIDER)
        by_endpoint = {str(row.get("endpoint_key")): row for row in latest_rows}
        missing = [endpoint for endpoint in required if endpoint not in by_endpoint]
        unreviewed: list[str] = []
        accessible: list[str] = []
        blocked: list[dict[str, Any]] = []
        partial: list[str] = []
        for endpoint in required:
            row = by_endpoint.get(endpoint)
            if row is None:
                continue
            provider_status = str(row.get("status") or "UNKNOWN").upper()
            review_status = str(row.get("operator_review_status") or "UNREVIEWED").upper()
            if review_status == ACCESSIBLE_REVIEW_STATUS and provider_status in {"ACCESSIBLE", "EMPTY"}:
                accessible.append(endpoint)
            elif review_status in BLOCKING_REVIEW_STATUSES or provider_status in {"DENIED", "RATE_LIMITED", "ERROR", "SKIPPED_NO_KEY"}:
                blocked.append(
                    {
                        "endpoint_key": endpoint,
                        "provider_status": provider_status,
                        "operator_review_status": review_status,
                        "error_code": row.get("error_code"),
                    }
                )
            elif review_status == "REVIEWED_PARTIAL":
                partial.append(endpoint)
            else:
                unreviewed.append(endpoint)
        if blocked:
            status = "BLOCKED"
        elif missing or unreviewed:
            status = "UNREVIEWED"
        elif partial or len(accessible) < len(required):
            status = "PARTIAL"
        else:
            status = "READY"
        return {
            "status": status,
            "provider": FMP_PROVIDER,
            "required_endpoints": required,
            "required_count": len(required),
            "accessible_reviewed_count": len(accessible),
            "missing_endpoints": missing,
            "unreviewed_endpoints": unreviewed,
            "partial_endpoints": partial,
            "blocked_endpoints": blocked,
            "latest_capabilities": [by_endpoint[endpoint] for endpoint in required if endpoint in by_endpoint],
            "operator_review_required": True,
            "no_secrets": True,
        }

    def list_quote_snapshots(
        self,
        *,
        symbols: list[str] | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> dict[str, Any]:
        selected_symbols = normalize_symbols(symbols or [])
        return {
            "status": "ok",
            "provider": FMP_PROVIDER,
            "symbols": selected_symbols,
            "quote_snapshots": self.repos.quote_snapshots.list(
                symbols=selected_symbols or None,
                limit=limit,
                offset=offset,
            ),
            "limit": limit,
            "offset": offset,
            "no_secrets": True,
        }

    async def seed_ingestion(
        self,
        *,
        symbols: list[str] | None = None,
        intervals: list[str] | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        include_quotes: bool = True,
        include_eod: bool = True,
        include_intraday: bool = True,
        max_intraday_days: int = DEFAULT_MAX_INTRADAY_DAYS,
        require_reviewed_capabilities: bool = True,
        allow_unreviewed_capabilities: bool = False,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        selected_symbols = self._bounded_symbols(symbols or DEFAULT_SEED_SYMBOLS)
        selected_intervals = self._bounded_seed_intervals(intervals)
        seed_end = end or _now()
        seed_start = start or seed_end - timedelta(days=min(max_intraday_days, DEFAULT_MAX_INTRADAY_DAYS))
        if (seed_end - seed_start).days > min(max_intraday_days, DEFAULT_MAX_INTRADAY_DAYS):
            raise ValueError("FMP seed ingestion intraday span exceeds the configured bounded window")
        intraday_intervals = [item for item in selected_intervals if item != "1day"]
        required_endpoints = self._required_seed_endpoints(
            selected_intervals,
            include_quotes=include_quotes,
            include_eod=include_eod,
            include_intraday=include_intraday,
        )
        review_summary = self.capability_review_summary(required_endpoints=required_endpoints)
        would_block = bool(
            require_reviewed_capabilities
            and not allow_unreviewed_capabilities
            and review_summary.get("status") != "READY"
        )
        plan = {
            "provider": FMP_PROVIDER,
            "symbols": selected_symbols,
            "intervals": selected_intervals,
            "start": seed_start.isoformat(),
            "end": seed_end.isoformat(),
            "include_quotes": include_quotes,
            "include_eod": include_eod,
            "include_intraday": include_intraday,
            "max_intraday_days": max_intraday_days,
            "required_endpoints": required_endpoints,
            "review_summary": review_summary,
            "requires_fmp_api_key": not dry_run,
            "no_broker_execution": True,
        }
        if dry_run:
            return {
                "status": "dry_run",
                "plan": plan,
                "would_block": would_block,
                "warnings": ["seed_ingestion_dry_run_no_provider_call"] + (["capability_review_not_ready"] if would_block else []),
                "model_activation_unchanged": True,
                "no_secrets": True,
            }
        if not self.settings.fmp_api_key:
            return self._blocked_run("seed_ingestion", selected_symbols, selected_intervals, start=seed_start, end=seed_end) | {
                "plan": plan,
                "review_summary": review_summary,
            }
        if would_block:
            return self._save_run(
                ingestion_type="seed_ingestion",
                symbols=selected_symbols,
                intervals=selected_intervals,
                start=seed_start,
                end=seed_end,
                records_fetched=0,
                records_inserted=0,
                provider_request_ids=[],
                status="BLOCKED",
                errors=[{"reason": "operator_review_required", "review_status": review_summary.get("status")}],
                warnings=["Required FMP capabilities must be operator-reviewed before live seed ingestion."],
            ) | {"plan": plan, "review_summary": review_summary}
        child_runs: list[dict[str, Any]] = []
        if include_quotes:
            child_runs.append(await self.ingest_quotes(selected_symbols))
        if include_eod and "1day" in selected_intervals:
            child_runs.append(await self.ingest_eod(selected_symbols, seed_start, seed_end))
        if include_intraday and intraday_intervals:
            self._guard_intraday_span(seed_start, seed_end)
            child_runs.append(await self.ingest_intraday(selected_symbols, intraday_intervals, seed_start, seed_end))
        provider_request_ids = [
            str(request_id)
            for run in child_runs
            for request_id in (run.get("provider_request_ids") or [])
        ]
        errors = [error for run in child_runs for error in (run.get("errors") or [])]
        warnings = [str(warning) for run in child_runs for warning in (run.get("warnings") or [])]
        fetched = sum(int(run.get("records_fetched") or 0) for run in child_runs)
        inserted = sum(int(run.get("records_inserted") or 0) for run in child_runs)
        updated = sum(int(run.get("records_updated") or 0) for run in child_runs)
        skipped = sum(int(run.get("records_skipped") or 0) for run in child_runs)
        statuses = {str(run.get("status") or "UNKNOWN").upper() for run in child_runs}
        status = "COMPLETED" if statuses <= {"COMPLETED"} else ("PARTIAL" if fetched else "FAILED")
        return self._save_run(
            ingestion_type="seed_ingestion",
            symbols=selected_symbols,
            intervals=selected_intervals,
            start=seed_start,
            end=seed_end,
            records_fetched=fetched,
            records_inserted=inserted,
            records_updated=updated,
            records_skipped=skipped,
            provider_request_ids=provider_request_ids,
            dirty_windows=self.repos.pipeline_windows.list_dirty(symbols=selected_symbols, intervals=intraday_intervals or None),
            errors=errors,
            warnings=warnings,
            status=status,
        ) | {
            "plan": plan,
            "review_summary": review_summary,
            "child_runs": child_runs,
            "model_activation_unchanged": True,
            "no_broker_execution": True,
            "no_secrets": True,
        }

    def freshness_check(
        self,
        *,
        symbols: list[str] | None = None,
        intervals: list[str] | None = None,
        max_bar_age_minutes: dict[str, int] | None = None,
        max_quote_age_seconds: int = DEFAULT_QUOTE_FRESHNESS_SECONDS,
        include_quotes: bool = True,
        require_reviewed_capabilities: bool = True,
        persist: bool = True,
        reference_time: datetime | None = None,
    ) -> dict[str, Any]:
        generated_at = _now()
        age_reference = reference_time or generated_at
        selected_symbols = self._bounded_symbols(symbols or DEFAULT_SEED_SYMBOLS)
        selected_intervals = self._bounded_seed_intervals(intervals or DEFAULT_SEED_INTERVALS)
        age_limits = {**DEFAULT_BAR_FRESHNESS_MINUTES, **(max_bar_age_minutes or {})}
        latest_bars: list[dict[str, Any]] = []
        latest_quotes: list[dict[str, Any]] = []
        missing_items: list[dict[str, Any]] = []
        stale_items: list[dict[str, Any]] = []
        for symbol in selected_symbols:
            for interval in selected_intervals:
                bars = self.repos.bars.query(symbols=[symbol], intervals=[interval])
                latest = max(bars, key=lambda bar: bar.timestamp_utc, default=None)
                if latest is None:
                    missing_items.append({"type": "bar", "symbol": symbol, "interval": interval})
                    latest_bars.append({"symbol": symbol, "interval": interval, "latest_bar_timestamp_utc": None, "bar_count": 0})
                    continue
                age_minutes = max(0.0, (age_reference - latest.timestamp_utc).total_seconds() / 60.0)
                row = {
                    "symbol": symbol,
                    "interval": interval,
                    "latest_bar_timestamp_utc": latest.timestamp_utc.isoformat(),
                    "age_minutes": round(age_minutes, 2),
                    "max_age_minutes": age_limits.get(interval),
                    "bar_count": len(bars),
                    "source": latest.source,
                }
                latest_bars.append(row)
                if age_limits.get(interval) is not None and age_minutes > float(age_limits[interval]):
                    stale_items.append({"type": "bar", **row})
        if include_quotes:
            quote_rows = {str(row.get("symbol")): row for row in self.repos.quote_snapshots.latest_by_symbol(selected_symbols)}
            for symbol in selected_symbols:
                quote = quote_rows.get(symbol)
                if quote is None:
                    missing_items.append({"type": "quote", "symbol": symbol})
                    latest_quotes.append({"symbol": symbol, "latest_quote_timestamp_utc": None})
                    continue
                timestamp = _parse_datetime(quote.get("timestamp_utc")) or generated_at
                age_seconds = max(0.0, (age_reference - timestamp).total_seconds())
                row = {
                    "symbol": symbol,
                    "latest_quote_timestamp_utc": timestamp.isoformat(),
                    "age_seconds": round(age_seconds, 2),
                    "max_age_seconds": max_quote_age_seconds,
                    "price": quote.get("price"),
                    "source": quote.get("source") or FMP_PROVIDER,
                }
                latest_quotes.append(row)
                if age_seconds > max_quote_age_seconds:
                    stale_items.append({"type": "quote", **row})
        required_endpoints = self._required_seed_endpoints(selected_intervals, include_quotes=include_quotes, include_eod="1day" in selected_intervals, include_intraday=True)
        capability_summary = self.capability_review_summary(required_endpoints=required_endpoints)
        dirty_status = self.repos.pipeline_windows.status(symbols=selected_symbols, intervals=[item for item in selected_intervals if item != "1day"])
        warnings: list[str] = []
        if missing_items:
            warnings.append("freshness_missing_required_data")
        if stale_items:
            warnings.append("freshness_stale_required_data")
        if dirty_status.get("dirty_window_count"):
            warnings.append("freshness_dirty_pipeline_windows")
        if require_reviewed_capabilities and capability_summary.get("status") != "READY":
            warnings.append("freshness_capability_review_not_ready")
        if require_reviewed_capabilities and capability_summary.get("status") != "READY":
            status = "BLOCKED"
        elif missing_items:
            status = "BLOCKED"
        elif stale_items or dirty_status.get("dirty_window_count"):
            status = "STALE"
        else:
            status = "READY"
        recommendations = self._freshness_recommendations(status, missing_items, stale_items, dirty_status, capability_summary)
        payload = {
            "provider": FMP_PROVIDER,
            "status": status,
            "symbols": selected_symbols,
            "intervals": selected_intervals,
            "required_capability_endpoints": required_endpoints,
            "latest_bars": latest_bars,
            "latest_quotes": latest_quotes,
            "missing_items": missing_items,
            "stale_items": stale_items,
            "dirty_windows": dirty_status.get("dirty_windows") or [],
            "dirty_window_status": dirty_status,
            "capability_summary": capability_summary,
            "warnings": sorted(set(warnings)),
            "recommendations": recommendations,
            "max_bar_age_minutes": age_limits,
            "max_quote_age_seconds": max_quote_age_seconds,
            "generated_at": generated_at.isoformat(),
            "freshness_reference_time": age_reference.isoformat(),
            "no_broker_execution": True,
            "model_activation_unchanged": True,
            "no_secrets": True,
        }
        if persist:
            saved = self.repos.data_freshness_reports.save(payload)
            payload["freshness_report_id"] = saved.get("freshness_report_id")
            payload["persisted_report"] = saved
        return payload

    def latest_freshness_report(self) -> dict[str, Any]:
        latest = self.repos.data_freshness_reports.latest(provider=FMP_PROVIDER)
        return latest or {"status": "not_found", "provider": FMP_PROVIDER}

    def provider_status(self) -> dict[str, Any]:
        latest_matrix = self.repos.provider_capabilities.latest_matrix(provider=FMP_PROVIDER)
        latest_ingestion = self.repos.ingestion_runs.latest(provider=FMP_PROVIDER)
        latest_freshness = self.repos.data_freshness_reports.latest(provider=FMP_PROVIDER)
        provider_requests = self.repos.provider_requests.list_all()
        provider_errors = [
            row for row in provider_requests if str(row.get("status") or "").upper() not in {"ACCESSIBLE", "OK", "SUCCESS", "EMPTY"}
        ][:20]
        return {
            "status": "ok",
            **self.key_status(),
            "latest_capabilities": latest_matrix,
            "latest_ingestion_run": latest_ingestion,
            "capability_review_summary": self.capability_review_summary(),
            "latest_freshness_report": latest_freshness,
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

    def export_entitlement_review(self, kind: str = "json") -> dict[str, Any]:
        payload = self.capability_review_summary()
        rows = payload.get("latest_capabilities") or []
        return self._export_payload("fmp_entitlement_review", kind, payload, rows, source_id="fmp")

    def export_quote_snapshots(self, kind: str = "csv") -> dict[str, Any]:
        rows = self.repos.quote_snapshots.list(limit=1000)
        return self._export_rows("fmp_quote_snapshots", kind, rows, source_id="fmp")

    def export_seed_ingestion(self, kind: str = "json") -> dict[str, Any]:
        rows = self.repos.ingestion_runs.list(provider=FMP_PROVIDER, ingestion_type="seed_ingestion", limit=1000)
        payload = {
            "status": "ok",
            "seed_ingestion_runs": rows,
            "created_at": _now().isoformat(),
            "no_secrets": True,
        }
        return self._export_payload("fmp_seed_ingestion", kind, payload, rows, source_id="fmp")

    def export_freshness(self, kind: str = "json") -> dict[str, Any]:
        rows = self.repos.data_freshness_reports.list(provider=FMP_PROVIDER, limit=1000)
        payload = {
            "status": "ok",
            "freshness_reports": rows,
            "latest_freshness_report": rows[0] if rows else None,
            "created_at": _now().isoformat(),
            "no_secrets": True,
        }
        return self._export_payload("data_freshness_report", kind, payload, rows, source_id="fmp")

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
        updated = 0
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
                    bar_inserts, bar_updates = self._upsert_bars_with_counts(bars)
                    inserted += bar_inserts
                    updated += bar_updates
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
            records_updated=updated,
            provider_request_ids=provider_request_ids,
            dirty_windows=dirty,
            errors=errors,
            warnings=warnings,
            status=status,
        )

    def _upsert_bars_with_counts(self, bars: list[Bar]) -> tuple[int, int]:
        if not bars:
            return 0, 0
        incoming_keys = self._bar_keys(bars)
        existing_keys = self._existing_bar_keys(bars)
        self.repos.bars.upsert_many(bars)
        return len(incoming_keys - existing_keys), len(incoming_keys & existing_keys)

    def _existing_bar_keys(self, bars: list[Bar]) -> set[tuple[str, str, str, str]]:
        timestamps = [self._bar_timestamp_utc(bar) for bar in bars]
        existing = self.repos.bars.query(
            symbols=sorted({bar.symbol for bar in bars}),
            intervals=sorted({bar.interval for bar in bars}),
            start=min(timestamps),
            end=max(timestamps),
        )
        return self._bar_keys(existing)

    def _bar_keys(self, bars: list[Bar]) -> set[tuple[str, str, str, str]]:
        return {
            (
                normalize_symbol(bar.symbol),
                str(bar.interval),
                self._bar_timestamp_utc(bar).isoformat(),
                str(bar.source or "unknown"),
            )
            for bar in bars
        }

    def _bar_timestamp_utc(self, bar: Bar) -> datetime:
        timestamp = _parse_datetime(bar.timestamp_utc)
        if timestamp is None:
            raise ValueError("bar timestamp_utc is required")
        if timestamp.tzinfo is None:
            return timestamp.replace(tzinfo=UTC)
        return timestamp.astimezone(UTC)

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
        ingestion_run_id: str | None = None,
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
                "ingestion_run_id": ingestion_run_id,
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

    def _quote_snapshots_from_response(
        self,
        response: FMPResponse,
        *,
        provider_request_id: str,
        ingestion_run_id: str,
    ) -> list[dict[str, Any]]:
        if response.status not in {"ACCESSIBLE", "EMPTY"}:
            return []
        rows = response.data if isinstance(response.data, list) else []
        snapshots = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            quote = self.provider._quote_from_row(row)  # noqa: SLF001
            timestamp = self._quote_timestamp(row, quote)
            symbol = normalize_symbol(str(row.get("symbol") or quote.symbol))
            flags = []
            if not quote.price:
                flags.append("missing_or_zero_price")
            if row.get("volume") in {None, ""}:
                flags.append("missing_volume")
            snapshots.append(
                {
                    "provider": FMP_PROVIDER,
                    "endpoint_key": response.endpoint_key,
                    "symbol": symbol,
                    "timestamp_utc": timestamp,
                    "provider_timestamp": str(row.get("timestamp")) if row.get("timestamp") is not None else None,
                    "price": quote.price,
                    "bid": self._number(row, "bid", "bidPrice"),
                    "ask": self._number(row, "ask", "askPrice"),
                    "open": self._number(row, "open", "dayOpen"),
                    "high": self._number(row, "dayHigh", "high"),
                    "low": self._number(row, "dayLow", "low"),
                    "previous_close": self._number(row, "previousClose", "prevClose"),
                    "volume": int(row.get("volume") or 0) if row.get("volume") is not None and row.get("volume") != "" else None,
                    "change": self._number(row, "change", "changes"),
                    "change_percent": self._number(row, "changesPercentage", "changePercentage"),
                    "source": quote.source,
                    "ingestion_run_id": ingestion_run_id,
                    "provider_request_id": provider_request_id,
                    "raw_fields": row,
                    "data_quality_flags": flags,
                }
            )
        return snapshots

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

    def _quote_timestamp(self, row: dict[str, Any], quote: Quote) -> datetime:
        raw = row.get("timestamp")
        if isinstance(raw, (int, float)):
            return datetime.fromtimestamp(float(raw), tz=UTC)
        if isinstance(raw, str) and raw.strip():
            try:
                parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
            except ValueError:
                pass
        return quote.timestamp_utc or _now()

    def _number(self, row: dict[str, Any], *keys: str) -> float | None:
        for key in keys:
            value = row.get(key)
            if value is not None and value != "":
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return None
        return None

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

    def _bounded_seed_intervals(self, intervals: list[str] | None) -> list[str]:
        selected = [str(interval) for interval in (intervals or DEFAULT_SEED_INTERVALS)]
        invalid = sorted(set(selected) - (SUPPORTED_INTRADAY_INTERVALS | {"1day"}))
        if invalid:
            raise ValueError(f"Unsupported FMP seed intervals: {','.join(invalid)}")
        return [interval for interval in DEFAULT_SEED_INTERVALS if interval in selected]

    def _required_seed_endpoints(
        self,
        intervals: list[str],
        *,
        include_quotes: bool,
        include_eod: bool,
        include_intraday: bool,
    ) -> list[str]:
        required: list[str] = []
        if include_quotes:
            required.append("batch_quote")
        if include_eod and "1day" in intervals:
            required.append("historical_eod_full")
        if include_intraday:
            required.extend(f"intraday_{interval}" for interval in intervals if interval != "1day")
        return required

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

    def _freshness_recommendations(
        self,
        status: str,
        missing_items: list[dict[str, Any]],
        stale_items: list[dict[str, Any]],
        dirty_status: dict[str, Any],
        capability_summary: dict[str, Any],
    ) -> list[str]:
        steps = []
        if capability_summary.get("status") != "READY":
            steps.append("Run FMP capability checks and mark required endpoints REVIEWED_ACCESSIBLE.")
        if any(item.get("type") == "quote" for item in missing_items + stale_items):
            steps.append("Run quote snapshot ingestion or seed ingestion after FMP_API_KEY is configured.")
        if any(item.get("type") == "bar" for item in missing_items + stale_items):
            steps.append("Run bounded seed ingestion or incremental intraday refresh for stale symbols/intervals.")
        if dirty_status.get("dirty_window_count"):
            steps.append("Rebuild features, candidates, labels, and replay artifacts for dirty data windows.")
        if status == "READY":
            steps.append("Data freshness is ready for research-cycle dry-runs; model activation remains manual.")
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
