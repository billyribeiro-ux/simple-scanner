from __future__ import annotations

from datetime import datetime, timedelta

from app.backtesting.replay import (
    REPLAY_PURPOSE_COUNTERFACTUAL,
    SIMULATION_TYPE_COUNTERFACTUAL,
    CandidateMarketReplayEngine,
    ReplayConfig,
)
from app.db.repositories import RepositoryRegistry
from app.models.calibration_audit import ScoreCalibrationAuditEngine
from app.models.replay_evidence import (
    REPLAY_AWARE_MODEL_TYPE,
    REPLAY_AWARE_VALIDATION_MODE,
    CandidateOutcomeDatasetBuilder,
)
from app.schemas.market import Side
from app.services.workflows import ModelActivationService
from app.utils.time import UTC


def _candidate(bar, candidate_id: str, confidence: float = 0.8) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "symbol": bar.symbol,
        "interval": bar.interval,
        "timestamp_utc": bar.timestamp_utc,
        "side": Side.LONG.value,
        "setup_type": "VWAP reclaim long",
        "entry_price": 100.2,
        "stop_price": 99.0,
        "target_1": 101.0,
        "target_2": 101.5,
        "target_3": 102.5,
        "entry_context": {"vwap": 100.0, "atr_14": 1.0},
        "invalidation_context": {"opening_range_low": 99.0},
        "confidence_score": confidence,
        "expected_r": 0.4,
    }


def _feature(bar) -> dict[str, object]:
    return {
        "symbol": bar.symbol,
        "interval": bar.interval,
        "timestamp": bar.timestamp_utc.isoformat(),
        "timestamp_utc": bar.timestamp_utc,
        "timestamp_et": bar.timestamp_et,
        "feature_set_version": "test",
        "market_regime": "trend_long",
        "time_bucket": "opening_drive",
        "atr_14": 1.0,
        "data_quality_flags": [],
    }


def _replay_run(run_id: str, simulation_type: str, start: datetime, end: datetime) -> dict[str, object]:
    replay_purpose = REPLAY_PURPOSE_COUNTERFACTUAL if simulation_type == SIMULATION_TYPE_COUNTERFACTUAL else "portfolio_execution"
    return {
        "replay_run_id": run_id,
        "simulation_type": simulation_type,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "symbols": ["AAPL"],
        "intervals": ["1min"],
        "config": {"replay_purpose": replay_purpose, "symbols": ["AAPL"], "intervals": ["1min"]},
        "stale_window_status": {"status": "clean", "stale_window_ids": []},
        "summary_metrics": {},
        "created_at": datetime.now(UTC).isoformat(),
    }


def _trade(candidate_id: str, run_id: str, timestamp: datetime, realized_r: float, simulation_type: str, status: str = "TAKEN", skip_reason: str | None = None) -> dict[str, object]:
    is_counterfactual = simulation_type == SIMULATION_TYPE_COUNTERFACTUAL
    return {
        "trade_id": f"trade-{run_id}-{candidate_id}",
        "replay_run_id": run_id,
        "candidate_id": candidate_id,
        "symbol": "AAPL",
        "interval": "1min",
        "side": Side.LONG.value,
        "setup_type": "VWAP reclaim long",
        "signal_timestamp_utc": timestamp,
        "entry_timestamp_utc": timestamp + timedelta(minutes=1) if status == "TAKEN" else None,
        "exit_timestamp_utc": timestamp + timedelta(minutes=4) if status == "TAKEN" else None,
        "entry_price": 100.0 if status == "TAKEN" else None,
        "stop_price": 99.0 if status == "TAKEN" else None,
        "target_1": 101.0 if status == "TAKEN" else None,
        "target_2": 101.5 if status == "TAKEN" else None,
        "target_3": 102.5 if status == "TAKEN" else None,
        "exit_price": 101.5 if status == "TAKEN" and realized_r > 0 else None,
        "exit_reason": "target_2" if status == "TAKEN" and realized_r > 0 else None,
        "realized_r": realized_r if status == "TAKEN" else 0.0,
        "mfe_r": max(realized_r, 0.0) if status == "TAKEN" else 0.0,
        "mae_r": min(realized_r, 0.0) if status == "TAKEN" else 0.0,
        "bars_held": 4 if status == "TAKEN" else 0,
        "minutes_held": 4 if status == "TAKEN" else 0,
        "same_bar_ambiguous": False,
        "ambiguity_policy": None,
        "slippage_bps": 0,
        "spread_bps": 0,
        "commission": 0,
        "market_regime": "trend_long",
        "time_bucket": "opening_drive",
        "signal_score": 0.8,
        "expected_r": 0.4,
        "status": status,
        "skip_reason": skip_reason,
        "metadata": {
            "replay_purpose": REPLAY_PURPOSE_COUNTERFACTUAL if is_counterfactual else "portfolio_execution",
            "counterfactual_observed": is_counterfactual and status == "TAKEN",
            "concurrency_bucket": "pair",
            "overlap_density": 1,
        },
    }


