# API Smoke Testing

Status date: 2026-07-01

## Command

```bash
make api-smoke
```

This runs:

```bash
cd services/quant-engine && PYTHONPATH=. .venv/bin/python -m pytest tests/test_persisted_api_smoke.py
```

## Design

The smoke test uses FastAPI `TestClient`, a temporary SQLite repository, temporary export/model directories, and a mocked FMP provider. It does not require internet, live FMP, Redis, Postgres, or secrets.

The test sets a non-secret sentinel `FMP_API_KEY` only to exercise scanner gating. It verifies the sentinel is absent from the SQLite file, exported CSV/XLSX/JSON files, and active model artifact.

## Route Coverage

- `GET /health`
- `GET /config`
- `POST /data/ingest`
- `GET /data/bars`
- `GET /data/quotes/latest`
- `POST /features/build`
- `POST /labels/build`
- `POST /models/train`
- `POST /models/validate`
- `POST /models/activate`
- `GET /models`
- `GET /models/{model_version}`
- `POST /backtest/run`
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
- runs and persists a label-derived backtest report;
- starts the scanner with mocked quotes/context;
- persists a scanner run and live signals;
- exports live signals CSV and XLSX from persisted signals;
- persists a daily review and exports JSON/CSV/XLSX review artifacts;
- reinitializes the repository;
- re-queries bars, features, labels, active model, scanner run, signals, exports, and daily review from disk.

## Known Limits

- The smoke test proves current SQLite-backed API persistence only.
- It does not prove live FMP entitlement.
- It does not prove Postgres-backed API repository runtime.
- It does not validate profitability or execution quality.
