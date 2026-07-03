# FMP Live Operator Results

Status date: 2026-07-03

## Phase 18 Result

Phase 18 completed runtime-key live FMP bring-up on 2026-07-03. `FMP_API_KEY` was provided only through the runtime environment and was not written to tracked files, docs, exports, logs, provider metadata, or frontend bundles.

What was verified:

- `make doctor` reported only key presence, not the value.
- `make fmp-smoke` and `make fmp-live-smoke` completed with redacted metadata.
- Required endpoint rows persisted as `ACCESSIBLE` with HTTP 200.
- The latest required endpoint rows were operator-reviewed as `REVIEWED_ACCESSIBLE`.
- Review summary ended `READY`.
- Seed dry-run succeeded and live seed ran only after review readiness.
- Real quote snapshots, EOD bars, intraday bars, provider requests, ingestion runs, and dirty windows were persisted.
- Post-fix incremental intraday refresh ran twice with 0 inserts, 1976 updates per run, and flat bar count.
- Freshness checks persisted `STALE`, not `READY`, because bars are stale against strict thresholds and dirty build windows remain.
- A research-cycle dry-run and default run blocked on stale artifacts; `allow_stale=true` completed diagnostically without model activation.
- Backend, database, frontend, scheduler, export, compile, and secret-scan gates passed.

What remains gated:

- Freshness is still `STALE`.
- Research cycles should remain blocked by default until stale artifacts are rebuilt or `allow_stale=true` is an explicit operator decision.
- WebSocket production ingestion remains disabled.

## Phase 17 Result

The first Phase 17 operator execution did not prove live FMP entitlement because `FMP_API_KEY` was missing from the runtime shell.

What was verified:

- `.env` and `.env.local` are ignored.
- `make doctor` reports `FMP_API_KEY` only as missing.
- `make fmp-smoke` and `make fmp-live-smoke` skip safely without exposing secrets.
- Required endpoint rows persist as `SKIPPED_NO_KEY`.
- Review summary reports `BLOCKED`.
- Seed dry-run reports `dry_run` and `would_block=true` without provider calls.
- Freshness check persists `BLOCKED` from local data and capability-review state.
- Redacted entitlement, capability, quote snapshot, seed, freshness, and coverage exports are created with file hashes.
- Backend, database, frontend, scheduler, export, and secret-scan gates pass.

What was not verified:

- real endpoint accessibility;
- denied/rate-limited/empty live classifications;
- operator-reviewed accessible live rows;
- live seed ingestion;
- quote snapshot, EOD, or intraday counts from real FMP responses;
- incremental intraday duplicate avoidance on real FMP data;
- real-data research-cycle freshness gating.

## Current Endpoint Evidence

| Endpoint key | Measured status | HTTP | Sample count | Operator review |
| --- | --- | ---: | ---: | --- |
| `quote` | `ACCESSIBLE` | 200 | 1 | `REVIEWED_ACCESSIBLE` |
| `quote_short` | `ACCESSIBLE` | 200 | 1 | `REVIEWED_ACCESSIBLE` |
| `batch_quote` | `ACCESSIBLE` | 200 | 4 | `REVIEWED_ACCESSIBLE` |
| `batch_quote_short` | `ACCESSIBLE` | 200 | 4 | `REVIEWED_ACCESSIBLE` |
| `historical_eod_full` | `ACCESSIBLE` | 200 | 6 | `REVIEWED_ACCESSIBLE` |
| `intraday_1min` | `ACCESSIBLE` | 200 | 1170 | `REVIEWED_ACCESSIBLE` |
| `intraday_5min` | `ACCESSIBLE` | 200 | 468 | `REVIEWED_ACCESSIBLE` |
| `intraday_15min` | `ACCESSIBLE` | 200 | 156 | `REVIEWED_ACCESSIBLE` |

Review summary: `READY`, 8 reviewed accessible, 0 blocked, 0 missing, 0 unreviewed.

## Latest Real-Data Evidence

- Initial full seed: `ingestion_67f0fb86daeb3de661eb7d4d91d39c79`, `COMPLETED`, 12009 fetched, 12009 inserted, 41 provider requests, 0 errors.
- Current persisted bars: 11999.
- Current quote snapshots: 10.
- Post-fix incremental runs: `ingestion_97a9a4a054f4585fffc19aa0d540ed74` and `ingestion_4907dd2706ac17c9e11192e0f66628f5`, each 1976 fetched, 0 inserted, 1976 updated.
- Latest default freshness: `STALE`, 0 missing, 40 stale groups, 400 dirty windows.
- Latest research-cycle-scope freshness: `STALE`, 0 missing, 12 stale groups, 160 dirty windows.

No broker execution, order routing, production WebSocket ingestion, automatic activation, self-learning behavior, or profitability claim is part of this flow.
