# Phase 17 Live FMP Results

Date: 2026-07-01
Execution timestamp: 2026-07-03T01:03Z

## Result

Live FMP entitlement execution is `BLOCKED-NO-KEY` in this shell because `FMP_API_KEY` is missing from the runtime environment. No chat-provided key was copied into commands, docs, env files, databases, exports, scheduler payloads, frontend bundles, or logs.

`.env` and `.env.local` are git-ignored. Git status did not show tracked env files.

## Smoke Commands

Both smoke commands were run and skipped safely:

- `make fmp-smoke`
- `make fmp-live-smoke`

The smoke output reported `FMP_API_KEY not configured; live FMP REST smoke skipped safely.`

## Endpoint Matrix

| Endpoint key | Status | HTTP status | Sample count | Latency | Live accessibility |
| --- | --- | --- | --- | --- | --- |
| `quote` | `SKIPPED_NO_KEY` | none | 0 | 0 ms | Unknown |
| `quote_short` | `SKIPPED_NO_KEY` | none | 0 | 0 ms | Unknown |
| `batch_quote` | `SKIPPED_NO_KEY` | none | 0 | 0 ms | Unknown |
| `batch_quote_short` | `SKIPPED_NO_KEY` | none | 0 | 0 ms | Unknown |
| `historical_eod_full` | `SKIPPED_NO_KEY` | none | 0 | 0 ms | Unknown |
| `intraday_1min` | `SKIPPED_NO_KEY` | none | 0 | 0 ms | Unknown |
| `intraday_5min` | `SKIPPED_NO_KEY` | none | 0 | 0 ms | Unknown |
| `intraday_15min` | `SKIPPED_NO_KEY` | none | 0 | 0 ms | Unknown |

Grouped counts:

- `ACCESSIBLE`: 0
- `DENIED`: 0
- `RATE_LIMITED`: 0
- `EMPTY`: 0
- `ERROR`: 0
- `SKIPPED_NO_KEY`: 8

## Operator Review

The no-key smoke persisted skipped capability rows. The local review summary reported:

- status: `BLOCKED`
- blocked endpoints: 8
- unreviewed endpoints: 0
- reviewed accessible endpoints: 0

No endpoint was marked `REVIEWED_ACCESSIBLE`; accessibility was not faked.

## WebSocket

WebSocket probing was not enabled. `AMD_ENABLE_FMP_WS_PROBE` was not set to `true`, and no production WebSocket ingestion was attempted.

## Secret Handling

No key value appeared in smoke output. The smoke and export paths used only non-secret status fields and redacted metadata.
