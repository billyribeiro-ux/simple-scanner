# Phase 21R Evidence DB Audit - 2026-07-04

`PHASE_21R_EVIDENCE_DB_STATUS = CONTAMINATED`

This audit inspected the current runtime Postgres evidence database after the Phase 21R test-isolation repair and verification pass. The database was not deleted, reset, or treated as clean evidence.

## Evidence Database Identity

- Database: `adaptive_market_decoder`
- Host: `localhost`
- Port: `15432`
- Role: `evidence`
- Alembic revision: `0012_phase16_fmp_freshness`
- Missing tables: `none`
- Total rows: `2609`
- Fixture-like rows: `29`

## Evidence Table Counts

| Table | Rows | Fixture Rows | Live Rows |
|---|---:|---:|---:|
| `active_models` | 1 | 0 | 1 |
| `alembic_version` | 1 | 0 | 1 |
| `backtest_comparisons` | 1 | 1 | 0 |
| `bars` | 480 | 0 | 480 |
| `candidate_score_audits` | 1 | 1 | 0 |
| `candidate_signals` | 1256 | 0 | 1256 |
| `champion_challenger_comparisons` | 1 | 1 | 0 |
| `closed_signals` | 0 | 0 | 0 |
| `daily_reviews` | 1 | 0 | 1 |
| `data_freshness_reports` | 0 | 0 | 0 |
| `exports` | 1 | 0 | 1 |
| `features` | 576 | 0 | 576 |
| `ingestion_runs` | 1 | 0 | 1 |
| `labels` | 224 | 0 | 224 |
| `live_signals` | 1 | 1 | 0 |
| `model_artifacts` | 3 | 1 | 2 |
| `model_calibration_audits` | 1 | 1 | 0 |
| `model_calibration_bins` | 3 | 0 | 3 |
| `model_calibration_drift_reports` | 1 | 1 | 0 |
| `model_calibration_drift_windows` | 1 | 1 | 0 |
| `model_comparisons` | 1 | 1 | 0 |
| `model_decision_ledger` | 1 | 1 | 0 |
| `model_evidence_cells` | 1 | 1 | 0 |
| `model_proposals` | 1 | 1 | 0 |
| `model_review_reports` | 1 | 1 | 0 |
| `model_runs` | 3 | 1 | 2 |
| `pipeline_build_windows` | 16 | 0 | 16 |
| `provider_capability_checks` | 1 | 0 | 1 |
| `provider_requests` | 5 | 0 | 5 |
| `quote_snapshots` | 0 | 0 | 0 |
| `replay_runs` | 1 | 1 | 0 |
| `replay_sensitivity_runs` | 1 | 1 | 0 |
| `replay_sensitivity_scenarios` | 1 | 1 | 0 |
| `replay_window_results` | 1 | 1 | 0 |
| `replay_window_sets` | 1 | 1 | 0 |
| `research_cycle_artifacts` | 1 | 1 | 0 |
| `research_cycles` | 1 | 1 | 0 |
| `scanner_runs` | 1 | 1 | 0 |
| `scheduler_job_events` | 1 | 1 | 0 |
| `scheduler_jobs` | 2 | 2 | 0 |
| `simulated_trades` | 2 | 2 | 0 |
| `symbols` | 4 | 0 | 4 |
| `validation_reports` | 7 | 2 | 5 |
| `validation_windows` | 1 | 0 | 1 |

## Fixture Evidence

The audit found fixture-like IDs and references in governance, replay, model review, scheduler, scanner, and validation tables, including:

- `parity-replay`
- `parity-model-accepted`
- `parity-review`
- `parity-research-cycle`
- `parity-proposal`
- `parity-decision`
- `parity-scheduler-job`
- `parity-scheduler-worker-job`
- `parity-window-set`
- `parity-window-result`
- `parity-sensitivity`
- `parity-scenario`

These rows are sufficient to disqualify the current default Postgres database as clean Phase 20 or Phase 21 certification evidence.

## Test Database Cross-Check

The isolated Postgres test database was also audited after the repaired regression runs.

- Database: `adaptive_market_decoder_test`
- Role: `test`
- Alembic revision: `0012_phase16_fmp_freshness`
- Total rows: `275`
- Fixture-like rows: `31`

Fixture rows in `adaptive_market_decoder_test` are expected because mutating parity and API smoke tests now target the test database by default. They are not evidence-store contamination.

## Conclusion

The evidence database remains preserved but contaminated. It must not be used to certify Phase 20, Phase 21, or any model activation decision until restored from a clean source or regenerated from live runtime data under the evidence role.
