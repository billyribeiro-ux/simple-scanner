from __future__ import annotations

from app.backtesting.audit import replay_config_hash, replay_input_fingerprint, stable_json
from app.backtesting.replay import CandidateMarketReplayEngine, ReplayConfig
from app.backtesting.sensitivity import ReplaySensitivityEngine, SensitivityConfig
from app.db.repositories import RepositoryRegistry
from app.schemas.market import Side
from app.services.workflows import BacktestService, ValidationWorkflowService


def _candidate(bar, confidence: float = 0.8) -> dict[str, object]:
    return {
        "candidate_id": f"candidate-{bar.symbol}-{bar.timestamp_utc.isoformat()}",
        "symbol": bar.symbol,
        "interval": bar.interval,
        "timestamp_utc": bar.timestamp_utc,
        "side": Side.LONG.value,
        "setup_type": "VWAP reclaim long",
        "entry_context": {"vwap": 100.0, "atr_14": 1.0, "time_bucket": "opening_drive"},
        "invalidation_context": {"opening_range_low": 100.0, "premarket_low": 99.5},
        "reason_codes": ["test"],
        "warning_codes": [],
        "confidence_score": confidence,
        "expected_r": confidence * 0.5,
    }


def _feature(bar) -> dict[str, object]:
    return {
        "feature_set_version": "test",
        "symbol": bar.symbol,
        "interval": bar.interval,
        "timestamp": bar.timestamp_utc.isoformat(),
        "timestamp_utc": bar.timestamp_utc,
        "timestamp_et": bar.timestamp_et,
        "session_date": bar.timestamp_et.date().isoformat(),
        "close": bar.close,
        "vwap": 100.0,
        "atr_14": 1.0,
        "atr_14_proxy": 1.0,
        "market_regime": "trend_long",
        "time_bucket": "opening_drive",
        "data_quality_flags": [],
    }


def _bars(make_bar):
    return [
        make_bar(0, 100),
        make_bar(1, 100.5),
        make_bar(2, 101, open_=101, high=101.1, low=100.9),
        make_bar(3, 102.7, high=102.8, low=102.0),
        make_bar(4, 102.9, high=103.0, low=102.5),
    ]


def test_replay_hashes_are_stable_and_scrub_secret_values(make_bar) -> None:
    bars = _bars(make_bar)
    features = [_feature(bars[1])]
    candidates = [_candidate(bars[1]) | {"fmp_api_key": "test-secret-value"}]
    config = ReplayConfig(symbols=("AAPL",), intervals=("1min",), start=bars[0].timestamp_utc, end=bars[-1].timestamp_utc)

    config_hash_1 = replay_config_hash(config.to_dict())
    config_hash_2 = replay_config_hash(config.to_dict())
    input_hash_1 = replay_input_fingerprint(bars, features, candidates, config.to_dict())
    input_hash_2 = replay_input_fingerprint(bars, features, candidates, config.to_dict())

    assert config_hash_1 == config_hash_2
    assert input_hash_1 == input_hash_2
    assert "test-secret-value" not in stable_json(candidates)
    assert "[redacted]" in stable_json(candidates)


def test_replay_sensitivity_grid_reports_cases_and_fragility(make_bar) -> None:
    bars = _bars(make_bar)
    candidates = [_candidate(bars[1])]
    features = [_feature(bars[1])]
    config = ReplayConfig(symbols=("AAPL",), intervals=("1min",), start=bars[0].timestamp_utc, end=bars[-1].timestamp_utc)
    base = CandidateMarketReplayEngine().replay(bars, features, candidates, config, replay_run_id="replay-test")

    sensitivity = ReplaySensitivityEngine().run(
        base.replay_run_id,
        bars,
        features,
        candidates,
        config,
        SensitivityConfig(
            slippage_bps_grid=(0.0, 1.0),
            spread_bps_grid=(0.0, 2.0),
            intrabar_path_policies=("conservative",),
            minimum_total_trades=1,
            minimum_robustness_score=0.0,
        ),
    )

    assert sensitivity["scenario_count"] == 4
    assert sensitivity["coverage_mode"] == "FULL_GRID"
    assert sensitivity["completion_status"] == "BOUNDED_COMPLETE"
    assert sensitivity["configured_grid_complete"] is True
    assert sensitivity["full_default_grid_complete"] is False
    assert sensitivity["partial_grid_disclosure"] is True
    assert "bounded_sensitivity_not_full_default_grid" in sensitivity["coverage_warnings"]
    assert sensitivity["worst_case"]["scenario_id"]
    assert sensitivity["median_case"]["scenario_id"]
    assert sensitivity["best_case"]["scenario_id"]
    assert 0 <= sensitivity["robustness_score"] <= 1
    assert all("summary_metrics" in scenario for scenario in sensitivity["scenarios"])


def test_replay_sensitivity_records_partial_scenario_limits(make_bar) -> None:
    bars = _bars(make_bar)
    candidates = [_candidate(bars[1])]
    features = [_feature(bars[1])]
    config = ReplayConfig(symbols=("AAPL",), intervals=("1min",), start=bars[0].timestamp_utc, end=bars[-1].timestamp_utc)
    base = CandidateMarketReplayEngine().replay(bars, features, candidates, config, replay_run_id="replay-test")

    sensitivity = ReplaySensitivityEngine().run(
        base.replay_run_id,
        bars,
        features,
        candidates,
        config,
        SensitivityConfig(max_scenarios=1, minimum_total_trades=1, minimum_robustness_score=0.0),
    )

    assert sensitivity["completion_status"] == "PARTIAL"
    assert sensitivity["planned_scenario_count"] == 75
    assert sensitivity["completed_scenario_count"] == 1
    assert sensitivity["remaining_scenario_count"] == 74
    assert sensitivity["partial_reason"] == "max_scenarios_limited"
    assert sensitivity["configured_grid_complete"] is False
    assert sensitivity["partial_grid_disclosure"] is True
    assert sensitivity["gate_results"]["configured_grid_complete"] is False
    assert sensitivity["pass_fail"] == "fail"  # noqa: S105 - sensitivity status, not a password.


