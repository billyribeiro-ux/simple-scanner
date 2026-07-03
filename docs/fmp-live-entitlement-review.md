# FMP Live Entitlement Review

Phase 16 separates measured provider access from operator review.

## Safe Setup

Set `FMP_API_KEY` only in the runtime shell or an ignored env file. Do not put it in committed files, frontend code, request URLs, docs, exports, or logs.

```bash
export FMP_API_KEY="..."
```

The FMP client uses header auth only. Query-string API keys are stripped before requests and provider metadata is redacted.

## Run Capability Checks

```bash
curl -s -X POST http://localhost:8000/provider/capabilities/check \
  -H 'content-type: application/json' \
  -d '{"symbols":["SPY","QQQ","AAPL","NVDA"],"endpoint_keys":["quote","quote_short","batch_quote","batch_quote_short","historical_eod_full","intraday_1min","intraday_5min","intraday_15min"]}'
```

If `FMP_API_KEY` is absent, rows persist with `SKIPPED_NO_KEY`. If present, each endpoint records status, HTTP status, latency, sample count, response shape, and non-secret entitlement notes.

## Review Capability Rows

Review does not change the measured provider result. It adds only:

- `operator_review_status`
- `reviewed_by`
- `reviewed_at`
- `review_notes`

```bash
curl -s -X POST http://localhost:8000/provider/capabilities/{check_id}/review \
  -H 'content-type: application/json' \
  -d '{"operator_review_status":"REVIEWED_ACCESSIBLE","reviewed_by":"local-operator","review_notes":"sample rows and shape reviewed"}'
```

Valid statuses are `UNREVIEWED`, `REVIEWED_ACCESSIBLE`, `REVIEWED_PARTIAL`, `REVIEWED_BLOCKED`, `REVIEWED_RATE_LIMITED`, and `REVIEWED_UNUSABLE`.

## Readiness Summary

```bash
curl -s http://localhost:8000/provider/capabilities/review-summary
```

`READY` means all required endpoints have a usable provider result and are marked `REVIEWED_ACCESSIBLE`. `UNREVIEWED`, `PARTIAL`, or `BLOCKED` prevents live seed ingestion unless the operator explicitly overrides the review guard.

WebSocket remains disabled by default and is not used for production ingestion.

## Phase 17 Operator Result

On 2026-07-03, `FMP_API_KEY` was missing from the runtime shell. `make fmp-smoke` and `make fmp-live-smoke` ran and skipped safely. All required endpoint rows were persisted as `SKIPPED_NO_KEY`, review summary reported `BLOCKED`, and no endpoint was marked `REVIEWED_ACCESSIBLE`.

Live endpoint accessibility remains unknown until a runtime key is loaded outside tracked files and the capability check is rerun. Do not review skipped rows as accessible.

## Phase 18 Operator Result

On 2026-07-03, a runtime-only `FMP_API_KEY` was provided and the entitlement flow was rerun. All eight required REST endpoints returned `ACCESSIBLE` with HTTP 200 and usable sample counts. The latest measured rows were reviewed as `REVIEWED_ACCESSIBLE`, and the persisted review summary ended `READY`.

Latest reviewed sample counts:

| Endpoint | Sample count |
| --- | ---: |
| `quote` | 1 |
| `quote_short` | 1 |
| `batch_quote` | 4 |
| `batch_quote_short` | 4 |
| `historical_eod_full` | 6 |
| `intraday_1min` | 1170 |
| `intraday_5min` | 468 |
| `intraday_15min` | 156 |

Do not infer future entitlement from this result without rerunning the capability check. Provider plans and market-data availability can change.
