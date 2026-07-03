from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.config import get_settings
from app.data.fmp import FMPResponse
from app.db.repositories import RepositoryRegistry, reset_repository_registry
from app.schemas.market import Bar, Quote
from app.services.fmp_pipeline import DEFAULT_FMP_ENDPOINT_KEYS, FMPLiveDataService
from app.services.scheduler import SchedulerService
from app.utils.time import UTC

ET = ZoneInfo("America/New_York")
REVIEWED = "REVIEWED_ACCESSIBLE"


def _repo(tmp_path: Path, monkeypatch, *, key: str | None = None) -> RepositoryRegistry:
    monkeypatch.setenv("AMD_SQLITE_PATH", str(tmp_path / "phase16.sqlite3"))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    if key:
        monkeypatch.setenv("FMP_API_KEY", key)
    else:
        monkeypatch.delenv("FMP_API_KEY", raising=False)
    get_settings.cache_clear()
    reset_repository_registry()
    return RepositoryRegistry(settings=get_settings())


def _response(endpoint_key: str, data, *, symbol: str = "SPY", status: str = "ACCESSIBLE") -> FMPResponse:
    now = datetime(2026, 7, 1, 14, 0, tzinfo=UTC)
    return FMPResponse(
        request_id=f"req-{endpoint_key}-{symbol}",
        endpoint_key=endpoint_key,
        endpoint_category="intraday" if endpoint_key.startswith("intraday") else ("historical_eod" if "eod" in endpoint_key else "quote"),
        path=endpoint_key,
        status=status,
        http_status=200 if status in {"ACCESSIBLE", "EMPTY"} else 403,
        data=data,
        started_at=now,
        finished_at=now,
        latency_ms=8,
        sample_count=len(data) if isinstance(data, list) else 0,
        response_shape={"type": "list"},
        symbol=symbol,
        interval="1min" if endpoint_key.startswith("intraday") else None,
        error_code=None if status in {"ACCESSIBLE", "EMPTY"} else "denied",
        error_class=None if status in {"ACCESSIBLE", "EMPTY"} else "HTTPStatusError",
    )


class Phase16FakeProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def request_endpoint(self, endpoint_key, **kwargs):
        self.calls.append((endpoint_key, kwargs))
        symbol = str(kwargs.get("symbol") or (kwargs.get("symbols") or ["SPY"])[0])
        symbols = [str(item) for item in kwargs.get("symbols") or [symbol]]
        if endpoint_key == "batch_quote":
            return _response(
                endpoint_key,
                [
                    {
                        "symbol": item,
                        "price": 500.0 + index,
                        "timestamp": 1_780_000_000,
                        "volume": 100 + index,
                        "bid": 499.5,
                        "ask": 500.5,
                        "previousClose": 499.0,
                    }
                    for index, item in enumerate(symbols)
                ],
                symbol=symbol,
            )
        if endpoint_key == "historical_eod_full":
            return _response(
                endpoint_key,
                [{"date": "2026-07-01", "open": 100, "high": 101, "low": 99, "close": 100.5, "volume": 1000}],
                symbol=symbol,
            )
        if endpoint_key.startswith("intraday_"):
            return _response(
                endpoint_key,
                [{"date": "2026-07-01 09:30:00", "open": 100, "high": 101, "low": 99, "close": 100.5, "volume": 1000}],
                symbol=symbol,
            )
        return _response(endpoint_key, [{"symbol": symbol, "price": 500.0, "timestamp": 1_780_000_000, "volume": 100}], symbol=symbol)

    def _quote_from_row(self, row):
        return Quote(
            symbol=row["symbol"],
            price=float(row["price"]),
            timestamp_utc=datetime.fromtimestamp(float(row["timestamp"]), tz=UTC),
            volume=int(row["volume"]),
            source="fmp",
            raw=row,
        )

    def _bar_from_row(self, symbol, interval, row):
        timestamp_et = datetime(2026, 7, 1, 9, 30, tzinfo=ET)
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


