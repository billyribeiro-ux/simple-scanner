# Phase 6 Completion - Candidate-To-Trade Replay And Incremental Hardening

Date: 2026-07-01

## Executive Summary

Phase 6 adds a second, explicit backtest mode: `candidate_market_replay`. The existing `label_derived` backtest remains for fast evidence, but replay now starts from persisted candidate signals, enters on the next bar, replays raw bars chronologically, persists taken and skipped candidates, and exports replay outputs from persisted rows.

The project remains local-first research software only. It is not a broker, order router, self-learning system, calibrated profitability system, or options/market-internals platform.

## What Changed

- Added `services/quant-engine/app/backtesting/replay.py` with replay config, run, decision, simulated trade, skip reason, intrabar policy, execution assumption, and metrics objects.
- Added replay tables, incremental build-window metadata, SQLite initialization, and Alembic revision `0003_phase6_replay`.
- Added replay repositories for replay runs, simulated trades, and pipeline build windows.
- Added `POST /backtest/replay`, replay detail/trade routes, and combined backtest run listing.
- Kept `POST /backtest/run` label-derived and explicit with `simulation_type = label_derived`.
- Added replay summary XLSX, replay trades CSV/XLSX, and replay metrics JSON exports.
- Added dirty/stale window metadata from bar upserts and scoped feature/label rebuild responses.
- Added `validation_mode` support for label-derived and candidate replay validation.
- Added replay, export, API smoke, repository parity, and incremental rebuild tests.

## Replay Engine Status

Implemented. Replay uses persisted bars, features, and candidate signals. It supports next-bar-open entry, RTH session filtering, signal-time context stops/targets, fixed-risk fallback, R-multiple targets, slippage/spread, same-bar conservative stop-first handling, time/session exits, overlap/portfolio limits, cooldowns, deterministic candidate priority, skip recording, MFE/MAE, drawdown, daily R, and per-symbol/setup/regime/time/side breakdowns.

## Replay Persistence Status

Implemented for SQLite and PostgreSQL through the repository abstraction:

- `replay_runs`
- `simulated_trades`
- `pipeline_build_windows`

`make db-inspect` expects Alembic revision `0003_phase6_replay` and verifies replay indexes plus JSON columns.

## Replay API Status

Implemented:

- `POST /backtest/replay`
- `GET /backtest/replay/{replay_run_id}`
- `GET /backtest/replay/{replay_run_id}/trades`
- `GET /backtest/runs`
- `GET /backtest/runs/{run_id}`

Responses carry explicit `simulation_type` values.

## Replay Export Status

Implemented:

- `POST /exports/replay-summary.xlsx`
- `POST /exports/replay-trades.csv`
- `POST /exports/replay-trades.xlsx`

The summary export writes XLSX plus metrics JSON. Metadata records source run ID, created time, filters, and simulation type.

## Incremental Pipeline Status

Implemented V1 metadata and scoped rebuild behavior. Bar upserts mark dirty windows for features, candidates, labels, and replay. Feature and label build services return stale ranges and built windows, and scoped rebuild tests prove unrelated symbols are not rebuilt. This is not yet a full job scheduler or warmup-aware incremental planner.

## SQLite/Postgres Parity Status

Repository parity now includes replay runs, taken/skipped simulated trades, and pipeline build windows. Postgres requires `make db-migrate` to advance the local compose database to `0003_phase6_replay`.

## Tests Added

- Pure replay unit tests for target/stop/time exits, same-bar ambiguity, skips, overlap, cooldown, slippage/spread, drawdown, daily series, and breakdown metrics.
- Repository parity replay persistence tests.
- API smoke replay route and replay export coverage.
- Export unit tests for replay CSV/XLSX/JSON artifacts and workbook sheets.
- Incremental build-window scoping tests.

## Commands Run

All practical Phase 6 gates were run on the local machine:

| Command | Result |
| --- | --- |
| `make help` | PASS |
| `make doctor` | PASS with expected warnings: local Node is `25.3.0` while target is `24.18.0`; `DATABASE_URL` and `FMP_API_KEY` are optional and not configured in the shell. |
| `make setup-backend` | PASS on Python `3.14.6`. |
| `docker compose config` | PASS |
| `docker compose up -d postgres redis` | PASS |
| `docker compose ps` | PASS; Postgres/TimescaleDB and Redis healthy. |
| `make db-migrate` | PASS; upgraded `0002_phase5_indexes -> 0003_phase6_replay`. |
| `make db-inspect` | PASS; revision `0003_phase6_replay`, 20 tables, no missing indexes/constraints/columns/JSON columns. |
| `make quant-test` | PASS; 55 passed. |
| `make backend-test` | PASS; 68 passed, 1 FastAPI/httpx deprecation warning. |
| `make backend-lint` | PASS |
| `make backend-typecheck` | PASS with existing async-iterator note in `app/data/fmp.py`. |
| `make api-smoke-sqlite` | PASS |
| `make api-smoke-postgres` | PASS |
| `make repository-parity-test` | PASS; SQLite/Postgres parity covered. |
| `make replay-test` | PASS; 10 passed. |
| `make export-test` | PASS; 2 passed. |
| `make fmp-smoke` | SKIPPED; `FMP_API_KEY` is not configured in the process environment. |
| `corepack pnpm check` | PASS with expected Node engine warning. |
| `corepack pnpm build` | PASS with expected Node engine warning. |
| `corepack pnpm test` | PASS with expected Node engine warning and no frontend test files. |
| `corepack pnpm lint` | PASS with expected Node engine warning. |
| `python3 -m compileall services/quant-engine/app services/quant-engine/tests` | PASS; `python3` is `3.14.6`. |
| `git diff --check` | PASS |
| Secret scan | PASS; 257 files scanned, 0 findings. |

## Blockers

No source blocker is known. Postgres tests fail honestly if the local compose database is reachable but not migrated to `0003_phase6_replay`.

## Remaining Quant Risks

- Replay is OHLCV-based and cannot prove actual fills or intrabar path.
- Slippage/spread are fixed assumptions, not live liquidity estimates.
- Replay validation currently selects the latest persisted replay run.
- Warmup-aware incremental rebuild planning is still V1.
- Model confidence remains uncalibrated.

## Exact Next Phase

Phase 7 should be replay calibration audit and operational hardening: replay-run selection for validation, sensitivity reports for slippage/spread, Timescale hypertable/compression policies, richer stale-window observability, and export reproducibility checks. Do not add broker execution, options data, WebSocket scope, self-learning language, or profitability claims.
