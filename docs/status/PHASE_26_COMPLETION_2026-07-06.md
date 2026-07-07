# Phase 26 Completion

Status date: 2026-07-06

`PHASE_26_STATUS = ACCEPTED_DISCARD_TEN_AM`

## Executive Summary

Phase 26 ran the pre-registered broader 15min `ten_am_reversal_zone` evidence-density experiment. The broader all-actionable cohort improved OOS selected count from the current TAKE/WATCH slice's 2 candidates to 145 candidates, but the broader cohort remained negative OOS and failed full-grid sensitivity. The issue is not only scorer policy sparsity; the broader Ten-AM cohort itself is negative and not robust.

No model was activated, no proposal was approved, no threshold was changed from OOS outcomes, no stale gate was bypassed, no broker/order path was used, no WebSocket production ingestion was used, no black-box ML was added, and no profitability claim is made.

## Pre-Registered Policies

Spec version: `phase26_broader_15min_ten_am_evidence_density.v1`

Spec hash: `ff4df70e7d98246d4f4bde977e3aedd632db3dcc6a5a2fdce038fab3c93d4cf4`

Policies A-H are recorded in `docs/status/PHASE_26_FILTER_AND_THRESHOLD_SPEC_2026-07-06.md`. Thresholds were computed from training only:

| Policy | Frozen threshold |
|---|---:|
| B score q75 | 35.000000 |
| C score q90 | 35.000000 |
| D pre-ceiling q75 | 53.729132 |
| E pre-ceiling q90 | 69.735132 |
| F evidence quality q75 | 6.415500 |
| G time bucket q75 | 18.682600 |

## Data Sufficiency

| Metric | Value |
|---|---:|
| 15min RTH days | 33 |
| 15min bars | 3432 |
| 15min Ten-AM actionable candidates | 330 |
| Training / embargo / OOS candidates | 178 / 7 / 145 |
| OOS RTH days | 13 |
| Specialist exact cells | 79 |
| Exact cells with 5+ / 10+ observed outcomes | 7 / 0 |
| OOS broad-parent-reliant candidates | 113 |

Finding: the broader OOS sample is large enough for this diagnostic test. Exact specialist evidence density remains weak, but the primary blocker is now negative OOS performance and sensitivity failure.

## Split And Leakage

Training ended at `2026-06-11T14:00:00+00:00`; the 60-minute embargo ended at `2026-06-11T15:00:00+00:00`; the first OOS candidate was `2026-06-12T14:00:00+00:00`. Thresholds were frozen from training only. OOS outcomes, future labels, future outcomes, and realized same-bar ambiguity were not used as filters.

## Policy Evaluation

| Policy | OOS selected | Portfolio avg R | Counterfactual avg R | Robustness p/c | Decision |
|---|---:|---:|---:|---|---|
| A all actionable | 145 | -0.053513 | -0.057926 | 0.00 / 0.00 | REJECTED_BY_SENSITIVITY |
| B score q75 | 135 | -0.123590 | -0.136291 | 0.00 / 0.00 | REJECTED_BY_SENSITIVITY |
| C score q90 | 135 | -0.123590 | -0.136291 | 0.00 / 0.00 | REJECTED_BY_SENSITIVITY |
| D pre-ceiling q75 | 35 | -0.054547 | -0.205196 | 0.00 / 0.00 | REJECTED_BY_SENSITIVITY |
| E pre-ceiling q90 | 6 | -0.500000 | -0.583333 | 0.00 / 0.00 | REJECTED_BY_SENSITIVITY |
| F evidence quality q75 | 35 | -0.054547 | -0.205196 | 0.00 / 0.00 | REJECTED_BY_SENSITIVITY |
| G time bucket q75 | 35 | -0.054547 | -0.205196 | 0.00 / 0.00 | REJECTED_BY_SENSITIVITY |
| H TAKE/WATCH reference | 2 | -1.000000 | -1.000000 | 0.00 / 0.00 | REJECTED_BY_SENSITIVITY |

## Full-Grid Sensitivity

Phase 26 generated 16 replay runs, 16 full-grid sensitivity runs, and 1200 scenarios. Every policy failed portfolio or counterfactual full-grid sensitivity. Robustness was `0.00` for every policy/purpose pair.

## Phase 25 Vs Phase 26

Phase 25 concluded the current TAKE/WATCH slice was too sparse. Phase 26 confirms the broader all-actionable OOS test is not sparse, but it is still negative:

- selected count improved from 2 to 145;
- all-actionable counterfactual avg R stayed `-0.057926`;
- current TAKE/WATCH counterfactual avg R stayed `-1.000000`;
- full-grid robustness stayed `0.00`.

## Proposal And Activation Status

| Item | Status |
|---|---|
| Active models | 0 |
| Proposal approved | No |
| Model activated | No |
| Broker/order path | Not used |
| WebSocket production ingestion | Not used |
| Profitability claim | None |

## Evidence DB And Exports

Preflight evidence audit was `CLEAN`: database `adaptive_market_decoder_evidence`, role `evidence`, Alembic `0012_phase16_fmp_freshness`, fixture rows `0`, active models `0`, dirty windows `0`.

Phase 26 export source ID: `phase26_537f582b33387bf5`.