def _review_required(repo: RepositoryRegistry, service: FMPLiveDataService) -> None:
    now = datetime(2026, 7, 1, 14, 0, tzinfo=UTC)
    for endpoint_key in DEFAULT_FMP_ENDPOINT_KEYS:
        row = repo.provider_capabilities.save(
            {
                "provider": "fmp",
                "endpoint_key": endpoint_key,
                "endpoint_category": "intraday" if endpoint_key.startswith("intraday") else "quote",
                "symbol_scope": ["SPY"],
                "status": "ACCESSIBLE",
                "http_status": 200,
                "sample_count": 1,
                "response_shape": {"type": "list"},
                "checked_at": now,
            }
        )
        service.review_capability(row["check_id"], operator_review_status=REVIEWED, reviewed_by="test")


def test_operator_review_summary_and_api_review(tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path, monkeypatch, key="test-only-key")
    check = repo.provider_capabilities.save(
        {
            "provider": "fmp",
            "endpoint_key": "batch_quote",
            "endpoint_category": "quote",
            "symbol_scope": ["APPL"],
            "status": "ACCESSIBLE",
            "http_status": 200,
            "sample_count": 1,
            "response_shape": {"type": "list"},
            "checked_at": datetime(2026, 7, 1, 14, 0, tzinfo=UTC),
        }
    )
    from app.main import app

    with TestClient(app) as client:
        reviewed = client.post(
            f"/provider/capabilities/{check['check_id']}/review",
            json={"operator_review_status": REVIEWED, "reviewed_by": "operator", "review_notes": "mock ok"},
        ).json()
        summary = client.get("/provider/capabilities/review-summary").json()
    assert reviewed["capability"]["operator_review_status"] == REVIEWED
    assert reviewed["capability"]["symbol_scope"] == ["AAPL"]
    assert summary["status"] in {"UNREVIEWED", "PARTIAL"}
    assert "test-only-key" not in str(reviewed)


def test_quote_snapshots_are_durable_idempotent_and_normalize_appl(tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path, monkeypatch, key="test-only-key")
    service = FMPLiveDataService(repo, provider=Phase16FakeProvider(), settings=get_settings())
    first = asyncio.run(service.ingest_quotes(["APPL", "SPY"]))
    second = asyncio.run(service.ingest_quotes(["AAPL", "SPY"]))
    snapshots = repo.quote_snapshots.list(symbols=["AAPL", "SPY"])
    assert first["status"] == "COMPLETED"
    assert second["status"] == "COMPLETED"
    assert first["records_inserted"] == 2
    assert second["records_updated"] == 2
    assert {row["symbol"] for row in snapshots} == {"AAPL", "SPY"}
    assert len(snapshots) == 2


def test_seed_dry_run_needs_no_key_and_live_seed_requires_review(tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path, monkeypatch)
    fake = Phase16FakeProvider()
    service = FMPLiveDataService(repo, provider=fake, settings=get_settings())
    dry_run = asyncio.run(service.seed_ingestion(symbols=["SPY"], intervals=["1day", "1min"], dry_run=True))
    blocked = asyncio.run(service.seed_ingestion(symbols=["SPY"], intervals=["1day", "1min"], dry_run=False))
    assert dry_run["status"] == "dry_run"
    assert fake.calls == []
    assert blocked["status"] == "BLOCKED"

    repo = _repo(tmp_path, monkeypatch, key="test-only-key")
    service = FMPLiveDataService(repo, provider=Phase16FakeProvider(), settings=get_settings())
    unreviewed = asyncio.run(service.seed_ingestion(symbols=["SPY"], intervals=["1day", "1min"]))
    _review_required(repo, service)
    seeded = asyncio.run(service.seed_ingestion(symbols=["SPY"], intervals=["1day", "1min"]))
    assert unreviewed["status"] == "BLOCKED"
    assert seeded["status"] == "COMPLETED"
    assert seeded["records_fetched"] >= 3
    assert repo.quote_snapshots.latest_by_symbol(["SPY"])
    assert repo.bars.query(symbols=["SPY"], intervals=["1day"])
    assert repo.bars.query(symbols=["SPY"], intervals=["1min"])


