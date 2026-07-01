from __future__ import annotations

from datetime import datetime, timedelta

from app.db.repositories import RepositoryRegistry
from app.models.replay_evidence import (
    REPLAY_AWARE_MODEL_TYPE,
    REPLAY_AWARE_VALIDATION_MODE,
    CandidateOutcomeDatasetBuilder,
    EvidenceCubeBuilder,
    ReplayAwareMetaScorer,
    summarize_outcome_rows,
)
from app.schemas.market import Side
from app.services.workflows import (
    ModelActivationService,
    ModelTrainingService,
    ReplayAwareScoringService,
    ValidationWorkflowService,
)
from app.utils.time import UTC


def _feature(bar, symbol: str | None = None, setup_type: str = "VWAP reclaim long") -> dict[str, object]:
    symbol = symbol or bar.symbol
    return {
        "feature_set_version": "test",
        "symbol": symbol,
        "interval": "1min",
        "timestamp": bar.timestamp_utc.isoformat(),
        "timestamp_utc": bar.timestamp_utc,
        "timestamp_et": bar.timestamp_et,
        "session_date": bar.timestamp_et.date().isoformat(),
        "market_regime": "trend_long",
        "ticker_regime": "single_stock_momentum",
        "time_bucket": "opening_drive",
        "relative_volume": 1.8,
        "leadership_score": 0.01,
        "distance_from_vwap": 0.005,
        "data_quality_flags": [],
        "setup_type": setup_type,
    }


def _candidate(bar, candidate_id: str, symbol: str = "AAPL", setup_type: str = "VWAP reclaim long") -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "symbol": symbol,
        "interval": "1min",
        "timestamp_utc": bar.timestamp_utc,
        "timestamp_et": bar.timestamp_et,
        "session_date": bar.timestamp_et.date().isoformat(),
        "side": Side.LONG.value,
        "setup_type": setup_type,
        "reason_codes": ["test"],
        "warning_codes": [],
        "entry_price": 100,
        "stop_price": 99,
        "target_1": 101,
        "target_2": 101.5,
        "target_3": 102.5,
    }


def _trade(
    bar,
    candidate_id: str,
    replay_run_id: str = "replay-aware-test",
    symbol: str = "AAPL",
    realized_r: float = 1.5,
    status: str = "TAKEN",
    skip_reason: str | None = None,
    setup_type: str = "VWAP reclaim long",
) -> dict[str, object]:
    payload: dict[str, object] = {
        "trade_id": f"trade-{candidate_id}",
        "replay_run_id": replay_run_id,
        "candidate_id": candidate_id,
        "symbol": symbol,
        "interval": "1min",
        "side": Side.LONG.value,
        "setup_type": setup_type,
        "signal_timestamp_utc": bar.timestamp_utc,
        "entry_timestamp_utc": bar.timestamp_utc + timedelta(minutes=1),
        "exit_timestamp_utc": bar.timestamp_utc + timedelta(minutes=5),
        "entry_price": 100,
        "stop_price": 99,
        "target_1": 101,
        "target_2": 101.5,
        "target_3": 102.5,
        "exit_price": 101.5 if realized_r > 0 else 99,
        "exit_reason": "target_2" if realized_r > 0 else "stop",
        "realized_r": realized_r,
        "mfe_r": max(realized_r, 0.0),
        "mae_r": min(realized_r, 0.0),
        "bars_held": 4,
        "minutes_held": 4,
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
        "metadata": {},
    }
    if status == "SKIPPED":
        payload.update(
            {
                "entry_timestamp_utc": None,
                "exit_timestamp_utc": None,
                "entry_price": None,
                "exit_price": None,
                "realized_r": 0.0,
                "mfe_r": 0.0,
                "mae_r": 0.0,
                "skip_reason": skip_reason,
            }
        )
    return payload


