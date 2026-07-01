# Runtime Setup

Status date: 2026-07-01

## Pinned Runtime

- Node target: `24.18.0`
- Package manager: `pnpm@11.5.2` through Corepack
- Python target: `3.14.6`
- Python note: `3.14.6` is documented as the latest stable Python release for this project as of June 30, 2026.

Local audit result:

- Current Node: `25.3.0`, so pnpm commands warn about unsupported engine.
- Current Python: system `python3` is `3.9.6`; `python3.14` is not installed.
- Backend venv: missing.
- Docker: reachable.
- Postgres/TimescaleDB and Redis: healthy after `docker compose up -d postgres redis`.
- `FMP_API_KEY`: missing from shell.
- `DATABASE_URL`: missing from shell.

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
- Docker daemon
- compose service status
- `DATABASE_URL`
- `FMP_API_KEY`
- ignored env/runtime artifact paths

## Backend Setup

Install Python `3.14.6`, then:

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

Run migrations after the backend venv exists:

```bash
make db-migrate
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

Pure quant tests can run without Docker, FMP, or backend venv:

```bash
make quant-test
```

Full backend gates require the Python `3.14.6` venv:

```bash
make backend-test
make backend-lint
make backend-typecheck
```

Frontend gates:

```bash
corepack pnpm check
corepack pnpm build
corepack pnpm test
corepack pnpm lint
```

## FMP Key

Set `FMP_API_KEY` only in the shell or ignored local env files such as `.env.local`.

Never commit, log, print, export, or expose the key in frontend bundles.
