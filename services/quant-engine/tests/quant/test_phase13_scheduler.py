from __future__ import annotations

from datetime import datetime, timedelta

from app.db.repositories import RepositoryRegistry
from app.models.replay_evidence import (
    REPLAY_AWARE_MODEL_TYPE,
    REPLAY_AWARE_VALIDATION_MODE,
    REPLAY_AWARE_VALIDATION_PURPOSE,
)
from app.schemas.market import Bar
from app.services.scheduler import SchedulerService
from app.utils.time import UTC


def _bars() -> list[Bar]:
    start = datetime(2026, 6, 1, 13, 30, tzinfo=UTC)
    return [
        Bar(
            symbol="AAPL",
            interval="1min",
            timestamp_utc=start + timedelta(minutes=index),
            timestamp_et=start + timedelta(minutes=index),
            open=100 + index * 0.1,
            high=100.4 + index * 0.1,
            low=99.8 + index * 0.1,
            close=100.1 + index * 0.1,
            volume=1_000 + index,
            source="phase13",
        )
        for index in range(10)
    ]


def _model(version: str, *, active: bool = False, average_r: float = 0.3, profit_factor: float = 1.4) -> dict[str, object]:
    return {
        "model_version": version,
        "model_type": REPLAY_AWARE_MODEL_TYPE,
        "activation_decision": "accepted",
        "active": active,
        "metrics": {
            "average_r": average_r,
            "profit_factor": profit_factor,
            "max_drawdown_r": -1.0,
            "observed_outcome_count": 12,
            "total_trades": 12,
        },
        "validation_metrics": {},
        "created_at": datetime.now(UTC).isoformat(),
    }


def _accepted_validation(repo: RepositoryRegistry, model_version: str) -> dict[str, object]:
    return repo.validation_reports.save(
        {
            "model_version": model_version,
            "validation_mode": REPLAY_AWARE_VALIDATION_MODE,
            "summary": {"selected_candidate_count": 8, "average_r": 0.4, "profit_factor": 1.6},
            "windows": [],
            "activation_decision": "accepted",
            "rejection_reasons": [],
            "created_at": datetime.now(UTC).isoformat(),
        },
        model_version=model_version,
        purpose=REPLAY_AWARE_VALIDATION_PURPOSE,
    )


def _passing_governance_artifacts(repo: RepositoryRegistry, model_version: str) -> None:
    validation = _accepted_validation(repo, model_version)
    calibration = repo.model_calibration_audits.save(
        {
            "calibration_audit_id": f"calibration-{model_version}",
            "model_version": model_version,
            "replay_run_ids": [],
            "outcome_source": "counterfactual_preferred",
            "score_bins": [{"bin_key": "75-100", "sample_size": 8, "observed_average_r": 0.5}],
            "grade_bins": [{"bin_key": "A", "sample_size": 8, "observed_average_r": 0.5}],
            "action_bins": [{"bin_key": "TAKE", "sample_size": 8, "observed_average_r": 0.5}],
            "rank_correlation_score": 0.8,
            "monotonicity_pass": True,
            "separation_metrics": {"take_minus_watch_average_r": 0.4},
            "stability_metrics": {},
            "calibration_warnings": [],
            "rejection_reasons": [],
        }
    )
    drift = repo.model_calibration_drift.save(
        {
            "drift_report_id": f"drift-{model_version}",
            "model_version": model_version,
            "calibration_audit_ids": [calibration["calibration_audit_id"]],
            "summary": {"severity": "INFO"},
            "severity": "INFO",
            "drift_flags": [],
            "window_metrics": [],
        }
    )
    repo.model_review_reports.save(
        {
            "review_report_id": f"review-{model_version}",
            "model_version": model_version,
            "validation_report_ids": [validation["report_id"]],
            "calibration_audit_ids": [calibration["calibration_audit_id"]],
            "drift_report_ids": [drift["drift_report_id"]],
            "summary": {"readiness_status": "PASS", "model_activation_unchanged": True},
            "readiness_status": "PASS",
            "readiness_reasons": [],
            "unresolved_warnings": [],
        }
    )


def _mark_clean(repo: RepositoryRegistry) -> None:
    start = _bars()[0].timestamp_utc
    end = _bars()[-1].timestamp_utc
    for artifact, version in (
        ("features", "features.v2.no_leakage"),
        ("candidates", "candidate_signals.v1"),
        ("labels", "labels.v2.no_leakage"),
        ("replay", "candidate_market_replay"),
    ):
        repo.pipeline_windows.mark_built(artifact, ["AAPL"], ["1min"], start, end, version)


