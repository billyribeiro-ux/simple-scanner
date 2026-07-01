# Adaptive Market Decoder

Adaptive Market Decoder is a local-first trading research and live signal platform for a small, high-liquidity symbol universe. It produces evidence-based trade plans only; it does not place orders or integrate with brokers.

## Requirements

- Node.js `24.18.0`
- pnpm via Corepack
- Python `3.14.6`, the latest stable Python release as of June 30, 2026
- Docker for PostgreSQL/TimescaleDB and Redis
- Optional FMP API key in `FMP_API_KEY` for live provider smoke and live scanner use

## Setup

```bash
cp .env.example .env.local
# edit .env.local and set FMP_API_KEY
make doctor
make setup-backend
corepack pnpm install
make db-up
make db-migrate
make db-inspect
make api-smoke
```

`make doctor` does not print secrets. It reports whether `FMP_API_KEY` and `DATABASE_URL` are present.

## Run

```bash
make dev
```

Frontend: `http://localhost:5173`

Backend: `http://localhost:8000`

## Commands

```bash
corepack pnpm install
corepack pnpm dev
corepack pnpm build
corepack pnpm check
corepack pnpm test
corepack pnpm lint

make doctor
make setup-backend
make quant-test
make ingest
make features
make labels
make train
make validate
make backtest
make scanner
make export
make db-inspect
make api-smoke
make fmp-smoke
make test
```

`make quant-test` runs pure deterministic quant tests without FMP, Docker, Redis, Postgres, or internet. If the backend venv is missing, it falls back to `python3` for this pure test path only. Full backend runtime still targets Python `3.14.6`.

`make api-smoke` runs a persisted FastAPI vertical slice with a mocked provider. It does not require FMP, internet, or secrets.

`make fmp-smoke` is optional and runs live FMP REST checks only when `FMP_API_KEY` is configured. Otherwise it skips with a non-secret message.

## Persistence Contract

FastAPI currently uses the SQLite repository backend by default at `data/local_repo.sqlite3`. `GET /health`, `GET /config`, and `make doctor` report the active persistence backend without printing secrets or connection strings.

PostgreSQL/TimescaleDB migrations are verified through Alembic on the local compose database mapped to host port `15432`, but the active API repository implementation is still SQLite-only. Postgres-backed repository runtime is the next major persistence task.

## Typical Workflow

1. Set `FMP_API_KEY` in your shell or ignored env file.
2. Start services with `make db-up`.
3. Ingest bars through the Training page or `POST /data/ingest`.
4. Build features and labels.
5. Train and validate a model.
6. Activate only a passing model.
7. Start the scanner.
8. Export live signals, history, backtests, or daily reviews.

## Default Universe

`AMZN, AAPL, TSLA, SPY, QQQ, IWM, NVDA, GOOGL, BABA, SHOP`

`APPL` is normalized to `AAPL`.
