from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import create_engine, text

from app.config import get_settings
from app.db.repositories import (
    EXPECTED_TABLES,
    PersistenceConfigurationError,
    RepositoryRegistry,
    _sync_postgres_url,
    reset_repository_registry,
)
from app.schemas.market import Bar, Outcome, Side, Signal
from app.utils.time import UTC

ET = ZoneInfo("America/New_York")
DEFAULT_POSTGRES_AUTH = ":".join(("amd", "amd"))
DEFAULT_POSTGRES_URL = f"postgresql+psycopg://{DEFAULT_POSTGRES_AUTH}@localhost:15432/adaptive_market_decoder"


def _postgres_available(database_url: str = DEFAULT_POSTGRES_URL) -> bool:
    try:
        engine = create_engine(_sync_postgres_url(database_url), future=True)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _clear_postgres_tables(repo: RepositoryRegistry) -> None:
    tables = sorted(EXPECTED_TABLES - {"alembic_version"})
    quoted = ", ".join(f'"{table}"' for table in tables)
    with repo.store.engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"))


def _bar(symbol: str, index: int, close: float, day: int = 1) -> Bar:
    timestamp_et = datetime(2026, 6, day, 9, 30, tzinfo=ET) + timedelta(minutes=index)
    return Bar(
        symbol=symbol,
        interval="1min",
        timestamp_utc=timestamp_et.astimezone(UTC),
        timestamp_et=timestamp_et,
        open=close - 0.05,
        high=close + 0.25,
        low=close - 0.20,
        close=close,
        volume=1_000 + index * 10,
        source="parity",
    )


def _feature(bar: Bar) -> dict[str, object]:
    return {
        "feature_set_version": "parity",
        "symbol": bar.symbol,
        "interval": bar.interval,
        "timestamp": bar.timestamp_utc.isoformat(),
        "timestamp_utc": bar.timestamp_utc,
        "timestamp_et": bar.timestamp_et,
        "session_date": bar.timestamp_et.date().isoformat(),
        "close": bar.close,
        "previous_close": bar.open,
        "vwap": bar.close - 0.40,
        "distance_from_vwap": 0.004,
        "relative_volume": 1.6,
        "trend_slope_5": 0.006,
        "trend_slope_20": 0.002,
        "atr_14_proxy": 1.0,
        "market_regime": "trend_long",
        "ticker_regime": "single_stock_momentum",
        "data_quality_flags": [],
    }


def _label(symbol: str, index: int, realized_r: float, outcome: Outcome) -> dict[str, object]:
    timestamp = datetime(2026, 6, 1, 13, 30, tzinfo=UTC) + timedelta(minutes=index)
    return {
        "label_id": f"label-{symbol}-{index}",
        "symbol": symbol,
        "interval": "1min",
        "timestamp": timestamp,
        "timestamp_utc": timestamp,
        "side": Side.LONG.value,
        "setup_type": "VWAP reclaim long",
        "label_config_version": "parity",
        "entry_price": 100,
        "stop_price": 99,
        "target_1": 101,
        "target_2": 101.5,
        "target_3": 102.5,
        "realized_r": realized_r,
        "outcome": outcome.value,
        "market_regime": "trend_long",
        "max_favorable_excursion": max(realized_r, 0),
        "max_adverse_excursion": min(realized_r, 0),
        "hit_target_1": realized_r >= 1,
        "hit_target_2": realized_r >= 1.5,
        "hit_target_3": realized_r >= 2.5,
        "hit_stop": realized_r < 0,
    }


def _signal(symbol: str = "AAPL") -> Signal:
    return Signal(
        timestamp=datetime(2026, 6, 1, 14, 0, tzinfo=UTC),
        ticker=symbol,
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
        expected_r=0.25,
        confidence_score=0.76,
        signal_grade="A-",
        setup_type="VWAP reclaim long",
        market_regime="trend_long",
        ticker_regime="single_stock_momentum",
        reasons=["parity"],
        warnings=[],
        historical_sample_size=40,
        historical_win_rate=0.6,
        historical_average_r=0.25,
        model_version="parity-model-accepted",
    )


