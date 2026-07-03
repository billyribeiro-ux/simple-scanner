from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import get_settings
from app.db.repositories import (
    RepositoryRegistry,
    get_repository_registry,
    reset_repository_registry,
)
from app.services.artifact_readiness import ArtifactReadinessService
from app.services.scheduler import SchedulerService


def _trend_bars(make_bar, *, symbol: str = "AAPL", day: int = 1, count: int = 100, interval: str = "1min"):
    return [
        make_bar(
            index,
            100 + index * 0.08,
            symbol=symbol,
            day=day,
            interval=interval,
            volume=1000 + index * 25,
        )
        for index in range(count)
    ]


def test_artifact_readiness_rebuilds_multi_session_windows_and_replay(tmp_path, make_bar) -> None:
    repo = RepositoryRegistry(db_path=tmp_path / "phase19.sqlite3")
    bars = [
        *_trend_bars(make_bar, day=1),
        *_trend_bars(make_bar, day=2),
    ]
    repo.bars.upsert_many(bars)
    service = ArtifactReadinessService(repo)

    audit = service.dirty_window_audit(symbols=["AAPL"], intervals=["1min"])
    assert audit["dirty_by_artifact"]["features"] == 2
    assert audit["dirty_by_artifact"]["candidates"] == 2
    assert audit["dirty_by_artifact"]["labels"] == 2

    features = service.rebuild_features({"symbols": ["AAPL"], "intervals": ["1min"]})
    assert features["status"] == "ok"
    assert features["dirty_windows_cleared"] == 2
    assert repo.pipeline_windows.list_dirty("features", symbols=["AAPL"], intervals=["1min"]) == []

    candidates = service.rebuild_candidates({"symbols": ["AAPL"], "intervals": ["1min"]})
    assert candidates["status"] == "ok"
    assert candidates["candidate_summary"]["actionable_count"] > 0
    assert repo.pipeline_windows.list_dirty("candidates", symbols=["AAPL"], intervals=["1min"]) == []

    labels = service.rebuild_labels({"symbols": ["AAPL"], "intervals": ["1min"]})
    assert labels["status"] == "ok"
    assert labels["labels_written"] > 0
    assert labels["no_skipped_or_unobserved_as_losses"] is True
    assert repo.pipeline_windows.list_dirty("labels", symbols=["AAPL"], intervals=["1min"]) == []

    replay = service.rebuild_replay(
        {
            "symbols": ["AAPL"],
            "intervals": ["1min"],
            "start": bars[0].timestamp_utc.isoformat(),
            "end": bars[-1].timestamp_utc.isoformat(),
        }
    )
    assert replay["status"] == "ok"
    assert len(replay["replay_run_ids"]) == 2
    assert repo.pipeline_windows.list_dirty("replay", symbols=["AAPL"], intervals=["1min"]) == []


def test_artifact_readiness_api_normalizes_appl_and_rebuilds_features(tmp_path, monkeypatch, make_bar) -> None:
    monkeypatch.setenv("AMD_SQLITE_PATH", str(tmp_path / "phase19-api.sqlite3"))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    get_settings.cache_clear()
    reset_repository_registry()

    from app.main import app

    client = TestClient(app)
    repo = get_repository_registry()
    repo.bars.upsert_many(_trend_bars(make_bar, symbol="AAPL", day=1))

    audit = client.get("/pipeline/dirty-windows", params={"symbols": "APPL", "intervals": "1min"}).json()
    assert audit["dirty_window_count"] > 0
    assert {row["symbol"] for row in audit["dirty_windows"]} == {"AAPL"}

    rebuilt = client.post("/pipeline/rebuild/features", json={"symbols": "APPL", "intervals": "1min"}).json()
    assert rebuilt["status"] == "ok"
    assert rebuilt["symbols"] == ["AAPL"]
    assert repo.pipeline_windows.list_dirty("features", symbols=["AAPL"], intervals=["1min"]) == []


def test_scheduler_rebuild_features_job_is_bounded_and_local_only(tmp_path, make_bar, monkeypatch) -> None:
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    repo = RepositoryRegistry(db_path=tmp_path / "phase19-scheduler.sqlite3")
    repo.bars.upsert_many(_trend_bars(make_bar, symbol="AAPL", day=1))
    scheduler = SchedulerService(repo)

    job = scheduler.create_job(
        {
            "job_type": "rebuild_features",
            "payload": {"symbols": ["AAPL"], "intervals": ["1min"]},
            "created_by": "phase19-test",
        }
    )
    completed = scheduler.run_job(str(job["job_id"]))

    assert completed["status"] == "COMPLETED"
    assert completed["result"]["status"] == "ok"
    assert completed["result"]["no_fmp_calls"] is True
    assert completed["result"]["model_activation_unchanged"] is True
    assert repo.provider_requests.list_all() == []


def test_daily_bars_do_not_create_replay_dirty_windows(tmp_path, make_bar) -> None:
    repo = RepositoryRegistry(db_path=tmp_path / "phase19-daily.sqlite3")
    repo.bars.upsert_many(_trend_bars(make_bar, symbol="AAPL", day=1, interval="1day"))

    assert repo.pipeline_windows.list_dirty("features", symbols=["AAPL"], intervals=["1day"])
    assert repo.pipeline_windows.list_dirty("candidates", symbols=["AAPL"], intervals=["1day"])
    assert repo.pipeline_windows.list_dirty("labels", symbols=["AAPL"], intervals=["1day"])
    assert repo.pipeline_windows.list_dirty("replay", symbols=["AAPL"], intervals=["1day"]) == []
