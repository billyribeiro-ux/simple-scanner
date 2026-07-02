from __future__ import annotations

from datetime import datetime, timedelta

from app.db.repositories import RepositoryRegistry
from app.services.scheduler import SchedulerService
from app.utils.time import UTC


def test_scheduler_worker_once_leases_completes_and_clears_lease(tmp_path) -> None:
    repo = RepositoryRegistry(db_path=tmp_path / "worker.sqlite3")
    service = SchedulerService(repo)
    first = service.create_job({"job_type": "data_quality_report", "payload": {"symbols": ["AAPL"]}})
    second = service.create_job({"job_type": "data_quality_report", "payload": {"symbols": ["SPY"]}})

    result = service.run_worker_once(max_jobs=1, lease_owner="test-worker", lease_seconds=60)

    assert result["status"] == "ok"
    assert result["worker_mode"] == "bounded_one_shot"
    assert result["jobs_run"] == 1
    completed = repo.scheduler_jobs.get(first["job_id"])
    assert completed["status"] == "COMPLETED"
    assert completed["lease_owner"] is None
    assert completed["lease_expires_at"] is None
    assert completed["heartbeat_at"] is None
    assert completed["attempt_count"] == 1
    assert repo.scheduler_jobs.get(second["job_id"])["status"] == "QUEUED"
    event_types = {event["event_type"] for event in repo.scheduler_jobs.list_events(first["job_id"])}
    assert {"JOB_LEASED", "JOB_HEARTBEAT", "JOB_RELEASED", "JOB_COMPLETED"} <= event_types


def test_scheduler_worker_refresh_blocks_without_fmp_key(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    repo = RepositoryRegistry(db_path=tmp_path / "worker-refresh.sqlite3")
    service = SchedulerService(repo)
    job = service.create_job(
        {
            "job_type": "research_cycle_dry_run",
            "payload": {"research_cycle": {"symbols": ["AAPL"], "refresh_data": True}},
        }
    )

    result = service.run_worker_once(max_jobs=3, lease_owner="test-worker", lease_seconds=60)

    assert result["jobs_run"] == 1
    blocked = repo.scheduler_jobs.get(job["job_id"])
    assert blocked["status"] == "BLOCKED"
    assert blocked["failed_reason"] == "fmp_api_key_required_for_refresh_data"
    assert blocked["lease_owner"] is None
    assert repo.provider_requests.list_all() == []


def test_scheduler_stale_lease_recovery_fails_exhausted_attempt(tmp_path) -> None:
    repo = RepositoryRegistry(db_path=tmp_path / "worker-stale.sqlite3")
    service = SchedulerService(repo)
    job = service.create_job({"job_type": "data_quality_report", "payload": {"symbols": ["AAPL"]}})
    leased = repo.scheduler_jobs.lease(
        job["job_id"],
        lease_owner="stale-worker",
        lease_seconds=60,
        now=datetime.now(UTC) - timedelta(minutes=10),
    )
    assert leased is not None

    recovered = service.recover_stale_leases()

    assert recovered["jobs_recovered"] == 1
    failed = repo.scheduler_jobs.get(job["job_id"])
    assert failed["status"] == "FAILED"
    assert failed["failed_reason"] == "scheduler_lease_expired"
    assert failed["last_error"] == "scheduler_lease_expired"
    assert failed["lease_owner"] is None
    event_types = {event["event_type"] for event in repo.scheduler_jobs.list_events(job["job_id"])}
    assert "JOB_STALE_RECOVERED" in event_types


def test_scheduler_stale_lease_recovery_requeues_when_attempts_remain(tmp_path) -> None:
    repo = RepositoryRegistry(db_path=tmp_path / "worker-stale-requeue.sqlite3")
    service = SchedulerService(repo)
    job = service.create_job({"job_type": "data_quality_report", "payload": {"symbols": ["AAPL"]}})
    repo.scheduler_jobs.save(job | {"max_attempts": 2})
    leased = repo.scheduler_jobs.lease(
        job["job_id"],
        lease_owner="stale-worker",
        lease_seconds=60,
        now=datetime.now(UTC) - timedelta(minutes=10),
    )
    assert leased is not None

    recovered = service.recover_stale_leases()

    assert recovered["jobs_recovered"] == 1
    requeued = repo.scheduler_jobs.get(job["job_id"])
    assert requeued["status"] == "QUEUED"
    assert requeued["attempt_count"] == 1
    assert requeued["last_error"] == "scheduler_lease_expired_requeued"
    assert requeued["lease_owner"] is None
