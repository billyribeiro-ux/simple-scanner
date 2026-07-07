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

At the end of Phase 17, real quote snapshot, EOD bar, intraday bar, and incremental-refresh counts were still unverified. Phase 18 superseded that state with a runtime-key live seed.

## Phase 18 Operator Result

On 2026-07-03, the runtime key was available and required endpoint review reached `READY`. Live seed then completed:

- Initial seed run: `ingestion_67f0fb86daeb3de661eb7d4d91d39c79`
- Status: `COMPLETED`
- Provider requests: 41
- Records fetched: 12009
- Records inserted: 12009
- Records updated: 0
- Errors: 0
- Warnings: 0

Current persisted local FMP data after Phase 18:

- Bars: 11999
- Quote snapshots: 10
- Provider request records: 182

Post-fix incremental intraday refresh over `SPY,QQQ,AAPL,NVDA` and `1min,5min,15min` ran twice with 1976 fetched, 0 inserted, and 1976 updated per run. Bar count stayed flat, confirming duplicate avoidance and corrected insertion/update accounting.

## Phase 19 Artifact Follow-Up

After Phase 18 ingestion, Phase 19 rebuilt local artifacts from persisted bars only:

- `features`: 11999 rows written from persisted bars.
- `candidate_signals`: 14976 candidate rows written on the final all-interval pass.
- `labels`: 2088 label rows written on the final all-interval pass.
- `replay`: strict intraday replay ran for the required research scope and optional default intraday scope.
- `1day` replay windows: marked not applicable because candidate market replay is intraday-only in V1.

Final dirty-window audit is 0. Future `1day` bar ingestion no longer marks replay windows dirty.

## Phase 19A Audit Result

On 2026-07-04, the committed Phase 18/19 seed and rebuild counts were present in docs, but the current checkout did not include the ignored runtime DB/export artifacts that would prove those counts. The fresh SQLite runtime has 0 bars and 0 quote snapshots. Recover or regenerate real-data artifacts before certifying Phase 19 complete.
## Phase 19C Seed Status - 2026-07-04

Bounded seed ingestion was not run in live mode because `FMP_API_KEY` is not configured. The safe Postgres FMP smoke recorded all required capability endpoints as `SKIPPED_NO_KEY`. After an operator configures an approved key, rerun bounded seed ingestion for SPY, QQQ, AAPL, and NVDA over `1min`, `5min`, `15min`, and `1day`; do not backfill with synthetic bars.
