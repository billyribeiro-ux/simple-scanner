# Adaptive Market Decoder

Adaptive Market Decoder is a local-first trading research and live signal platform for a small, high-liquidity symbol universe. It produces evidence-based trade plans only; it does not place orders or integrate with brokers.

## Requirements

- Node.js `24.18.0`
- pnpm via Corepack
- Python `3.14.6`, the latest stable Python release as of June 30, 2026
- Docker for PostgreSQL/TimescaleDB and Redis
- Optional FMP API key in `FMP_API_KEY` for live provider smoke and live scanner use

## Setup

```bash
cp .env.example .env.local
# edit .env.local and set FMP_API_KEY
make doctor
make setup-backend
corepack pnpm install
make db-up
make db-migrate
make db-inspect
make api-smoke
make api-smoke-postgres
make repository-parity-test
```

`make doctor` does not print secrets. It reports whether `FMP_API_KEY` and `DATABASE_URL` are present.

## Run

```bash
make dev
```

Frontend: `http://localhost:5173`

Backend: `http://localhost:8000`

## Commands

```bash
corepack pnpm install
corepack pnpm dev
corepack pnpm build
corepack pnpm check
corepack pnpm test
corepack pnpm lint

make doctor
make setup-backend
make quant-test
make ingest
make features
make labels
make train
make validate
make backtest
make scanner
make export
make db-inspect
make api-smoke
make api-smoke-sqlite
make api-smoke-postgres
make repository-parity-test
make replay-test
make replay-sensitivity-test
make export-test
make fmp-smoke
make test
```

`make quant-test` runs pure deterministic quant tests without FMP, Docker, Redis, Postgres, or internet. If the backend venv is missing, it falls back to `python3` for this pure test path only. Full backend runtime still targets Python `3.14.6`.

`make api-smoke` runs the default SQLite persisted FastAPI vertical slice with a mocked provider. `make api-smoke-postgres` runs the same API workflow against the migrated local Postgres/TimescaleDB compose database. Neither smoke path requires FMP, internet, or secrets.

`make replay-test` runs the candidate-to-trade market replay unit tests. `make replay-sensitivity-test` runs replay audit/sensitivity tests. `make export-test` verifies replay, sensitivity, and signal CSV/XLSX export generation.

`make fmp-smoke` is optional and runs live FMP REST checks only when `FMP_API_KEY` is configured. Otherwise it skips with a non-secret message.

## Persistence Contract

FastAPI selects the repository backend explicitly:

- no `DATABASE_URL`: SQLite at `data/local_repo.sqlite3`, or `AMD_SQLITE_PATH` when set;
- `sqlite:///...`: SQLite at the configured path;
- `postgres://`, `postgresql://`, or `postgresql+...`: PostgreSQL repository runtime against the migrated schema;
- failed Postgres initialization: fail loudly unless `AMD_ALLOW_SQLITE_FALLBACK=true`;
- explicit fallback: SQLite with runtime mode `sqlite-fallback-from-postgres` and a non-secret fallback reason.

`GET /health`, `GET /config`, and `make doctor` report safe fields such as `persistence_backend`, `runtime_mode`, `database_configured`, `database_reachable`, `fallback_enabled`, and `fallback_reason`. They do not print passwords, API keys, or full database URLs.

## Typical Workflow

1. Set `FMP_API_KEY` in your shell or ignored env file.
2. Start services with `make db-up`.
3. Ingest bars through the Training page or `POST /data/ingest`.
4. Build features and labels.
5. Train and validate a model.
6. Activate only a passing model.
7. Run `POST /backtest/run` for label-derived evidence, or `POST /backtest/replay` for candidate-to-trade market replay.
8. For replay validation, pass an explicit `replay_run_id` or `replay_filter`.
9. Run replay sensitivity and label-vs-replay comparison before treating replay evidence as model-selection input.
10. Start the scanner.
11. Export live signals, replay summaries/trades, sensitivity artifacts, history, backtests, or daily reviews.

## Backtest Modes

