# Phase 19D Real Data Seed - 2026-07-04

`PHASE_19_STATUS = ACCEPTED`

The Phase 19D seed used live FMP REST responses for SPY, QQQ, AAPL, and NVDA only. The provider key was loaded through ignored local runtime config and was not printed, committed, exported, written to provider metadata, or exposed to frontend code.

## Reviewed Capabilities

All required REST endpoints were measured as `ACCESSIBLE` with HTTP 200 and reviewed as `REVIEWED_ACCESSIBLE`:

- `quote`
- `quote_short`
- `batch_quote`
- `batch_quote_short`
- `historical_eod_full`
- `intraday_1min`
- `intraday_5min`
- `intraday_15min`

Capability review summary: `READY`.

## Seed Scope

- Symbols: SPY, QQQ, AAPL, NVDA
- Intervals: `1day`, `1min`, `5min`, `15min`
- Start: `2026-07-01T13:30:00+00:00`
- End: `2026-07-02T19:59:00+00:00`
- Broker execution: not used
- Production WebSocket ingestion: not used

## Persisted Runs

| Run | Type | Status | Fetched | Inserted | Updated |
|---|---|---|---:|---:|---:|
| `ingestion_10d4f575c1a12c80363350d1d73adbe9` | `seed_ingestion` | `COMPLETED` | 3964 | 3964 | 0 |
| `ingestion_45bd53a41b77459a89d3aae8596eed19` | `quote_snapshot` | `COMPLETED` | 4 | 4 | 0 |
| `ingestion_3a1f2cafc6592934d6554cc8571ca7f8` | `eod_bars` | `COMPLETED` | 8 | 8 | 0 |
| `ingestion_24d9e29008b8e5b58e22d571e6460f10` | `intraday_bars` | `COMPLETED` | 3952 | 3952 | 0 |
| `ingestion_98b1d1b1c9206bc49d1b2fb3ddd909b8` | `seed_ingestion` rerun | `COMPLETED` | 3964 | 0 | 3964 |
| `ingestion_a0fccadf7e35d55612abfc1ba20272f9` | `incremental_intraday_refresh` | `COMPLETED` | 1976 | 0 | 1976 |
| `ingestion_898c297f7b30045dff4d5b111661dabb` | `incremental_intraday_refresh` | `COMPLETED` | 1976 | 0 | 1976 |

## Persisted Counts

- Bars: 3960 total
- `1day`: 8
- `1min`: 3120
- `5min`: 624
- `15min`: 208
- Quote snapshots: 4
- Provider requests: 74

The seed rerun and both incremental refreshes inserted zero bars, leaving bar counts flat and proving idempotent persistence for the bounded window.
