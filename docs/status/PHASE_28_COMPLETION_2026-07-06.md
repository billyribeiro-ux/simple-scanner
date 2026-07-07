# Phase 28 Completion

Status date: 2026-07-06

`PHASE_28_STATUS = ACCEPTED_REJECTED_BY_SENSITIVITY`

Final decision: `REJECTED_BY_SENSITIVITY`

## Executive Summary

Phase 28 completed the pre-registered `trend continuation short` diagnostic. The Phase 22 source-replay lead did not survive full-grid sensitivity. The `1min` and `5min` primary baselines were positive before sensitivity, but every interval failed portfolio or counterfactual full-grid sensitivity. The `15min` interval was negative in both portfolio and counterfactual replay before sensitivity.

This phase remained research-only. No model was activated, no proposal was approved, no validation/calibration/sensitivity gate was loosened, no filter or threshold was selected from OOS outcomes, no future labels or future outcomes were used for filters, no realized same-bar ambiguity was used as a live filter, no broker/order path was added, no production WebSocket ingestion was added, and no profitability claim is made.

## Registered Spec

| Field | Value |
|---|---|
| Source ID | `phase28_tcs_13dcd7f09159fc3c` |
| Spec version | `phase28_trend_continuation_short_diagnostic.v1` |
| Spec hash | `9bcac6111f0c6e079b20c6160386d4ad2f78c4c9755cbbad788992350903162b` |
| Setup type | `trend continuation short` |
| Side | `SHORT` |
| Symbols | All symbols in the clean evidence DB |
| Intervals | `1min`, `5min`, `15min`, evaluated separately |
| Primary exclusions | None |
| Split | Chronological 60% training, 60-minute embargo, post-embargo OOS |

The required first-read document `docs/status/PHASE_21U_COMPLETION_2026-07-05.md` remains missing from the checkout and is recorded as an upstream documentation gap.

## Primary Result

| Interval | OOS candidates | Portfolio avg R | Portfolio PF | Portfolio robustness | Counterfactual avg R | Counterfactual PF | Counterfactual robustness | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `1min` | 87 | 0.161701 | 1.308001 | 0.00 | 0.111022 | 1.203147 | 0.00 | `REJECTED_BY_SENSITIVITY` |
| `5min` | 89 | 0.168638 | 1.350594 | 0.44 | 0.170699 | 1.350681 | 0.00 | `REJECTED_BY_SENSITIVITY` |
| `15min` | 189 | -0.058462 | 0.888915 | 0.00 | -0.064282 | 0.873549 | 0.00 | `REJECTED_BY_SENSITIVITY` |

Every sensitivity run completed the full default 75-scenario grid. Total sensitivity scenario rows recorded for Phase 28: `450`.

## Data Sufficiency And Leakage

| Interval | Candidates | Training | Embargo | OOS | OOS days | Leakage status |
|---|---:|---:|---:|---:|---:|---|
| `1min` | 218 | 130 | 1 | 87 | 5 | PASS |
| `5min` | 236 | 141 | 6 | 89 | 5 | PASS |
| `15min` | 478 | 286 | 3 | 189 | 12 | PASS |

The split used signal-time candidate timestamps only. No OOS outcomes, future labels, future outcomes, or realized same-bar replay fields were used to select the primary cohort.

## Evidence DB Status

Preflight and final audits used the clean evidence store with evidence role.

Final post-test evidence audit:

| Metric | Value |
|---|---:|
| Contamination status | `CLEAN` |
| Alembic revision | `0012_phase16_fmp_freshness` |
| Total rows | 212002 |
| Fixture rows | 0 |
| Active models | 0 |
| Missing tables | none |
| Dirty windows | none |
| Exports | 340 |
| Replay runs | 72 |
| Sensitivity runs | 68 |
| Sensitivity scenarios | 4248 |

## Exports

| Export type | Export ID | Format | Rows | File SHA-256 |
|---|---|---|---:|---|
| `phase28_filter_spec` | `export_f00b2408e06695c97dcbff7ba0bc366d` | json | 1 | `fb3c1e52f03c2e6123f6ec4a6e71fd36ea74456e7c824de56568e60b9b4ebc55` |
| `phase28_data_sufficiency` | `export_9dd83209406e88bc97e9d4df1aa339f9` | json | 3 | `c4c7b8433d66beb280b9a9d2b931614a9ed0821259152fb19d00853f98b455e7` |
| `phase28_split_leakage` | `export_867286944863d5e13a282bb0a7544275` | json | 3 | `263c906c7e31254c304508f41cdd6dc2d840714306f784858f4652319c5963b9` |
| `phase28_primary_results` | `export_6b761552056a1173e890e10a5ab74ebe` | json | 3 | `6b600885f3d9923c749cfac690aedf3fa646812e1533bb97a26b47c357e7b3e4` |
| `phase28_exploratory_results` | `export_3d55ecc7ca0e1b813cf6347a28cb6b86` | json | 12 | `070a24208b991fa1d3934384624ee722d0f6fde36b7339ed8dab86301c0611fc` |
| `phase28_comparison` | `export_5ff966cce536fdec7af9f26bec515508` | json | 3 | `03122e1610f9de1db8ffee7efd9f75de479ec82e78e251fcc0fa8dcc41ce706c` |
| `phase28_decision` | `export_8a5679bc9bf94442d090179abb7e7ad6` | json | 3 | `7a8f93963d8fe544db84c22e670591b539396768eb33af9478d91fb2ae90d785` |
| `phase28_sensitivity_scenarios` | `export_f98c0a35f5bce38b2869a2b80ff686ce` | csv | 450 | `21921a7e1197354ea322da748a7ac95bf0fe2165f31df85f05f301c308aeec13` |
| `phase28_export_manifest` | `export_35de7fe0f9b479e5df2ef64eb25c3bb3` | json | 8 | `95c8708b7e4646a6a0a344e333bbe14d72ecb1ad76d001a0199653992eead8fa` |