- `label_derived`: the existing fast evidence mode that simulates from leakage-safe labels.
- `candidate_market_replay`: replay mode that starts from persisted candidates, enters at next-bar open, replays raw bars chronologically, records skipped candidates, computes metrics from simulated trades, and persists provenance hashes/fingerprints.
- `model_training_counterfactual`: independent per-candidate replay for candidate-quality evidence. It disables portfolio overlap/cooldown/max-open constraints by default and is not portfolio P/L.

Replay exports are available through `POST /exports/replay-summary.xlsx`, `POST /exports/replay-trades.csv`, and `POST /exports/replay-trades.xlsx` with `run_id` set to the replay run ID.

Replay sensitivity exports are available through `POST /exports/sensitivity-summary.xlsx`, `POST /exports/sensitivity-scenarios.csv`, `POST /exports/sensitivity-scenarios.xlsx`, and `POST /exports/sensitivity-metrics.json` with `run_id` set to the sensitivity run ID.

## Replay-Aware Baseline Model

Phase 8 adds `model_type = replay_aware_baseline`. Train it from explicit persisted replay runs:

```bash
curl -s -X POST http://localhost:8000/models/train \
  -H 'content-type: application/json' \
  -d '{"model_type":"replay_aware_baseline","symbols":["AAPL"],"intervals":["1min"],"training_start":"2026-06-01T13:30:00+00:00","training_end":"2026-06-01T19:59:00+00:00","replay_run_ids":["{replay_run_id}"],"minimum_observed_outcomes":5,"minimum_cell_sample_size":5}'
```

Validate and activate through `replay_aware_walk_forward`:

```bash
curl -s -X POST 'http://localhost:8000/models/validate?model_version={model_version}&validation_mode=replay_aware_walk_forward'
curl -s -X POST 'http://localhost:8000/models/activate?model_version={model_version}&validation_mode=replay_aware_walk_forward'
```

Evidence and score audits:

```bash
curl -s http://localhost:8000/models/{model_version}/evidence
curl -s -X POST http://localhost:8000/models/{model_version}/score-candidates \
  -H 'content-type: application/json' \
  -d '{"candidate_ids":["{candidate_id}"],"persist_audit":true}'
curl -s http://localhost:8000/models/{model_version}/score-audits
```

Replay-aware exports:

- `POST /exports/replay-aware-model-summary.xlsx`
- `POST /exports/evidence-cells.csv`
- `POST /exports/evidence-cells.xlsx`
- `POST /exports/score-audits.csv`
- `POST /exports/score-audits.xlsx`
- `POST /exports/replay-aware-validation.xlsx`

The replay-aware score is an explainable evidence score, not a calibrated probability or profitability claim.

## Phase 9 Counterfactual And Calibration

Run counterfactual replay by posting to `/backtest/replay` with `replay_purpose = model_training_counterfactual`. Train `replay_aware_baseline` with `outcome_source = counterfactual_preferred`, `counterfactual_replay_run_ids`, and optional `portfolio_replay_run_ids`.

Calibration audits:

- `POST /models/{model_version}/calibration-audit`
- `GET /models/{model_version}/calibration-audits`
- `GET /models/calibration-audits/{calibration_audit_id}`
- `GET /models/calibration-audits/{calibration_audit_id}/bins`

Diagnostic comparisons:

- `POST /models/compare`
- `POST /backtest/compare-counterfactual-vs-portfolio`
- `GET /backtest/counterfactual-comparisons/{comparison_id}`

Calibration exports:

- `POST /exports/calibration-audit.xlsx`
- `POST /exports/calibration-bins.csv`
- `POST /exports/calibration-bins.xlsx`
- `POST /exports/calibration-metrics.json`
- `POST /exports/model-comparison.xlsx`

Activation can require calibration with `calibration_audit_required=true`. If the active replay-aware model requires calibration and the audit is missing or failed, scanner output suppresses actionable TAKE and emits `calibration_required_or_failed`.

## Default Universe

`AMZN, AAPL, TSLA, SPY, QQQ, IWM, NVDA, GOOGL, BABA, SHOP`

`APPL` is normalized to `AAPL`.
