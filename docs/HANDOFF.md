# Adaptive Market Decoder Handoff

## What Was Built

- Local-first monorepo for `billyribeiro-ux/simple-scanner`.
- SvelteKit/Svelte 5 dashboard with Dashboard, Research, Backtest, Scanner, Exports, and Settings pages.
- FastAPI quant-engine scaffold with FMP provider abstraction, redacted client, feature engine, labeling engine, regime classifier, setup rules, model/versioning scaffold, signal scorer, scanner loop, backtest metrics, CSV/XLSX exports, Alembic migration, and tests.
- Official-doc research notes for FMP capabilities and Svelte MCP availability.
- Docker Compose for TimescaleDB/Postgres and Redis.
- Root commands through pnpm and Make.

## Commands

```bash
corepack enable
corepack pnpm install
corepack pnpm dev
corepack pnpm check
corepack pnpm build
corepack pnpm test
corepack pnpm lint
```

Backend target runtime:

```bash
cd services/quant-engine
python3.13 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev,ml]"
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Database:

```bash
make db-up
make db-migrate
```

## FMP API Key

Set the key outside committed files:

```bash
cp .env.example .env.local
# edit .env.local and set FMP_API_KEY
```

The key is read only through `FMP_API_KEY`; it is not in frontend code, docs, package files, or tests.

## Ingest, Train, Scan, Export

- Ingest historical data: `POST /data/ingest`
- Build features: `POST /features/build`
- Build labels: `POST /labels/build`
- Train model: `POST /models/train`
- Validate model: `POST /models/validate`
- Activate model: `POST /models/activate`
- Start scanner: `POST /scanner/start`
- Stream signals: `GET /signals/stream`
- Export signals: `POST /exports/signals.csv` or `POST /exports/signals.xlsx`
- Daily review: `POST /review/daily`

The current dashboard exposes the workflow controls and calls the backend when the user clicks refresh/start/export actions.

## Checks Run

- `corepack pnpm check` passed.
- `corepack pnpm build` passed.
- `corepack pnpm test` passed.
- `corepack pnpm lint` passed.
- Playwright smoke tests passed after installing Chromium.
- Browser verification passed: page content present, no Vite overlay, scanner controls visible, no console errors on initial load.
- `python3 -m compileall services/quant-engine/app services/quant-engine/tests` passed.
- Secret scan found no occurrence of the provided FMP key substring.

Backend pytest/ruff/mypy were not run because the machine only exposes Python `3.9.6`; the project targets Python `3.13.14` and requires Python `>=3.11`.

## Known Limitations

- The repository is built locally but the connected GitHub app reports pull-only access, so pushing to `billyribeiro-ux/simple-scanner` must be done with your own Git credentials.
- V1 uses in-memory API workflow state as a scaffold while the PostgreSQL schema/migrations are present. The next backend hardening step is wiring repositories to persist bars, features, labels, model runs, signals, and exports.
- WebSocket streaming is intentionally entitlement-gated and not enabled by default.
- FMP gaps remain documented: OPRA options, gamma exposure, market internals, L2/order book, and dark-pool style feeds should be separate future provider adapters.
- The ML layer starts with rules/statistical evidence and a model artifact contract; a production classifier can be swapped into `ModelEngine` once enough labeled samples are available.

## Next Recommended Work

1. Run backend tests with Python `3.13.14`.
2. Persist the in-memory route workflow into PostgreSQL repositories.
3. Add live FMP entitlement checks using your local `FMP_API_KEY`.
4. Expand walk-forward validation and calibration reports.
5. Add provider adapters for non-FMP data categories only after verifying official provider capabilities.
