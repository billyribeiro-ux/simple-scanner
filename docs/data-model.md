# Data Model

Core storage is designed around PostgreSQL with TimescaleDB when available. If the Timescale extension is not available, the same tables function as plain PostgreSQL tables. Phase 5 verifies Alembic revision `0002_phase5_indexes`, 17 expected tables, critical indexes, unique constraints, JSON columns, and `timescaledb` against the local compose database. The API repository runtime supports both SQLite local storage and PostgreSQL.

## Tables

- `symbols`: normalized symbol metadata and active flag.
- `bars`: interval OHLCV bars with UTC/ET timestamps, source, ingestion time, and quality flags.
- `features`: per-symbol timestamp feature payloads with feature-set version and data-quality flags.
- `candidate_signals`: deterministic setup candidates emitted before labeling/scoring.
- `labels`: leakage-safe hypothetical trade outcomes.
- `validation_reports`: validation or backtest report summaries, leakage warnings, activation decision, and rejection reasons.
- `validation_windows`: walk-forward or chronological validation windows tied to a validation report.
- `model_runs`: model versions, training windows, feature set, label config, activation state.
- `model_artifacts`: model artifact metadata and local path tracking.
- `active_models`: the current active model pointer by model type and strategy scope.
- `live_signals`: current signal/trade-plan rows with all required live output fields.
- `closed_signals`: completed signal outcomes and realized R.
- `scanner_runs`: scanner start/stop status, symbols, threshold, active model version, and run stats.
- `daily_reviews`: end-of-day review artifacts and recommendations.
- `provider_requests`: redacted request accounting and provider health.
- `exports`: generated CSV/XLSX artifact metadata.

## Signal Fields

Signals include timestamp, ticker, side, entry/stop/targets, R metrics, confidence, grade, setup type, market and ticker regime, reasons, warnings, historical sample metrics, model metadata, status, exit fields, and realized R.

## Phase 5 Indexes And Constraints

`make db-inspect` verifies the migration revision plus critical lookup indexes on bars, features, labels, live signals, validation reports, and scanner runs. It also verifies the unique constraints that preserve idempotent upserts for bars, features, candidate signals, labels, and active model scope.
