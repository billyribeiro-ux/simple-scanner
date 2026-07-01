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

Replay exports are available through `POST /exports/replay-summary.xlsx`, `POST /exports/replay-trades.csv`, and `POST /exports/replay-trades.xlsx` with `run_id` set to the replay run ID.

Replay sensitivity exports are available through `POST /exports/sensitivity-summary.xlsx`, `POST /exports/sensitivity-scenarios.csv`, `POST /exports/sensitivity-scenarios.xlsx`, and `POST /exports/sensitivity-metrics.json` with `run_id` set to the sensitivity run ID.

## Default Universe

`AMZN, AAPL, TSLA, SPY, QQQ, IWM, NVDA, GOOGL, BABA, SHOP`

`APPL` is normalized to `AAPL`.
