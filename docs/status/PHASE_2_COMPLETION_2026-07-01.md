# Phase 2 Completion — Quant Core Hardening and No-Leakage Foundation

Report date: 2026-07-01

## What Changed

- Added runtime checks and pure quant commands: `make doctor`, `make setup-backend`, and `make quant-test`.
- Added pure quant domain objects in `app/quant/types.py`.
- Rebuilt the feature engine around symbol/interval/session grouping.
- Added deterministic candidate signal detection.
- Rebuilt labeling around next-bar-open entries, candidate-time stops, future-only outcomes, conservative same-bar handling, and overlap controls.
- Replaced label-only backtest summary with chronological simulated trade metrics over labels.
- Added validation engine with chronological splits, walk-forward windows, embargo checks, leakage warnings, and activation gates.
- Upgraded the model artifact format to baseline statistical evidence with rejection reasons.
- Refactored scanner scoring to hydrate historical context and suppress insufficient-context signals.
- Added daily-bar support to the FMP provider for previous-day-level workflows.
- Reconciled the most obvious feature/label schema drift and added repository interfaces.
- Added pure quant regression tests.

## Files Changed

- `Makefile`
- `scripts/doctor.sh`
- `README.md`
- `docs/HANDOFF.md`
- `docs/signal-methodology.md`
- `docs/validation-methodology.md`
- `docs/quant-core-performance.md`
- `docs/status/PHASE_2_PLAN_2026-07-01.md`
- `docs/status/PHASE_2_COMPLETION_2026-07-01.md`
- `services/quant-engine/app/quant/types.py`
- `services/quant-engine/app/features/engine.py`
- `services/quant-engine/app/signals/candidates.py`
- `services/quant-engine/app/signals/rules.py`
- `services/quant-engine/app/labels/engine.py`
- `services/quant-engine/app/backtesting/engine.py`
- `services/quant-engine/app/validation/engine.py`
- `services/quant-engine/app/models/engine.py`
- `services/quant-engine/app/jobs/scanner.py`
- `services/quant-engine/app/data/fmp.py`
- `services/quant-engine/app/db/schema.py`
- `services/quant-engine/app/db/repositories.py`
- `services/quant-engine/alembic/versions/0001_initial.py`
- `services/quant-engine/tests/quant/*`

## Tests Added

- Grouped VWAP no cross-symbol/session leakage.
- True ATR.
- Previous-day levels no current-day future leakage.
- Same-time-of-day relative volume using prior sessions.
- Opening range incomplete/complete behavior.
- Relative strength timestamp alignment.
- Data quality flags for duplicates and invalid prices.
- Candidate tests for all requested setup types.
- Label tests for long/short winners and losers, neutral, next-bar-open entry, conservative same-bar handling, missing next bar, no future stop calculation, and no overlapping same setup.
- Backtest tests for profit factor, drawdown, side precision, and one-open-trade behavior.
- Validation tests for chronological split, walk-forward windows, embargo, activation rejection, and activation acceptance.
- Scanner tests for mocked context hydration and insufficient-context suppression.
- Mocked FMP tests for quote, batch quote, intraday bars, daily bars, and redaction.

## Commands Run

| Command | Result | Notes |
| --- | --- | --- |
| `make doctor` | PASS | Reports Node mismatch, missing Python 3.14, missing backend venv, Docker reachable, missing FMP key, and missing database URL without printing secrets. |
| `make quant-test` | PASS | 40 pure quant tests passed on system Python fallback without FMP/Docker/Redis/Postgres. |
| `python3 -m compileall services/quant-engine/app services/quant-engine/tests` | PASS | App and test source compile under system Python. |
| `cd services/quant-engine && .venv/bin/python -m pytest` | BLOCKED | `.venv/bin/python` does not exist. |
| `cd services/quant-engine && .venv/bin/ruff check app tests` | BLOCKED | `.venv/bin/ruff` does not exist. |
| `cd services/quant-engine && .venv/bin/mypy app` | BLOCKED | `.venv/bin/mypy` does not exist. |
| `cd services/quant-engine && PYTHONPATH=. python3 -m pytest` | BLOCKED | Full backend pytest collection stops at missing `openpyxl`; backend venv/dependencies are not installed. |
| `docker compose config` | PASS | Compose config renders successfully. |
| `corepack pnpm check` | PASS | TypeScript/Svelte checks passed with Node engine warnings because local Node is `25.3.0`, target is `24.18.0`. |
| `corepack pnpm build` | PASS | Frontend/shared build passed with Node engine warnings and the existing adapter-auto production-environment warning. |
| `git diff --check` | PASS | No whitespace errors. |
| Secret scan | PASS | No supplied FMP key substring or obvious committed key assignment found. |

## Unresolved Blockers

- Python `3.14.6` is still not installed locally.
- Backend `.venv` is still missing.
- Full backend dependencies are missing from system Python.
- Full backend pytest/ruff/mypy have not passed through the target venv.
- Alembic migrations were not run against Postgres.
- API routes still use module-level `_MEMORY` state.
- Validation/model artifacts are not persisted to database repositories yet.

## Remaining Quant Risks

- Backtest simulation is still label-derived; the next version should simulate directly from candidate signals and bars.
- Confidence scoring is still baseline heuristic evidence, not calibrated probability.
- Walk-forward validation exists as an engine but is not fully wired through persisted model runs.
- Scanner context hydration is real but not live-FMP verified in this environment.
- Same-time-of-day relative volume uses prior available sessions; larger production datasets should stress-test sparse-session behavior.

## Next Recommended Phase

Backend runtime and persistence hardening:

1. Install Python `3.14.6` and build `services/quant-engine/.venv`.
2. Run full backend `pytest`, `ruff`, and `mypy`.
3. Apply and verify migrations against Postgres/TimescaleDB.
4. Replace API `_MEMORY` with repository-backed persistence.
5. Wire validation reports and activation decisions into persisted model runs.
