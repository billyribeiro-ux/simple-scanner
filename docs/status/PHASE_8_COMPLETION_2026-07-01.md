# Phase 8 Completion

Status date: 2026-07-01

## What Changed

Phase 8 adds replay-aware baseline model selection and meta-scoring. The system can train `replay_aware_baseline` models from persisted replay outcomes, persist evidence cells, score candidates with explainable suppression reasons, validate chronologically with `replay_aware_walk_forward`, activate only after accepted replay-aware validation, use the active replay-aware model in the scanner, and export model/evidence/audit/validation artifacts.

## Files Changed

- `services/quant-engine/app/models/replay_evidence.py`
- `services/quant-engine/app/models/meta_scorer.py`
- `services/quant-engine/app/services/workflows.py`
- `services/quant-engine/app/api/routes.py`
- `services/quant-engine/app/jobs/scanner.py`
- `services/quant-engine/app/db/schema.py`
- `services/quant-engine/app/db/repositories.py`
- `services/quant-engine/alembic/versions/0005_phase8_replay_aware_models.py`
- `services/quant-engine/app/exports/service.py`
- backend tests, smoke tests, repository parity tests, and docs

## Status

- Candidate outcome dataset: implemented from persisted replay runs/trades with no-loss handling for unobserved skips.
- Evidence cube: implemented with six-level hierarchy, shrinkage/backoff, metrics, grades, fragility/divergence/stale fields.
- Meta-scorer: implemented with deterministic score components, penalties, action, grade, warnings, and suppression reasons.
- Replay-aware training: implemented through `/models/train` with `model_type=replay_aware_baseline`.
- Replay-aware validation: implemented through `/models/validate?validation_mode=replay_aware_walk_forward`.
- Scanner integration: implemented; active replay-aware model is preferred, fallback warning is emitted otherwise.
- Exports: implemented for model summary, evidence cells, score audits, and validation workbook.
- SQLite/Postgres parity: verified after applying Alembic `0005_phase8_replay_aware_models`.
- Runtime targets: `.node-version` and package metadata target Node `24.18.0`; `.python-version` and backend venv use Python `3.14.6`.

## Tests Added

- Candidate outcome dataset skip handling.
- Evidence shrinkage/backoff suppression.
- Replay-aware training and evidence persistence.
- Candidate scoring and score audit persistence.
- Replay-aware validation and activation guard.
- Replay-aware exports.
- Repository parity coverage for evidence cells and score audits.
- API smoke coverage for replay-aware train/evidence/score/validate/activate/export paths.

## Verification

- `make help` passed.
- `make doctor` passed with warnings for local Node `v25.3.0` versus target `24.18.0`, missing `DATABASE_URL`, missing `FMP_API_KEY`, and no active API backend to inspect.
- `make setup-backend` passed with Python `3.14.6`.
- `docker compose config --quiet` passed.
- `docker compose up -d postgres redis` passed; both services were healthy.
- `make db-migrate` passed and applied `0005_phase8_replay_aware_models`.
- `make db-inspect` passed with `alembic_version=0005_phase8_replay_aware_models`, `tables=25`, no missing tables/indexes/constraints/columns/JSON columns, and `bars` as the Timescale hypertable.
- `python3 -m compileall -q services/quant-engine/app services/quant-engine/tests` passed.
- `make backend-test` passed: `77 passed, 1 warning`.
- `make quant-test` passed: `62 passed`.
- `make backend-lint` passed.
- `make backend-typecheck` passed.
- `make api-smoke-sqlite` passed: `1 passed, 1 warning`.
- `make api-smoke-postgres` passed: `1 passed, 1 warning`.
- `make repository-parity-test` passed: `3 passed`.
- `make replay-test` passed: `10 passed`.
- `make replay-sensitivity-test` passed: `3 passed`.
- `make export-test` passed: `4 passed`.
- `PYTHONPATH=. .venv/bin/python -m pytest tests/quant/test_replay_aware_model.py` passed: `4 passed`.
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm install --frozen-lockfile` passed with the known local Node warning.
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm check` passed with the known local Node warning.
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm build` passed with the known local Node warning and SvelteKit adapter-auto environment notice.
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm test` passed with no frontend test files found and `--passWithNoTests`.
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm lint` passed.
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm --filter @amd/web test:e2e` passed: `2 passed`.
- `make fmp-smoke` was skipped because `FMP_API_KEY` was not configured in the shell environment.
- `git diff --check` passed.
- Secret scan for the provided FMP key fragment passed across the repo, generated frontend bundle output, local export paths, and model artifact paths excluding dependency/vendor directories.

During verification, the first full backend run exposed one Phase 8 export bug: Postgres score-audit rows returned timezone-aware datetimes, and OpenPyXL rejects timezone-aware workbook cells. The export normalization helper now converts `datetime` and `date` values to Excel-safe ISO strings before workbook write. The failing Postgres smoke and the full backend suite passed after that fix.

## Remaining Quant Risks

- Replay-aware scoring is an evidence score, not a calibrated probability.
- Replay remains OHLCV assumption-based and not proof of live fills.
- Counterfactual per-candidate replay is documented but not implemented.
- Validation is chronological and no-leakage, but still only as representative as the selected replay runs and sensitivity scenarios.

## Exact Next Phase

Phase 9 should implement explicit `model_training_counterfactual` replay, richer replay-aware validation windows, and calibration research against broader sampled replay datasets. Keep broker execution, order routing, WebSocket, options, Greeks, market internals, self-learning language, and profitability claims out of scope.