def test_chunked_full_grid_sensitivity_resumes_without_duplicate_scenarios(tmp_path, make_bar) -> None:
    repo = RepositoryRegistry(db_path=tmp_path / "chunked-sensitivity.sqlite3")
    bars = _bars(make_bar)
    features = [_feature(bars[1])]
    candidate = _candidate(bars[1])
    repo.bars.upsert_many(bars)
    repo.features.upsert_many(features)
    repo.candidate_signals.upsert_many([candidate])
    repo.pipeline_windows.mark_built("features", ["AAPL"], ["1min"], bars[0].timestamp_utc, bars[-1].timestamp_utc, "features.v2.no_leakage")
    repo.pipeline_windows.mark_built("candidates", ["AAPL"], ["1min"], bars[0].timestamp_utc, bars[-1].timestamp_utc, "candidate_signals.v1")

    service = BacktestService(repo)
    replay = service.run_replay(
        {
            "symbols": ["AAPL"],
            "intervals": ["1min"],
            "start": bars[0].timestamp_utc.isoformat(),
            "end": bars[-1].timestamp_utc.isoformat(),
            "minimum_reward_risk": 0.5,
        }
    )
    first = service.run_sensitivity(
        replay["replay_run_id"],
        {
            "coverage_mode": "CHUNKED_FULL_GRID",
            "max_scenarios_per_invocation": 2,
            "minimum_total_trades": 1,
            "full_default_grid_required": True,
        },
    )

    assert first["completion_status"] == "PARTIAL"
    assert first["planned_scenario_count"] == 75
    assert first["completed_scenario_count"] == 2
    assert first["remaining_scenario_count"] == 73
    assert first["partial_grid_disclosure"] is True
    assert first["activation_grade_sensitivity"] is False
    assert first["sensitivity_classification"] == "diagnostic"
    assert first["resume_token"]
    assert first["next_scenario_index"] == 3

    second = service.run_sensitivity(
        replay["replay_run_id"],
        {
            "sensitivity_run_id": first["sensitivity_run_id"],
            "max_scenarios_per_invocation": 2,
        },
    )
    scenarios = repo.replay_sensitivity.list_scenarios(first["sensitivity_run_id"])
    scenario_ids = [scenario["scenario_id"] for scenario in scenarios]

    assert second["sensitivity_run_id"] == first["sensitivity_run_id"]
    assert second["completed_scenario_count"] == 4
    assert second["remaining_scenario_count"] == 71
    assert len(scenario_ids) == len(set(scenario_ids)) == 4

    final = service.run_sensitivity(
        replay["replay_run_id"],
        {
            "sensitivity_run_id": first["sensitivity_run_id"],
            "max_scenarios_per_invocation": 100,
        },
    )
    final_scenarios = repo.replay_sensitivity.list_scenarios(first["sensitivity_run_id"])
    final_ids = [scenario["scenario_id"] for scenario in final_scenarios]

    assert final["completion_status"] == "COMPLETE"
    assert final["completed_scenario_count"] == 75
    assert final["remaining_scenario_count"] == 0
    assert final["full_default_grid_complete"] is True
    assert final["activation_grade_sensitivity"] is True
    assert final["sensitivity_classification"] == "activation_grade"
    assert final["grid_version"]
    assert final["grid_hash"]
    assert len(final_ids) == len(set(final_ids)) == 75


def test_replay_workflow_blocks_stale_inputs_and_requires_explicit_validation_selection(tmp_path, make_bar) -> None:
    repo = RepositoryRegistry(db_path=tmp_path / "phase7.sqlite3")
    bars = _bars(make_bar)
    features = [_feature(bars[1])]
    candidate = _candidate(bars[1])
    repo.bars.upsert_many(bars)
    repo.features.upsert_many(features)
    repo.candidate_signals.upsert_many([candidate])

    payload = {
        "symbols": ["AAPL"],
        "intervals": ["1min"],
        "start": bars[0].timestamp_utc.isoformat(),
        "end": bars[-1].timestamp_utc.isoformat(),
        "minimum_reward_risk": 0.5,
    }
    blocked = BacktestService(repo).run_replay(payload)
    assert blocked["status"] == "error"
    assert blocked["reason"] == "stale_replay_inputs"

    repo.pipeline_windows.mark_built("features", ["AAPL"], ["1min"], bars[0].timestamp_utc, bars[-1].timestamp_utc, "features.v2.no_leakage")
    repo.pipeline_windows.mark_built("candidates", ["AAPL"], ["1min"], bars[0].timestamp_utc, bars[-1].timestamp_utc, "candidate_signals.v1")
    replay = BacktestService(repo).run_replay(payload)
    assert replay["simulation_type"] == "candidate_market_replay"
    assert replay["config_hash"]
    assert replay["input_fingerprint"]
    assert replay["candidate_fingerprint"]
    assert replay["stale_window_status"]["status"] == "clean"

    rejected = ValidationWorkflowService(repo).validate(validation_mode="candidate_market_replay")
    assert rejected["activation_decision"] == "rejected"
    assert "replay_run_selection_required" in rejected["rejection_reasons"]

    selected = ValidationWorkflowService(repo).validate(
        validation_mode="candidate_market_replay",
        replay_run_id=replay["replay_run_id"],
    )
    assert selected["replay_run_id"] == replay["replay_run_id"]
    assert selected["replay_run_selection"]["reason"] == "explicit_replay_run_id"
