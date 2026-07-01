# Operational Hardening

Status date: 2026-07-01

## Scope

Phase 7 hardens replay operations without adding broker execution, order routing, options data, market internals, WebSockets, calibrated ML, self-learning behavior, or profitability claims.

## Database Revision

Postgres/Timescale targets Alembic revision:

```text
0004_phase7_audit
```

`make db-inspect` expects 23 tables, the Phase 7 replay sensitivity/comparison indexes, JSON columns, and `bars` as a Timescale hypertable when the extension is available.

The local verified result:

```text
alembic_version=0004_phase7_audit
tables=23
missing_tables=none
missing_indexes=none
missing_constraints=none
missing_columns=none
missing_json_columns=none
extensions=plpgsql,timescaledb
timescale_hypertables=bars
```

## New Tables

- `replay_sensitivity_runs`
- `replay_sensitivity_scenarios`
- `backtest_comparisons`

The existing `replay_runs` table also stores audit fields such as `config_hash`, `input_fingerprint`, `candidate_fingerprint`, and `stale_window_status_json`.

## Diagnostics

Use:

```bash
make db-diagnostics
```

This runs `scripts/db_query_diagnostics.py` and prints non-secret row counts, dirty-window counts, recent replay hashes, and Timescale hypertable status.

## Exports

Export records now include:

- `file_sha256`
- `workbook_sheets` for XLSX outputs
- row count
- source run ID
- source simulation type when available
- config hash and input fingerprint when available
- filters and warnings

Replay sensitivity exports:

- `POST /exports/sensitivity-summary.xlsx`
- `POST /exports/sensitivity-scenarios.csv`
- `POST /exports/sensitivity-scenarios.xlsx`
- `POST /exports/sensitivity-metrics.json`

The sensitivity summary workbook includes `Summary`, `Scenario Metrics`, `Worst Case`, `Median Case`, `Best Case`, `Fragility Flags`, `Gate Results`, `Config`, and `Warnings`.

## Remaining Operational Limits

- Timescale compression and retention policies are not enabled yet.
- FMP live entitlement remains unverified unless `FMP_API_KEY` is configured outside the repo and `make fmp-smoke` is run.
- Replay still uses OHLCV assumptions, not order book or queue simulation.
