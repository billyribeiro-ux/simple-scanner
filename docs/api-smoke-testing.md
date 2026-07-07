# API Smoke Testing

Status date: 2026-07-04

## Command

```bash
make api-smoke
make api-smoke-sqlite
make api-smoke-postgres
```

The default smoke is SQLite:

```bash
cd services/quant-engine && PYTHONPATH=. .venv/bin/python -m pytest tests/test_persisted_api_smoke.py::test_persisted_api_vertical_slice_sqlite
```

The Postgres smoke uses the isolated test database `adaptive_market_decoder_test` on local compose port `15432` unless `TEST_DATABASE_URL` is supplied.

Phase 14 verification on 2026-07-02 ran `make api-smoke-postgres` successfully against Alembic head `0010_phase14_scheduler_worker`. Phase 21R verification on 2026-07-04 ran `make api-smoke-postgres` against isolated test DB Alembic head `0012_phase16_fmp_freshness`.

## Design

The smoke test uses FastAPI `TestClient`, temporary export/model directories, and a mocked FMP provider. The SQLite path uses a temporary SQLite repository. The Postgres path uses the migrated local compose Postgres/TimescaleDB test database and clears test data between runs. It does not require internet, live FMP, or secrets.

The test sets a non-secret sentinel `FMP_API_KEY` only to exercise scanner gating. It verifies the sentinel is absent from SQLite files, exported CSV/XLSX/JSON files, active model artifacts, and persisted provider metadata.

## Phase 21R Isolation Requirement

`make api-smoke-postgres` must not write fixtures to the evidence database. It now prepares the test DB with `make test-db-smoke`, then runs with:

- `DATABASE_URL=$TEST_DATABASE_URL`
- `TEST_DATABASE_URL` set to the isolated Postgres test DB
- `AMD_DB_ROLE=test`

Evidence-mode writes reject fixture-like IDs by default. Run `make evidence-guard-test` to verify the guard and `make evidence-db-audit` to confirm the evidence DB did not gain new fixture rows.

## Route Coverage

- `GET /health`
- `GET /config`
- `POST /data/ingest`
- `GET /data/bars`
- `GET /data/quality-report`
- `GET /data/quotes/latest`
- `POST /features/build`
- `POST /labels/build`
- `POST /models/train`
- `GET /models/{model_version}/evidence`
- `POST /models/{model_version}/score-candidates`
- `GET /models/{model_version}/score-audits`
- `POST /models/{model_version}/calibration-drift`
- `GET /models/{model_version}/calibration-drift`
- `GET /models/calibration-drift/{drift_report_id}`
- `GET /models/calibration-drift/{drift_report_id}/windows`
- `POST /models/{model_version}/review-report`
- `GET /models/{model_version}/review-reports`
- `GET /models/review-reports/{review_report_id}`
- `POST /models/validate`
- `POST /models/activate`
- `GET /models`
- `GET /models/{model_version}`
- `POST /backtest/run`
- `POST /backtest/replay`
- `GET /pipeline/status`
- `POST /orchestration/replay-window-sets`
- `GET /orchestration/replay-window-sets`
- `GET /orchestration/replay-window-sets/{window_set_id}`
- `GET /orchestration/replay-window-sets/{window_set_id}/results`
- `POST /orchestration/replay-window-sets/{window_set_id}/run`
- `POST /orchestration/replay-window-sets/{window_set_id}/export`
- `GET /backtest/replay/{replay_run_id}`
- `GET /backtest/replay/{replay_run_id}/trades`
- `POST /backtest/replay/{replay_run_id}/sensitivity`
- `GET /backtest/replay/sensitivity/{sensitivity_run_id}`
- `GET /backtest/replay/sensitivity/{sensitivity_run_id}/scenarios`
- `GET /backtest/replay/{replay_run_id}/sensitivity`
- `POST /backtest/compare-label-vs-replay`
- `GET /backtest/comparisons/{comparison_id}`
- `GET /backtest/runs`
- `GET /backtest/runs/{run_id}`
- `POST /scanner/start`
- `GET /scanner/status`
- `GET /signals/live`
- `GET /signals/history`
- `POST /scanner/stop`
- `POST /exports/signals.csv`
- `POST /exports/signals.xlsx`
- `POST /exports/backtest.xlsx`
- `POST /exports/replay-summary.xlsx`
- `POST /exports/replay-trades.csv`
- `POST /exports/replay-trades.xlsx`
- `POST /exports/sensitivity-summary.xlsx`
- `POST /exports/sensitivity-scenarios.csv`
- `POST /exports/sensitivity-scenarios.xlsx`
- `POST /exports/sensitivity-metrics.json`
- `POST /exports/replay-aware-model-summary.xlsx`
- `POST /exports/evidence-cells.csv`
- `POST /exports/evidence-cells.xlsx`
- `POST /exports/score-audits.csv`
- `POST /exports/score-audits.xlsx`
- `POST /exports/replay-aware-validation.xlsx`
- `POST /exports/replay-window-set.xlsx`
- `POST /exports/calibration-drift.xlsx`
- `POST /exports/calibration-drift.json`
- `POST /exports/calibration-drift-windows.csv`
- `POST /exports/calibration-drift-windows.xlsx`
- `POST /exports/model-review.xlsx`
- `POST /exports/model-review.json`
- `POST /research/cycles`
- `GET /research/cycles`
- `GET /research/cycles/{research_cycle_id}`
- `POST /research/cycles/{research_cycle_id}/dry-run`
- `POST /research/cycles/{research_cycle_id}/run`
- `GET /research/cycles/{research_cycle_id}/artifacts`
- `GET /research/model-proposals`
- `GET /research/model-proposals/{proposal_id}`
- `POST /research/model-proposals/{proposal_id}/approve`
- `POST /research/model-proposals/{proposal_id}/activate`
- `GET /research/decision-ledger`
- `GET /operations/research-status`
- `POST /scheduler/jobs`
- `GET /scheduler/jobs`
- `GET /scheduler/jobs/{job_id}`
- `POST /scheduler/jobs/{job_id}/run`
- `POST /scheduler/jobs/run-pending`
- `POST /scheduler/jobs/{job_id}/cancel`
- `GET /scheduler/jobs/{job_id}/events`
- `GET /operations/scheduler-status`
- `POST /exports/research-cycle.xlsx`
- `POST /exports/research-cycle.json`
- `POST /exports/model-proposal.xlsx`
- `POST /exports/model-proposal.json`
- `POST /exports/champion-challenger-comparison.xlsx`
- `POST /review/daily`
- `GET /review/daily/{date}`
- `POST /exports/daily-review.xlsx`
- `GET /exports/{export_id}`

