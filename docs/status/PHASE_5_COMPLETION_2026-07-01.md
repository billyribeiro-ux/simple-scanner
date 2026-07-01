# Phase 5 Completion - PostgreSQL Repository Runtime

Date: 2026-07-01

## Summary

Phase 5 implements the PostgreSQL repository runtime behind the existing repository registry contract and keeps SQLite as the no-configuration local default. The API, services, scanner, exports, model activation guard, and daily review workflow remain backend-agnostic.

## Implemented

- Explicit backend selection for missing `DATABASE_URL`, `sqlite:///...`, and Postgres URLs.
- Synchronous Postgres store using SQLAlchemy/psycopg with safe URL normalization and redacted status.
- Startup schema verification for required tables and Alembic revision `0002_phase5_indexes`.
- Hard failure on Postgres initialization errors unless `AMD_ALLOW_SQLITE_FALLBACK=true`.
- Explicit fallback status `sqlite-fallback-from-postgres` with non-secret fallback reason.
- Standards-compliant JSON serialization for both SQLite and Postgres payload columns.
- Model activation consistency across relational active flags and stored model payload JSON.
- Strengthened `make db-inspect` for tables, indexes, constraints, selected columns, JSON columns, Timescale extension, and Alembic revision.
- SQLite and Postgres API smoke targets plus repository parity tests.

## Guardrails Preserved

- No broker execution or order routing.
- No WebSocket entitlement path.
- No options, gamma, Greeks, IV, or market internals.
- No ML calibration or profitability claims.
- No frontend redesign.
- No secrets in committed files, docs, route payloads, exports, or logs.

## Verification Snapshot

- `make db-inspect`: passed with revision `0002_phase5_indexes`.
- `make api-smoke-sqlite`: passed.
- `make api-smoke-postgres`: passed.
- `make repository-parity-test`: passed.
- Full command matrix results are recorded in `docs/status/PHASE_5_POSTGRES_PARITY_2026-07-01.md`.

## Remaining Limits

- SQLite remains the default for local no-config development.
- Postgres query planning, hypertable policy tuning, and incremental rebuild performance are future work.
- Live FMP entitlement coverage remains optional and depends on `FMP_API_KEY` outside the repository.
- Backtest remains label-derived research evidence, not market replay execution.
