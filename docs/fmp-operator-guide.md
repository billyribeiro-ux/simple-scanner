# FMP Operator Guide

Status date: 2026-07-01

## Setup

Set `FMP_API_KEY` outside tracked files, for example in a local shell or ignored `.env.local`. Do not paste the key into commands, docs, exports, screenshots, or frontend environment variables.

## Smoke

```bash
make fmp-smoke
make fmp-live-smoke
```

If the key is missing, the smoke exits successfully with a safe skip message. If present, it probes quote, quote-short, batch quote, batch quote-short, EOD, and 1/5/15 minute intraday endpoints.

## Capability Check

```bash
curl -s -X POST http://localhost:8000/provider/capabilities/check \
  -H 'content-type: application/json' \
  -d '{"symbols":["SPY","QQQ","AAPL","NVDA"]}'
```

View:

```bash
curl -s http://localhost:8000/provider/capabilities
curl -s http://localhost:8000/provider/capabilities/history
```

## Ingestion

```bash
curl -s -X POST http://localhost:8000/data/ingest/fmp/eod \
  -H 'content-type: application/json' \
  -d '{"symbols":["SPY"],"start":"2026-06-01T00:00:00Z","end":"2026-06-05T00:00:00Z"}'

curl -s -X POST http://localhost:8000/data/ingest/fmp/intraday \
  -H 'content-type: application/json' \
  -d '{"symbols":["SPY"],"intervals":["1min"],"start":"2026-06-01T13:30:00Z","end":"2026-06-01T20:00:00Z"}'

curl -s -X POST http://localhost:8000/data/ingest/fmp/incremental-intraday \
  -H 'content-type: application/json' \
  -d '{"symbols":["SPY"],"intervals":["1min","5min","15min"]}'
```

## UI

- `/operations/provider`: key status, capability matrix, smoke, bounded ingestion actions, and latest ingestion runs.
- `/operations/data`: coverage, latest bars, missing windows, dirty windows, and data quality payload.

## Trust Boundary

Safe to trust: endpoint status, persisted request metadata, ingestion run counts, bar upsert idempotency, and local data coverage warnings.

Not safe to trust: entitlement without a live check, exchange-calendar-perfect missing window estimates, WebSocket production readiness, or any metric as a profitability claim.

## Phase 16 Operator Review And Freshness

Run capability checks, review required endpoints as `REVIEWED_ACCESSIBLE`, run seed dry-run, then run live seed only when the key and review gate are ready. `/operations/provider` contains review and seed controls. `/operations/data` contains freshness checks and quote snapshot tables. Research cycles block on `BLOCKED` or `STALE` freshness unless `allow_stale=true`.

## Phase 17 Operator Result

The 2026-07-03 operator attempt found `FMP_API_KEY` missing. Smoke targets skipped safely, the review summary was `BLOCKED`, seed dry-run would block, and freshness persisted `BLOCKED`. Load the key outside tracked files before the next live entitlement attempt. Do not mark skipped endpoint rows accessible.
