# Evidence Store Governance

Status date: 2026-07-04

The runtime evidence store is the durable source used for phase certification, research-cycle records, model-review records, exports, and governance decisions. It must not receive test fixtures.

## Database Roles

- Evidence role: `DATABASE_URL` plus `AMD_DB_ROLE=evidence`.
- Test role: `TEST_DATABASE_URL` plus `AMD_DB_ROLE=test`.
- Local development without `DATABASE_URL`: SQLite local mode.

`RepositoryRegistry.info()` exposes the non-secret role and fixture-guard status through health/config diagnostics. It must not expose full database URLs, passwords, or API keys.

## Fixture Guard

When `AMD_DB_ROLE=evidence`, repository writes reject known fixture-like IDs unless `AMD_ALLOW_TEST_FIXTURES_IN_EVIDENCE=true` is explicitly set.

Blocked fixture patterns include:

- prefixes: `parity-`, `test-`, `smoke-`, `fixture-`;
- exact IDs: `parity-model-accepted`, `parity-proposal`, `parity-review`;
- known fixture text: `model-accepted test`.

The override exists only for emergency local debugging. It cannot be used for phase acceptance, evidence certification, or release readiness.

## Evidence Certification Rules

An evidence database is certification-ready only when:

- it is migrated to the expected Alembic head;
- fixture audit reports zero fixture-like rows;
- bars are real persisted bars with known source provenance;
- downstream features, candidate signals, labels, replay artifacts, freshness reports, research cycles, and exports were rebuilt from those bars;
- export records include hashes and source IDs;
- strict research-cycle dry-run uses `allow_stale=false`;
- tests and secret scans pass after the rebuild.

Mixed real and fixture rows are contamination. Do not treat partial real row counts as clean evidence.

## Audit Procedure

Run:

```bash
make evidence-db-audit
```

For the isolated test DB, run the audit with `DATABASE_URL` pointing to `TEST_DATABASE_URL` and `AMD_DB_ROLE=test`. Fixture rows in the test DB are expected; fixture rows in evidence mode are not.

## Restoration Policy

Never silently delete, reset, or rewrite an evidence database to make a report pass. If contamination is found:

1. Preserve the database for audit.
2. Record the contaminated tables and samples.
3. Restore from a clean backup when one exists.
4. Otherwise regenerate from runtime-only live data credentials and ignored local env files.
5. If no clean source exists, report `BLOCKED_NO_CLEAN_SOURCE` or the phase-specific partial-blocked status.

## Phase 21S Restoration Result

On 2026-07-04, Phase 21S archived the contaminated default database `adaptive_market_decoder` before creating a separate clean evidence database. The archive is stored at `data/raw/phase21s/adaptive_market_decoder_contaminated_phase21s_2026-07-04.pgdump` with SHA-256 `6a8cb438e766f2ab59a398f8bcd9790ecebe1c1fa656465d163524d180b1b7ec`.

The clean evidence database is `adaptive_market_decoder_evidence`. It migrated to Alembic `0012_phase16_fmp_freshness`, was regenerated from bounded live FMP data through ignored `.env.local`, and audits `CLEAN` with `0` fixture-like rows after tests. Phase 21S is `ACCEPTED`: real bars, downstream artifacts, governance rows, sensitivity rows, freshness reports, and export ledger rows were regenerated from clean evidence. The regenerated challenger remains rejected and inactive.

## Safety Boundaries

Evidence governance does not approve models, activate challengers, connect to brokers, route orders, use production WebSockets, bypass stale gates, or claim profitability.
