# Runtime Setup

Status date: 2026-07-01

## Pinned Runtime

- Node target: `24.18.0`
- Package manager: `pnpm@11.5.2` through Corepack
- Python target: `3.14.6`
- Python note: `3.14.6` is documented as the latest stable Python release for this project as of June 30, 2026.

Local audit result:

- Current Node: `25.3.0`; pnpm commands warn because the project target is Node `24.18.0`.
- Current Python: `python3.14 --version` reports `3.14.6`.
- Backend venv: `services/quant-engine/.venv` exists and reports Python `3.14.6`.
- Docker: reachable.
- Postgres/TimescaleDB and Redis: healthy after `docker compose up -d postgres redis`.
- Postgres host port: `15432`.
- `FMP_API_KEY`: optional; live FMP smoke skips when it is not configured.
- `DATABASE_URL`: optional; no URL selects SQLite local, while a Postgres URL selects the Postgres repository runtime.

## First Checks

```bash
make help
make doctor
```

`make doctor` checks:

- `.node-version`
- `.python-version`
- Node
- Corepack/pnpm with a timeout-safe probe
- `python3.14`
- backend venv
- backend venv tools: `pytest`, `ruff`, `mypy`, `alembic`, `uvicorn`
- backend dependency imports when the venv exists
- active API persistence backend selection
- Docker daemon and compose service status
- `DATABASE_URL`
- `FMP_API_KEY`
- ignored env/runtime artifact paths

## Python 3.14.6 Install

On this macOS machine, Python `3.14.6` was installed with Homebrew:

```bash
brew install python@3.14
python3.14 --version
```

Other safe local options:

```bash
pyenv install 3.14.6
pyenv local 3.14.6
```

```bash
asdf plugin add python
asdf install python 3.14.6
asdf local python 3.14.6
```

Do not create the target backend venv with system Python `3.9`.

## Backend Setup

```bash
make setup-backend
```

Equivalent manual commands:

```bash
cd services/quant-engine
python3.14 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev,ml]"
```

## Database

Start local services:

```bash
make db-up
```

Run migrations:

```bash
make db-migrate
make db-inspect
```

`make db-inspect` confirms the Alembic revision, expected table count, critical indexes, unique constraints, selected columns, JSON columns, and installed extensions. The current local result is:

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

Stop local services:

```bash
make db-down
```

Development-only reset:

```bash
make db-reset-dev
```

`db-reset-dev` deletes local compose volumes after a visible delay. It is not a production command.

## API Persistence Backend

The FastAPI repository implementation supports SQLite and PostgreSQL. With no `DATABASE_URL`, it writes to:

```text
data/local_repo.sqlite3
```

Safe runtime status is available from:

```bash
make doctor
curl http://localhost:8000/health
curl http://localhost:8000/config
```

With a Postgres `DATABASE_URL`, it uses the PostgreSQL repository runtime and verifies the migrated schema at startup. Postgres initialization failures are hard failures unless `AMD_ALLOW_SQLITE_FALLBACK=true`, in which case the runtime reports `sqlite-fallback-from-postgres`.

## API And Web

Backend:

```bash
make api-dev
```

Frontend:

```bash
make web-dev
```

Both, with database services:

```bash
make dev
```

## Tests And Quality

Pure quant tests:

```bash
make quant-test
```

Full backend gates:

```bash
make backend-test
make backend-lint
make backend-typecheck
make api-smoke
make api-smoke-sqlite
make api-smoke-postgres
make repository-parity-test
```

Frontend gates:

```bash
corepack pnpm check
corepack pnpm build
corepack pnpm test
corepack pnpm lint
```

Optional live FMP smoke:

```bash
make fmp-smoke
```

Set `FMP_API_KEY` only in the shell or ignored local env files such as `.env.local`. Never commit, log, print, export, or expose the key in frontend bundles.
