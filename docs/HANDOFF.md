# Adaptive Market Decoder Handoff

Report status date: 2026-07-01

## Executive State

Phase 6 candidate-to-trade market replay implementation is complete in source. Python `3.14.6` is installed through Homebrew, `services/quant-engine/.venv` exists on Python `3.14.6`, Docker Postgres/TimescaleDB plus Redis are the required database runtime, Alembic upgrades the target database to `0003_phase6_replay`, and the persisted FastAPI vertical-slice smoke test covers both label-derived and replay backtest modes with a mocked provider and no FMP key.

This remains a local-first scanner, research, validation, backtest, signal, and export platform only. It is not a broker, auto-trader, order router, self-learning system, or profitability system.

## Runtime Pins

- Node target: `24.18.0`
- Package manager: `pnpm@11.5.2` through Corepack
- Python target: `3.14.6`, documented as the latest stable Python release for this project as of June 30, 2026
- Current local Node: `25.3.0`, which triggers an expected target warning
- Current local Python: `python3.14` and Homebrew `python3` report `3.14.6`
- Backend venv: `services/quant-engine/.venv` on Python `3.14.6`

## Exact Setup Commands

```bash
make help
make doctor
make setup-backend
corepack pnpm install
make db-up
make db-migrate
make db-inspect
```

The local Postgres/Timescale container is mapped to host port `15432` because this machine already has another Postgres on `5432` and another Docker project on `55432`.

## Exact Verification Commands

```bash
make quant-test
make backend-test
make backend-lint
make backend-typecheck
make api-smoke
make api-smoke-sqlite
make api-smoke-postgres
make repository-parity-test
make replay-test
make export-test
make fmp-smoke
corepack pnpm check
corepack pnpm build
corepack pnpm test
corepack pnpm lint
python3 -m compileall services/quant-engine/app services/quant-engine/tests
git diff --check
```

`make fmp-smoke` is optional and gated. It skips with a non-secret message when `FMP_API_KEY` is not configured.

## Persistence Contract

The FastAPI repository backend is selected explicitly:

- no `DATABASE_URL`: SQLite local repository at `data/local_repo.sqlite3`, or `AMD_SQLITE_PATH` when set;
- `sqlite:///...`: SQLite repository at the configured path;
- Postgres URL: PostgreSQL repository runtime through sync SQLAlchemy/psycopg against the migrated schema;
- failed Postgres init: hard failure by default;
- `AMD_ALLOW_SQLITE_FALLBACK=true`: explicit SQLite fallback reported as `sqlite-fallback-from-postgres`.

Phase 6 adds persisted replay state:

- `replay_runs`: one row per candidate market replay run with config, filters, simulation type, metrics, warnings, and backend.
- `simulated_trades`: one row per taken or skipped candidate, including execution assumptions, entry/exit prices, realized R, MFE/MAE, skip reason, and ambiguity policy.
- `pipeline_build_windows`: dirty/stale metadata for feature, candidate, label, and replay rebuild awareness by artifact, symbol, interval, session date, version, and timestamp range.

Safe status fields are exposed through `GET /health`, `GET /config`, and `make doctor`: `persistence_backend`, `runtime_mode`, `database_configured`, `database_reachable`, `fallback_enabled`, and `fallback_reason`. Full database URLs, passwords, and API keys are never returned.

## What Is Safe To Trust

- Deterministic quant feature/label/backtest/model baseline tests.
- Repository-backed API route state instead of route-level `_MEMORY`.
- SQLite local API persistence and reinitialization survival for bars, features, labels, replay runs/trades, model runs, active model, scanner runs/signals, exports, and daily reviews.
- Postgres API persistence and reinitialization survival for the same vertical slice after `make db-migrate`.
- Alembic migration and schema inspection success against local Postgres/TimescaleDB on host port `15432` when the database is at revision `0003_phase6_replay`.
- SQLite/Postgres repository parity for symbols, bars, features, labels, replay runs/trades, pipeline build windows, models, scanner runs, signals, provider requests, exports, and daily reviews.
- CSV/XLSX/JSON export generation from persisted signals, replay runs/trades, and daily reviews.
- Activation guard requiring a persisted accepted validation report.
- Secret redaction behavior and absence of the supplied FMP key from repo files.

## What Is Not Safe To Trust Yet

- Live FMP entitlement coverage. The live smoke was not run because `FMP_API_KEY` is not loaded into the process environment or ignored env files.
- Market replay as execution-grade reality. Phase 6 improves honesty by replaying raw bars, but fills are still simulated from OHLCV with conservative same-bar rules, configurable slippage/spread, and no true market depth.
- Model calibration. V1 remains a statistical evidence baseline, not a calibrated ML classifier.
- Live trading readiness. No broker execution or order routing exists.

## Backtest Modes

Label-derived evidence remains available and explicit:

```bash
curl -s -X POST http://localhost:8000/backtest/run \
  -H 'content-type: application/json' \
  -d '{"symbols":["AAPL"],"start":"2026-06-01T13:30:00+00:00","end":"2026-06-01T19:59:00+00:00"}'
```

The response includes `simulation_type = label_derived`.

Candidate market replay uses persisted bars, features, and candidate signals:

```bash
curl -s -X POST http://localhost:8000/backtest/replay \
  -H 'content-type: application/json' \
  -d '{"symbols":["AAPL"],"intervals":["1min"],"start":"2026-06-01T13:30:00+00:00","end":"2026-06-01T19:59:00+00:00","max_hold_minutes":60,"minimum_reward_risk":1.0}'
```

The response includes `simulation_type = candidate_market_replay`, `replay_run_id`, `summary_metrics`, and `trades_written`. Query the run and paginated trades with:

```bash
curl -s http://localhost:8000/backtest/replay/{replay_run_id}
curl -s 'http://localhost:8000/backtest/replay/{replay_run_id}/trades?limit=500&offset=0'
```

Export replay outputs with:

```bash
curl -s -X POST http://localhost:8000/exports/replay-summary.xlsx \
  -H 'content-type: application/json' \
  -d '{"kind":"replay-summary","run_id":"{replay_run_id}"}'
curl -s -X POST http://localhost:8000/exports/replay-trades.csv \
  -H 'content-type: application/json' \
  -d '{"kind":"replay-trades","run_id":"{replay_run_id}"}'
curl -s -X POST http://localhost:8000/exports/replay-trades.xlsx \
  -H 'content-type: application/json' \
  -d '{"kind":"replay-trades","run_id":"{replay_run_id}"}'
```

## Current Blockers

- Local Node is `25.3.0`, while the project target is `24.18.0`. Corepack pnpm still runs, but frontend commands emit the expected engine warning.
- Optional live FMP smoke requires `FMP_API_KEY` to be configured outside the committed repo.

## Exact Next Recommended Phase

Phase 7: replay calibration audit and operational hardening.

The next phase should audit replay assumptions against sampled real intraday paths, add richer slippage/spread sensitivity reporting, tighten Timescale hypertable/compression policies, and add replay-oriented monitoring around stale windows and export reproducibility. Do not add broker execution, WebSocket scope, options data, self-learning language, or profitability claims in that phase.
