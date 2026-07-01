# Adaptive Market Decoder Handoff

Report status date: 2026-07-01

## Executive State

Phase 3 backend runtime and persistence hardening is complete for code scope. The API source of truth is now repository-backed instead of route-level `_MEMORY`, scanner runs and signals persist, validation/model activation artifacts persist, export metadata persists, and runtime docs/commands have been hardened.

Full target-runtime verification is still blocked because Python `3.14.6` and `services/quant-engine/.venv` are missing on this machine. Docker is reachable and Postgres/TimescaleDB plus Redis are currently healthy.

This remains a local-first scanner, research, validation, backtest, signal, and export platform only. It is not a broker, auto-trader, order router, or profitability system.

## Runtime Pins

- Node target: `24.18.0`
- Package manager: `pnpm@11.5.2` through Corepack
- Python target: `3.14.6`, documented as the latest stable Python release for this project as of June 30, 2026
- Current local Node: `25.3.0`, which triggers engine warnings
- Current local Python: system `python3` is `3.9.6`; `python3.14` is not installed
- Backend venv: missing

## What Exists Now

- SvelteKit/Svelte 5 frontend with Dashboard, Research, Backtest, Scanner, Exports, and Settings pages.
- FastAPI quant engine with FMP provider abstraction, redacted client, feature builder, label builder, setup rules, regime classifier, statistical evidence model, signal scorer, scanner loop, backtest summary, and CSV/XLSX exports.
- Repository-backed local SQLite persistence for API runtime when Postgres is not configured.
- Aligned SQLAlchemy metadata and Alembic migration for PostgreSQL/TimescaleDB target.
- Docker Compose for TimescaleDB/Postgres and Redis.
- Validation/model activation guard based on persisted validation reports.
- Scanner persistence for runs, context bars during real runs, provider requests, and live signals.
- Export persistence for generated artifact metadata.

## Current Persistence Contract

See `docs/persistence-architecture.md`.

Implemented repositories cover:

- symbols
- bars
- features
- candidate signals
- labels
- validation reports
- model runs
- active models
- live signals
- scanner runs
- provider requests
- exports
- daily reviews

The API no longer uses `_MEMORY` as workflow state. SSE queue state remains transient delivery plumbing only.

## Runtime Commands

Primary commands:

```bash
make help
make doctor
make setup-backend
make db-up
make db-migrate
make quant-test
make backend-test
make backend-lint
make backend-typecheck
make api-dev
make web-dev
make dev
```

See `docs/runtime-setup.md` for the full runtime path.

## Checks Run

Passed:

- `make help`
- `make doctor` with expected missing target runtime warnings
- `docker compose config`
- `docker compose up -d postgres redis`
- `docker compose ps`: Postgres and Redis healthy
- `make quant-test`: 44 passed with system Python fallback
- `cd services/quant-engine && PYTHONPATH=. python3 -m pytest`: 51 passed
- `corepack pnpm check`
- `corepack pnpm build`
- `corepack pnpm test`
- `corepack pnpm lint`
- `python3 -m compileall services/quant-engine/app services/quant-engine/tests`
- `git diff --check`
- Secret scan for the supplied FMP key without echoing it

Blocked:

- `make setup-backend`: `python3.14` missing
- `make db-migrate`: backend venv missing
- `make backend-test`: backend venv missing
- `make backend-lint`: backend venv missing
- `make backend-typecheck`: backend venv missing

## FMP API Key Handling

The supplied FMP API key was not written to repository files. The project expects it at runtime as `FMP_API_KEY` in the shell or an ignored local env file such as `.env.local`.

Confirmed:

- `.env` and `.env.local` are ignored
- `FMP_API_KEY` is absent from the shell used during the audit
- secret scan found no occurrence of the supplied key in repository files

## Immediate Next Work

1. Install Python `3.14.6`.
2. Run `make setup-backend`.
3. Run `make backend-test`, `make backend-lint`, and `make backend-typecheck`.
4. Run `make db-migrate` against local Postgres/TimescaleDB.
5. Smoke-test repository-backed API flows with mocked or controlled FMP inputs.

## Exact Next Recommended Phase

Phase 4: Target Runtime Bring-Up, Migration Verification, and API Smoke Testing.

Start Phase 4 by installing Python `3.14.6`, creating the backend venv, running full backend quality gates, applying migrations to the healthy local Postgres service, and smoke-testing the persisted API vertical slice.
