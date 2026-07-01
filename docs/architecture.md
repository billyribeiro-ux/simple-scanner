# Architecture

Adaptive Market Decoder is a local-first research and signal platform. It is intentionally not a broker or auto-trader.

## Components

- `apps/web`: SvelteKit dashboard for scanner status, model metrics, research controls, backtests, exports, and settings.
- `services/quant-engine`: FastAPI service for data provider access, ingestion, feature building, labels, models, backtests, signals, reviews, and exports.
- `packages/shared`: TypeScript schemas shared by the web app.
- Repository layer: local durable SQLite fallback for API runtime plus aligned PostgreSQL/TimescaleDB schema and Alembic migration.
- PostgreSQL/TimescaleDB: durable relational and time-series storage.
- Redis: future queue/cache backend.
- DuckDB/Parquet: local research cache and portable datasets.

## Data Flow

1. FMP provider fetches quotes, intraday bars, and daily bars using a single redacting client.
2. Ingestion validates payloads, normalizes timestamps to UTC and America/New_York, and stores raw/normalized records.
3. Feature builder computes price structure, VWAP, ATR, relative volume, market context, ticker personality inputs, and regime features without future data.
4. Label builder evaluates candidate bars using future bars only after the candidate execution timestamp.
5. Validation and backtest services persist leakage warnings, chronological reports, and rejection reasons.
6. Model engine writes statistical evidence model runs, while activation requires an accepted persisted validation report.
7. Scanner polls quotes/bars, hydrates context from persisted bars first, suppresses weak or hostile-regime trades, persists typed trade plans, and streams them over SSE.
8. Replay orchestration can generate daily, rolling, anchored, or custom replay windows and persist per-window diagnostic results.
9. Calibration drift and model review services read persisted validation, replay, calibration, sensitivity, and comparison artifacts to produce advisory reports.
10. Data quality reporting summarizes persisted bar gaps, invalid rows, dirty pipeline windows, and provider request errors.
11. Export service reads persisted signals and research/review artifacts and writes CSV/XLSX/JSON workbooks plus export metadata.

## Safety Boundaries

- No broker routes.
- No order placement.
- No frontend secrets.
- No silent model activation.
- No random time-series shuffle.
- No route-level in-memory workflow source of truth.
- No model review report automatically activates or deactivates a model.
