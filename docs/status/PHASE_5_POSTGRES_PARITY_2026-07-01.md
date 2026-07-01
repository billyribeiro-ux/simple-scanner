# Phase 5 PostgreSQL Parity Status

Date: 2026-07-01

## Backend Contract

- No `DATABASE_URL`: SQLite local runtime.
- `sqlite:///...`: SQLite configured runtime.
- Postgres URL: PostgreSQL repository runtime after schema verification.
- Postgres initialization failure: hard failure by default.
- `AMD_ALLOW_SQLITE_FALLBACK=true`: explicit SQLite fallback with runtime mode `sqlite-fallback-from-postgres`.

Safe status fields are exposed through `/health`, `/config`, and `make doctor`: `persistence_backend`, `runtime_mode`, `database_configured`, `database_reachable`, `fallback_enabled`, and `fallback_reason`.

## Schema Inspection

Local Postgres/TimescaleDB inspection passed:

```text
alembic_version=0002_phase5_indexes
tables=17
missing_tables=none
missing_indexes=none
missing_constraints=none
missing_columns=none
missing_json_columns=none
extensions=plpgsql,timescaledb
```

## API Smoke Parity

The same persisted FastAPI vertical slice now runs against both SQLite and Postgres:

- health and config backend reporting;
- ingestion with `APPL` normalized to `AAPL`;
- persisted bars and latest quotes;
- feature and label builds;
- model training, validation, activation rejection, accepted activation, and active replacement;
- backtest report persistence;
- scanner start/status/stop and live signal persistence;
- signal, backtest, and daily review CSV/XLSX exports;
- daily review persistence and reload;
- repository reinitialization survival.

## Repository Parity

`tests/test_repository_parity.py` covers deterministic repository behavior across SQLite and Postgres for:

- symbols;
- bars;
- features;
- candidate signals;
- labels;
- model runs and active models;
- validation reports;
- scanner runs and live signals;
- provider request metadata;
- export records;
- daily reviews;
- backend selection and fallback behavior.

## Security And Redaction

- The supplied FMP key is not committed or referenced in docs.
- Provider metadata stores redacted accounting only.
- Route status exposes database configuration shape but not database URLs or passwords.
- Postgres smoke does not create the temporary SQLite file used by the SQLite smoke path.

## Current Status

SQLite/Postgres persistence parity for V1 repository workflows is complete. Remaining work is performance and operational hardening, not feature expansion into broker execution, WebSockets, options data, or model calibration.

## Verification Matrix

- `make help`: passed.
- `make doctor`: passed with expected warnings for local Node `25.3.0` versus target `24.18.0`, missing optional `DATABASE_URL`, and missing optional `FMP_API_KEY`.
- `DATABASE_URL=... make doctor`: passed with sanitized Postgres backend status and no URL/password output.
- `make setup-backend`: passed on Python `3.14.6`.
- `docker compose config`: passed.
- `docker compose up -d postgres redis`: passed.
- `docker compose ps`: Postgres and Redis healthy.
- `make db-migrate`: passed at Alembic head.
- `make db-inspect`: passed with revision `0002_phase5_indexes`.
- `make quant-test`: passed, 44 tests.
- `make backend-test`: passed, 56 tests.
- `make backend-lint`: passed.
- `make backend-typecheck`: passed.
- `make api-smoke`: passed.
- `make api-smoke-sqlite`: passed.
- `make api-smoke-postgres`: passed.
- `make repository-parity-test`: passed, 3 tests.
- `make fmp-smoke`: skipped because `FMP_API_KEY` is not configured in the shell.
- `corepack pnpm check`: passed with expected Node engine warning.
- `corepack pnpm build`: passed with expected Node engine warning and adapter-auto note.
- `corepack pnpm test`: passed with no frontend test files found and `--passWithNoTests`.
- `corepack pnpm lint`: passed with expected Node engine warning.
- `python3 -m compileall services/quant-engine/app services/quant-engine/tests`: passed.
- `git diff --check`: passed.
- Supplied FMP key scan: passed, 0 findings across 246 scanned files.