## Persisted Workflow Proof

The smoke test:

- starts with a clean temporary repository;
- ingests mocked historical bars for `AAPL`, `SPY`, `QQQ`, and `NVDA`;
- verifies `APPL` normalizes to `AAPL`;
- persists bars;
- builds and persists features;
- builds and persists candidate signals plus labels;
- trains and persists a baseline evidence model run;
- verifies activation fails without an accepted validation report;
- verifies activation fails with a rejected validation report;
- persists validation reports;
- verifies accepted validation can activate the model;
- verifies a replacement active model leaves one active model per scope;
- runs and persists a label-derived backtest report with `simulation_type = label_derived`;
- runs and persists a candidate market replay with `simulation_type = candidate_market_replay`, `config_hash`, `input_fingerprint`, and `candidate_fingerprint`;
- re-queries replay summary and paginated simulated trades;
- verifies replay validation rejects missing explicit replay selection;
- validates with an explicit `replay_run_id`;
- runs and persists replay sensitivity scenarios;
- persists a label-vs-replay comparison;
- creates and runs a controlled replay window set;
- trains a `replay_aware_baseline` model from the persisted replay run;
- retrieves evidence cells, scores an inline candidate, persists a score audit, validates with `replay_aware_walk_forward`, and activates through the replay-aware validation guard;
- creates a calibration drift report and model review report;
- creates, dry-runs, and runs a controlled research cycle with explicit validation/calibration/drift/review evidence IDs;
- verifies the cycle creates persisted artifacts and does not activate during cycle run;
- creates a champion/challenger comparison and model proposal;
- verifies proposal approval does not activate the model;
- verifies proposal activation is blocked without `confirm_manual_activation=true`;
- verifies explicit confirmed proposal activation uses the existing replay-aware activation guard;
- verifies decision-ledger and operations research-status routes;
- creates, runs, cancels, lists, and reopens bounded scheduler jobs/events;
- verifies scheduler refresh-data requests block without `FMP_API_KEY`;
- verifies scheduler-run research-cycle jobs do not activate a model;
- starts the scanner with mocked quotes/context;
- persists a scanner run and live signals;
- exports live signals CSV and XLSX from persisted signals;
- exports replay summary XLSX plus metrics JSON and replay trades CSV/XLSX from persisted replay data;
- exports replay sensitivity summary XLSX, scenarios CSV/XLSX, and metrics JSON;
- exports replay-aware model summary XLSX, evidence cells CSV/XLSX, score audits CSV/XLSX, and replay-aware validation XLSX;
- exports replay window set XLSX, calibration drift XLSX/JSON/windows CSV/XLSX, model review XLSX/JSON, research cycle XLSX/JSON, model proposal XLSX/JSON, and champion/challenger comparison XLSX;
- persists a daily review and exports JSON/CSV/XLSX review artifacts;
- reinitializes the repository;
- re-queries bars, features, labels, replay runs/trades, sensitivity runs, comparisons, active model, scanner run, signals, exports, and daily review from disk.
- re-queries replay window sets/results, calibration drift reports/windows, model review reports, research cycles/artifacts, model proposals, and decision-ledger rows from disk.