Workbook sheets: `[]` for Phase 28 JSON/CSV exports.

## Report Artifacts

| Markdown artifact | Lines | SHA-256 |
|---|---:|---|
| `docs/status/PHASE_28_PLAN_2026-07-06.md` | 78 | `62315b1aaddfe6bc5222809c8487f9ad6109ce8760149ccfe69721789f66158c` |
| `docs/status/PHASE_28_FILTER_SPEC_2026-07-06.md` | 84 | `2670d27e20e00649f2ebc76a116ec7e9ed4f696bfd8f358b18591f4583319800` |
| `docs/status/PHASE_28_DATA_SUFFICIENCY_2026-07-06.md` | 67 | `281458aa0fc0215ca1c26a050d25f875bb9dc09d58b033219250ac764b017214` |
| `docs/status/PHASE_28_SPLIT_AND_LEAKAGE_2026-07-06.md` | 45 | `eb6f3dc84492de342fd18d97080f7e8f340f81003939ef55cbe1dba8b77cd028` |
| `docs/status/PHASE_28_PRIMARY_RESULTS_2026-07-06.md` | 60 | `c6299fe1a8400eb2ca74660f33dcd130092418e6315c3b3a70fd2505bd2a0f99` |
| `docs/status/PHASE_28_EXPLORATORY_RESULTS_2026-07-06.md` | 82 | `071f13c15b43cbba1ecb27b5c580ac96a4d6f861ed1246d8c87d933236dcac8f` |
| `docs/status/PHASE_28_COMPARISON_2026-07-06.md` | 50 | `e9130428b0183bbeaf41d4be498f0b7da8fe9c3000df3f1512fea45203f7068e` |
| `docs/status/PHASE_28_DECISION_2026-07-06.md` | 60 | `82272d3ca0b7c45de3ba1774ce69d112bd4defe87df19f86ab25775d7b733a1d` |
| `docs/live-data-research-cycle-results.md` | 214 | `228e3d57520f85e3dc179ba528bb4d732f2379ec1e8d6db5c86edc6988e05089` |
| `docs/HANDOFF.md` | 996 | `f28ea66bb61bfe1aaf1f3c245ffb002ad81e652c7571e8bb98cb7f873e26c0d9` |

## Commands And Tests Run

Passed:

- `make doctor` with expected warnings for missing default database URL in the shell and missing live-provider key.
- `DATABASE_URL=... AMD_DB_ROLE=evidence make db-migrate`
- `DATABASE_URL=... AMD_DB_ROLE=evidence make db-inspect`
- `DATABASE_URL=... AMD_DB_ROLE=evidence make db-query-diagnostics`
- `DATABASE_URL=... AMD_DB_ROLE=evidence make evidence-db-audit`
- `make test-db-smoke`
- `make evidence-guard-test`
- `make backend-test` (`132 passed, 1 warning`)
- `make backend-lint`
- `make backend-typecheck` (`Success: no issues found`, notes only)
- `make replay-sensitivity-test` (`5 passed`)
- `make model-review-test` (`6 passed`)
- `make research-cycle-test` (`4 passed, 2 deselected`)
- `make export-test` (`5 passed`)
- `make scheduler-test` (`15 passed, 1 warning`)
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm check`
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm build`
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm test`
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm lint`
- `PLAYWRIGHT_PORT=5174 COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm --filter @amd/web test:e2e` (`11 passed`)
- `python3 -m compileall services/quant-engine/app services/quant-engine/tests`
- `git diff --check`
- High-signal secret scan across source, docs, exports, work artifacts, scripts, packages, apps, and frontend output (`high_signal_secret_findings=0`)
- Final post-test evidence audit

## Docs Changes Made

- Added Phase 28 plan, filter-spec, data-sufficiency, split/leakage, primary-results, exploratory-results, comparison, decision, and completion reports.
- Updated `docs/live-data-research-cycle-results.md` with the Phase 28 status.
- Updated `docs/HANDOFF.md` with the Phase 28 outcome and next-work warning.

No application code was changed.

## Critical Blockers

- The current pre-registered `trend continuation short` formulation is rejected by sensitivity.
- The `1min` and `5min` positive baselines are fragile under full-grid sensitivity.
- The `15min` interval is negative before sensitivity and fails full-grid sensitivity.
- Phase 28 exploratory slices must not be promoted into live filters.
- `docs/status/PHASE_21U_COMPLETION_2026-07-05.md` remains missing as an upstream documentation gap.

## Remaining Risks

- Replay evidence cannot prove live fills.
- Counterfactual replay is candidate-quality evidence only, not executable P/L.
- Future work could overfit if it uses Phase 28 OOS outcomes to choose symbols, regimes, time buckets, or ambiguity filters.

## Exact Next Recommended Work

Do not activate the current `trend continuation short` cohort. Either select another signal family through a pre-registered research plan or design a materially new trend-continuation-short hypothesis with a new spec hash and training-only rationale.
