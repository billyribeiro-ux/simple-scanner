# Phase 14 Postgres Verification - 2026-07-01

Status date: 2026-07-02
Result: VERIFIED

## Infrastructure

Docker Desktop is reachable through the `desktop-linux` context. Local services are running through Docker Compose:

- Postgres/TimescaleDB: `adaptive-market-decoder-postgres`, host port `15432`, healthy
- Redis: `adaptive-market-decoder-redis`, host port `6379`, healthy

Verified commands:

```bash
docker context ls
docker info
docker compose config
docker compose up -d postgres redis
docker compose ps
nc -zv localhost 15432
```

`nc -zv localhost 15432` succeeded.

## Migration

Alembic was first verified through Phase 13:

```text
0008_phase11_research -> 0009_phase13_scheduler
```

Phase 14 then added and applied:

```text
0009_phase13_scheduler -> 0010_phase14_scheduler_worker
```

Expected head is now:

```text
0010_phase14_scheduler_worker
```

## Schema Inspection

`make db-inspect` passed:

```text
alembic_version=0010_phase14_scheduler_worker
tables=40
missing_tables=none
missing_indexes=none
missing_constraints=none
missing_columns=none
missing_json_columns=none
extensions=plpgsql,timescaledb
timescale_hypertables=bars
```

## Diagnostics

`make db-query-diagnostics` passed and reported non-secret row counts, recent replay/research/scheduler rows, and:

```text
alembic_version=0010_phase14_scheduler_worker
timescale_hypertables=bars
```

## Postgres Gates

Passed:

- `make api-smoke-postgres`
- `make repository-parity-test`
- `make db-inspect`
- `make db-query-diagnostics`

## Boundaries

No live FMP production ingestion was run. No broker execution, order routing, options data, WebSocket dependency, automatic proposal approval, or automatic model activation was added or verified.