def _replay_run(replay_run_id: str, start: datetime, end: datetime, symbols: list[str] | None = None) -> dict[str, object]:
    return {
        "replay_run_id": replay_run_id,
        "simulation_type": "candidate_market_replay",
        "start": start.isoformat(),
        "end": end.isoformat(),
        "symbols": symbols or ["AAPL"],
        "intervals": ["1min"],
        "config": {"symbols": symbols or ["AAPL"], "intervals": ["1min"], "entry_mode": "next_bar_open"},
        "config_hash": f"hash-{replay_run_id}",
        "input_fingerprint": f"input-{replay_run_id}",
        "candidate_fingerprint": f"candidate-{replay_run_id}",
        "feature_set_version": "test",
        "candidate_config_version": "candidate_signals.v1",
        "stale_window_status": {"status": "clean", "stale_window_ids": []},
        "summary_metrics": {},
        "warnings": [],
        "created_at": datetime.now(UTC).isoformat(),
    }


def test_outcome_dataset_skipped_overlap_is_not_a_loss(make_bar) -> None:
    bar = make_bar(1, 100)
    replay = _replay_run("replay-aware-test", bar.timestamp_utc, bar.timestamp_utc + timedelta(minutes=30))
    trades = [
        _trade(bar, "candidate-taken", realized_r=1.5),
        _trade(make_bar(2, 100.1), "candidate-overlap", status="SKIPPED", skip_reason="overlapping_trade"),
    ]
    rows = CandidateOutcomeDatasetBuilder().build(
        replay_runs=[replay],
        trades_by_run={"replay-aware-test": trades},
        features=[_feature(bar), _feature(make_bar(2, 100.1))],
        candidates=[_candidate(bar, "candidate-taken"), _candidate(make_bar(2, 100.1), "candidate-overlap")],
        training_start=bar.timestamp_utc,
        training_end=bar.timestamp_utc + timedelta(minutes=30),
    )
    metrics = summarize_outcome_rows(rows, minimum_cell_sample_size=1)
    assert metrics["observed_outcome_count"] == 1
    assert metrics["skipped_count"] == 1
    assert metrics["average_r"] == 1.5
    skipped = [row for row in rows if row["status"] == "SKIPPED"][0]
    assert skipped["not_observed_outcome"] is True


def test_evidence_shrinkage_suppresses_tiny_edge_against_bad_parent(make_bar) -> None:
    rows = []
    good_bar = make_bar(1, 100, symbol="AAPL")
    rows.append(
        {
            **_trade(good_bar, "candidate-good", symbol="AAPL", realized_r=2.0),
            "observed_outcome": True,
            "not_observed_outcome": False,
            "sensitivity_robustness_score": 1.0,
            "sensitivity_fragility_flags": [],
            "label_vs_replay_divergence_flags": [],
            "stale_window_status": {"status": "clean"},
            "data_quality_flags": [],
        }
    )
    for index in range(10):
        bar = make_bar(index + 2, 100, symbol="MSFT")
        rows.append(
            {
                **_trade(bar, f"candidate-bad-{index}", symbol="MSFT", realized_r=-1.0),
                "observed_outcome": True,
                "not_observed_outcome": False,
                "sensitivity_robustness_score": 1.0,
                "sensitivity_fragility_flags": [],
                "label_vs_replay_divergence_flags": [],
                "stale_window_status": {"status": "clean"},
                "data_quality_flags": [],
            }
        )
    cube = EvidenceCubeBuilder().build(rows, minimum_cell_sample_size=1)
    scorer = ReplayAwareMetaScorer(
        cube,
        {
            "minimum_observed_outcomes": 1,
            "minimum_cell_sample_size": 1,
            "shrinkage_strength": 20,
            "minimum_profit_factor": 1.0,
        },
    )
    score = scorer.score(_candidate(good_bar, "candidate-good"), _feature(good_bar), model_version="test")
    assert score["action"] == "SUPPRESS"
    assert "negative_expectancy_after_shrinkage" in score["suppression_reasons"]


