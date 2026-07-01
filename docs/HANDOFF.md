# Adaptive Market Decoder Handoff

Report status date: 2026-07-01

## Executive State

Adaptive Market Decoder V1 is now past scaffold-only status for the quant core: Phase 2 added pure quant schemas, grouped no-leakage feature computation, deterministic candidate detection, configurable label generation, chronological backtest metrics, a validation/activation gate, baseline evidence model metadata, scanner context hydration, repository interfaces, and pure quant regression tests.

It is still not a production-ready scanner or model platform. Full backend runtime remains unverified until Python `3.14.6`, the backend venv, and backend dependencies are installed.

The frontend checks and smoke tests pass. The backend source compiles syntactically, but backend tests and runtime validation are blocked in this environment because only Python 3.9.6 is installed while the project targets Python 3.14.6. Docker is also unavailable, so PostgreSQL/TimescaleDB and Redis were not started and migrations were not verified.

## Runtime Pins

- Node target: `24.18.0`
- Package manager: `pnpm@11.5.2` through Corepack
- Python target: `3.14.6`, documented as the latest stable Python release for this project as of June 30, 2026
- Current local Node: `25.3.0`, which triggers engine warnings
- Current local Python: `python3` is `3.9.6`; `python3.14` is not installed
- `uv` is not installed

Use `corepack pnpm`, not the bare `pnpm` shim. The bare `pnpm --version` command hung while trying to bootstrap itself.

## What Exists

- SvelteKit/Svelte 5 frontend with Dashboard, Research, Backtest, Scanner, Exports, and Settings pages.
- FastAPI quant-engine source with FMP provider abstraction, redacted client, feature builder, label builder, setup rules, regime classifier, statistical model scaffold, signal scorer, scanner loop, backtest summary, and CSV/XLSX exports.
- Phase 2 quant foundation: `app/quant/types.py`, grouped features, candidate signals, no-leakage labels, chronological backtest metrics, validation engine, activation gate, scanner historical context, and pure quant tests.
- Alembic migration and SQLAlchemy schema files for the intended storage model.
- Docker Compose for TimescaleDB/Postgres and Redis.
- Research documentation for FMP and Svelte.
- Secret handling through `FMP_API_KEY` only.

## What Is Still Scaffolded

- API workflow state is in memory, not persisted to PostgreSQL.
- Live scanner now hydrates historical context before scoring, but live FMP execution was not verified without `FMP_API_KEY`.
- Backtests now have a chronological trade-metric path over labels; full strategy simulation from raw candidates and bars is still partial.
- Model training writes statistical evidence artifacts with activation rejection reasons; there is no real scikit-learn classifier in the active path yet.
- WebSocket support is documented as entitlement-gated but not implemented.
- Several frontend pages are useful UI shells with limited backend wiring.
- Database schema/migration definitions are better aligned for features and labels, but migrations were not run against Postgres in this phase.

## Checks Run

Passed:

- `corepack pnpm install`
- `corepack pnpm check`
- `corepack pnpm build`
- `corepack pnpm test` pass, but no Vitest tests are currently discovered
- `corepack pnpm lint`
- `corepack pnpm --filter @amd/web exec playwright test`
- `python3 -m compileall services/quant-engine/app services/quant-engine/tests`
- `make doctor`
- `make quant-test`: 40 pure quant tests passed on the system Python fallback without FMP/Docker/Redis/Postgres
- `docker compose config`
- Secret scan for the provided FMP key substring

Failed or blocked:

- Full `python3 -m pytest` is blocked under system Python because backend dependencies such as `openpyxl` are not installed outside the target venv.
- `python3 -m ruff check .` fails because `ruff` is not installed.
- `python3 -m mypy app` fails because `mypy` is not installed.
- `make test` fails because `services/quant-engine/.venv/bin/python` does not exist.
- `make db-migrate` fails because `services/quant-engine/.venv/bin/alembic` does not exist.
- `docker compose up -d postgres redis` fails because the Docker daemon is not reachable.
- `make help` does not exist.

## FMP API Key Handling

The supplied FMP API key was not written to repository files. The project expects it at runtime as `FMP_API_KEY` in the shell or an ignored local env file such as `.env.local`.

