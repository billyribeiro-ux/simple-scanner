# Phase 3 Completion - Backend Runtime and Persistence Hardening

Date: 2026-07-01

## Executive Summary

Phase 3 is complete for the implementation scope: API route-level `_MEMORY` state has been removed as the source of truth, repository-backed persistence now covers the V1 workflow, scanner runs/signals persist, model activation is guarded by persisted validation evidence, exports persist metadata, and runtime commands/docs were hardened.

Target-runtime verification is not complete because Python `3.14.6` and the backend venv are not installed on this machine. The local compatibility path passes, Docker database services are healthy, and frontend gates pass with Node-version warnings.

## Runtime Status

- Node target: `24.18.0`.
- Local Node: `25.3.0`; pnpm commands pass with unsupported-engine warnings.
- Corepack/pnpm: available; `corepack pnpm --version` reports `11.9.0`.
- Python target: `3.14.6`.
- Local Python target status: `python3.14` missing.
- Backend venv: missing.
- Docker: reachable.
- Postgres/TimescaleDB: running and healthy after `docker compose up -d postgres redis`.
- Redis: running and healthy.
- `FMP_API_KEY`: not present in shell.
- `DATABASE_URL`: not present in shell.

## Backend Venv Status

`make setup-backend` fails correctly because `python3.14` is missing. Full backend target gates (`make backend-test`, `make backend-lint`, `make backend-typecheck`, `make db-migrate`) are blocked until Python `3.14.6` and `services/quant-engine/.venv` exist.

## Database And Migration Status

Implemented:

- SQLAlchemy metadata aligned with Phase 3 table set.
- Alembic initial migration delegates to the aligned metadata.
- Timescale extension creation is gated to PostgreSQL only.
- Docker Compose configuration is valid.
- Postgres/TimescaleDB and Redis containers are healthy.

Blocked:

- `make db-migrate` cannot run because the backend venv and `alembic` executable are missing.

## Repository And Persistence Status

Implemented `services/quant-engine/app/db/repositories.py` with durable local SQLite repositories for:

- symbols
- bars
- features
- candidate signals
- labels
- validation reports
- model runs
- active models
- live signals
- scanner runs
- provider requests
- exports
- daily reviews

Local runtime artifacts are ignored: SQLite files, SQLite WAL sidecars, exports, and model artifacts.

## API Routes Converted From `_MEMORY`

Converted:

- `/data/ingest`
- `/data/bars`
- `/features/build`
- `/labels/build`
- `/models/train`
- `/models/validate`
- `/models/activate`
- `/models`
- `/models/{model_version}`
- `/backtest/run`
- `/backtest/runs`
- `/backtest/runs/{run_id}`
- `/signals/live`
- `/signals/history`
- `/exports/signals.csv`
- `/exports/signals.xlsx`
- `/exports/backtest.xlsx`
- `/exports/daily-review.xlsx`
- `/exports/{export_id}`
- `/review/daily`
- `/review/daily/{review_date}`

`/signals/stream` still uses an in-process queue for transient SSE delivery, not durable state.

## Validation And Model Persistence Status

- Model training reads persisted labels/features and writes persisted model runs/artifact metadata.
- Validation writes persisted validation reports.
- Backtests write persisted reports with purpose `backtest`.
- Model activation requires an accepted persisted validation report for the model version.
- Active model pointer is persisted in `active_models`.

## Scanner Persistence Status

- Scanner start writes a scanner run.
- Scanner loads persisted active model first.
- Scanner checks persisted historical bars before FMP context hydration during real runs.
- Scanner persists fetched context bars during real runs.
- Scanner persists each scored signal.
- Provider requests are recorded without secrets.

## Export Persistence Status

- Signal CSV and XLSX exports read persisted signals.
- Daily review exports read persisted review payloads.
- Export metadata is persisted to `exports`.
- XLSX export has an `openpyxl` path plus a minimal fallback writer for no-venv compatibility tests.

## Commands Run And Results

Passed:

- `make help`
- `make doctor` with expected warnings/missing target runtime tools
- `docker compose config`
- `docker compose up -d postgres redis`
- `docker compose ps`: Postgres and Redis healthy
- `make quant-test`: 44 passed, 1 warning, using system Python fallback
- `cd services/quant-engine && PYTHONPATH=. python3 -m pytest`: 51 passed, 1 warning
- `corepack pnpm check`
- `corepack pnpm build`
- `corepack pnpm test`
- `corepack pnpm lint`
- `python3 -m compileall services/quant-engine/app services/quant-engine/tests`
- `git diff --check`
- Secret scan for the provided FMP key without echoing it

Failed or blocked as expected:

- `make setup-backend`: blocked because `python3.14` is missing.
- `make db-migrate`: blocked because backend venv is missing.
- `make backend-test`: blocked because backend venv is missing.
- `make backend-lint`: blocked because backend venv is missing.
- `make backend-typecheck`: blocked because backend venv is missing.

## Tests Added

Added `services/quant-engine/tests/quant/test_persistence_workflows.py` covering:

- repository durability across registry instances;
- persisted bars/features/labels/signals;
- feature, label, and backtest services over repositories;
- activation guard requiring accepted persisted validation;
- export workflow reading persisted signals and recording metadata.

## Critical Blockers

- Python `3.14.6` is not installed.
- Backend venv is missing.
- Full backend target gates cannot run until the venv exists.
- Alembic migrations cannot run until the venv exists.
- Live FMP ingestion/scanner cannot run until `FMP_API_KEY` is provided at runtime.

## Remaining Quant Risks

- Local SQLite fallback is sufficient for Phase 3 local-first persistence but not the final production persistence layer.
- Backtest path remains label-derived; a richer candidate-to-trade simulator over raw bars is still needed.
- Baseline statistical evidence model is not a calibrated ML classifier.
- Activation guard now persists, but thresholds still need larger out-of-sample datasets before trust.
- Scanner confidence remains sensitive to feature history quality and FMP entitlement/rate limits.

## Required Paths

- `docs/HANDOFF.md`
- `docs/status/PHASE_3_PLAN_2026-07-01.md`
- `docs/status/PHASE_3_COMPLETION_2026-07-01.md`
- `docs/persistence-architecture.md`
- `docs/runtime-setup.md`

## Exact Next Recommended Phase

Phase 4: Target Runtime Bring-Up, Migration Verification, and API Smoke Testing.

The first Phase 4 actions should be: install Python `3.14.6`, build `services/quant-engine/.venv`, run full backend `pytest`/`ruff`/`mypy`, run Alembic migrations against the healthy local Postgres/TimescaleDB service, and then smoke-test the repository-backed API with mocked or small controlled FMP inputs.
