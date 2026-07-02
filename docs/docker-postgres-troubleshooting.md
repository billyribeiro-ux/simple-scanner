# Docker And Postgres Troubleshooting

Status date: 2026-07-01

Phase 13 verified that the compose file renders cleanly, but this shell still cannot reach Docker Desktop because `unix:///Users/billyribeiro/.docker/run/docker.sock` does not exist. Postgres on `localhost:15432` refuses connections while the daemon is unavailable.

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

Observed blocker in this run:

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
- `make db-migrate` upgrades to `0009_phase13_scheduler`.
- `make db-inspect` reports no missing scheduler tables, indexes, constraints, JSON columns, or Timescale hypertable state.

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
