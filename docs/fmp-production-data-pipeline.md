# FMP Production Data Pipeline

Status date: 2026-07-01

Phase 15 adds a REST-only FMP ingestion path for provider verification and persisted market data. It is a scanner/research data pipeline only.

## Supported Jobs

- `quote_snapshot`: fetches batch quotes and records a provider request. No quote table exists in V1, so quote snapshots are audit/accounting records.
- `eod_bars`: fetches `historical-price-eod/full` and upserts `1day` bars.
- `intraday_bars`: fetches `historical-chart/1min`, `5min`, and `15min` and upserts bars.
- `incremental_intraday_refresh`: starts from the latest persisted bar per symbol/interval with a small overlap and upserts idempotently.
- `fmp_capability_check`: probes configured endpoint entitlement and persists redacted capability rows.

## Bounds

- Max symbols per run: 10.
- Intraday intervals: `1min`, `5min`, `15min`.
- Default intraday span: 5 days.
- WebSocket is not a production ingestion path.

## API

- `POST /data/ingest/fmp/quotes`
- `POST /data/ingest/fmp/eod`
- `POST /data/ingest/fmp/intraday`
- `POST /data/ingest/fmp/incremental-intraday`
- `GET /data/ingestion-runs`
- `GET /data/ingestion-runs/{ingestion_run_id}`

## Persistence

`ingestion_runs` records symbols, intervals, start/end, status, fetched/written/skipped counts, provider request IDs, dirty windows, warnings, and errors. Bars remain idempotent through the existing `(symbol, interval, timestamp_utc, source)` upsert key.

## Safety

The pipeline does not place orders, route orders, activate models, deploy models, claim profitability, or use WebSocket for production ingestion.

## Phase 16 Update

Phase 16 adds operator-reviewed entitlement, durable `quote_snapshots`, aggregate `seed_ingestion` runs, and persisted `data_freshness_reports`. Use `POST /data/ingest/fmp/seed` with `{"dry_run":true}` before live seed. Live seed requires `FMP_API_KEY` and reviewed accessible required endpoints unless an operator explicitly overrides the review guard.
