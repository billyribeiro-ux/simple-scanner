# Phase 19C Migration Repair - 2026-07-04

Status: COMPLETED

## Root Cause

Revision `0001_initial` imported `app.db.schema.metadata` and ran `metadata.create_all(bind=op.get_bind())`. Because that metadata reflects the current application schema, a clean base-to-head migration created future tables during revision 0001 and then collided with later migrations such as `0008_phase11_research`.

## Repair

- Replaced the dynamic live-schema import in `services/quant-engine/alembic/versions/0001_initial.py` with a static baseline migration.
- Limited revision 0001 to the baseline persistence tables: symbols, bars, features, candidate signals, labels, validation reports/windows, model runs/artifacts, active models, live/closed signals, scanner runs, provider requests, exports, and daily reviews.
- Preserved later table ownership in revisions 0003 through 0012.
- Added `services/quant-engine/tests/test_migrations.py` to fail if revision 0001 imports live schema metadata, calls `metadata.create_all`, or uses `metadata.sorted_tables`.

## Runtime Alignment

- Installed Homebrew `python@3.14` 3.14.6.
- Updated `Makefile` to prefer `/opt/homebrew/opt/python@3.14/bin/python3.14` when available.
- Updated `make setup-backend` to recreate the generated venv with `python -m venv --clear`.
- Rebuilt `services/quant-engine/.venv`; `services/quant-engine/.venv/bin/python --version` now reports `Python 3.14.6`.

## Redis Routing

- Updated `docker-compose.yml` to publish Redis as `${REDIS_HOST_PORT:-16379}:6379`.
- Added `REDIS_HOST_PORT=16379` to `.env.example`.
- Updated `scripts/doctor.sh` to report the configured Redis host port.

## Verification

- `make db-migrate`: PASS, clean base-to-head migration through `0012_phase16_fmp_freshness`.
- `make db-inspect`: PASS, 44 tables, no missing tables/indexes/constraints/columns/json columns, `timescaledb` present, `bars` hypertable present.
- `make db-query-diagnostics`: PASS.
- `make api-smoke-postgres`: PASS.
- `make repository-parity-test`: PASS when run alone. An earlier parallel run with `api-smoke-postgres` was invalid because both processes wrote/cleared the same local Postgres test database.
- `make backend-test`: PASS, 125 tests, 1 upstream Starlette deprecation warning.
- `make backend-lint`: PASS.
- `make backend-typecheck`: PASS.
- `git diff --check`: PASS.
