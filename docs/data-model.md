# Data Model

Core storage is designed around PostgreSQL with TimescaleDB when available. If the Timescale extension is not available, the same tables function as plain PostgreSQL tables.

## Tables

- `symbols`: normalized symbol metadata and active flag.
- `bars`: interval OHLCV bars with UTC/ET timestamps, source, ingestion time, and quality flags.
- `quotes`: latest and historical quote snapshots.
- `features`: per-symbol timestamp feature payloads.
- `labels`: leakage-safe hypothetical trade outcomes.
- `regimes`: market and ticker regime snapshots.
- `model_runs`: model versions, training windows, feature set, label config, activation state.
- `model_metrics`: validation and backtest metrics by symbol/setup/regime/window.
- `live_signals`: current signal/trade-plan rows with all required live output fields.
- `closed_signals`: completed signal outcomes and realized R.
- `daily_reviews`: end-of-day review artifacts and recommendations.
- `provider_requests`: redacted request accounting and provider health.
- `exports`: generated CSV/XLSX artifact metadata.

## Signal Fields

Signals include timestamp, ticker, side, entry/stop/targets, R metrics, confidence, grade, setup type, market and ticker regime, reasons, warnings, historical sample metrics, model metadata, status, exit fields, and realized R.
