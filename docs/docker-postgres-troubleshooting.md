# Docker And Postgres Troubleshooting

Status date: 2026-07-02

Phase 14 verified Docker Desktop, local Postgres/TimescaleDB, and Redis from this shell. These steps remain the recovery checklist if Docker Desktop or the local database becomes unavailable again.

## Diagnosis Commands

```bash
docker context ls
docker info
docker compose config
docker compose up -d postgres redis
docker compose ps
lsof -i :15432
nc -zv localhost 15432
make doctor
```

Observed Phase 13 blocker that Phase 14 recovered:

```text
failed to connect to the docker API at unix:///Users/billyribeiro/.docker/run/docker.sock
```

## Recovery Steps

1. Start Docker Desktop from macOS.
2. Wait until Docker Desktop reports the daemon is running.
3. Confirm the active context:

```bash
docker context ls
docker info
```

4. If the active context points at a missing socket, switch context deliberately:

```bash
docker context use desktop-linux
```

5. Start local services:

```bash
make db-up
docker compose ps
```

6. Confirm Postgres port:

```bash
nc -zv localhost 15432
```

7. Run migrations and inspection:

```bash
make db-migrate
make db-inspect
make db-query-diagnostics
```

## Expected Healthy State

- `docker info` returns server information.
- `docker compose ps` shows Postgres and Redis running or healthy.
- `nc -zv localhost 15432` succeeds.
- `make db-migrate` upgrades to `0010_phase14_scheduler_worker`.
- `make db-inspect` reports no missing scheduler tables, indexes, constraints, JSON columns, or Timescale hypertable state.

Verified Phase 14 result:

```text
alembic_version=0010_phase14_scheduler_worker
missing_tables=none
missing_indexes=none
missing_constraints=none
missing_columns=none
missing_json_columns=none
extensions=plpgsql,timescaledb
timescale_hypertables=bars
```

## If It Still Fails

- Keep the exact error message.
- Do not paste database passwords or full `DATABASE_URL` values into logs.
- Run SQLite gates while Docker is unavailable:

```bash
make quant-test
make backend-test
make api-smoke-sqlite
make scheduler-test
```

SQLite fallback tests do not prove local Postgres health. They only preserve the local repository contract until Docker is reachable.
