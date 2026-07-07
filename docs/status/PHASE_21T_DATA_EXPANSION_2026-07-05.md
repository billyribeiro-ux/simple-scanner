# Phase 21T Data Expansion Report - 2026-07-05

`DATA_EXPANSION_STATUS = PARTIAL_BLOCKED_PROVIDER_DEPTH`

## Scope

- Database: `adaptive_market_decoder_evidence`
- Role: `evidence`
- Symbols: `SPY`, `QQQ`, `AAPL`, `NVDA`
- Intervals: `1day`, `1min`, `5min`, `15min`
- Provider: FMP REST only
- Key source: runtime environment or ignored `.env.local`

## Capability Review

The latest Phase 21T capability review returned `ok`. Reviewed accessible endpoints were:

- `quote`
- `quote_short`
- `batch_quote`
- `batch_quote_short`
- `historical_eod_full`
- `intraday_1min`
- `intraday_5min`
- `intraday_15min`

No API key was written to tracked files, query strings, provider metadata, docs, or exports.

## Seed Runs

| Run | Window | Fetched | Inserted | Updated | Status |
|---|---|---:|---:|---:|---|
| `ingestion_2afbc605111ecaefa01a13fa450510cd` | 2026-06-18 to 2026-06-22 | 2404 | 2400 | 4 | `COMPLETED` |
| `ingestion_9572060015dad11e79d3085ab426d74f` | 2026-06-23 to 2026-06-27 | 4804 | 4800 | 4 | `COMPLETED` |
| `ingestion_c39f5b6ce1009948805ef4520717ef7b` | 2026-06-28 to 2026-07-02 | 6364 | 2400 | 3964 | `COMPLETED` |
| `ingestion_cebbfd68034d90851bb1f44b758af758` | incremental rerun | 1976 | 0 | 1976 | `COMPLETED` |

## Coverage

| Interval | Rows | Dates | Per-Symbol Rows |
|---|---:|---:|---:|
| `1day` | 40 | 10 | 10 |
| `1min` | 9360 | 6 | 2340 |
| `5min` | 3120 | 10 | 780 |
| `15min` | 1040 | 10 | 260 |

The 10-day target was met for `1day`, `5min`, and `15min`. The `1min` target was not met because the provider returned rows for only six RTH dates in the bounded windows.

## Final Data Status

Final bar count is `13560`, all from live provider data, with `0` fixture rows in the evidence audit. Dirty windows were created after ingestion and cleared by the rebuild phase.
