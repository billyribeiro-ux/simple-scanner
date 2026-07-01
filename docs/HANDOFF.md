# Adaptive Market Decoder Handoff

Report status date: 2026-07-01

## Executive State

Phase 4 target runtime bring-up is complete for the local machine. Python `3.14.6` is installed through Homebrew, `services/quant-engine/.venv` exists on Python `3.14.6`, backend dependencies install, backend pytest/ruff/mypy pass through the venv, Docker Postgres/TimescaleDB plus Redis are healthy, Alembic upgrades the target database to `0001_initial`, and the persisted FastAPI vertical-slice smoke test passes with a mocked provider and no FMP key.

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

The active FastAPI repository backend is SQLite:

- Backend type: `sqlite`
- Runtime mode without `DATABASE_URL`: `sqlite-local`
- Default path: `data/local_repo.sqlite3`
- Safe status fields: `GET /health`, `GET /config`, and `make doctor`

Postgres/TimescaleDB is migration-verified and remains the intended serious research/production target schema. The current repository implementation is still SQLite-only. If `DATABASE_URL` is set to Postgres, the API reports `sqlite-fallback` rather than pretending Postgres is the active API database.

## What Is Safe To Trust

- Deterministic quant feature/label/backtest/model baseline tests.
- Repository-backed API route state instead of route-level `_MEMORY`.
- SQLite local API persistence and reinitialization survival for bars, features, labels, model runs, active model, scanner runs/signals, exports, and daily reviews.
- Alembic migration success against local Postgres/TimescaleDB on host port `15432`.
- CSV/XLSX export generation from persisted signals and daily reviews.
- Activation guard requiring a persisted accepted validation report.
- Secret redaction behavior and absence of the supplied FMP key from repo files.

## What Is Not Safe To Trust Yet

- Postgres-backed FastAPI repository runtime. The migration exists; the repository implementation still writes to SQLite.
- Live FMP entitlement coverage. The live smoke was not run because `FMP_API_KEY` is not loaded into the process environment or ignored env files.
- Backtest realism. Current backtest remains label-derived evidence, not market replay execution.
- Model calibration. V1 remains a statistical evidence baseline, not a calibrated ML classifier.
- Live trading readiness. No broker execution or order routing exists.

## Current Blockers

- Local Node is `25.3.0`, while the project target is `24.18.0`. Corepack pnpm still runs, but frontend commands emit the expected engine warning.
- Postgres repository runtime is not implemented yet.
- Optional live FMP smoke requires `FMP_API_KEY` to be configured outside the committed repo.

## Exact Next Recommended Phase

Phase 5: PostgreSQL repository runtime implementation and parity testing.

The next phase should implement a Postgres-backed repository adapter behind the existing repository contract, run the same API smoke suite against SQLite and Postgres, and keep REST polling as the live-data default. Do not add broker execution, WebSocket scope, options data, or ML calibration in that phase.