def test_counterfactual_replay_observes_overlapping_candidates(make_bar) -> None:
    bars = [make_bar(index, 100.2, high=100.4, low=100.0) for index in range(8)]
    candidates = [_candidate(bars[1], "candidate-1"), _candidate(bars[2], "candidate-2")]
    features = [_feature(bars[1]), _feature(bars[2])]

    portfolio = CandidateMarketReplayEngine().replay(
        bars,
        features,
        candidates,
        ReplayConfig(symbols=("AAPL",), intervals=("1min",), max_hold_minutes=4),
    )
    counterfactual = CandidateMarketReplayEngine().replay(
        bars,
        features,
        candidates,
        ReplayConfig.from_payload(
            {
                "symbols": ["AAPL"],
                "intervals": ["1min"],
                "max_hold_minutes": 4,
                "replay_purpose": REPLAY_PURPOSE_COUNTERFACTUAL,
            }
        ),
    )

    assert len([trade for trade in portfolio.trades if trade.status == "TAKEN"]) == 1
    assert "overlapping_trade" in {trade.skip_reason for trade in portfolio.trades if trade.status == "SKIPPED"}
    assert len([trade for trade in counterfactual.trades if trade.status == "TAKEN"]) == 2
    assert counterfactual.simulation_type == SIMULATION_TYPE_COUNTERFACTUAL
    assert counterfactual.metrics["candidate_quality_mode"] is True
    assert counterfactual.metrics["is_portfolio_pnl"] is False
    assert all(trade.metadata["counterfactual_observed"] for trade in counterfactual.trades if trade.status == "TAKEN")


def test_dataset_prefers_counterfactual_and_recovers_portfolio_overlap(make_bar) -> None:
    bar = make_bar(1, 100)
    cf_run = _replay_run("cf-run", SIMULATION_TYPE_COUNTERFACTUAL, bar.timestamp_utc, bar.timestamp_utc + timedelta(minutes=10))
    pf_run = _replay_run("pf-run", "candidate_market_replay", bar.timestamp_utc, bar.timestamp_utc + timedelta(minutes=10))
    rows = CandidateOutcomeDatasetBuilder().build(
        replay_runs=[cf_run, pf_run],
        trades_by_run={
            "cf-run": [_trade("candidate-1", "cf-run", bar.timestamp_utc, 1.5, SIMULATION_TYPE_COUNTERFACTUAL)],
            "pf-run": [_trade("candidate-1", "pf-run", bar.timestamp_utc, 0.0, "candidate_market_replay", status="SKIPPED", skip_reason="overlapping_trade")],
        },
        features=[_feature(bar)],
        candidates=[_candidate(bar, "candidate-1")],
        outcome_source="counterfactual_preferred",
    )
    assert len(rows) == 1
    assert rows[0]["candidate_quality_source"] == "counterfactual"
    assert rows[0]["candidate_quality_outcome_available"] is True
    assert rows[0]["portfolio_execution_outcome_available"] is False
    assert rows[0]["portfolio_constraint_skip_reason"] == "overlapping_trade"
    assert rows[0]["counterfactual_realized_r"] == 1.5