def test_scheduler_jobs_persist_events_and_reopen(tmp_path) -> None:
    db_path = tmp_path / "scheduler.sqlite3"
    repo = RepositoryRegistry(db_path=db_path)
    service = SchedulerService(repo)
    job = service.create_job(
        {
            "job_type": "data_quality_report",
            "payload": {"symbols": ["APPL"], "api_key": "do-not-store"},
            "created_by": "operator",
        }
    )
    assert job["status"] == "QUEUED"
    assert job["payload"]["symbols"] == ["APPL"]
    assert job["payload"]["api_key"] == "[REDACTED]"
    ran = service.run_job(job["job_id"])
    assert ran["status"] == "COMPLETED"
    assert ran["result"]["status"] == "ok"
    assert service.events(job["job_id"])["events"]

    reopened = RepositoryRegistry(db_path=db_path)
    assert reopened.scheduler_jobs.get(job["job_id"])["status"] == "COMPLETED"
    assert reopened.scheduler_jobs.list_events(job["job_id"])


def test_scheduler_dry_run_blocks_refresh_without_fmp_key(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    repo = RepositoryRegistry(db_path=tmp_path / "refresh.sqlite3")
    repo.bars.upsert_many(_bars())
    _mark_clean(repo)
    service = SchedulerService(repo)
    job = service.create_job(
        {
            "job_type": "research_cycle_dry_run",
            "payload": {
                "research_cycle": {
                    "cycle_date": "2026-07-01",
                    "symbols": ["AAPL"],
                    "intervals": ["1min"],
                    "start": _bars()[0].timestamp_utc.isoformat(),
                    "end": _bars()[-1].timestamp_utc.isoformat(),
                    "refresh_data": True,
                }
            },
        }
    )
    result = service.run_job(job["job_id"])
    assert result["status"] == "BLOCKED"
    assert result["failed_reason"] == "fmp_api_key_required_for_refresh_data"
    assert repo.provider_requests.list_all() == []


def test_scheduler_run_cycle_does_not_activate_model(tmp_path) -> None:
    repo = RepositoryRegistry(db_path=tmp_path / "cycle-run.sqlite3")
    repo.bars.upsert_many(_bars())
    _mark_clean(repo)
    champion = repo.model_runs.save(_model("champion", active=True, average_r=0.2, profit_factor=1.2))
    repo.active_models.activate(champion, validation_report_id="champion-validation")
    repo.model_runs.save(_model("challenger", average_r=0.5, profit_factor=2.0))
    _passing_governance_artifacts(repo, "challenger")
    service = SchedulerService(repo)
    job = service.create_job(
        {
            "job_type": "research_cycle_run",
            "payload": {
                "research_cycle": {
                    "cycle_date": "2026-07-01",
                    "symbols": ["AAPL"],
                    "intervals": ["1min"],
                    "start": _bars()[0].timestamp_utc.isoformat(),
                    "end": _bars()[-1].timestamp_utc.isoformat(),
                    "challenger_model_version": "challenger",
                    "allow_stale": False,
                },
                "run": {"allow_stale": False},
            },
        }
    )
    result = service.run_job(job["job_id"])
    assert result["status"] == "COMPLETED"
    assert result["result"]["summary"]["model_activation_unchanged"] is True
    assert repo.active_models.get_active(REPLAY_AWARE_MODEL_TYPE)["model_version"] == "champion"
    assert repo.model_proposals.latest()["status"] == "PROPOSED"


def test_scheduler_run_pending_bounds_and_cancel(tmp_path) -> None:
    repo = RepositoryRegistry(db_path=tmp_path / "pending.sqlite3")
    service = SchedulerService(repo)
    jobs = [
        service.create_job({"job_type": "data_quality_report", "payload": {"symbols": ["AAPL"]}})
        for _ in range(3)
    ]
    cancelled = service.cancel(jobs[2]["job_id"])
    assert cancelled["status"] == "CANCELLED"
    pending = service.run_pending(max_jobs=1)
    assert pending["jobs_run"] == 1
    assert len(repo.scheduler_jobs.list(status="COMPLETED")) == 1
    assert len(repo.scheduler_jobs.list(status="QUEUED")) == 1
    assert len(repo.scheduler_jobs.list(status="CANCELLED")) == 1
