# Phase 24 Data Expansion

`PHASE_24_DATA_EXPANSION_STATUS = COMPLETED_33_RTH_DATES`

FMP REST expansion used the existing reviewed header-auth provider path. The key was loaded through runtime settings from ignored `.env.local`; it was not printed, committed, exported, placed in query strings, or persisted in reports.

## Scope

- Provider: FMP REST
- Auth mode: header
- Symbols: `SPY`, `QQQ`, `AAPL`, `NVDA`
- Intervals: `15min`, `1day`
- Requested range: `2026-05-15T00:00:00+00:00` through `2026-07-03T23:59:59+00:00`
- Returned coverage: 33 RTH dates, `2026-05-15` through `2026-07-02`

## Ingestion Summary

| Metric | Value |
|---|---:|
| Ingestion runs | 11 |
| Provider requests | 148 |
| Records fetched | 3,564 |
| Records inserted | 2,484 |
| Records updated | 1,080 |
| Provider errors | 0 |

## Coverage After Expansion

| Interval | Rows per symbol | RTH dates | Min timestamp | Max timestamp |
|---|---:|---:|---|---|
| `15min` | 858 | 33 | `2026-05-15T13:30:00+00:00` | `2026-07-02T19:45:00+00:00` |
| `1day` | 33 | 33 | `2026-05-15T04:00:00+00:00` | `2026-07-02T04:00:00+00:00` |

## Source Run IDs

`ingestion_332459eaa64f08bd626fe8d16f3f054a`, `ingestion_32cf259a3ed34c358277cc1ec759e6ec`, `ingestion_437f953e0b1f9bd0af3b3de065f40d62`, `ingestion_8d9a5b29fb95f6ea06080960d201b7b3`, `ingestion_d25fa1730689348892da8593a9ff71ec`, `ingestion_4840502287a09682c915f1c6faba7725`, `ingestion_4064cdf22c62b2901a8de10e0cb3add8`, `ingestion_5cae0a38dfd58aa3732fe5c1217aae89`, `ingestion_529bb5ae81f5bcbf5fa5135091983490`, `ingestion_a12801e472122d216a865bd6735ab6f9`, `ingestion_22005c40ca5ff99d1ddd9b7cf164d873`.

No duplicate-key blocker, provider-depth blocker, or secret leak was observed.
