# Phase 17 Real-Data Freshness

Date: 2026-07-01
Execution timestamp: 2026-07-03T01:03Z

## Result

Real-data freshness is `BLOCKED-NO-KEY` for live FMP ingestion in this shell. No live seed ingestion ran, so no new live quote snapshots, EOD bars, or intraday bars were inserted from FMP.

A local freshness check was still executed from persisted local data and capability-review state:

- freshness status: `BLOCKED`
- latest freshness report status: `BLOCKED`
- warning count: 2
- primary causes: missing required local data and capability review not ready

## Seed Dry-Run

Seed dry-run was executed without provider calls:

- status: `dry_run`
- `would_block`: `true`
- provider calls: none
- reason: capability review summary is `BLOCKED` because the runtime FMP key is missing

Live seed was not run because Phase 17 requires reviewed accessible endpoints before live seed unless performing an explicit controlled negative test.

## Live Seed Counts

Because live seed did not run:

- quote snapshots fetched/inserted/updated/skipped: not run
- EOD bars fetched/inserted/updated/skipped: not run
- intraday bars fetched/inserted/updated/skipped: not run
- incremental intraday refresh: not run
- duplicate avoidance on real data: not verified

Mocked regression tests still verify quote snapshot idempotency, bar upsert idempotency, seed gating, freshness states, and research-cycle freshness behavior.

## Research-Cycle Freshness Gates

No real-data research cycle was run because live FMP ingestion was blocked. Mocked regression gates passed and continue to verify:

- `BLOCKED` or `STALE` freshness blocks by default;
- `allow_stale=true` permits the cycle with warnings;
- quote freshness and capability-review gates are opt-in for research cycles unless configured.

## Exports

Redacted no-key exports were generated and export metadata was recorded:

| Export | Status | Rows | File hash |
| --- | --- | ---: | --- |
| entitlement review | `ok` | 8 | present |
| capability matrix | `ok` | 8 | present |
| quote snapshots | `ok` | 0 | present |
| seed ingestion | `ok` | 0 | present |
| freshness report | `ok` | 1 | present |
| data coverage | `ok` | 0 | present |

Export files remain ignored runtime artifacts. They were used for verification and are not committed.
