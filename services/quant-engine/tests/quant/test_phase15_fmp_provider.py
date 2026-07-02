from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.config import get_settings
from app.data.fmp import FMPClient, FMPResponse
from app.db.repositories import RepositoryRegistry, reset_repository_registry
from app.schemas.market import Bar, Quote
from app.services.fmp_pipeline import FMPLiveDataService
from app.services.scheduler import SchedulerService
from app.utils.time import UTC

ET = ZoneInfo("America/New_York")


def _repo(tmp_path, monkeypatch, *, key: str | None = None) -> RepositoryRegistry:
    monkeypatch.setenv("AMD_SQLITE_PATH", str(tmp_path / "phase15.sqlite3"))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    if key:
        monkeypatch.setenv("FMP_API_KEY", key)
    else:
        monkeypatch.delenv("FMP_API_KEY", raising=False)
    get_settings.cache_clear()
    reset_repository_registry()
    return RepositoryRegistry(settings=get_settings())


def _response(endpoint_key: str, data, *, status: str = "ACCESSIBLE", sample_count: int | None = None) -> FMPResponse:
    now = datetime.now(UTC)
    return FMPResponse(
        request_id=f"req-{endpoint_key}",
        endpoint_key=endpoint_key,
        endpoint_category="intraday" if endpoint_key.startswith("intraday") else "quote",
        path=endpoint_key,
        status=status,
        http_status=200 if status in {"ACCESSIBLE", "EMPTY"} else 403,
        data=data,
        started_at=now,
        finished_at=now,
        latency_ms=12,
        sample_count=len(data) if sample_count is None and isinstance(data, list) else (sample_count or 0),
        response_shape={"type": "list"},
        symbol="SPY",
        interval="1min" if endpoint_key.startswith("intraday") else None,
        error_code=None if status in {"ACCESSIBLE", "EMPTY"} else "denied",
        error_class=None if status in {"ACCESSIBLE", "EMPTY"} else "HTTPStatusError",
    )


class FakeHTTPResponse:
    status_code = 200

    def json(self):
        return [{"symbol": "SPY", "price": 500.0, "timestamp": 1_780_000_000, "volume": 100}]


class FakeAsyncClient:
    def __init__(self, timeout):
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def get(self, url, params=None, headers=None):
        assert "apikey" not in dict(params or {})
        assert headers == {"apikey": "test-only-key"}
        assert "apikey" not in str(url).lower()
        return FakeHTTPResponse()


class FakeHTTPX:
    AsyncClient = FakeAsyncClient


class FakeProvider:
    async def request_endpoint(self, endpoint_key, **_kwargs):
        if endpoint_key == "batch_quote":
            return _response(
                endpoint_key,
                [{"symbol": "SPY", "price": 500.0, "timestamp": 1_780_000_000, "volume": 100}],
            )
        if endpoint_key == "historical_eod_full":
            return _response(
                endpoint_key,
                [{"date": "2026-06-01", "open": 100, "high": 101, "low": 99, "close": 100.5, "volume": 1000}],
            )
        if endpoint_key.startswith("intraday_"):
            return _response(
                endpoint_key,
                [{"date": "2026-06-01 09:30:00", "open": 100, "high": 101, "low": 99, "close": 100.5, "volume": 1000}],
            )
        return _response(endpoint_key, [{"symbol": "SPY", "price": 500.0, "timestamp": 1_780_000_000, "volume": 100}])

    def _quote_from_row(self, row):
        return Quote(symbol=row["symbol"], price=float(row["price"]), timestamp_utc=datetime.now(UTC), volume=100, source="fmp", raw=row)

    def _bar_from_row(self, symbol, interval, row):
        timestamp_et = datetime(2026, 6, 1, 9, 30, tzinfo=ET)
        return Bar(
            symbol=symbol,
            interval=interval,
            timestamp_utc=timestamp_et.astimezone(UTC),
            timestamp_et=timestamp_et,
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=int(row["volume"]),
            source="fmp",
        )


