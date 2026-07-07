# Data Quality Reporting

Status date: 2026-07-03

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

## Phase 17 Operator Result

The 2026-07-03 Phase 17 run did not ingest live FMP data because `FMP_API_KEY` was missing. `GET /data/quality-report` and no-key exports remain safe persisted-data paths, but real provider coverage and real missing-window conclusions remain unverified until bounded live seed succeeds.

## Phase 18 Operator Result

Bounded live FMP seed succeeded on 2026-07-03. `GET /data/quality-report` now reads real local FMP bars and provider accounting:

- Bars: 11999.
- Source breakdown: `fmp`.
- Latest bar groups: 40.
- Provider request records: 182.
- Quote snapshots: 10.

The quality and freshness reports intentionally remain conservative. Current freshness is `STALE` because strict age thresholds and dirty build windows are still active after ingestion.

## Phase 19 Operator Result

Phase 19 removed the dirty-window portion of the quality/freshness blocker:

- Initial dirty windows: 560.
- Final dirty windows: 0.
- Default freshness remains `STALE` from bar age only.
- Research-scope freshness is `READY`.

Use `GET /pipeline/dirty-windows` for an exportable artifact-specific audit before and after rebuilds. Use `docs/live-data-artifact-readiness.md` for the local-only rebuild order.

## Phase 19A Audit Result

On 2026-07-04, data-quality and Phase 19 tests passed, but runtime evidence was not present: current SQLite has 0 bars and 0 dirty-window rows, and Phase 19 exports are absent. Treat the Phase 19 data-quality/freshness repair as documentary evidence until real runtime artifacts are recovered or regenerated.
## Phase 19C Data Quality Note - 2026-07-04

The repaired Postgres runtime currently has no real bars or quote snapshots after synthetic verification rows were cleaned. Phase 19C data quality should therefore be read as missing-source evidence, not as a valid quality sample. Rebuild quality reports only after real FMP data is restored or ingested.
