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
