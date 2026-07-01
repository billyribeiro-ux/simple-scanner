# API Smoke Testing

Status date: 2026-07-01

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

The Postgres smoke uses the local compose database on host port `15432` unless `DATABASE_URL` is supplied.

## Design

The smoke test uses FastAPI `TestClient`, temporary export/model directories, and a mocked FMP provider. The SQLite path uses a temporary SQLite repository. The Postgres path uses the migrated local compose Postgres/TimescaleDB database and clears test data between runs. It does not require internet, live FMP, or secrets.

The test sets a non-secret sentinel `FMP_API_KEY` only to exercise scanner gating. It verifies the sentinel is absent from SQLite files, exported CSV/XLSX/JSON files, active model artifacts, and persisted provider metadata.

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
- starts the scanner with mocked quotes/context;
- persists a scanner run and live signals;
- exports live signals CSV and XLSX from persisted signals;
- exports replay summary XLSX plus metrics JSON and replay trades CSV/XLSX from persisted replay data;
- exports replay sensitivity summary XLSX, scenarios CSV/XLSX, and metrics JSON;
- exports replay-aware model summary XLSX, evidence cells CSV/XLSX, score audits CSV/XLSX, and replay-aware validation XLSX;
- exports replay window set XLSX, calibration drift XLSX/JSON/windows CSV/XLSX, and model review XLSX/JSON;
- persists a daily review and exports JSON/CSV/XLSX review artifacts;
- reinitializes the repository;
- re-queries bars, features, labels, replay runs/trades, sensitivity runs, comparisons, active model, scanner run, signals, exports, and daily review from disk.
- re-queries replay window sets/results, calibration drift reports/windows, and model review reports from disk.

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
