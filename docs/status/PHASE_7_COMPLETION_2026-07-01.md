# Phase 7 Completion - Replay Calibration Audit And Operational Hardening

Status date: 2026-07-01

## Summary

Phase 7 makes candidate market replay auditable, reproducible, sensitivity-tested, stale-aware, and explicitly selectable for validation. No frontend UI, broker execution, order routing, options data, market internals, WebSocket scope, calibrated ML, self-learning claims, or profitability claims were added.

## Delivered

- Added deterministic replay audit helpers for config hashes, input fingerprints, candidate fingerprints, git commit capture, and secret scrubbing.
- Added replay provenance fields to persisted replay payloads and `replay_runs`.
- Added `GET /pipeline/status`.
- Added stale replay input rejection by default, with explicit `allow_stale=true` override.
- Added explicit replay-run validation selection through `replay_run_id`, `replay_filter`, and `allow_latest_replay_fallback`.
- Added stale replay validation rejection by default, with explicit `allow_stale_replay_validation=true` override.
- Added replay sensitivity engine, persistence, APIs, exports, and validation gates.
- Added persisted label-vs-replay comparison API.
- Added export reproducibility metadata: file SHA-256, workbook sheets, source simulation metadata, filters, and warnings.
- Added Alembic revision `0004_phase7_audit`, SQLite parity schema, and Timescale hypertable creation for `bars` when available.
- Added `scripts/db_query_diagnostics.py` and `make db-diagnostics`.

## New Routes

- `GET /pipeline/status`
- `POST /backtest/replay/{replay_run_id}/sensitivity`
- `GET /backtest/replay/sensitivity/{sensitivity_run_id}`
- `GET /backtest/replay/sensitivity/{sensitivity_run_id}/scenarios`
- `GET /backtest/replay/{replay_run_id}/sensitivity`
- `POST /backtest/compare-label-vs-replay`
- `GET /backtest/comparisons/{comparison_id}`
- `POST /exports/sensitivity-summary.xlsx`
- `POST /exports/sensitivity-scenarios.csv`
- `POST /exports/sensitivity-scenarios.xlsx`
- `POST /exports/sensitivity-metrics.json`

## Database

`make db-inspect` verified:

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

## Verification Run

```text
make doctor
PASS with expected warnings: local Node is 25.3.0 while target is 24.18.0; DATABASE_URL and FMP_API_KEY are optional and not configured in the shell.

PYTHONPATH=services/quant-engine python3 -m compileall -q services/quant-engine/app scripts/inspect_db_schema.py scripts/db_query_diagnostics.py
PASS

cd services/quant-engine && .venv/bin/alembic upgrade head
PASS

cd services/quant-engine && PYTHONPATH=. .venv/bin/python -m pytest tests/quant/test_replay_sensitivity.py -q
3 passed

cd services/quant-engine && PYTHONPATH=. .venv/bin/python -m pytest tests/test_exports.py -q
3 passed

cd services/quant-engine && PYTHONPATH=. .venv/bin/python -m pytest tests/test_repository_parity.py -q
3 passed

cd services/quant-engine && PYTHONPATH=. .venv/bin/python -m pytest tests/test_persisted_api_smoke.py::test_persisted_api_vertical_slice_sqlite -q
1 passed, 1 warning

cd services/quant-engine && PYTHONPATH=. .venv/bin/python -m pytest tests/test_persisted_api_smoke.py::test_persisted_api_vertical_slice_postgres -q
1 passed, 1 warning

cd services/quant-engine && PYTHONPATH=. .venv/bin/python -m pytest -q
72 passed, 1 warning

cd services/quant-engine && .venv/bin/ruff check app tests
PASS

cd services/quant-engine && .venv/bin/mypy app
PASS

corepack pnpm check
PASS with expected Node target warning

corepack pnpm build
PASS with expected Node target warning

corepack pnpm test
PASS with expected Node target warning

corepack pnpm lint
PASS with expected Node target warning

PYTHONPATH=services/quant-engine services/quant-engine/.venv/bin/python scripts/inspect_db_schema.py
PASS

PYTHONPATH=services/quant-engine services/quant-engine/.venv/bin/python scripts/db_query_diagnostics.py
PASS

git diff --check
PASS

Secret scan
PASS; supplied FMP key fragments were absent from repo files, logs, exports, and frontend build output. Expected symbolic `FMP_API_KEY` references remain.
```

## Remaining Limits

- FMP entitlement remains unverified unless `make fmp-smoke` is run with `FMP_API_KEY` loaded from environment or ignored local env.
- Timescale compression/retention policies are documented as future hardening.
- Replay remains an OHLCV simulator with explicit assumptions. It is not execution-grade fill proof.
- Model confidence remains uncalibrated; no calibrated ML was added.
