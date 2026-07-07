from __future__ import annotations

from datetime import datetime, timedelta

from app.db.repositories import RepositoryRegistry
from app.models.calibration_drift import CalibrationDriftEngine
from app.orchestration.windowing import generate_replay_windows
from app.schemas.market import Bar
from app.services.workflows import (
    CalibrationDriftService,
    DataQualityService,
    ModelReviewReportService,
    ReplayWindowOrchestrationService,
)
from app.utils.time import UTC


def _audit(
    audit_id: str,
    rank: float,
    high_grade_r: float,
    take_minus_watch: float,
    created_at: datetime,
    monotonicity: bool = True,
    high_grade_samples: int = 8,
) -> dict[str, object]:
    return {
        "calibration_audit_id": audit_id,
        "model_version": "phase10-model",
        "replay_run_ids": [],
        "outcome_source": "counterfactual_preferred",
        "score_bins": [
            {"bin_key": "0-40", "sample_size": 8, "observed_average_r": -0.2},
            {"bin_key": "75-100", "sample_size": high_grade_samples, "observed_average_r": high_grade_r},
        ],
        "grade_bins": [{"bin_key": "A", "sample_size": high_grade_samples, "observed_average_r": high_grade_r}],
        "action_bins": [
            {"bin_key": "TAKE", "sample_size": high_grade_samples, "observed_average_r": high_grade_r},
            {"bin_key": "WATCH", "sample_size": 8, "observed_average_r": high_grade_r - take_minus_watch},
        ],
        "rank_correlation_score": rank,
        "monotonicity_pass": monotonicity,
        "separation_metrics": {"take_minus_watch_average_r": take_minus_watch},
        "stability_metrics": {},
        "calibration_warnings": [],
        "rejection_reasons": [],
        "created_at": created_at.isoformat(),
    }


def _model() -> dict[str, object]:
    return {
        "model_version": "phase10-model",
        "model_type": "replay_aware_baseline",
        "activation_decision": "accepted",
        "active": False,
        "metrics": {"average_r": 0.3, "profit_factor": 1.4},
        "validation_metrics": {},
        "created_at": datetime.now(UTC).isoformat(),
    }


def test_window_generation_supports_modes_and_embargo() -> None:
    start = datetime(2026, 6, 1, tzinfo=UTC)
    end = datetime(2026, 6, 4, tzinfo=UTC)
    daily, warnings = generate_replay_windows({"window_mode": "daily", "start": start, "end": end})
    rolling, _ = generate_replay_windows(
        {
            "window_mode": "rolling",
            "start": start,
            "end": end,
            "window_size_days": 2,
            "step_days": 1,
            "train_size_days": 1,
            "embargo_minutes": 30,
        }
    )
    anchored, _ = generate_replay_windows(
        {
            "window_mode": "anchored",
            "start": start,
            "end": end + timedelta(days=5),
            "min_training_days": 2,
            "window_size_days": 1,
            "step_days": 1,
            "embargo_minutes": 60,
        }
    )
    custom, custom_warnings = generate_replay_windows(
        {
            "window_mode": "custom",
            "windows": [
                {
                    "replay_start": start.isoformat(),
                    "replay_end": (start + timedelta(minutes=1)).isoformat(),
                    "train_end": start.isoformat(),
                    "validation_start": (start + timedelta(minutes=10)).isoformat(),
                    "embargo_minutes": 15,
                }
            ],
        }
    )
    assert warnings == []
    assert len(daily) == 3
    assert rolling[0]["train_end"] < rolling[0]["replay_start"]
    assert anchored[0]["train_start"] == start.isoformat()
    assert "short_replay_window" in custom[0]["warnings"]
    assert "window_1_embargo_overlap" in custom_warnings


def test_replay_window_orchestration_persists_window_sets_and_results(tmp_path) -> None:
    repo = RepositoryRegistry(db_path=tmp_path / "phase10.sqlite3")
    service = ReplayWindowOrchestrationService(repo)
    start = datetime(2026, 6, 1, 13, 30, tzinfo=UTC)
    end = start + timedelta(minutes=20)
    created = service.create(
        {
            "name": "phase10-window-set",
            "symbols": ["APPL"],
            "intervals": ["1min"],
            "window_mode": "custom",
            "windows": [{"replay_start": start.isoformat(), "replay_end": end.isoformat()}],
            "replay_config": {"allow_stale": True},
            "run_immediately": False,
        }
    )
    assert created["status"] == "created"
    assert created["symbols"] == ["AAPL"]
    assert "insufficient_data_no_bars" in created["generated_windows"][0]["warnings"]

    run = service.run(created["window_set_id"], {"run_replay": False})
    assert run["status"] == "ok"
    assert run["summary"]["completed_window_count"] == 1
    persisted = repo.replay_windows.list_results(created["window_set_id"])
    assert persisted[0]["status"] == "completed"


def test_calibration_drift_flags_recent_deterioration_and_persists(tmp_path) -> None:
    first = _audit("calibration-1", 0.6, 0.8, 0.5, datetime(2026, 6, 1, tzinfo=UTC))
    recent = _audit("calibration-2", 0.2, -0.3, -0.1, datetime(2026, 6, 2, tzinfo=UTC), monotonicity=False, high_grade_samples=2)
    report = CalibrationDriftEngine().run(
        model_version="phase10-model",
        calibration_audits=[first, recent],
        window_results=[
            {"window_result_id": "window-result-1", "window_index": 1, "metrics": {"average_r": 0.8, "profit_factor": 2.0}},
            {"window_result_id": "window-result-2", "window_index": 2, "metrics": {"average_r": -0.3, "profit_factor": 0.8}, "warnings": ["stale replay inputs"]},
        ],
    )
    assert report["severity"] == "BLOCKING"
    assert "rank_correlation_deteriorating" in report["drift_flags"]
    assert "high_grade_expectancy_turns_negative" in report["drift_flags"]
    assert "stale_window_contamination" in report["drift_flags"]

    repo = RepositoryRegistry(db_path=tmp_path / "drift.sqlite3")
    repo.model_runs.save(_model())
    repo.model_calibration_audits.save(first)
    repo.model_calibration_audits.save(recent)
    saved = CalibrationDriftService(repo).create("phase10-model")
    assert saved["status"] == "ok"
    assert repo.model_calibration_drift.get(saved["drift_report_id"])["model_version"] == "phase10-model"


