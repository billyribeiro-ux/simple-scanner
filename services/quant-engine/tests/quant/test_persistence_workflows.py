from __future__ import annotations

from datetime import datetime, timedelta

from app.db.repositories import RepositoryRegistry
from app.exports.service import ExportService
from app.schemas.market import Outcome, Side, Signal
from app.services.workflows import (
    BacktestService,
    ExportWorkflowService,
    FeatureBuildService,
    LabelBuildService,
    ModelActivationService,
)
from app.utils.time import UTC


def _repo(tmp_path) -> RepositoryRegistry:
    return RepositoryRegistry(tmp_path / "amd.sqlite3")


def _signal() -> Signal:
    return Signal(
        timestamp=datetime(2026, 6, 1, 14, 0, tzinfo=UTC),
        ticker="AAPL",
        side=Side.LONG,
        entry_price=100,
        stop_price=99,
        target_1=101,
        target_2=101.5,
        target_3=102.5,
        risk_per_share=1,
        reward_risk_to_t1=1,
        reward_risk_to_t2=1.5,
        reward_risk_to_t3=2.5,
        expected_r=0.2,
        confidence_score=0.75,
        signal_grade="B+",
        setup_type="VWAP reclaim long",
        market_regime="trend_long",
        ticker_regime="single_stock_momentum",
        reasons=["test"],
        warnings=[],
        historical_sample_size=50,
        historical_win_rate=0.6,
        historical_average_r=0.3,
        model_version="test-model",
    )


def test_repository_persists_core_rows_across_registry_instances(tmp_path, make_bar, feature_for_bar, make_label) -> None:
    repo = _repo(tmp_path)
    bars = [make_bar(index, 100 + index * 0.1) for index in range(3)]
    repo.bars.upsert_many(bars)
    repo.features.upsert_many([feature_for_bar(bars[0])])
    repo.labels.upsert_many([make_label(0, 1.5, Outcome.WIN)])
    repo.live_signals.upsert_many([_signal()])

    reopened = RepositoryRegistry(tmp_path / "amd.sqlite3")
    assert len(reopened.bars.list_all()) == 3
    assert len(reopened.features.list_all()) == 1
    assert len(reopened.labels.list_all()) == 1
    assert reopened.live_signals.list_latest()[0].ticker == "AAPL"


def test_feature_label_and_backtest_services_use_persisted_rows(tmp_path, make_bar, feature_for_bar) -> None:
    repo = _repo(tmp_path)
    bars = [make_bar(index, 100 + index * 0.05, volume=1000 + index * 20) for index in range(90)]
    repo.bars.upsert_many(bars)

    feature_result = FeatureBuildService(repo).build(symbols=["AAPL"], intervals=["1min"])
    assert feature_result["features_written"] == 90

    repo.features.upsert_many([feature_for_bar(bar) for bar in bars[:-5]])
    label_result = LabelBuildService(repo).build(symbols=["AAPL"], intervals=["1min"])
    assert label_result["labels_written"] > 0

    report = BacktestService(repo).run(["AAPL"], bars[0].timestamp_utc, bars[-1].timestamp_utc)
    assert report["summary"]["total_trades"] > 0
    assert repo.validation_reports.latest(purpose="backtest")["report_id"] == report["report_id"]


def test_model_activation_requires_accepted_validation_report(tmp_path) -> None:
    repo = _repo(tmp_path)
    model = {
        "model_version": "amd-test",
        "model_type": "statistical_evidence_baseline",
        "feature_set_version": "features.v2.no_leakage",
        "label_config_version": "labels.v2.no_leakage",
        "training_start": "2026-06-01T13:30:00+00:00",
        "training_end": "2026-06-01T14:30:00+00:00",
        "activation_decision": "accepted",
        "metrics": {"total_trades": 40, "average_r": 0.2, "profit_factor": 1.5},
        "validation_metrics": {"passes_activation_gate": True},
        "statistical_evidence": {},
        "created_at": datetime.now(UTC).isoformat(),
    }
    repo.model_runs.save(model, artifact_path=str(tmp_path / "amd-test.json"))
    service = ModelActivationService(repo)

    missing_report = service.activate("amd-test")
    assert missing_report["activated"] is False
    assert missing_report["reason"] == "accepted_validation_report_required"

    repo.validation_reports.save(
        {
            "model_version": "amd-test",
            "summary": {},
            "windows": [],
            "activation_decision": "rejected",
            "rejection_reasons": ["minimum_trades_not_met"],
            "created_at": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
        },
        model_version="amd-test",
    )
    rejected_report = service.activate("amd-test")
    assert rejected_report["activated"] is False

    repo.validation_reports.save(
        {
            "model_version": "amd-test",
            "summary": {"total_trades": 40, "average_r": 0.2, "profit_factor": 1.5},
            "windows": [],
            "activation_decision": "accepted",
            "rejection_reasons": [],
            "created_at": datetime.now(UTC).isoformat(),
        },
        model_version="amd-test",
    )
    activated = service.activate("amd-test")
    assert activated["activated"] is True
    assert repo.active_models.get_active()["model_version"] == "amd-test"


def test_export_workflow_reads_persisted_signals_and_records_metadata(tmp_path, monkeypatch) -> None:
    repo = _repo(tmp_path)
    repo.live_signals.upsert_many([_signal()])
    exporter = ExportService()
    monkeypatch.setattr(exporter.settings, "exports_dir", tmp_path)

    csv_result = ExportWorkflowService(repo, exporter).export_signals("csv")
    xlsx_result = ExportWorkflowService(repo, exporter).export_signals("xlsx")

    assert csv_result["rows"] == 1
    assert xlsx_result["rows"] == 1
    assert len(repo.exports.list_all()) == 2
