# Phase 18 Live FMP Endpoint Matrix

Status date: 2026-07-03

## Result

`FMP_API_KEY` was supplied only through the runtime environment. No key value was written to tracked files, docs, exports, frontend bundles, provider metadata, or logs.

All required FMP REST endpoints were reachable with HTTP 200 and usable response shapes. The latest measured rows were reviewed as `REVIEWED_ACCESSIBLE`, and the persisted review summary ended `READY`.

WebSocket ingestion remained disabled. REST polling remains the V1 default.

## Latest Reviewed Matrix

| Endpoint | Status | HTTP | Sample count | Latest latency ms | Operator review |
| --- | --- | ---: | ---: | ---: | --- |
| `quote` | `ACCESSIBLE` | 200 | 1 | 374 | `REVIEWED_ACCESSIBLE` |
| `quote_short` | `ACCESSIBLE` | 200 | 1 | 196 | `REVIEWED_ACCESSIBLE` |
| `batch_quote` | `ACCESSIBLE` | 200 | 4 | 192 | `REVIEWED_ACCESSIBLE` |
| `batch_quote_short` | `ACCESSIBLE` | 200 | 4 | 180 | `REVIEWED_ACCESSIBLE` |
| `historical_eod_full` | `ACCESSIBLE` | 200 | 6 | 171 | `REVIEWED_ACCESSIBLE` |
| `intraday_1min` | `ACCESSIBLE` | 200 | 1170 | 217 | `REVIEWED_ACCESSIBLE` |
| `intraday_5min` | `ACCESSIBLE` | 200 | 468 | 201 | `REVIEWED_ACCESSIBLE` |
| `intraday_15min` | `ACCESSIBLE` | 200 | 156 | 193 | `REVIEWED_ACCESSIBLE` |

Persisted review summary:

- Status: `READY`
- Required endpoints: 8
- Reviewed accessible endpoints: 8
- Missing endpoints: 0
- Blocked endpoints: 0
- Unreviewed endpoints: 0

## Smoke Gates

`make fmp-smoke` and `make fmp-live-smoke` both completed with redacted provider metadata. Both returned `ACCESSIBLE` for the eight required endpoints. The latest smoke pass created fresh capability rows; those rows were then reviewed as accessible so persisted readiness ended `READY`.

## Security Notes

- Client auth mode: header auth.
- Query-string `apikey` values are stripped before provider requests.
- Provider metadata records request IDs, endpoint keys, latency, status, sample counts, and response shape only.
- Review notes intentionally contain no secret material.