## Known Limits

- `make api-smoke` is intentionally the SQLite default for local development.
- Postgres smoke requires a reachable migrated database or skips honestly when run through pytest.
- It does not prove live FMP entitlement.
- It does not validate profitability or execution quality.
- Replay smoke is still mocked-provider OHLCV simulation; it verifies persistence and API/export wiring, not live fill realism.

## Phase 9 Coverage

The persisted API smoke now covers:

- counterfactual replay with `simulation_type = model_training_counterfactual`;
- replay-aware training with `outcome_source = counterfactual_preferred`;
- calibration audit create/list/get/bins;
- model comparison;
- counterfactual-vs-portfolio comparison;
- calibration audit XLSX, calibration bins CSV/XLSX, calibration metrics JSON, and model comparison XLSX exports;
- reopened SQLite/Postgres repository reads for calibration audits, model comparisons, and counterfactual comparisons.

## Phase 10 Coverage

The persisted API smoke now covers data quality reporting, replay window set orchestration, calibration drift reporting, model review reporting, Phase 10 exports, and reopened repository reads for all new Phase 10 tables.

## Phase 11 Coverage

The persisted API smoke now covers controlled research cycle create/dry-run/run/list/get/artifacts, explicit champion/challenger evidence IDs, proposal approve/activate flow, blocked activation without manual confirmation, operations research status, decision-ledger reads, Phase 11 exports, and reopened repository reads for research cycles, cycle artifacts, comparisons, proposals, and ledger rows.

## Phase 12 Frontend Smoke

Phase 12 adds Playwright coverage in `apps/web/tests/governance.spec.ts`. These tests mock the FastAPI backend and require no FMP key. They verify:

- `/operations` loads research status;
- `/research/cycles` loads, accepts safe create defaults, normalizes `APPL` to `AAPL`, and calls dry-run;
- `/research/proposals/{proposal_id}` loads, approval does not activate, and activation requires explicit phrase plus checkbox;
- `/research/decision-ledger` loads and applies filters;
- governance pages do not expose `FMP_API_KEY`, `DATABASE_URL`, or execution-control button/link labels.
- `/operations/scheduler` creates safe queued jobs and runs bounded pending batches;
- `/operations/scheduler/{job_id}` displays payload, result, warnings, and events without activation controls.

Run with:

```bash
source "$HOME/.nvm/nvm.sh"
nvm use 24.18.0
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack prepare pnpm@11.9.0 --activate
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm --filter @amd/web test:e2e
```

## Phase 13 Scheduler Coverage

Phase 13 adds `make scheduler-test`, which covers scheduler persistence, service transitions, API routes, FMP gating, runbook docs, and the no-activation guard. The persisted API smoke also reopens scheduler jobs/events from the repository and includes scheduler status in the operations status path. Postgres coverage remains conditional on a reachable Docker/Postgres runtime.

## Phase 15 FMP API Coverage

Additional FMP surfaces include `POST /provider/fmp/smoke`, `POST /provider/capabilities/check`, `POST /data/ingest/fmp/quotes`, `POST /data/ingest/fmp/eod`, `POST /data/ingest/fmp/intraday`, `POST /data/ingest/fmp/incremental-intraday`, `GET /data/ingestion-runs`, and `GET /operations/provider-status`.

Missing-key routes return safe skipped or blocked statuses and never expose the key.

## Phase 16 FMP API Coverage

Additional mocked coverage includes capability review, review summary, durable quote snapshots, seed dry-run/live guards, data freshness reports, `fmp_seed_ingestion`, `data_freshness_check`, and freshness exports. Live entitlement is still only claimed after `FMP_API_KEY` is present and a bounded check is run.