def test_data_freshness_ready_stale_and_missing(tmp_path, monkeypatch) -> None:
    missing_repo = _repo(tmp_path, monkeypatch, key="test-only-key")
    missing = FMPLiveDataService(missing_repo, provider=Phase16FakeProvider(), settings=get_settings()).freshness_check(
        symbols=["SPY"],
        intervals=["1min"],
        require_reviewed_capabilities=False,
    )
    assert missing["status"] == "BLOCKED"

    repo = _repo(tmp_path, monkeypatch, key="test-only-key")
    service = FMPLiveDataService(repo, provider=Phase16FakeProvider(), settings=get_settings())
    _review_required(repo, service)
    asyncio.run(service.seed_ingestion(symbols=["SPY"], intervals=["1day", "1min"]))
    for dirty in repo.pipeline_windows.list_dirty(symbols=["SPY"], intervals=["1day", "1min"]):
        start = datetime.fromisoformat(str(dirty["start"]).replace("Z", "+00:00")) if dirty.get("start") else None
        end = datetime.fromisoformat(str(dirty["end"]).replace("Z", "+00:00")) if dirty.get("end") else None
        repo.pipeline_windows.mark_built(
            str(dirty["artifact_type"]),
            [str(dirty["symbol"])],
            [str(dirty["interval"])],
            start,
            end,
            str(dirty["version"]),
        )
    ready = service.freshness_check(
        symbols=["SPY"],
        intervals=["1day", "1min"],
        max_bar_age_minutes={"1day": 10_000_000, "1min": 10_000_000},
        max_quote_age_seconds=10_000_000,
    )
    stale = service.freshness_check(
        symbols=["SPY"],
        intervals=["1min"],
        max_bar_age_minutes={"1min": 1},
        max_quote_age_seconds=1,
        require_reviewed_capabilities=False,
    )
    assert ready["status"] == "READY"
    assert stale["status"] == "STALE"
    assert repo.data_freshness_reports.latest()["status"] == "STALE"


def test_scheduler_seed_dry_run_and_freshness_job_without_key(tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path, monkeypatch)
    scheduler = SchedulerService(repo)
    seed = scheduler.create_job({"job_type": "fmp_seed_ingestion", "payload": {"symbols": ["SPY"], "intervals": ["1day", "1min"], "dry_run": True}})
    seed_result = scheduler.run_job(seed["job_id"])
    freshness = scheduler.create_job({"job_type": "data_freshness_check", "payload": {"symbols": ["SPY"], "intervals": ["1min"], "require_reviewed_capabilities": False}})
    freshness_result = scheduler.run_job(freshness["job_id"])
    assert seed_result["status"] == "COMPLETED"
    assert seed_result["result"]["status"] == "dry_run"
    assert freshness_result["status"] == "BLOCKED"
    assert freshness_result["result"]["status"] == "BLOCKED"


def test_phase16_api_and_exports(tmp_path, monkeypatch) -> None:
    _repo(tmp_path, monkeypatch, key="test-only-key")
    settings = get_settings()
    settings.exports_dir = tmp_path / "exports"
    from app.main import app

    with TestClient(app) as client:
        dry_run = client.post("/data/ingest/fmp/seed", json={"symbols": ["SPY"], "intervals": ["1day", "1min"], "dry_run": True}).json()
        freshness = client.post("/data/freshness/check", json={"symbols": ["SPY"], "intervals": ["1min"], "require_reviewed_capabilities": False}).json()
        latest = client.get("/data/freshness/latest").json()
        quotes = client.get("/data/quotes/snapshots?symbols=SPY").json()
        exported = client.post("/exports/data-freshness-report", json={"kind": "xlsx"}).json()
    assert dry_run["status"] == "dry_run"
    assert freshness["status"] == "BLOCKED"
    assert latest["status"] == "BLOCKED"
    assert quotes["quote_snapshots"] == []
    assert exported["export"]["file_sha256"]
    assert Path(exported["path"]).exists()
    assert "test-only-key" not in Path(exported["path"]).read_bytes().decode("latin1", errors="ignore")