def test_calibration_audit_monotonic_and_inverted_warnings() -> None:
    outcomes = [
        {"candidate_id": "c1", "observed_outcome": True, "counterfactual_realized_r": -1.0, "symbol": "AAPL", "setup_type": "VWAP", "market_regime": "trend_long", "time_bucket": "open"},
        {"candidate_id": "c2", "observed_outcome": True, "counterfactual_realized_r": 0.2, "symbol": "AAPL", "setup_type": "VWAP", "market_regime": "trend_long", "time_bucket": "open"},
        {"candidate_id": "c3", "observed_outcome": True, "counterfactual_realized_r": 1.5, "symbol": "AAPL", "setup_type": "VWAP", "market_regime": "trend_long", "time_bucket": "open"},
    ]
    good_scores = [
        {"score_id": "s1", "model_version": "m", "candidate_id": "c1", "symbol": "AAPL", "timestamp_utc": "t1", "side": "LONG", "setup_type": "VWAP", "signal_quality_score": 10, "grade": "NO_TRADE", "action": "SUPPRESS"},
        {"score_id": "s2", "model_version": "m", "candidate_id": "c2", "symbol": "AAPL", "timestamp_utc": "t2", "side": "LONG", "setup_type": "VWAP", "signal_quality_score": 65, "grade": "B", "action": "WATCH"},
        {"score_id": "s3", "model_version": "m", "candidate_id": "c3", "symbol": "AAPL", "timestamp_utc": "t3", "side": "LONG", "setup_type": "VWAP", "signal_quality_score": 90, "grade": "A", "action": "TAKE"},
    ]
    good = ScoreCalibrationAuditEngine().run(model_version="m", score_audits=good_scores, outcome_rows=outcomes)
    assert good["monotonicity_pass"] is True
    assert good["rank_correlation_score"] > 0

    bad_scores = [
        {**good_scores[0], "signal_quality_score": 90, "grade": "A", "action": "TAKE"},
        good_scores[1],
        {**good_scores[2], "signal_quality_score": 10, "grade": "NO_TRADE", "action": "SUPPRESS"},
    ]
    inverted = ScoreCalibrationAuditEngine().run(
        model_version="m",
        score_audits=bad_scores,
        outcome_rows=outcomes,
        config={"require_monotonic_score_bins": True, "require_take_outperforms_watch": True, "minimum_high_grade_samples": 1},
    )
    assert inverted["monotonicity_pass"] is False
    assert "score_bins_not_monotonic" in inverted["rejection_reasons"]
    assert "high_score_negative_expectancy" in inverted["calibration_warnings"]


def test_activation_calibration_required_missing_then_passing(tmp_path) -> None:
    repo = RepositoryRegistry(db_path=tmp_path / "phase9.sqlite3")
    model = {
        "trained": True,
        "model_version": "phase9-model",
        "model_type": REPLAY_AWARE_MODEL_TYPE,
        "activation_decision": "rejected",
        "active": False,
        "metrics": {},
        "validation_metrics": {},
        "activation_criteria": {"calibration_audit_required": True},
        "created_at": datetime.now(UTC).isoformat(),
    }
    repo.model_runs.save(model)
    repo.validation_reports.save(
        {
            "model_version": "phase9-model",
            "validation_mode": REPLAY_AWARE_VALIDATION_MODE,
            "summary": {},
            "windows": [],
            "activation_decision": "accepted",
            "rejection_reasons": [],
            "created_at": datetime.now(UTC).isoformat(),
        },
        model_version="phase9-model",
        purpose="replay_aware_validation",
    )
    missing = ModelActivationService(repo).activate("phase9-model", validation_mode=REPLAY_AWARE_VALIDATION_MODE)
    assert missing["activated"] is False
    assert missing["calibration"]["status"] == "failed"

    repo.model_calibration_audits.save(
        {
            "calibration_audit_id": "calibration-pass",
            "model_version": "phase9-model",
            "replay_run_ids": [],
            "outcome_source": "counterfactual_only",
            "score_bins": [{"bin_key": "85-100", "sample_size": 5, "observed_average_r": 1.0}],
            "grade_bins": [{"bin_key": "A", "sample_size": 5, "observed_average_r": 1.0}],
            "action_bins": [{"bin_key": "TAKE", "sample_size": 5, "observed_average_r": 1.0}],
            "rank_correlation_score": 0.8,
            "monotonicity_pass": True,
            "separation_metrics": {"take_minus_watch_average_r": 1.0},
            "stability_metrics": {},
            "calibration_warnings": [],
            "rejection_reasons": [],
            "created_at": datetime.now(UTC).isoformat(),
        }
    )
    activated = ModelActivationService(repo).activate("phase9-model", validation_mode=REPLAY_AWARE_VALIDATION_MODE)
    assert activated["activated"] is True
    assert activated["calibration"]["status"] == "passed"
