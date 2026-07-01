# Architecture

Adaptive Market Decoder is a local-first research and signal platform. It is intentionally not a broker or auto-trader.

## Components

- `apps/web`: SvelteKit dashboard for scanner status, model metrics, research controls, backtests, exports, and settings.
- `services/quant-engine`: FastAPI service for data provider access, ingestion, feature building, labels, models, backtests, signals, reviews, and exports.
- `packages/shared`: TypeScript schemas shared by the web app.
- PostgreSQL/TimescaleDB: durable relational and time-series storage.
- Redis: future queue/cache backend.
- DuckDB/Parquet: local research cache and portable datasets.

## Data Flow

1. FMP provider fetches quotes, intraday bars, and daily bars using a single redacting client.
2. Ingestion validates payloads, normalizes timestamps to UTC and America/New_York, and stores raw/normalized records.
3. Feature builder computes price structure, VWAP, ATR, relative volume, market context, ticker personality inputs, and regime features without future data.
4. Label builder evaluates candidate bars using future bars only after the candidate execution timestamp.
5. Model engine combines transparent setup rules, statistical evidence, an ML classifier when available, regime classification, and a meta-scorer.
6. Scanner polls quotes/bars, suppresses weak or hostile-regime trades, emits typed trade plans, and streams them over SSE.
7. Export service writes CSV and XLSX workbooks.

## Safety Boundaries

- No broker routes.
- No order placement.
- No frontend secrets.
- No silent model activation.
- No random time-series shuffle.
