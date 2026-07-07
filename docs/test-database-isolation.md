# Test Database Isolation

Status date: 2026-07-04

Mutating regression tests must write fixture data to a dedicated test database, not to the runtime evidence database.

## Environment Contract

- `DATABASE_URL`: evidence database connection for real runtime evidence.
- `TEST_DATABASE_URL`: test database connection for mutating Postgres tests.
- `AMD_DB_ROLE=evidence`: enables evidence fixture guard.
- `AMD_DB_ROLE=test`: allows fixture writes in the isolated test database.
- `AMD_ALLOW_TEST_FIXTURES_IN_EVIDENCE=false`: default and required for certification.

The local default Postgres test database is `adaptive_market_decoder_test` on the same local compose host/port as the evidence DB.

## Test DB Preparation

Run:

```bash
make test-db-smoke
```

This creates the local test database when missing and runs Alembic migrations against it. The helper does not print full connection strings.

## Isolated Regression Targets

Run:

```bash
make api-smoke-postgres
make repository-parity-test
make evidence-guard-test
```

`api-smoke-postgres` and `repository-parity-test` now prepare the test DB and run with `AMD_DB_ROLE=test`. `evidence-guard-test` verifies that fixture writes are rejected in evidence mode and accepted in test mode.

## Evidence Check

After mutating tests, run:

```bash
make evidence-db-audit
```

The evidence database row counts should not gain new `parity-*`, `test-*`, `smoke-*`, or `fixture-*` rows from regression tests. The test database may contain those rows by design.

## Phase 21R Verification

On 2026-07-04:

- `make test-db-smoke`: passed.
- `make api-smoke-postgres`: passed.
- `make repository-parity-test`: passed.
- `make evidence-guard-test`: passed.
- post-test evidence audit stayed at `2609` total rows and `29` fixture-like rows, confirming no new evidence contamination during the repaired run.

## Phase 21S Verification

On 2026-07-04, the repaired test-isolation path was rechecked while the clean evidence database `adaptive_market_decoder_evidence` remained separate from mutating tests.

- `make test-db-smoke`: passed.
- `make api-smoke-postgres`: passed against the isolated test database.
- `make repository-parity-test`: passed against the isolated test database.
- `make evidence-guard-test`: passed.
- clean evidence audit after regeneration and checks stayed `CLEAN`, with `27377` total rows, `0` fixture-like rows, and populated live-data/governance/export evidence tables.

## Safety Boundaries

The test database is not evidence. Do not use test DB rows to certify model readiness, freshness readiness, export provenance, research-cycle results, or challenger activation.
