# Adaptive Market Decoder Handoff

Report status date: 2026-07-01

## Executive State

Phase 5 PostgreSQL repository runtime implementation is complete. Python `3.14.6` is installed through Homebrew, `services/quant-engine/.venv` exists on Python `3.14.6`, Docker Postgres/TimescaleDB plus Redis are healthy, Alembic upgrades the target database to `0002_phase5_indexes`, and the persisted FastAPI vertical-slice smoke test passes against both SQLite and PostgreSQL with a mocked provider and no FMP key.

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

Safe status fields are exposed through `GET /health`, `GET /config`, and `make doctor`: `persistence_backend`, `runtime_mode`, `database_configured`, `database_reachable`, `fallback_enabled`, and `fallback_reason`. Full database URLs, passwords, and API keys are never returned.

## What Is Safe To Trust

- Deterministic quant feature/label/backtest/model baseline tests.
- Repository-backed API route state instead of route-level `_MEMORY`.
- SQLite local API persistence and reinitialization survival for bars, features, labels, model runs, active model, scanner runs/signals, exports, and daily reviews.
- Postgres API persistence and reinitialization survival for the same vertical slice.
- Alembic migration and schema inspection success against local Postgres/TimescaleDB on host port `15432`.
- SQLite/Postgres repository parity for symbols, bars, features, labels, models, scanner runs, signals, provider requests, exports, and daily reviews.
- CSV/XLSX export generation from persisted signals and daily reviews.
- Activation guard requiring a persisted accepted validation report.
- Secret redaction behavior and absence of the supplied FMP key from repo files.

## What Is Not Safe To Trust Yet

- Live FMP entitlement coverage. The live smoke was not run because `FMP_API_KEY` is not loaded into the process environment or ignored env files.
- Backtest realism. Current backtest remains label-derived evidence, not market replay execution.
- Model calibration. V1 remains a statistical evidence baseline, not a calibrated ML classifier.
- Live trading readiness. No broker execution or order routing exists.

## Current Blockers

- Local Node is `25.3.0`, while the project target is `24.18.0`. Corepack pnpm still runs, but frontend commands emit the expected engine warning.
- Optional live FMP smoke requires `FMP_API_KEY` to be configured outside the committed repo.

## Exact Next Recommended Phase

Phase 6: incremental data pipeline and operational query hardening.

The next phase should add incremental rebuild paths for bars/features/labels, tighten repository query performance around scanner and validation workloads, and keep REST polling as the live-data default. Do not add broker execution, WebSocket scope, options data, or ML calibration in that phase.
