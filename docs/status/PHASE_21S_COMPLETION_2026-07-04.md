# Phase 21S Completion Report

Status date: 2026-07-04

`PHASE_21S_STATUS = ACCEPTED`

## Executive Summary

Phase 21S restored certification-grade evidence by archiving the contaminated default DB, creating a clean evidence DB, regenerating live FMP data, rebuilding artifacts, regenerating governance evidence, resolving sensitivity status, and passing tests/secret scans. The challenger remains rejected and inactive.

## Acceptance Checklist

| Requirement | Result |
|---|---|
| Contaminated DB archived before cleanup | PASS |
| Clean evidence DB created and migrated | PASS |
| Fixture audit before/after regeneration | PASS, `0` fixture-like rows |
| Real bars exist in clean DB | PASS, 3960 bars |
| Downstream artifacts rebuilt from bars | PASS |
| Freshness after-state recorded | PASS |
| Strict dry-run with `allow_stale=false` | PASS |
| Governance evidence regenerated | PASS |
| Sensitivity status resolved | PASS, regenerated and failed robustness gates |
| Exports generated with hashes/source IDs | PASS, 94 export rows |
| Tests pass | PASS |
| Secret scans pass | PASS |

## Final Clean Evidence Counts

| Artifact | Count / status |
|---|---:|
| Bars | 3960 |
| Quote snapshots | 4 |
| Features | 3960 |
| Candidate signals | 4846 |
| Labels | 578 |
| Replay runs | 12 |
| Sensitivity runs / scenarios | 6 / 450 |
| Model runs | 1 |
| Evidence cells | 421 |
| Score audits | 3723 |
| Validation reports | 1 |
| Model review reports | 1 |
| Model proposals | 2 |
| Decision ledger rows | 6 |
| Export rows | 94 |
| Active models | 0 |

## Key IDs

- Live seed: `ingestion_6e7c635f3b0ae005dc563a6c8ab4ca58`.
- Strict dry-run: `research_cycle_800e1858ac7792b72e92c1281ba296eb`, `blocked=false`.
- Governance cycle: `research_cycle_2aa5a1efb11f49113c5b31508e31283a`, `BLOCKED`.
- Challenger: `amd-replay-aware-20260702-133838`, inactive.
- Model review: `model_review_0539414cb274f7d47fa86114f6d83613`, `BLOCK`.
- Cycle proposal: `proposal_bbf68aeec5410239d265279e372bf7b8`, `REJECTED`, `REJECT_CHALLENGER`.
- Phase 21S artifact manifest export: `export_a2aff8597cfd6fbda9cf340165e7a2e7`, SHA-256 `073b34efa2b5fea7ca30cf6142199b29c265d9f73f8ea3e339d5261567e01450`.
- Phase 21S governance manifest export: `export_610787870119d166617ee796ca79b798`, SHA-256 `28608edc08efbf4b9c09de0eeadfb6406261d657bf3514ec7790bbd95d110910`.

## Verification

Passed: `make doctor`, `make db-migrate`, `make db-inspect`, `make db-query-diagnostics`, `make evidence-db-audit`, `make backend-test`, `make backend-lint`, `make backend-typecheck`, `make api-smoke-postgres`, `make repository-parity-test`, `make model-review-test`, `make research-cycle-test`, `make export-test`, `make scheduler-test`, `make test-db-smoke`, `make evidence-guard-test`, `corepack pnpm check`, `corepack pnpm build`, `corepack pnpm test`, `corepack pnpm lint`, `corepack pnpm --filter @amd/web test:e2e`, `python3 -m compileall services/quant-engine/app services/quant-engine/tests`, `git diff --check`, and final secret scans.

`corepack pnpm test` passed with `--passWithNoTests` because the frontend/shared packages currently have no matching Vitest test files.

## Final Decision

Phase 21S is accepted. Exact next phase: Phase 22 should analyze why the clean challenger failed validation/calibration/sensitivity gates and design evidence-improvement experiments without activation, gate loosening, or profitability claims.
