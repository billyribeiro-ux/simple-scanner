# Adaptive Market Decoder

Adaptive Market Decoder is a local-first trading research and live signal platform for a small, high-liquidity symbol universe. It produces evidence-based trade plans only; it does not place orders or integrate with brokers.

## Requirements

- Node.js `24.18.0`
- pnpm via Corepack
- Python `3.13.14` recommended for quant packages
- Docker for PostgreSQL/TimescaleDB and Redis
- FMP API key in `FMP_API_KEY`

## Setup

```bash
cp .env.example .env.local
# edit .env.local and set FMP_API_KEY
make setup
make db-up
make db-migrate
```

## Run

```bash
make dev
```

Frontend: `http://localhost:5173`

Backend: `http://localhost:8000`

## Commands

```bash
pnpm install
pnpm dev
pnpm build
pnpm check
pnpm test
pnpm lint

make ingest
make features
make labels
make train
make validate
make backtest
make scanner
make export
make test
```

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
