# Phase 4 Completion - Target Runtime Bring-Up, Migration Verification, And Persisted API Smoke Testing

Date: 2026-07-01

## Summary

Phase 4 is complete for the requested runtime truth objective. Python `3.14.6` is installed, the backend venv exists, dependencies install, backend tests/lint/typecheck pass, Postgres/TimescaleDB and Redis are healthy, Alembic migrations pass, schema inspection confirms all expected tables, and a persisted API vertical-slice smoke test passes without FMP, internet, or secrets.

## What Changed

- Added backend packaging metadata so editable install works with the `app` package.
- Added `psycopg[binary]` for synchronous Alembic migrations.
- Switched the local TimescaleDB host port to `15432` to avoid conflicts with existing local services.
- Made Alembic use the synchronous `psycopg` driver while preserving asyncpg-style app URLs when present.
- Added safe persistence backend descriptors to repository registry, `/health`, `/config`, and `make doctor`.
- Added repeatable `make api-smoke`, `make db-inspect`, and `make fmp-smoke` commands.
- Added deterministic persisted FastAPI smoke testing with a mocked provider.
- Updated runtime, persistence, handoff, and smoke-testing docs.

## Files Changed

- `Makefile`
- `docker-compose.yml`
- `scripts/doctor.sh`
- `scripts/fmp_smoke.py`
- `scripts/inspect_db_schema.py`
- `services/quant-engine/pyproject.toml`
- `services/quant-engine/alembic.ini`
- `services/quant-engine/alembic/env.py`
- `services/quant-engine/app/api/routes.py`
- `services/quant-engine/app/db/repositories.py`
- `services/quant-engine/tests/test_persisted_api_smoke.py`
- runtime docs and Phase 4 status docs

Several backend modules and existing tests were also normalized by Ruff import/format fixes.

## Runtime Status

- Python `3.14.6`: installed and used.
- Backend venv: exists at `services/quant-engine/.venv`.
- Dependencies: installed through `make setup-backend`.
- Backend tool versions: pytest `9.1.1`, ruff `0.15.20`, mypy `2.1.0`, Alembic `1.18.5`, Uvicorn `0.49.0`.
- Local Node: `25.3.0`, target is `24.18.0`.
- pnpm through Corepack: `11.5.2`.

## Docker/Postgres/Redis

- Docker daemon reachable.
- Postgres/TimescaleDB healthy.
- Redis healthy.
- Postgres host port is `15432`.

## Alembic Migration Status

- `make db-migrate`: passed.
- Current revision: `0001_initial`.
- `make db-inspect`: passed.
- Expected tables: 17.
- Missing tables: none.
- Extensions: `plpgsql,timescaledb`.

## Active API Persistence Backend

The active API repository backend is SQLite local fallback:

- Backend: `sqlite`
- Runtime: `sqlite-local`
- Default path: `data/local_repo.sqlite3`

Postgres/TimescaleDB is migration-verified but not yet the active API repository runtime.

## API Smoke Status

`make api-smoke` passed. The smoke test proves persisted route workflow survival across repository reinitialization with mocked market data and no live FMP dependency.

Covered route groups include health/config, data ingest/bars/latest quotes, features, labels, models, validation/activation, backtest, scanner/signals, exports, and daily review.

## FMP Smoke Status

`make fmp-smoke` is implemented and safe. It skipped during Phase 4 because `FMP_API_KEY` is not configured in the shell or ignored env files.

## Tests Added

- `services/quant-engine/tests/test_persisted_api_smoke.py`

The test covers route-level ingestion, feature build, labels, model train/validate/activate, backtest, scanner persistence, live signals, exports, daily review, export metadata, reinitialization survival, and non-secret output checks.

## Command Results

- `make help`: passed.
- `make doctor`: passed with expected warnings for local Node `25.3.0`, missing `DATABASE_URL`, and missing `FMP_API_KEY`.
- `make setup-backend`: passed.
- `make quant-test`: passed, 44 tests.
- `make backend-test`: passed, 52 tests with one upstream Starlette/FastAPI TestClient deprecation warning.
- `make backend-lint`: passed.
- `make backend-typecheck`: passed.
- `docker compose config`: passed.
- `docker compose up -d postgres redis`: passed.
- `docker compose ps`: Postgres/TimescaleDB and Redis healthy.
- `make db-migrate`: passed.
- `make db-inspect`: passed.
- `make api-smoke`: passed.
- `make fmp-smoke`: skipped cleanly because `FMP_API_KEY` is not configured.
- `corepack pnpm check`: passed with expected Node target warning.
- `corepack pnpm build`: passed with expected Node target warning.
- `corepack pnpm test`: passed with expected Node target warning and no frontend test files.
- `corepack pnpm lint`: passed with expected Node target warning.
- `python3 -m compileall services/quant-engine/app services/quant-engine/tests`: passed.
- `git diff --check`: passed.
- Secret scan: scanned 344 repo/build/artifact files, 0 findings for the supplied FMP key.

## Export Verification

- Live signals CSV export passed through API smoke.
- Live signals XLSX export passed through API smoke.
- Backtest XLSX route returned the current V1 scaffold note and persisted export metadata.
- Daily review export wrote JSON, CSV, and XLSX files from persisted review payload.
- Export metadata was queryable by `export_id`.
- Smoke test verified exported files and active model artifact did not contain the FMP sentinel.

## Model Activation Lifecycle Proof

- Model run with no validation report: activation rejected.
- Model run with rejected validation report: activation rejected with reason.
- Model run with accepted validation report: activation accepted.
- Replacement model activation left one active model row for the default scope.
- Repository reinitialization preserved the active model pointer.

## Scanner Persistence Proof

- Scanner start persisted `scanner_run`.
- Scanner used mocked provider and persisted live signal rows.
- `/signals/live` and `/signals/history` returned persisted rows.
- Scanner stop returned `running = false`.
- Repository reinitialization preserved the scanner run and live signals.

## Blockers

- Postgres-backed repository runtime is not implemented yet.
- Live FMP entitlement is unverified because the key was not loaded into the runtime environment.
- Local Node is newer than target and emits expected engine warnings.

## Remaining Risks

- Backtest remains label-derived and should not be interpreted as execution simulation.
- The baseline evidence model is not calibrated ML.
- Scanner signals are research outputs only and not live-trading recommendations.
- SSE delivery remains transient by design.

## Exact Next Phase

Phase 5: PostgreSQL repository runtime implementation and parity testing.

Implement a Postgres repository adapter, run API smoke against both SQLite and Postgres, and keep V1 scope limited to scanner/research/backtest/signal/export without broker execution or new ML.
