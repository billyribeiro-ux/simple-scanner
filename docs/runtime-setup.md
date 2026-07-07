# Runtime Setup

Status date: 2026-07-02

## Pinned Runtime

- Node target: `24.18.0`
- Package manager: `pnpm@11.9.0` through Corepack
- Python target: `3.14.6`
- Python note: `3.14.6` is documented as the latest stable Python release for this project as of June 30, 2026.

Local audit result:

- Target Node available through NVM: `source "$HOME/.nvm/nvm.sh" && nvm use 24.18.0`.
- Current Homebrew Node: `25.3.0`; on 2026-07-01 it aborts before Corepack can run because a `simdjson` dynamic library is missing. Do not use it for frontend acceptance.
- Current Python: `python3.14 --version` reports `3.14.6`.
- Backend venv: `services/quant-engine/.venv` exists and reports Python `3.14.6`.
- Docker: reachable in the Phase 14 shell through the `desktop-linux` Docker Desktop context.
- Postgres/TimescaleDB and Redis: verified healthy through Docker Compose on 2026-07-02.
- Postgres host port: `15432`.
- `FMP_API_KEY`: optional; live FMP smoke skips when it is not configured.
- `DATABASE_URL`: optional; no URL selects SQLite local, while a Postgres URL selects the Postgres repository runtime.

## First Checks

```bash
source "$HOME/.nvm/nvm.sh"
nvm use 24.18.0
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack prepare pnpm@11.9.0 --activate
make frontend-doctor
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

`make db-inspect` confirms the Alembic revision, expected table count, critical indexes, unique constraints, selected columns, JSON columns, and installed extensions. The expected Phase 14 head is `0010_phase14_scheduler_worker`.

On 2026-07-02 Phase 14 verification, `docker context ls`, `docker info`, `docker compose config`, `docker compose up -d postgres redis`, `docker compose ps`, `nc -zv localhost 15432`, `make db-migrate`, `make db-inspect`, `make db-query-diagnostics`, `make api-smoke-postgres`, and `make repository-parity-test` passed.

Read-only query diagnostics:

```bash
make db-diagnostics
```

Bounded local scheduler worker:

```bash
make scheduler-worker-once
make scheduler-recover-stale
```

The worker command runs once and exits. It uses persisted scheduler leases and does not create a daemon, cron, infinite loop, automatic proposal approval, automatic model activation, broker execution, or order routing.

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
make replay-sensitivity-test
```

Frontend gates:

```bash
source "$HOME/.nvm/nvm.sh"
nvm use 24.18.0
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack prepare pnpm@11.9.0 --activate
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm install --frozen-lockfile
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm check
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm build
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm test
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm lint
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm --filter @amd/web test:e2e
```

Root package scripts and Playwright's `webServer.command` call `corepack pnpm` internally so nested workspace commands stay on `pnpm@11.9.0`.

Optional live FMP smoke:

```bash
make fmp-smoke
```

Set `FMP_API_KEY` only in the shell or ignored local env files such as `.env.local`. Never commit, log, print, export, or expose the key in frontend bundles.

## Phase 15 FMP Runtime

Run `make fmp-smoke` or `make fmp-live-smoke` after setting `FMP_API_KEY` in the shell or ignored local env files. If the key is absent, smoke skips successfully. WebSocket probes remain disabled unless `AMD_ENABLE_FMP_WS_PROBE=true`.

## Phase 16 Runtime Notes

Target runtime remains Node `24.18.0`, pnpm `11.9.0`, and Python `3.14.6`. Live entitlement and live seed require `FMP_API_KEY`. Seed dry-run and freshness checks can run without it.
## Phase 19C Runtime Notes - 2026-07-04

- Backend target Python remains `3.14.6`; Homebrew `python@3.14` provides `/opt/homebrew/opt/python@3.14/bin/python3.14` on this workstation.
- `make setup-backend` now recreates the generated venv with `python -m venv --clear` so interpreter changes are applied to `services/quant-engine/.venv`.
- Redis compose host port is configurable with `REDIS_HOST_PORT`; the default is `16379` to avoid local services already using `6379`.
- `make doctor` reports the selected Python 3.14 interpreter and configured Redis host port.
