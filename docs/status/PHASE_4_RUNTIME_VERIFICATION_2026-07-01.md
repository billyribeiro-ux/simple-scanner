# Phase 4 Runtime Verification

Date: 2026-07-01

## Runtime

- Node target: `24.18.0`
- Local Node: `25.3.0`; expected warning remains
- pnpm: `11.5.2` through Corepack
- Python target: `3.14.6`
- Local `python3.14`: `3.14.6`
- Backend venv: `services/quant-engine/.venv`
- Backend venv Python: `3.14.6`

## Backend Tooling

- `pytest`: `9.1.1`
- `ruff`: `0.15.20`
- `mypy`: `2.1.0`
- `alembic`: `1.18.5`
- `uvicorn`: `0.49.0`

## Docker And Database

- `docker compose config`: passed
- `docker compose up -d postgres redis`: passed
- `docker compose ps`: Postgres/TimescaleDB healthy, Redis healthy
- Postgres host port: `15432`
- Alembic command: `make db-migrate`
- Alembic result: upgraded to `0001_initial`
- Schema inspection: 17 tables, no missing tables
- Extensions: `plpgsql,timescaledb`

## Active API Persistence Backend

- Backend: `sqlite`
- Runtime: `sqlite-local` when `DATABASE_URL` is unset
- Path: `data/local_repo.sqlite3`
- Safe reporting: `make doctor`, `GET /health`, `GET /config`

Postgres/TimescaleDB migration is verified. Postgres-backed API repository runtime is not implemented yet.

## Smoke Status

- `make api-smoke`: passed
- `make fmp-smoke`: skipped because `FMP_API_KEY` is not configured

## Notes

The local machine also has a Postgres instance on port `5432` and another Docker project on `55432`, so this project maps TimescaleDB to host port `15432` to avoid ambiguous connections.