def test_fmp_client_header_auth_only(monkeypatch) -> None:
    monkeypatch.setenv("FMP_API_KEY", "test-only-key")
    get_settings.cache_clear()
    import app.data.fmp as fmp_module

    monkeypatch.setattr(fmp_module, "httpx", FakeHTTPX)
    client = FMPClient(get_settings())
    response = asyncio.run(client.request(endpoint_key="quote", path="quote", params={"symbol": "SPY"}))
    assert response.status == "ACCESSIBLE"
    assert response.sample_count == 1
    assert "test-only-key" not in str(response.provider_request_metadata())
    assert "apikey" not in str(response.provider_request_metadata()).lower()


def test_capability_no_key_persists_skipped(tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path, monkeypatch)
    result = asyncio.run(FMPLiveDataService(repo).capability_check(endpoint_keys=["quote"], symbols=["SPY"]))
    assert result["capabilities"][0]["status"] == "SKIPPED_NO_KEY"
    assert repo.provider_capabilities.latest_matrix()[0]["status"] == "SKIPPED_NO_KEY"
    assert "apikey" not in str(repo.provider_requests.list_all()).lower()


def test_ingest_intraday_idempotent_and_quality_coverage(tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path, monkeypatch, key="test-only-key")
    service = FMPLiveDataService(repo, provider=FakeProvider())
    start = datetime(2026, 6, 1, 13, 30, tzinfo=UTC)
    end = start + timedelta(minutes=5)
    first = asyncio.run(service.ingest_intraday(["SPY"], ["1min"], start, end))
    second = asyncio.run(service.ingest_intraday(["SPY"], ["1min"], start, end))
    assert first["status"] == "COMPLETED"
    assert second["status"] == "COMPLETED"
    assert len(repo.bars.query(symbols=["SPY"], intervals=["1min"])) == 1
    quality = service.coverage_report(symbols=["SPY"], intervals=["1min"], start=start - timedelta(days=1), end=end)
    assert quality["summary"]["source_breakdown"]["fmp"] == 1
    assert quality["latest_bars"][0]["symbol"] == "SPY"


def test_quote_eod_capability_exports(tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path, monkeypatch, key="test-only-key")
    settings = get_settings()
    settings.exports_dir = tmp_path / "exports"
    service = FMPLiveDataService(repo, provider=FakeProvider(), settings=settings)
    capability = asyncio.run(service.capability_check(endpoint_keys=["batch_quote"], symbols=["SPY"]))
    quotes = asyncio.run(service.ingest_quotes(["SPY"]))
    eod = asyncio.run(service.ingest_eod(["SPY"], datetime(2026, 6, 1, tzinfo=UTC), datetime(2026, 6, 2, tzinfo=UTC)))
    exported = service.export_capabilities("json")
    assert capability["capabilities"][0]["status"] == "ACCESSIBLE"
    assert quotes["status"] == "COMPLETED"
    assert eod["status"] == "COMPLETED"
    assert exported["export"]["file_sha256"]
    assert "test-only-key" not in (tmp_path / "exports").read_text() if (tmp_path / "exports").is_file() else True


def test_scheduler_fmp_job_blocks_without_key(tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path, monkeypatch)
    job = SchedulerService(repo).create_job({"job_type": "fmp_quote_snapshot", "payload": {"symbols": ["SPY"]}})
    result = SchedulerService(repo).run_job(job["job_id"])
    assert result["status"] == "BLOCKED"
    assert result["failed_reason"] == "fmp_api_key_required"


def test_phase15_api_missing_key_routes(tmp_path, monkeypatch) -> None:
    _repo(tmp_path, monkeypatch)
    from app.main import app

    with TestClient(app) as client:
        smoke = client.post("/provider/fmp/smoke").json()
        ingest = client.post("/data/ingest/fmp/quotes", json={"symbols": ["SPY"]}).json()
        status = client.get("/operations/provider-status").json()
    assert smoke["status"] == "skipped"
    assert ingest["status"] == "BLOCKED"
    assert status["key_status"] == "missing"
    assert "apikey" not in str(smoke).lower()
