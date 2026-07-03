# FMP Seed Ingestion

Phase 16 adds bounded real-data seed ingestion for the default V1 universe:

`AMZN,AAPL,TSLA,SPY,QQQ,IWM,NVDA,GOOGL,BABA,SHOP`

Default intervals are `1day,1min,5min,15min`. Intraday seed ingestion is capped at five days. `APPL` input is normalized to `AAPL`.

## Dry-Run

Dry-run does not call FMP and does not require `FMP_API_KEY`.

```bash
curl -s -X POST http://localhost:8000/data/ingest/fmp/seed \
  -H 'content-type: application/json' \
  -d '{"dry_run":true}'
```

The response includes the planned symbols, intervals, time window, required endpoints, and current operator-review readiness.

## Live Seed

Live seed requires:

- `FMP_API_KEY` configured in the runtime environment;
- required endpoints reviewed as `REVIEWED_ACCESSIBLE`, unless explicitly overridden;
- no API keys in query strings;
- no broker execution or model activation.

```bash
curl -s -X POST http://localhost:8000/data/ingest/fmp/seed \
  -H 'content-type: application/json' \
  -d '{"dry_run":false}'
```

The live seed writes:

- `quote_snapshots` for batch quotes;
- `bars` for EOD and intraday rows;
- `provider_requests` for redacted provider accounting;
- `ingestion_runs` for quote, EOD, intraday, and aggregate `seed_ingestion` summaries.

Rows are idempotent by symbol, interval, timestamp, and provider/source keys. Re-running seed updates existing rows instead of creating duplicate bars or quote snapshots.

## Scheduler

Queue a dry-run:

```bash
curl -s -X POST http://localhost:8000/scheduler/jobs \
  -H 'content-type: application/json' \
  -d '{"job_type":"fmp_seed_ingestion","payload":{"dry_run":true}}'
```

Queue live seed only after key and reviews are ready:

```bash
curl -s -X POST http://localhost:8000/scheduler/jobs \
  -H 'content-type: application/json' \
  -d '{"job_type":"fmp_seed_ingestion","payload":{"dry_run":false}}'
```

The scheduler is bounded and non-autonomous. It never activates models.

## Phase 17 Operator Result

On 2026-07-03, `FMP_API_KEY` was missing from the runtime shell. Seed dry-run returned `dry_run` with `would_block=true` and made no provider calls. Live seed was not run because required endpoints were `SKIPPED_NO_KEY` and review summary was `BLOCKED`.

Real quote snapshot, EOD bar, intraday bar, and incremental-refresh counts remain unverified until the runtime key is present and the required endpoints are reviewed accessible.
