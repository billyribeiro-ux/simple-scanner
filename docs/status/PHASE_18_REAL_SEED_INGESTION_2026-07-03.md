# Phase 18 Real Seed Ingestion

Status date: 2026-07-03

## Result

Bounded live seed ingestion ran after the required FMP endpoints were measured and reviewed. The platform ingested real FMP quote snapshots, EOD bars, and intraday bars without broker execution, order routing, automatic model activation, or WebSocket production ingestion.

Default seed universe:

`AMZN,AAPL,TSLA,SPY,QQQ,IWM,NVDA,GOOGL,BABA,SHOP`

Default seed intervals:

`1day,1min,5min,15min`

## Full Seed Evidence

Initial full seed run:

- Aggregate ingestion run: `ingestion_67f0fb86daeb3de661eb7d4d91d39c79`
- Status: `COMPLETED`
- Provider requests: 41
- Records fetched: 12009
- Records inserted: 12009
- Records updated: 0
- Errors: 0
- Warnings: 0
- Dirty windows: 400

Child runs:

| Type | Status | Provider requests | Fetched | Inserted | Updated | Dirty windows |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `quote_snapshot` | `COMPLETED` | 1 | 10 | 10 | 0 | 0 |
| `eod_bars` | `COMPLETED` | 10 | 40 | 40 | 0 | 160 |
| `intraday_bars` | `COMPLETED` | 30 | 11959 | 11959 | 0 | 400 |

Current persisted totals after the Phase 18 run:

- Bar rows: 11999
- Quote snapshots: 10
- Provider request records: 182

## Upsert Accounting Fix

During live incremental verification, bar table cardinality stayed flat while run metadata still reported repeated upsert attempts as inserts. The table was not duplicating rows; the ingestion-run accounting was imprecise.

Fix applied in `FMPLiveDataService`: bar ingestion now computes existing symbol/interval/timestamp/source keys before upsert and reports actual new keys as `records_inserted` and existing keys as `records_updated`.

Regression added:

- `test_ingest_intraday_idempotent_and_quality_coverage` now asserts first identical intraday ingest inserts 1 bar and the second inserts 0, updates 1.

Post-fix live incremental rerun:

| Run ID | Status | Fetched | Inserted | Updated | Provider requests | Dirty windows |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `ingestion_97a9a4a054f4585fffc19aa0d540ed74` | `COMPLETED` | 1976 | 0 | 1976 | 12 | 160 |
| `ingestion_4907dd2706ac17c9e11192e0f66628f5` | `COMPLETED` | 1976 | 0 | 1976 | 12 | 160 |

For the two post-fix incremental runs over `SPY,QQQ,AAPL,NVDA` and `1min,5min,15min`, bar count stayed flat at 4784 before, between, and after both runs.

## Later Seed Evidence

A later bounded seed run also completed:

- Aggregate ingestion run: `ingestion_411a614de72e2dd2ca5f76519dd2d5ab`
- Status: `COMPLETED`
- Provider requests: 17
- Records fetched: 4804
- Records inserted: 4800
- Records updated: 4
- Errors: 0
- Warnings: 0

The four updates were quote snapshot updates. This is expected for repeated quote snapshots on the same provider/symbol keys.
