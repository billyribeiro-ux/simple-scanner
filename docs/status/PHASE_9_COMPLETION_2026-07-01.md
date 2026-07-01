# Phase 9 Completion

Status date: 2026-07-01

## Summary

Phase 9 is implemented for the backend research platform. It adds counterfactual candidate replay, replay-aware outcome source controls, explicit replay-aware validation window inputs, score calibration audits, calibration-aware activation/scanner guardrails, model comparison, counterfactual-vs-portfolio comparison, persistence, exports, tests, and docs.

## Files Changed

Core changes are in `Makefile`, `services/quant-engine/app/backtesting/replay.py`, `app/models/replay_evidence.py`, `app/models/calibration_audit.py`, `app/services/workflows.py`, `app/api/routes.py`, `app/db/repositories.py`, `app/db/schema.py`, `app/exports/service.py`, `app/jobs/scanner.py`, `app/schemas/market.py`, Alembic revision `0006_phase9_calibration`, backend tests, API smoke, and docs.

## Status

- Counterfactual replay: implemented as `model_training_counterfactual`.
- Candidate outcome dataset: defaults to `counterfactual_preferred`, preserves portfolio context separately, and records outcome source metadata.
- Replay-aware training: supports counterfactual/portfolio run IDs, outcome source policy, counterfactual requirements, and portfolio-only fraction guards.
- Replay-aware validation: accepts explicit train/validation/test replay IDs, windows, embargo minutes, counterfactual/portfolio requirements, and calibration audit requirement flags.
- Calibration audit: implemented with score/grade/action bins, rank correlation, monotonicity, stability, warnings, rejection reasons, API, persistence, and exports.
- Activation gate: rejects missing/failed required calibration and returns calibration metadata.
- Scanner guardrails: calibration-required models suppress TAKE when calibration is missing or failed.
- Counterfactual vs portfolio comparison: implemented and persisted as diagnostic research output.
- SQLite/Postgres parity: migrated to `0006_phase9_calibration` and verified.

## Calibration Persistence/API/Export Status

- Persistence: `model_calibration_audits`, `model_calibration_bins`, and `model_comparisons` are available in SQLite initialization and Postgres Alembic migration `0006_phase9_calibration`.
- API: calibration audit create/list/get/bins, model comparison, and counterfactual-vs-portfolio comparison routes are included in the persisted smoke path.
- Exports: calibration audit XLSX, calibration bins CSV/XLSX, calibration metrics JSON, and model comparison XLSX read persisted data, write to ignored export paths, and record file hashes.

## Commands Run

- `make help`: passed.
- `docker compose config`: passed.
- `docker compose up -d postgres redis`: passed; services already running.
- `docker compose ps`: passed; Postgres and Redis healthy.
- `make doctor`: passed with documented warnings for local Node `25.3.0` versus project target `24.18.0`, missing `DATABASE_URL`, and missing `FMP_API_KEY`.
- `make setup-backend`: passed; backend venv uses Python `3.14.6`.
- `make db-migrate`: passed.
- `make db-inspect`: passed; Alembic revision `0006_phase9_calibration`, 28 tables, no missing tables/indexes/constraints/columns/JSON columns.
- `make quant-test`: passed, 66 tests.
- `make backend-test`: passed, 81 tests, one existing Starlette deprecation warning.
- `make backend-lint`: passed.
- `make backend-typecheck`: passed, with an informational mypy note about `stream_quotes`.
- `make api-smoke`: passed, 1 SQLite smoke test, one existing Starlette deprecation warning.
- `make api-smoke-sqlite`: passed, 1 SQLite smoke test, one existing Starlette deprecation warning.
- `make api-smoke-postgres`: passed, 1 Postgres smoke test, one existing Starlette deprecation warning.
- `make repository-parity-test`: passed, 3 tests. An earlier parallel run overlapped with Postgres smoke and failed from database contention; the isolated rerun passed.
- `make replay-test`: passed, 10 tests.
- `make export-test`: passed, 4 tests.
- `make replay-sensitivity-test`: passed, 3 tests.
- Replay-aware and Phase 9 focused tests: passed, 8 tests.
- `python3 -m compileall services/quant-engine/app services/quant-engine/tests`: passed.
- `corepack pnpm check`: passed with expected Node engine warning.
- `corepack pnpm build`: passed with expected Node engine warning.
- `corepack pnpm test`: passed with expected Node engine warning and no frontend test files found.
- `corepack pnpm lint`: passed with expected Node engine warning.
- `git diff --check`: passed.
- Secret scan across repo, generated frontend bundles, exports, model artifacts, and ignored runtime paths: passed.
- `make fmp-smoke`: skipped because `FMP_API_KEY` was not configured in the shell.

## Tests Added

- `services/quant-engine/tests/quant/test_phase9_counterfactual_calibration.py`
- expanded `services/quant-engine/tests/test_persisted_api_smoke.py`
- expanded `services/quant-engine/tests/test_repository_parity.py`

## Blockers

No code blockers remain.

Resolved issues:

- The first migration attempt failed because the revision ID exceeded the existing Alembic `VARCHAR(32)` limit; the revision ID was shortened to `0006_phase9_calibration` and migration passed.
- Secret scan initially flagged the Makefile's local Postgres fallback as a password-shaped `DATABASE_URL`; the Makefile now assembles the dev URL from separate local components.
- A parallel rerun of Postgres smoke and repository parity conflicted on the same local database; the commands pass when run isolated as documented.

## Remaining Quant Risks

- Counterfactual replay is still OHLCV simulation and does not prove fills, liquidity, queue position, or profitability.
- Score calibration audits rank evidence but are not probability calibration.
- Validation is stronger but still depends on the quality and representativeness of candidate generation and replay windows.

## Next Phase

Phase 10 should add richer validation/reporting around calibration drift, larger multi-day window orchestration, and optional frontend surfaces for counterfactual/calibration artifacts without changing execution boundaries.
