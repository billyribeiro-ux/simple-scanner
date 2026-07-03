# Data Quality Reporting

Status date: 2026-07-01

`GET /data/quality-report` summarizes persisted local data quality without querying FMP or exposing secrets.

## Checks

- duplicate symbol/interval/timestamp bars
- invalid OHLC or negative volume
- gaps larger than the expected interval
- dirty/stale pipeline build windows
- provider request errors

Query parameters:

- `symbols=AAPL,SPY`
- `intervals=1min,5min`
- `start=2026-06-01T13:30:00+00:00`
- `end=2026-06-01T20:00:00+00:00`
- `session=rth`

The report is intentionally conservative. Missing-bar detection is interval-gap based in V1 and does not claim exchange-calendar completeness.

## Phase 11 Governance Use

Research cycles call the data-quality report before comparison. Invalid price/volume findings and stale build windows become proposal gate evidence and cycle warnings.

`refresh_data=false` is the default and allows cycles to run with persisted data. If `refresh_data=true` and `FMP_API_KEY` is not configured, the cycle is blocked with a non-secret reason. Live provider credentials are never stored in cycle, proposal, ledger, status, or export payloads.

## Phase 13 Scheduler Use

The `data_quality_report` scheduler job calls the same persisted report path without requiring FMP. Job payloads can include symbols, intervals, start/end, and session. Results and job events are redacted before persistence, and a nested `refresh_data=true` request blocks before any provider request when `FMP_API_KEY` is missing.

## Phase 15 Provider Coverage

The report now includes:

- source breakdown by `Bar.source`
- latest bar timestamp per symbol/interval
- provider request summary
- ingestion run summary
- provider capability warnings
- recommended refresh steps

It still reads persisted local data only. It does not query FMP directly and does not claim exchange-calendar-perfect missing-window detection.

## Phase 16 Freshness Reports

`POST /data/freshness/check` persists a local freshness report using bars, quote snapshots, dirty pipeline windows, and capability review state. `GET /data/freshness/latest` returns the latest report. Research cycles include the report and block on stale or missing data by default.