def test_replay_aware_training_persists_evidence_and_scores_candidate(tmp_path, make_bar) -> None:
    repo = RepositoryRegistry(db_path=tmp_path / "replay-aware.sqlite3")
    bars = [make_bar(index, 100 + index * 0.1) for index in range(8)]
    repo.features.upsert_many([_feature(bar) for bar in bars])
    repo.candidate_signals.upsert_many([_candidate(bar, f"candidate-{index}") for index, bar in enumerate(bars[:6])])
    replay = _replay_run("replay-aware-train", bars[0].timestamp_utc, bars[-1].timestamp_utc)
    trades = [_trade(bar, f"candidate-{index}", realized_r=1.5) for index, bar in enumerate(bars[:6])]
    repo.replays.save(replay, trades)
    repo.replay_sensitivity.save(
        {
            "sensitivity_run_id": "sensitivity-replay-aware-train",
            "replay_run_id": "replay-aware-train",
            "config": {},
            "scenario_count": 1,
            "passed_scenario_count": 1,
            "failed_scenario_count": 0,
            "robustness_score": 1.0,
            "pass_fail": "pass",
            "fragility_flags": [],
            "gate_results": {"robustness_score_met": True},
            "scenarios": [],
        }
    )

    model = ModelTrainingService(repo).train(
        ["AAPL"],
        bars[0].timestamp_utc,
        bars[-1].timestamp_utc,
        min_samples=1,
        model_type=REPLAY_AWARE_MODEL_TYPE,
        replay_run_ids=["replay-aware-train"],
        minimum_observed_outcomes=1,
        minimum_cell_sample_size=1,
        scoring_config={"take_score_threshold": 50},
    )
    assert model["trained"] is True
    assert model["model_type"] == REPLAY_AWARE_MODEL_TYPE
    assert repo.model_evidence_cells.count(model["model_version"]) > 0

    score = ReplayAwareScoringService(repo).score_candidates(
        model["model_version"],
        candidates=[_candidate(bars[1], "candidate-live")],
    )
    assert score["status"] == "ok"
    assert repo.candidate_score_audits.list(model["model_version"])


def test_replay_aware_validation_gate_required_for_activation(tmp_path, make_bar) -> None:
    repo = RepositoryRegistry(db_path=tmp_path / "replay-aware-validation.sqlite3")
    bars = [make_bar(index, 100 + index * 0.1) for index in range(12)]
    repo.features.upsert_many([_feature(bar) for bar in bars])
    repo.candidate_signals.upsert_many([_candidate(bar, f"candidate-{index}") for index, bar in enumerate(bars)])
    replay = _replay_run("replay-aware-validation", bars[0].timestamp_utc, bars[-1].timestamp_utc)
    trades = [_trade(bar, f"candidate-{index}", realized_r=1.5) for index, bar in enumerate(bars)]
    repo.replays.save(replay, trades)

    model = ModelTrainingService(repo).train(
        ["AAPL"],
        bars[0].timestamp_utc,
        bars[-1].timestamp_utc,
        min_samples=1,
        model_type=REPLAY_AWARE_MODEL_TYPE,
        replay_run_ids=["replay-aware-validation"],
        minimum_observed_outcomes=1,
        minimum_cell_sample_size=1,
        scoring_config={"take_score_threshold": 50},
        activation_criteria={
            "minimum_selected_trades": 1,
            "minimum_profit_factor": 1.0,
            "maximum_symbol_profit_share": 1.0,
            "maximum_setup_profit_share": 1.0,
        },
    )
    wrong_mode = ModelActivationService(repo).activate(model["model_version"])
    assert wrong_mode["activated"] is False
    assert wrong_mode["reason"] == "replay_aware_validation_required"

    report = ValidationWorkflowService(repo).validate(
        model_version=model["model_version"],
        validation_mode=REPLAY_AWARE_VALIDATION_MODE,
    )
    assert report["validation_mode"] == REPLAY_AWARE_VALIDATION_MODE
    assert report["activation_decision"] == "accepted"
    activated = ModelActivationService(repo).activate(
        model["model_version"],
        validation_mode=REPLAY_AWARE_VALIDATION_MODE,
    )
    assert activated["activated"] is True