Confirmed:

- `.env` is absent
- `.env.local` is absent
- `FMP_API_KEY` is absent from the shell used during the audit
- `.env` and `.env.local` are ignored
- Secret scan found no occurrence of the provided key substring in repository files

## How To Run Once The Local Toolchain Is Ready

Frontend:

```bash
make doctor
corepack pnpm install
corepack pnpm dev
```

Backend:

```bash
cd services/quant-engine
python3.14 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev,ml]"
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Pure quant tests without Docker/FMP:

```bash
make quant-test
```

Database:

```bash
docker compose up -d postgres redis
services/quant-engine/.venv/bin/alembic -c services/quant-engine/alembic.ini upgrade head
```

FMP key:

```bash
cp .env.example .env.local
# set FMP_API_KEY in .env.local without committing it
```

## Workflow Commands Once Backend Is Running

These commands assume the backend is available at `http://localhost:8000`. They are the intended workflow paths, but they were not end-to-end verified in this audit because Python `3.14.6`, the backend venv, Docker, and the FMP runtime environment were unavailable.

Ingest historical bars:

```bash
curl -X POST http://localhost:8000/data/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["AMZN", "AAPL", "TSLA", "SPY", "QQQ", "IWM", "NVDA", "GOOGL", "BABA", "SHOP"],
    "intervals": ["1min", "5min", "15min"],
    "start": "2026-06-01T09:30:00-04:00",
    "end": "2026-06-30T16:00:00-04:00"
  }'
```

Build features and labels:

```bash
curl -X POST http://localhost:8000/features/build
curl -X POST http://localhost:8000/labels/build
```

Train and optionally validate/activate the current statistical model scaffold:

```bash
curl -X POST http://localhost:8000/models/train \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["AMZN", "AAPL", "TSLA", "SPY", "QQQ", "IWM", "NVDA", "GOOGL", "BABA", "SHOP"],
    "training_start": "2026-06-01T09:30:00-04:00",
    "training_end": "2026-06-30T16:00:00-04:00",
    "activate_if_passes": false
  }'

curl -X POST "http://localhost:8000/models/validate"
```

Run the scanner:

```bash
curl -X POST http://localhost:8000/scanner/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["AMZN", "AAPL", "TSLA", "SPY", "QQQ", "IWM", "NVDA", "GOOGL", "BABA", "SHOP"],
    "confidence_threshold": 0.70
  }'

curl http://localhost:8000/scanner/status
curl http://localhost:8000/signals/live
curl -N http://localhost:8000/signals/stream
curl -X POST http://localhost:8000/scanner/stop
```

Export:

```bash
curl -X POST http://localhost:8000/exports/signals.csv \
  -H "Content-Type: application/json" \
  -d '{"kind": "live_signals"}'

curl -X POST http://localhost:8000/exports/signals.xlsx \
  -H "Content-Type: application/json" \
  -d '{"kind": "live_signals"}'

curl -X POST http://localhost:8000/exports/daily-review.xlsx \
  -H "Content-Type: application/json" \
  -d '{"kind": "daily_review"}'
```

## Immediate Next Work

1. Install Node `24.18.0` and Python `3.14.6`, then rebuild the backend virtual environment.
2. Install backend dependencies and run full `pytest`, `ruff`, and `mypy` through `services/quant-engine/.venv`.
3. Apply Alembic migrations against Postgres/TimescaleDB and verify schema compatibility.
4. Replace route-level `_MEMORY` workflow state with repository-backed persistence.
5. Connect validation reports and model activation to persisted model runs.
6. Add a true candidate-to-trade simulator over raw bars, not only labels.
7. Add real ML only after baseline evidence and walk-forward validation stay green.

## Next Recommended Prompt Focus

Focus the next build prompt on backend runtime and persistence hardening only: install/verify Python `3.14.6`, build the backend venv, run full backend quality gates, apply migrations, replace API `_MEMORY` with repositories, and persist validation/model artifacts.

See `docs/status/ARCHITECT_REPORT_2026-07-01.md` for the full principal/staff+ audit.