def _settings_for_current_env(monkeypatch, tmp_path, database_url: str | None = None):
    reset_repository_registry()
    get_settings.cache_clear()
    monkeypatch.setenv("AMD_SQLITE_PATH", str(tmp_path / "parity.sqlite3"))
    monkeypatch.delenv("AMD_ALLOW_SQLITE_FALLBACK", raising=False)
    if database_url:
        monkeypatch.setenv("DATABASE_URL", database_url)
    else:
        monkeypatch.delenv("DATABASE_URL", raising=False)
    return get_settings()


def _repo_for_backend(monkeypatch, tmp_path, backend: str) -> RepositoryRegistry:
    database_url = DEFAULT_POSTGRES_URL if backend == "postgresql" else None
    if backend == "postgresql" and not _postgres_available(database_url or DEFAULT_POSTGRES_URL):
        pytest.skip("local Postgres/TimescaleDB is not available for repository parity")
    settings = _settings_for_current_env(monkeypatch, tmp_path, database_url)
    repo = RepositoryRegistry(settings=settings)
    if backend == "postgresql":
        _clear_postgres_tables(repo)
    return repo


@pytest.mark.parametrize("backend", ["sqlite", "postgresql"])
def test_repository_core_contract_parity(tmp_path, monkeypatch, backend: str) -> None:
    repo = _repo_for_backend(monkeypatch, tmp_path, backend)
    info = repo.info()
    assert info["persistence_backend"] == backend
    assert info["database_reachable"] is True

    symbols = ["APPL", "SPY", "QQQ", "NVDA"]
    assert repo.symbols.upsert_many(symbols) == 4
    assert {row["symbol"] for row in repo.symbols.list_all()} == {"AAPL", "SPY", "QQQ", "NVDA"}

    bars = []
    for symbol in ["AAPL", "SPY", "QQQ", "NVDA"]:
        bars.extend(_bar(symbol, index, 100 + index * 0.1, day=1) for index in range(12))
        bars.extend(_bar(symbol, index, 102 + index * 0.1, day=2) for index in range(12))
    assert repo.bars.upsert_many(bars) == 96
    assert repo.bars.upsert_many(bars[:4]) == 4
    assert len(repo.bars.query(symbols=["AAPL"], start=bars[0].timestamp_utc, end=bars[-1].timestamp_utc)) == 24
    dirty_artifacts = {
        row["artifact_type"]
        for row in repo.pipeline_windows.list_dirty(symbols=["AAPL"], intervals=["1min"])
    }
    assert {"features", "candidates", "labels", "replay"} <= dirty_artifacts

    features = [_feature(bar) for bar in bars]
    assert repo.features.upsert_many(features) == 96
    assert len(repo.features.query(symbols=["AAPL"], intervals=["1min"])) == 24

    candidates = [
        {
            "candidate_id": f"candidate-{symbol}",
            "symbol": symbol,
            "interval": "1min",
            "timestamp_utc": bars[index].timestamp_utc,
            "side": Side.LONG.value,
            "setup_type": "VWAP reclaim long",
            "reason_codes": ["parity"],
            "warning_codes": [],
        }
        for index, symbol in enumerate(["AAPL", "SPY", "QQQ", "NVDA"])
    ]
    assert repo.candidate_signals.upsert_many(candidates) == 4
    assert len(repo.candidate_signals.list_all()) == 4

    labels = [
        _label("AAPL", 0, 1.5, Outcome.WIN),
        _label("SPY", 1, -1.0, Outcome.LOSS),
        _label("QQQ", 2, 0.5, Outcome.NEUTRAL),
        _label("NVDA", 3, 2.0, Outcome.WIN),
    ]
    assert repo.labels.upsert_many(labels) == 4
    assert len(repo.labels.query(symbols=["AAPL", "SPY"])) == 2

    model = {
        "model_version": "parity-model-accepted",
        "model_type": "statistical_evidence_baseline",
        "feature_set_version": "parity",
        "label_config_version": "parity",
        "training_start": "2026-06-01T13:30:00+00:00",
        "training_end": "2026-06-02T14:30:00+00:00",
        "activation_decision": "accepted",
        "metrics": {"total_trades": 40, "average_r": 0.25, "profit_factor": 1.6},
        "validation_metrics": {"passes_activation_gate": True},
        "created_at": datetime.now(UTC).isoformat(),
    }
    assert repo.model_runs.save(model)["model_version"] == "parity-model-accepted"
    evidence_cells = [
        {
            "cell_key": "side_global:side=LONG",
            "dimensions": {"side": "LONG"},
            "hierarchy_level": "side_global",
            "parent_cell_key": None,
            "metrics": {
                "sample_size": 4,
                "observed_outcome_count": 4,
                "average_r": 0.5,
                "median_r": 0.5,
                "profit_factor": 2.0,
                "max_drawdown_r": -1.0,
                "sensitivity_robustness_score": 1.0,
                "fragility_flags": [],
                "evidence_quality_grade": "B",
            },
            "sample_size": 4,
            "observed_outcome_count": 4,
            "average_r": 0.5,
            "median_r": 0.5,
            "profit_factor": 2.0,
            "max_drawdown_r": -1.0,
            "robustness_score": 1.0,
            "fragility_flags": [],
            "evidence_quality_grade": "B",
        }
    ]
    assert repo.model_evidence_cells.save_many("parity-model-accepted", evidence_cells) == 1
    score_audit = repo.candidate_score_audits.save(
        {
            "score_id": "score-parity",
            "model_version": "parity-model-accepted",
            "candidate_id": "candidate-AAPL",
            "symbol": "AAPL",
            "interval": "1min",
            "timestamp_utc": bars[0].timestamp_utc,
            "side": Side.LONG.value,
            "setup_type": "VWAP reclaim long",
            "signal_quality_score": 76.0,
            "grade": "A-",
            "action": "TAKE",
            "expected_r_estimate": 0.4,
            "score_components": {"evidence_quality_score": 80},
            "suppression_reasons": [],
            "evidence_cell_keys_used": ["side_global:side=LONG"],
            "warnings": [],
        }
    )
    assert score_audit["score_id"] == "score-parity"
    calibration = repo.model_calibration_audits.save(
        {
            "calibration_audit_id": "calibration-parity",
            "model_version": "parity-model-accepted",
            "validation_report_id": None,
            "replay_run_ids": ["parity-replay"],
            "outcome_source": "counterfactual_preferred",
            "score_bins": [{"bin_key": "75-85", "sample_size": 1, "observed_average_r": 1.5}],
            "grade_bins": [{"bin_key": "A", "sample_size": 1, "observed_average_r": 1.5}],
            "action_bins": [{"bin_key": "TAKE", "sample_size": 1, "observed_average_r": 1.5}],
            "rank_correlation_score": 1.0,
            "monotonicity_pass": True,
            "separation_metrics": {"take_minus_watch_average_r": 1.5},
            "stability_metrics": {"by_symbol": [{"bin_key": "AAPL", "sample_size": 1}]},
            "calibration_warnings": [],
            "rejection_reasons": [],
        }
    )
    assert calibration["calibration_audit_id"] == "calibration-parity"
    rejected = repo.validation_reports.save(
        {
            "model_version": "parity-model-accepted",
            "summary": {},
            "windows": [],
            "activation_decision": "rejected",
            "rejection_reasons": ["controlled_rejection"],
            "created_at": (datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
        },
        model_version="parity-model-accepted",
    )
    assert rejected["activation_decision"] == "rejected"
    accepted = repo.validation_reports.save(
        {
            "model_version": "parity-model-accepted",
            "summary": {"total_trades": 40, "average_r": 0.25},
            "windows": [],
            "activation_decision": "accepted",
            "rejection_reasons": [],
            "created_at": datetime.now(UTC).isoformat(),
        },
        model_version="parity-model-accepted",
    )
    active = repo.active_models.activate(model, validation_report_id=accepted["report_id"])
    assert active["model_version"] == "parity-model-accepted"

    scanner_run_id = repo.scanner_runs.start(["AAPL", "SPY"], 0.7, "parity-model-accepted")
    repo.live_signals.upsert_many([_signal("AAPL")], scanner_run_id=scanner_run_id)
    repo.scanner_runs.finish(scanner_run_id, status="stopped", stats={"latest_count": 1})
    repo.provider_requests.record(
        provider="fmp",
        endpoint="batch-quote",
        status="ok",
        row_count=2,
        metadata={"symbols": ["AAPL", "SPY"]},
    )
    export = repo.exports.record("live_signals", "csv", tmp_path / "signals.csv", row_count=1)
    review = repo.daily_reviews.save(date(2026, 6, 1), {"date": "2026-06-01", "signals_reviewed": 1})
    replay_run = {
        "replay_run_id": "parity-replay",
        "simulation_type": "candidate_market_replay",
        "start": bars[0].timestamp_utc.isoformat(),
        "end": bars[-1].timestamp_utc.isoformat(),
        "symbols": ["AAPL"],
        "intervals": ["1min"],
        "config": {
            "symbols": ["AAPL"],
            "intervals": ["1min"],
            "entry_mode": "next_bar_open",
            "same_bar_stop_target_policy": "conservative_stop_first",
        },
        "summary_metrics": {
            "total_candidates": 2,
            "candidates_taken": 1,
            "candidates_skipped": 1,
            "total_trades": 1,
            "expectancy_r": 1.5,
            "skip_breakdown": {"missing_entry_bar": 1},
            "per_symbol_metrics": {"AAPL": {"total_trades": 1, "expectancy_r": 1.5}},
            "per_setup_metrics": {"VWAP reclaim long": {"total_trades": 1, "expectancy_r": 1.5}},
            "per_regime_metrics": {"trend_long": {"total_trades": 1}},
            "per_time_bucket_metrics": {"opening_drive": {"total_trades": 1}},
            "daily_r_series": [{"date": "2026-06-01", "r": 1.5}],
            "drawdown_series": [0.0],
        },
        "warnings": [],
        "created_at": datetime.now(UTC).isoformat(),
    }
    signal_timestamp = bars[0].timestamp_utc
    replay_trades = [
        {
            "trade_id": "parity-trade-taken",
            "replay_run_id": "parity-replay",
            "candidate_id": "candidate-AAPL",
            "symbol": "AAPL",
            "interval": "1min",
            "side": Side.LONG.value,
            "setup_type": "VWAP reclaim long",
            "signal_timestamp_utc": signal_timestamp,
            "entry_timestamp_utc": signal_timestamp + timedelta(minutes=1),
            "exit_timestamp_utc": signal_timestamp + timedelta(minutes=6),
            "entry_price": 100,
            "stop_price": 99,
            "target_1": 101,
            "target_2": 101.5,
            "target_3": 102.5,
            "exit_price": 101.5,
            "exit_reason": "target_2",
            "realized_r": 1.5,
            "mfe_r": 1.7,
            "mae_r": -0.2,
            "bars_held": 5,
            "minutes_held": 5,
            "same_bar_ambiguous": False,
            "ambiguity_policy": "conservative_stop_first",
            "slippage_bps": 0,
            "spread_bps": 0,
            "commission": 0,
            "market_regime": "trend_long",
            "time_bucket": "opening_drive",
            "signal_score": 0.8,
            "expected_r": 1.5,
            "status": "TAKEN",
            "metadata": {"contract": "parity"},
        },
        {
            "trade_id": "parity-trade-skipped",
            "replay_run_id": "parity-replay",
            "candidate_id": "candidate-AAPL-missing-entry",
            "symbol": "AAPL",
            "interval": "1min",
            "side": Side.LONG.value,
            "setup_type": "VWAP reclaim long",
            "signal_timestamp_utc": signal_timestamp + timedelta(minutes=30),
            "status": "SKIPPED",
            "skip_reason": "missing_entry_bar",
            "metadata": {"contract": "parity"},
        },
    ]
    saved_replay = repo.replays.save(replay_run, replay_trades)
    sensitivity = repo.replay_sensitivity.save(
        {
            "sensitivity_run_id": "parity-sensitivity",
            "replay_run_id": "parity-replay",
            "created_at": datetime.now(UTC).isoformat(),
            "config": {"slippage_bps_grid": [0, 1], "spread_bps_grid": [0, 2]},
            "scenario_count": 1,
            "passed_scenario_count": 1,
            "failed_scenario_count": 0,
            "robustness_score": 1.0,
            "pass_fail": "pass",
            "fragility_flags": [],
            "gate_results": {"robustness_score_met": True},
            "worst_case": {"scenario_id": "parity-scenario"},
            "median_case": {"scenario_id": "parity-scenario"},
            "best_case": {"scenario_id": "parity-scenario"},
            "scenarios": [
                {
                    "scenario_id": "parity-scenario",
                    "replay_run_id": "parity-replay",
                    "slippage_bps": 0,
                    "spread_bps": 0,
                    "intrabar_path_policy": "conservative",
                    "same_bar_stop_target_policy": "conservative_stop_first",
                    "summary_metrics": {"total_trades": 1, "average_r": 1.5, "profit_factor": 0},
                    "gate_results": {"minimum_total_trades_met": True},
                    "pass_fail": "pass",
                }
            ],
        }
    )
    comparison = repo.backtest_comparisons.save(
        {
            "comparison_type": "label_vs_replay",
            "replay_run_id": "parity-replay",
            "summary": {"status": "aligned_with_tolerance", "deltas": {"average_r": 0}},
            "label_summary": {"total_trades": 1},
            "replay_summary": {"total_trades": 1},
        }
    )
    model_comparison = repo.model_comparisons.save(
        {
            "comparison_type": "model_comparison",
            "model_versions": ["parity-model-accepted"],
            "validation_report_ids": [accepted["report_id"]],
            "calibration_audit_ids": ["calibration-parity"],
            "replay_run_ids": ["parity-replay"],
            "summary": {"diagnostic_only": True},
        }
    )
    window_set = repo.replay_windows.save_set(
        {
            "window_set_id": "parity-window-set",
            "name": "parity-window-set",
            "symbols": ["AAPL"],
            "intervals": ["1min"],
            "setup_types": ["VWAP reclaim long"],
            "start": bars[0].timestamp_utc.isoformat(),
            "end": bars[-1].timestamp_utc.isoformat(),
            "window_mode": "custom",
            "generated_windows": [
                {
                    "window_index": 1,
                    "replay_start": bars[0].timestamp_utc.isoformat(),
                    "replay_end": bars[-1].timestamp_utc.isoformat(),
                }
            ],
            "summary": {"window_count": 1, "completed_window_count": 1},
            "status": "completed",
            "warnings": [],
        }
    )
    window_result = repo.replay_windows.save_result(
        {
            "window_result_id": "parity-window-result",
            "window_set_id": "parity-window-set",
            "window_index": 1,
            "replay_start": bars[0].timestamp_utc.isoformat(),
            "replay_end": bars[-1].timestamp_utc.isoformat(),
            "replay_run_ids": ["parity-replay"],
            "counterfactual_replay_run_id": None,
            "portfolio_replay_run_id": "parity-replay",
            "model_versions": ["parity-model-accepted"],
            "status": "completed",
            "metrics": {"total_trades": 1, "average_r": 1.5, "profit_factor": 0},
            "warnings": [],
        }
    )
    drift = repo.model_calibration_drift.save(
        {
            "drift_report_id": "parity-drift",
            "model_version": "parity-model-accepted",
            "calibration_audit_ids": ["calibration-parity"],
            "window_result_ids": ["parity-window-result"],
            "replay_run_ids": ["parity-replay"],
            "summary": {"severity": "INFO", "diagnostic_only": True},
            "score_bin_drift": {},
            "grade_bin_drift": {},
            "action_bin_drift": {},
            "stability_metrics": {"rank_correlation_latest": 1.0},
            "drift_flags": [],
            "severity": "INFO",
            "warnings": [],
            "window_metrics": [
                {
                    "window_result_id": "parity-window-result",
                    "window_index": 1,
                    "metrics": {"rank_correlation_score": 1.0, "high_grade_average_r": 1.5},
                    "flags": [],
                    "severity": "INFO",
                }
            ],
        }
    )
    review_report = repo.model_review_reports.save(
        {
            "review_report_id": "parity-review",
            "model_version": "parity-model-accepted",
            "window_set_id": "parity-window-set",
            "validation_report_ids": [accepted["report_id"]],
            "calibration_audit_ids": ["calibration-parity"],
            "drift_report_ids": ["parity-drift"],
            "sensitivity_run_ids": ["parity-sensitivity"],
            "comparison_ids": [model_comparison["comparison_id"]],
            "summary": {"readiness_status": "PASS", "model_activation_unchanged": True},
            "readiness_status": "PASS",
            "readiness_reasons": [],
            "unresolved_warnings": [],
        }
    )
    replay_windows = repo.pipeline_windows.mark_built(
        "replay",
        ["AAPL"],
        ["1min"],
        bars[0].timestamp_utc,
        bars[-1].timestamp_utc,
        "candidate_market_replay",
        {"replay_run_id": "parity-replay"},
    )
    assert saved_replay["trades_written"] == 2
    assert sensitivity["scenarios_written"] == 1
    assert comparison["comparison_id"]
    assert window_set["window_set_id"] == "parity-window-set"
    assert window_result["window_result_id"] == "parity-window-result"
    assert drift["drift_report_id"] == "parity-drift"
    assert review_report["review_report_id"] == "parity-review"
    assert replay_windows[0]["dirty"] is False
    research_cycle = repo.research_cycles.save(
        {
            "research_cycle_id": "parity-research-cycle",
            "cycle_date": "2026-07-01",
            "cycle_type": "daily",
            "status": "COMPLETED",
            "symbols": ["AAPL"],
            "intervals": ["1min"],
            "start": bars[0].timestamp_utc.isoformat(),
            "end": bars[-1].timestamp_utc.isoformat(),
            "session": "rth",
            "active_model_version": "parity-model-accepted",
            "challenger_model_version": "parity-model-challenger",
            "summary": {"diagnostic_only": True, "model_activation_unchanged": True},
            "warnings": [],
            "config_hash": "config-hash",
            "input_fingerprint": "input-fingerprint",
            "database_revision": "0009_phase13_scheduler",
            "persistence_backend": backend,
            "created_at": datetime.now(UTC).isoformat(),
        }
    )
    cycle_artifact = repo.research_cycles.save_artifact(
        "parity-research-cycle",
        {
            "artifact_type": "model_review",
            "source_id": "parity-review",
            "source_table": "model_review_reports",
        },
    )
    champion_comparison = repo.champion_challenger_comparisons.save(
        {
            "comparison_id": "parity-champion-comparison",
            "champion_model_version": "parity-model-accepted",
            "challenger_model_version": "parity-model-challenger",
            "champion_metrics": {"average_r": 0.25},
            "challenger_metrics": {"average_r": 0.35},
            "delta_metrics": {"average_r": 0.1},
            "challenger_better_flags": ["average_r_improved"],
            "challenger_worse_flags": [],
            "gate_results": {"all_passed": True},
            "recommended_action": "APPROVE_CHALLENGER_FOR_ACTIVATION",
            "readiness_status": "PASS",
            "warnings": [],
        }
    )
    proposal = repo.model_proposals.save(
        {
            "proposal_id": "parity-proposal",
            "research_cycle_id": "parity-research-cycle",
            "proposal_type": "challenger_model",
            "status": "PROPOSED",
            "champion_model_version": "parity-model-accepted",
            "challenger_model_version": "parity-model-challenger",
            "recommended_action": "APPROVE_CHALLENGER_FOR_ACTIVATION",
            "readiness_status": "PASS",
            "comparison_ids": ["parity-champion-comparison"],
            "evidence_summary": {"diagnostic_only": True},
            "champion_metrics": {"average_r": 0.25},
            "challenger_metrics": {"average_r": 0.35},
            "delta_metrics": {"average_r": 0.1},
            "pass_fail_gates": {"all_passed": True},
            "rejection_reasons": [],
            "approval_required": True,
        }
    )
    decision = repo.model_decision_ledger.append(
        {
            "decision_id": "parity-decision",
            "decision_type": "PROPOSAL_CREATED",
            "research_cycle_id": "parity-research-cycle",
            "proposal_id": "parity-proposal",
            "model_version": "parity-model-challenger",
            "previous_model_version": "parity-model-accepted",
            "decision_status": "RECORDED",
            "reason_codes": ["parity"],
            "evidence_refs": [{"comparison_id": "parity-champion-comparison"}],
            "actor": "test",
            "metadata": {"secret_free": True},
        }
    )
    scheduler_job = repo.scheduler_jobs.save(
        {
            "job_id": "parity-scheduler-job",
            "job_type": "data_quality_report",
            "status": "QUEUED",
            "priority": 100,
            "payload": {"symbols": ["AAPL"]},
            "result": {},
            "warnings": [],
            "created_by": "test",
        }
    )
    scheduler_event = repo.scheduler_jobs.append_event(
        "parity-scheduler-job",
        "JOB_CREATED",
        "Parity scheduler event.",
        {"secret_free": True},
    )
    assert research_cycle["research_cycle_id"] == "parity-research-cycle"
    assert cycle_artifact["cycle_artifact_id"]
    assert champion_comparison["comparison_id"] == "parity-champion-comparison"
    assert proposal["proposal_id"] == "parity-proposal"
    assert decision["decision_id"] == "parity-decision"
    assert scheduler_job["job_id"] == "parity-scheduler-job"
    assert scheduler_event["event_id"]

    reopened = RepositoryRegistry(settings=get_settings())
    assert len(reopened.bars.list_all()) == 96
    assert len(reopened.features.list_all()) == 96
    assert len(reopened.candidate_signals.list_all()) == 4
    assert len(reopened.labels.list_all()) == 4
    assert reopened.model_runs.get("parity-model-accepted")["model_version"] == "parity-model-accepted"
    assert reopened.model_evidence_cells.count("parity-model-accepted") == 1
    assert reopened.candidate_score_audits.list("parity-model-accepted")[0]["score_id"] == "score-parity"
    assert reopened.model_calibration_audits.get("calibration-parity")["model_version"] == "parity-model-accepted"
    assert reopened.model_calibration_audits.list_bins("calibration-parity")
    assert reopened.model_comparisons.get(model_comparison["comparison_id"])["comparison_type"] == "model_comparison"
    assert reopened.replay_windows.get_set("parity-window-set")["status"] == "completed"
    assert reopened.replay_windows.list_results("parity-window-set")[0]["window_result_id"] == "parity-window-result"
    assert reopened.model_calibration_drift.get("parity-drift")["severity"] == "INFO"
    assert reopened.model_calibration_drift.list_windows("parity-drift")[0]["window_index"] == 1
    assert reopened.model_review_reports.get("parity-review")["readiness_status"] == "PASS"
    assert reopened.research_cycles.get("parity-research-cycle")["status"] == "COMPLETED"
    assert reopened.research_cycles.list_artifacts("parity-research-cycle")[0]["source_id"] == "parity-review"
    assert reopened.champion_challenger_comparisons.get("parity-champion-comparison")["readiness_status"] == "PASS"
    assert reopened.model_proposals.get("parity-proposal")["status"] == "PROPOSED"
    assert reopened.model_decision_ledger.list(proposal_id="parity-proposal")[0]["decision_id"] == "parity-decision"
    assert reopened.scheduler_jobs.get("parity-scheduler-job")["status"] == "QUEUED"
    assert reopened.scheduler_jobs.list_events("parity-scheduler-job")[0]["event_type"] == "JOB_CREATED"
    assert reopened.validation_reports.latest(model_version="parity-model-accepted")["activation_decision"] == "accepted"
    assert reopened.active_models.get_active()["model_version"] == "parity-model-accepted"
    assert reopened.scanner_runs.latest()["scanner_run_id"] == scanner_run_id
    assert len(reopened.live_signals.history()) == 1
    assert reopened.exports.list_all()[0]["export_id"] == export["export_id"]
    assert reopened.daily_reviews.get(date(2026, 6, 1))["review_id"] == review["review_id"]
    assert reopened.replays.get("parity-replay")["simulation_type"] == "candidate_market_replay"
    assert len(reopened.replays.list_trades("parity-replay")) == 2
    assert reopened.replay_sensitivity.get("parity-sensitivity")["pass_fail"] == "pass"  # noqa: S105
    assert len(reopened.replay_sensitivity.list_scenarios("parity-sensitivity")) == 1
    assert reopened.backtest_comparisons.get(comparison["comparison_id"])["comparison_type"] == "label_vs_replay"
    skipped_replay_trades = reopened.replays.list_trades("parity-replay", status="SKIPPED")
    assert skipped_replay_trades[0]["skip_reason"] == "missing_entry_bar"
    replay_builds = reopened.pipeline_windows.list_dirty("replay", symbols=["AAPL"], intervals=["1min"])
    assert all(row["artifact_type"] == "replay" for row in replay_builds)
    assert "apikey" not in str(reopened.provider_requests.list_all()).lower()


def test_backend_selection_contract(tmp_path, monkeypatch) -> None:
    settings = _settings_for_current_env(monkeypatch, tmp_path)
    sqlite_local = RepositoryRegistry(settings=settings)
    assert sqlite_local.info()["runtime_mode"] == "sqlite-local"

    sqlite_url = f"sqlite:///{tmp_path / 'configured.sqlite3'}"
    settings = _settings_for_current_env(monkeypatch, tmp_path, sqlite_url)
    sqlite_configured = RepositoryRegistry(settings=settings)
    assert sqlite_configured.info()["runtime_mode"] == "sqlite-configured"

    bad_postgres = f"postgresql+psycopg://{DEFAULT_POSTGRES_AUTH}@127.0.0.1:1/adaptive_market_decoder"
    settings = _settings_for_current_env(monkeypatch, tmp_path, bad_postgres)
    with pytest.raises(PersistenceConfigurationError):
        RepositoryRegistry(settings=settings)

    monkeypatch.setenv("AMD_ALLOW_SQLITE_FALLBACK", "true")
    get_settings.cache_clear()
    fallback = RepositoryRegistry(settings=get_settings())
    info = fallback.info()
    assert info["persistence_backend"] == "sqlite"
    assert info["runtime_mode"] == "sqlite-fallback-from-postgres"
    assert info["fallback_enabled"] is True