| Export | ID | Rows | SHA-256 |
|---|---|---:|---|
| Filter/threshold spec JSON | `export_dd3b54ef31bf6f9e821a2249e3f68ca5` | 1 | `3f45cb9f788110f487ac589b130c1284fa41fb7eeeb4f033bcd789e17acca436` |
| Data sufficiency JSON | `export_24eb994002baf33334cec0f20c9a2748` | 1 | `363ff8348afeaaeb38d3b725eb405e67ca9a3e16183da5e6e042a0b299044e7b` |
| Split/leakage JSON | `export_02f6326fdb4eebf04296d2991cb1dc36` | 1 | `471e9e212095a00d155479436899e0e272a5b38e4c77a12240ffb936587459fe` |
| Policy evaluation CSV | `export_a6dbc80527168baa153d8a6dc937df4d` | 8 | `4a7d47e840a76e00a210e70c2ab5c1c4dc2b56c84a81241e0050709ac9081d50` |
| Policy evaluation JSON | `export_ab23a796d40881b45412afdd33b88842` | 8 | `888877c84f9ebfe9cc084198f35ad7e2df591252e3309b59c99e919645d42fcb` |
| Sensitivity scenarios CSV | `export_3ceb3e1258e9b5d8a273a1b5d7506679` | 1200 | `fc8acc332b84137f350a679bf5f5136312da4b6791a2bb8b462ac08d3697acfc` |
| Phase 25 comparison JSON | `export_9be6079ddc327f55e34dd378fbd88b54` | 1 | `0a7bab81926973aad43ee3a4a76bec72b00ecb7e6916be515887a2a7b4f10591` |
| Decision JSON | `export_a3c5d91c3f45474ee10564d99d53a2c0` | 1 | `e6f079bd345e294e4cfa8d1efbb71963101e9d21cc1d128e127ffd0fc6832f4e` |
| Score diagnostic CSV | `export_27ff7de59bba29464faf33d1e583b867` | 330 | `871be6d3631bab54f2b30b44041e2d18cbf504363dd11d439709cedff39e7f5b` |
| Report pack XLSX | `export_2ccdec26381eabeec675c9eb3070a20f` | 1232 | `a0c3ba33376a81edb0607d434b23376b6cd8bf6b8aedd4943419617352291c9c` |

Workbook sheets: `Filter Spec`, `Data Sufficiency`, `Days Needed`, `Split Leakage`, `Policy Evaluation`, `Sensitivity Results`, `Phase25 Comparison`, `Decision`, `Replay Sources`.

## Critical Blockers

- The broader 15min Ten-AM cohort is negative OOS.
- Every policy fails full-grid sensitivity.
- Exact specialist evidence remains sparse: only 7 exact cells have 5+ observed outcomes and none have 10+.
- The missing upstream `docs/status/PHASE_21U_COMPLETION_2026-07-05.md` remains a documentation gap.

## Remaining Risks

- The experiment is still OHLCV replay-based and cannot prove live fills.
- Current score thresholds are deterministic ranking diagnostics, not calibrated probabilities.
- The evidence DB is clean, but the worktree had substantial unrelated pre-existing modifications before Phase 26.

## Verification Status

Completed after report generation.

Post-run evidence audit remained `CLEAN`: total rows `210461`, fixture rows `0`, active models `0`, Alembic `0012_phase16_fmp_freshness`, missing tables `none`.

| Area | Result |
|---|---|
| Evidence DB | `make db-migrate`, `make doctor`, `make db-inspect`, `make db-query-diagnostics`, `make evidence-db-audit`, `make test-db-smoke`, and `make evidence-guard-test` passed. `make doctor` reported the expected missing `FMP_API_KEY` warning. |
| Backend | `make backend-test` passed with `132 passed, 1 warning`; `make backend-lint` passed; `make backend-typecheck` passed with notes only. |
| Targeted backend | `make replay-sensitivity-test`, `make model-review-test`, `make research-cycle-test`, `make export-test`, and `make scheduler-test` passed. |
| Frontend | `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm check`, `build`, `test`, and `lint` passed. |
| E2E | Initial default-port run reused an unrelated server already on `5173`; after adding `PLAYWRIGHT_PORT`, `PLAYWRIGHT_PORT=5174 COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm --filter @amd/web test:e2e` passed with `11 passed`. |
| Artifact QA | Phase 26 workbook opened successfully with expected sheets and row counts. |
| Static checks | `python3 -m compileall services/quant-engine/app services/quant-engine/tests` passed; `git diff --check` passed. |
| Secret scan | High-signal scan across source, docs, exports, workbook internals, frontend, provider, scheduler, and model artifacts found `0` secret findings. |

Verification-support fixes made during final QA:

- `apps/web/playwright.config.ts` now accepts `PLAYWRIGHT_PORT` so e2e can avoid unrelated local servers.
- `services/quant-engine/tests/quant/test_phase16_fmp_freshness.py` pins the fake FMP seed window around its fixture timestamp to preserve chronological validation independent of wall-clock date.

## Exact Next Recommended Phase

`PHASE 27 - Ten-AM Hypothesis Discard And Signal-Family Failure Post-Mortem`

Phase 27 should stop treating current 15min Ten-AM as a promotion candidate and instead decompose why the signal families remain negative under replay and cost sensitivity. It must stay research-only unless a future pre-registered redesign passes OOS validation, calibration, and full-grid sensitivity.
