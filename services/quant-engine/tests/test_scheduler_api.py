from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import get_settings
from app.db.repositories import reset_repository_registry


def _client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("AMD_SQLITE_PATH", str(tmp_path / "scheduler-api.sqlite3"))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    get_settings.cache_clear()
    reset_repository_registry()
    from app.main import app

    return TestClient(app)


def test_scheduler_api_create_run_events_status(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    created = client.post(
        "/scheduler/jobs",
        json={
            "job_type": "data_quality_report",
            "payload": {"symbols": ["APPL"], "intervals": ["1min"]},
            "created_by": "api-test",
        },
    ).json()
    assert created["status"] == "QUEUED"
    job_id = created["job_id"]

    listed = client.get("/scheduler/jobs").json()
    assert job_id in {job["job_id"] for job in listed["jobs"]}
    detail = client.get(f"/scheduler/jobs/{job_id}").json()
    assert detail["job_id"] == job_id

    ran = client.post(f"/scheduler/jobs/{job_id}/run").json()
    assert ran["status"] == "COMPLETED"
    assert ran["result"]["status"] == "ok"
    events = client.get(f"/scheduler/jobs/{job_id}/events").json()
    assert {event["event_type"] for event in events["events"]} >= {"JOB_CREATED", "JOB_STARTED", "JOB_COMPLETED"}

    status = client.get("/operations/scheduler-status").json()
    assert status["completed_jobs"] == 1
    assert status["queued_jobs"] == 0
    assert status["latest_job"]["job_id"] == job_id


def test_scheduler_api_cancel_and_run_pending_bounds(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    first = client.post("/scheduler/jobs", json={"job_type": "data_quality_report", "payload": {}}).json()
    second = client.post("/scheduler/jobs", json={"job_type": "data_quality_report", "payload": {}}).json()
    cancelled = client.post(f"/scheduler/jobs/{second['job_id']}/cancel").json()
    assert cancelled["status"] == "CANCELLED"

    pending = client.post("/scheduler/jobs/run-pending", json={"max_jobs": 1}).json()
    assert pending["jobs_run"] == 1
    assert pending["results"][0]["job_id"] == first["job_id"]
    status = client.get("/operations/scheduler-status").json()
    assert status["completed_jobs"] == 1
    assert status["cancelled_jobs"] == 1


def test_scheduler_api_refresh_data_blocks_without_fmp_key(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    job = client.post(
        "/scheduler/jobs",
        json={
            "job_type": "research_cycle_run",
            "payload": {
                "research_cycle": {
                    "cycle_date": "2026-07-01",
                    "symbols": ["AAPL"],
                    "intervals": ["1min"],
                    "refresh_data": True,
                }
            },
        },
    ).json()
    blocked = client.post(f"/scheduler/jobs/{job['job_id']}/run").json()
    assert blocked["status"] == "BLOCKED"
    assert blocked["failed_reason"] == "fmp_api_key_required_for_refresh_data"
    status = client.get("/operations/scheduler-status").json()
    assert status["failed_jobs"] == 1


def test_scheduler_api_rejects_unsupported_job_type(tmp_path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    response = client.post("/scheduler/jobs", json={"job_type": "activate_model", "payload": {}})
    assert response.status_code == 422
