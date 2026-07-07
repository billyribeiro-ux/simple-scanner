# Phase 21R Test Isolation - 2026-07-04

`PHASE_21R_TEST_ISOLATION_STATUS = FIXED_AND_VERIFIED`

Phase 21R repaired the mutating regression path so fixture-bearing tests use a dedicated test database instead of the runtime evidence database.

## Database Role Contract

- Evidence runtime: `DATABASE_URL` with `AMD_DB_ROLE=evidence`.
- Mutating Postgres tests: `TEST_DATABASE_URL` with `AMD_DB_ROLE=test`.
- Local no-URL development: SQLite local mode.
- Fixture override: `AMD_ALLOW_TEST_FIXTURES_IN_EVIDENCE=true`, reserved only for emergency local debugging and not allowed for evidence certification.

## Repaired Test Targets

- `make api-smoke-postgres` now prepares and migrates `adaptive_market_decoder_test` by default, then runs with `DATABASE_URL=$TEST_DATABASE_URL` and `AMD_DB_ROLE=test`.
- `make repository-parity-test` uses the same isolated Postgres test database by default.
- `scripts/ensure_test_database.py` creates the test database when it is missing without printing secrets.
- `scripts/evidence_db_audit.py` provides non-secret row counts and fixture detection for evidence and test DB checks.

## Evidence Fixture Guard

Evidence mode rejects fixture-like IDs and references in guarded repository write paths unless the explicit override is set. The guard detects:

- Prefixes: `parity-`, `test-`, `smoke-`, `fixture-`
- Exact IDs: `parity-model-accepted`, `parity-proposal`, `parity-review`
- Known fixture text: `model-accepted test`

Guarded write paths include model runs, validation-adjacent model governance records, calibration, drift, review reports, research cycles, cycle artifacts, proposals, decision-ledger entries, replay, sensitivity, backtest comparisons, scheduler jobs, and exports.

## Verification

Commands run on 2026-07-04:

| Command | Result |
|---|---|
| `make test-db-smoke` | Pass; test DB created/migrated to `0012_phase16_fmp_freshness` |
| `make evidence-guard-test` | Pass; 2 passed, 3 deselected |
| `make api-smoke-postgres` | Pass; 1 passed, 1 warning |
| `make repository-parity-test` | Pass; 5 passed |
| `make backend-test` | Pass; 127 passed, 1 warning |
| `make backend-lint` | Pass |
| `make backend-typecheck` | Pass |
| `python3 -m compileall services/quant-engine/app services/quant-engine/tests` | Pass |

The evidence audit after these runs still reported `2609` total rows and `29` fixture-like rows, matching the pre-repair contamination snapshot. The repaired tests did not add new fixture rows to the evidence database.

## Conclusion

The regression isolation failure is repaired. Future mutating Postgres regression runs are expected to write fixtures only to the test database unless an operator explicitly overrides the evidence fixture guard.
