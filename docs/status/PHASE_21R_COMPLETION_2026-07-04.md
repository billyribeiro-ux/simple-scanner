# Phase 21R Completion - 2026-07-04

`PHASE_21R_STATUS = PARTIAL_BLOCKED`

Phase 21R restored the database role contract and isolated mutating regression fixtures from the evidence database. It could not certify the runtime evidence store as restored because the only available default Postgres evidence database remains contaminated and no clean backup, runtime key, or clean persisted local source was available.

## Final Determination

`PARTIAL_BLOCKED` is the only honest status for this phase.

- Test isolation: fixed and verified.
- Evidence fixture guard: implemented and verified.
- Evidence DB: preserved but contaminated.
- Evidence restoration/regeneration: blocked by no clean source.
- Challenger activation: not performed.
- Broker/order routing: not present and not used.
- Stale gates: not bypassed.
- Profitability: not claimed.
- Secrets: not exposed in docs or command outputs.

## Implementation Summary

- Added `TEST_DATABASE_URL`, `AMD_DB_ROLE`, and `AMD_ALLOW_TEST_FIXTURES_IN_EVIDENCE` settings.
- Added repository-level fixture guards for evidence-mode writes to high-risk governance, replay, model-selection, scheduler, and export repositories.
- Updated Postgres API smoke and repository parity tests to default to `adaptive_market_decoder_test`.
- Added explicit tests proving fixture writes fail in evidence mode and pass in test mode.
- Added `scripts/ensure_test_database.py` for isolated test DB creation.
- Added `scripts/evidence_db_audit.py` for non-secret evidence/test database row and fixture audits.
- Updated Makefile targets so `api-smoke-postgres` and `repository-parity-test` prepare and use the isolated test DB.

## Evidence Audit Result

The default evidence DB audit reported:

- Database: `adaptive_market_decoder`
- Role: `evidence`
- Alembic revision: `0012_phase16_fmp_freshness`
- Total rows: `2609`
- Fixture-like rows: `29`
- Status: `CONTAMINATED`

The isolated test DB audit reported:

- Database: `adaptive_market_decoder_test`
- Role: `test`
- Alembic revision: `0012_phase16_fmp_freshness`
- Total rows: `275`
- Fixture-like rows: `31`
- Status interpretation: expected fixture-bearing test DB, not evidence.

## Restoration Result

No restoration was performed because:

- no runtime `FMP_API_KEY` was present;
- no ignored `.env.local` or `.env` key source was present;
- `data/local_repo.sqlite3` was empty;
- no clean backup or dump was found;
- the default Postgres DB was contaminated and could not be used as a clean source.

The contaminated DB was not reset or cleaned destructively.

## Verification

Commands run on 2026-07-04:

| Command | Result |
|---|---|
| `make doctor` | Pass with expected missing `DATABASE_URL` and `FMP_API_KEY` warnings |
| `make db-migrate` | Pass |
| `make db-inspect` | Pass |
| `make db-query-diagnostics` | Pass; confirmed current DB contamination indicators |
| `make test-db-smoke` | Pass |
| `make evidence-guard-test` | Pass; 2 passed, 3 deselected |
| `make api-smoke-postgres` | Pass; 1 passed, 1 warning |
| `make repository-parity-test` | Pass; 5 passed |
| `make evidence-db-audit` | Pass; evidence DB still contaminated |
| `make backend-test` | Pass; 127 passed, 1 warning |
| `make backend-lint` | Pass |
| `make backend-typecheck` | Pass |
| `make model-review-test` | Pass; 5 passed |
| `make research-cycle-test` | Pass; 4 passed, 2 deselected |
| `make export-test` | Pass; 5 passed |
| `make scheduler-test` | Pass; 15 passed, 1 warning |
| `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm check` | Pass |
| `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm build` | Pass |
| `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm test` | Pass; no test files found with pass-with-no-tests |
| `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm lint` | Pass |
| `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm --filter @amd/web test:e2e` | Pass; 11 passed |
| `python3 -m compileall services/quant-engine/app services/quant-engine/tests` | Pass |
| `git diff --check` | Pass |
| Runtime key/env-file check | Pass; `FMP_API_KEY`, `.env.local`, and `.env` absent |
| Assignment/URL secret scan | Pass with only known local/test placeholders allowlisted |
| `make frontend-doctor` | Pass with expected symbolic secret-identifier warning |

## Acceptance Gate Review

Phase 21R cannot be accepted because clean evidence restoration is incomplete.

| Gate | Status |
|---|---|
| Test isolation fixed | Pass |
| Evidence fixture guard added | Pass |
| Mutating tests use test DB | Pass |
| Evidence DB clean/restored | Fail |
| Downstream artifacts rebuilt from clean real bars | Blocked |
| Freshness after-state recorded from clean evidence | Blocked |
| Strict research-cycle dry-run from clean evidence | Blocked |
| Exports generated with hashes/source IDs from clean evidence | Blocked |
| Tests pass | Pass |
| Secret scans pass | Pass |
| Challenger remains inactive/rejected | Pass |

## Required Next Step

Provide a clean evidence source, then rerun the bounded evidence regeneration under `AMD_DB_ROLE=evidence`. Until that happens, the current default Postgres database is an audited contaminated store and must not be used as certification evidence.