def test_model_review_report_blocks_on_calibration_drift_without_activation(tmp_path) -> None:
    repo = RepositoryRegistry(db_path=tmp_path / "review.sqlite3")
    repo.model_runs.save(_model())
    repo.validation_reports.save(
        {
            "model_version": "phase10-model",
            "summary": {"average_r": 0.3},
            "windows": [],
            "activation_decision": "accepted",
            "rejection_reasons": [],
            "created_at": datetime.now(UTC).isoformat(),
        },
        model_version="phase10-model",
    )
    drift = repo.model_calibration_drift.save(
        {
            "drift_report_id": "drift-blocking",
            "model_version": "phase10-model",
            "severity": "BLOCKING",
            "drift_flags": ["stale_window_contamination"],
            "summary": {"diagnostic_only": True},
            "window_metrics": [],
            "created_at": datetime.now(UTC).isoformat(),
        }
    )
    review = ModelReviewReportService(repo).create(
        "phase10-model",
        {"drift_report_ids": [drift["drift_report_id"]], "calibration_required": False},
    )
    assert review["readiness_status"] == "BLOCK"
    assert "calibration_drift_blocking" in review["readiness_reasons"]
    assert repo.active_models.get_active() is None


def test_model_review_blocks_required_bounded_sensitivity_without_activation(tmp_path) -> None:
    repo = RepositoryRegistry(db_path=tmp_path / "review-sensitivity.sqlite3")
    repo.model_runs.save(_model())
    repo.validation_reports.save(
        {
            "model_version": "phase10-model",
            "summary": {"average_r": 0.3},
            "windows": [],
            "activation_decision": "accepted",
            "rejection_reasons": [],
            "created_at": datetime.now(UTC).isoformat(),
        },
        model_version="phase10-model",
    )
    sensitivity = repo.replay_sensitivity.save(
        {
            "sensitivity_run_id": "sensitivity-bounded",
            "replay_run_id": "replay-bounded",
            "created_at": datetime.now(UTC).isoformat(),
            "config": {"coverage_mode": "TIERED_ESSENTIAL"},
            "coverage_mode": "TIERED_ESSENTIAL",
            "completion_status": "BOUNDED_COMPLETE",
            "configured_grid_complete": True,
            "full_default_grid_complete": False,
            "partial_grid_disclosure": True,
            "planned_scenario_count": 4,
            "completed_scenario_count": 4,
            "remaining_scenario_count": 0,
            "scenario_count": 4,
            "passed_scenario_count": 4,
            "failed_scenario_count": 0,
            "robustness_score": 1.0,
            "pass_fail": "fail",
            "coverage_warnings": ["bounded_sensitivity_not_full_default_grid"],
            "fragility_flags": [],
            "gate_results": {"configured_grid_complete": True, "full_default_grid_complete": False},
            "scenarios": [],
        }
    )
    review = ModelReviewReportService(repo).create(
        "phase10-model",
        {"sensitivity_run_ids": [sensitivity["sensitivity_run_id"]], "sensitivity_required": True},
    )
    assert review["readiness_status"] == "BLOCK"
    assert "activation_grade_sensitivity_missing" in review["readiness_reasons"]
    assert "sensitivity_scope_not_full_grid" in review["readiness_reasons"]
    assert "sensitivity_gate_failed" in review["readiness_reasons"]
    assert review["summary"]["sensitivity_report_count"] == 1
    assert review["sensitivity_reports"][0]["partial_grid_disclosure"] is True
    assert review["sensitivity_reports"][0]["sensitivity_classification"] == "diagnostic"
    assert repo.active_models.get_active() is None


def test_data_quality_report_detects_gaps_invalid_rows_and_dirty_windows(tmp_path) -> None:
    repo = RepositoryRegistry(db_path=tmp_path / "quality.sqlite3")
    start = datetime(2026, 6, 1, 13, 30, tzinfo=UTC)
    bars = [
        Bar(
            symbol="AAPL",
            interval="1min",
            timestamp_utc=start,
            timestamp_et=start,
            open=100,
            high=100.5,
            low=99.8,
            close=100.1,
            volume=1000,
            source="test",
        ),
        Bar(
            symbol="AAPL",
            interval="1min",
            timestamp_utc=start + timedelta(minutes=5),
            timestamp_et=start + timedelta(minutes=5),
            open=100,
            high=99,
            low=101,
            close=100,
            volume=-1,
            source="test",
        ),
    ]
    repo.bars.upsert_many(bars)
    report = DataQualityService(repo).report(symbols=["AAPL"], intervals=["1min"], start=start, end=start + timedelta(minutes=5))
    assert report["summary"]["invalid_price_or_volume_count"] == 1
    assert report["summary"]["missing_bar_window_count"] == 1
    assert report["summary"]["dirty_pipeline_window_count"] >= 1
    assert "invalid_price_or_volume_detected" in report["warnings"]
