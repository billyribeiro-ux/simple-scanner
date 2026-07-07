# Phase 22 Completion

Date: 2026-07-05
Status: ACCEPTED_DIAGNOSTIC_REJECTION

## 1. Executive Summary

Phase 22 diagnosed the Phase 21W full-grid sensitivity rejection. The challenger failed because the zero-cost conservative baselines were already negative across every interval/purpose, and slippage/spread stress made the weakness worse. Same-bar ambiguity was a major contributor, but non-ambiguous trades were also negative. No full-grid robust subset was found.

No model was activated, no proposal was approved, no stale gate was bypassed, no broker/order/WebSocket production path was used, no secret was exposed, and no profitability claim is made.

## 2. Phase 22 Status

`PHASE_22_STATUS = ACCEPTED_DIAGNOSTIC_REJECTION`

This means the diagnostic/reporting phase is accepted, while the current challenger remains rejected.

## 3. Evidence And Test DB Isolation

Final evidence audit:

- database: `adaptive_market_decoder_evidence`
- role: `evidence`
- Alembic revision: `0012_phase16_fmp_freshness`
- contaminated status: `CLEAN`
- fixture rows: `0`
- active models: `0`
- dirty windows: `none`
- bars/features/candidates/labels: `19800 / 19800 / 23882 / 3032`
- replay runs / sensitivity runs / sensitivity scenarios: `26 / 24 / 948`
- exports: `238`
- total rows: `183039`

Test DB isolation was verified with:

- `make test-db-smoke`: passed.
- `make evidence-guard-test`: 2 passed.
- `make api-smoke-postgres`: initially failed only because it was run in parallel with `repository-parity-test` against the same isolated test DB; rerun sequentially passed, 1 passed.
- `make repository-parity-test`: initially failed for the same shared-test-DB collision; rerun sequentially passed, 6 passed.

The evidence DB remained clean after all checks.

## 4. Sensitivity Failure Decomposition

All six Phase 21W runs completed 75/75 scenarios and failed all 75 scenarios.

| Interval | Purpose | Baseline avg R | Baseline PF | Best avg R | Worst avg R | High-cost delta |
|---|---|---:|---:|---:|---:|---:|
| `1min` | portfolio | -0.064168 | 0.896834 | -0.064168 | -0.967995 | -0.610678 |
| `1min` | counterfactual | -0.087211 | 0.861505 | -0.087211 | -0.943494 | -0.589124 |
| `5min` | portfolio | -0.116468 | 0.814970 | -0.116468 | -0.823555 | -0.409657 |
| `5min` | counterfactual | -0.137221 | 0.782513 | -0.137221 | -0.759394 | -0.365919 |
| `15min` | portfolio | -0.145227 | 0.752779 | -0.145227 | -0.660877 | -0.292641 |
| `15min` | counterfactual | -0.174658 | 0.704234 | -0.174658 | -0.625826 | -0.256016 |

Isolated slippage was the strongest explicit cost driver: 10 bps isolated slippage moved mean average R by `-0.564005`; 10 bps isolated spread moved it by `-0.303855`.

The three intrabar path policies produced identical aggregate metrics in the current replay implementation. Same-bar ambiguity still mattered materially: 917 ambiguous observed source replay trades produced `-917.000000R`, while 12,482 non-ambiguous observed trades produced `-440.295730R`.

## 5. Robust Subset Findings

Full-grid robust groups found: `0`.

The best research-only pockets were:

| Dimension | Value | Interval | Purpose | Scenario pass rate | Avg scenario avg R | Worst scenario avg R |
|---|---|---|---|---:|---:|---:|
| `time_bucket` | `ten_am_reversal_zone` | `15min` | counterfactual | 68.00% | 0.086835 | -0.424572 |
| `time_bucket` | `ten_am_reversal_zone` | `15min` | portfolio | 64.00% | 0.108785 | -0.353597 |

These failed worst-case scenarios and are not activation-grade evidence.

## 6. Symbol / Setup / Interval Triage

Worst source replay contributors:

- symbols: `NVDA` total `-457.184007R`, `SPY` total `-444.535404R`; `SPY` worst average R at `-0.146133`.
- setup families: `opening range breakdown short`, `opening range breakout long`, `VWAP reclaim long`, `trend continuation long`, `failed breakdown long`, `failed breakout short`, and `liquidity sweep reversal long` were materially negative.
- side: longs lost `-797.530128R`; shorts lost `-559.765603R`.
- time buckets: `power_hour` lost `-719.188186R`; `afternoon_continuation` lost `-414.350265R`.
- regimes: `chop` lost the most total R; `trend_long` and `mixed_uncertain` were weak by average R.

Score audit cohorts were positive in observed replay (`TAKE` avg R `0.936020`, `WATCH` avg R `0.402456`), but they do not have full-grid grade/action sensitivity proof and the model-level calibration remained rejected.

## 7. Candidate Filter Research Plan

The exact next research plan is `PHASE 23 - Diagnostic Candidate Filter Experiment for 15min Ten-AM Reversal and Ambiguity Suppression`.

It should test:

- `15min` `ten_am_reversal_zone` specialist cohort.
- signal-time ambiguity-risk proxies.
- score `TAKE`/`WATCH` diagnostic slice.
- downweight/block candidates from `power_hour`, `afternoon_continuation`, weak setup families, and weak symbol/setup combinations.

All filters must be derived from training-fold or signal-time information only.

## 8. Proposal And Activation Status

- Current challenger: `amd-replay-aware-20260702-164145`.
- Model review remains `BLOCK`.
- Comparison remains `REJECT_CHALLENGER`.
- Proposal remains `REJECTED`.
- Active models remain `0`.

No Phase 22 report or export changes model state.

## 9. Export Verification

Phase 22 generated 18 supported sensitivity exports through the existing export service. Each has source replay ID and SHA-256 file hash in the export ledger.

| Export ID | Type | Format | Source run | Rows | SHA-256 |
|---|---|---|---|---:|---|
| `export_e2996002b6ff267936fb22e47f93eb79` | `replay_sensitivity_summary` | `xlsx` | `replay_20260705222826_33726551f81599994d55da1b` | 75 | `ef50fc1b972eae6923fccfce393c519af0c502713b17ece00662ca8965420039` |
| `export_6d983807febd5ac6a0ddd296ab2fa990` | `replay_sensitivity_scenarios` | `csv` | `replay_20260705222826_33726551f81599994d55da1b` | 75 | `63a3f1bd91ca9fb89fe3413c8ff0b49fbb2e6ff11f89f77681be86c722915688` |
| `export_1afacbd497e42bd966002ae4342d7c2c` | `replay_sensitivity_metrics` | `json` | `replay_20260705222826_33726551f81599994d55da1b` | 75 | `8f7694c6e6c323000d89952975bb66e8d2e4d77fa26eb980036d17c08f602a86` |
| `export_e015404b5644cdd781f7798d8ae47442` | `replay_sensitivity_summary` | `xlsx` | `replay_20260705222903_30a05915b7d9ab1dc2a0566c` | 75 | `b95258ac0ac29a9c59bf4b193399a93feee83fc182fde4cf0d8e2f203f16303e` |
| `export_7b4124fc2d10065e57ba29b907afc589` | `replay_sensitivity_scenarios` | `csv` | `replay_20260705222903_30a05915b7d9ab1dc2a0566c` | 75 | `4c757720592c2e498a0e216d1c68c2ad8b26612a40fd37e9f5cf75435f761af7` |
| `export_18f80fb92e841d86425491c601c95dc2` | `replay_sensitivity_metrics` | `json` | `replay_20260705222903_30a05915b7d9ab1dc2a0566c` | 75 | `1bb462b1aa46c027b16422cea303fe1d6f2f4663e61b8d109d5c8561b06bb1b5` |
| `export_74280b1a0a63f1739eceed98de04c79e` | `replay_sensitivity_summary` | `xlsx` | `replay_20260705223001_2a3bedc9d2abaa0a750aefc2` | 75 | `4c2de223cd4b807f4031b2bf2933fd84544c7ce83556fbf0bde8fdb25829dad2` |
| `export_d6c7e6cbe398341e38410bd2af0ed823` | `replay_sensitivity_scenarios` | `csv` | `replay_20260705223001_2a3bedc9d2abaa0a750aefc2` | 75 | `cba72de137ef0be3d569031896931214dbd21ec8a90618511412ca39a03e9fd1` |
| `export_518d0aae26a35350e562c6971158a522` | `replay_sensitivity_metrics` | `json` | `replay_20260705223001_2a3bedc9d2abaa0a750aefc2` | 75 | `a9ebf6098d14e8537ce19d7fbcf8cda21dcc7c24640260a91788fec4143f8b4b` |
| `export_e3fd463f64e1e9ecde38539005c25aaf` | `replay_sensitivity_summary` | `xlsx` | `replay_20260705223005_7e38150cc8ad1259cd668e04` | 75 | `f438334461a31402c190ca998ca48384464cba78a8354c92a934f6250f532ef2` |
| `export_9f7cffa718ac583a75f1c102af08fa3c` | `replay_sensitivity_scenarios` | `csv` | `replay_20260705223005_7e38150cc8ad1259cd668e04` | 75 | `39a488786eaffe79e7b63aa6ca398ed4cb3efea45b1fd87729431c46f1946a99` |
| `export_7e53f5ec6f0d20dad1e4c60d1b9b892a` | `replay_sensitivity_metrics` | `json` | `replay_20260705223005_7e38150cc8ad1259cd668e04` | 75 | `7e7de0dc755b3f6b54f405aeb9f2eb191e8f674f299a1c72536fb5cad2dc2370` |
| `export_2421a1677fcb2e83db2ad3a55e8710e7` | `replay_sensitivity_summary` | `xlsx` | `replay_20260705223012_afc4202e318c155d012444f6` | 75 | `783761e609667740392d2c1e84d218434adbcc06b7ccc077254831a8e821f013` |
| `export_2c04cc55e93acae7b84b5feb9905b2e5` | `replay_sensitivity_scenarios` | `csv` | `replay_20260705223012_afc4202e318c155d012444f6` | 75 | `1ea96a2ecbde7efec98f6f87e637c781a2ba7e1f6bfa0aed68583b4706835a23` |
| `export_afea4ebc8f37eadcb071ef1c224baff3` | `replay_sensitivity_metrics` | `json` | `replay_20260705223012_afc4202e318c155d012444f6` | 75 | `9879c08c786064508aee516324e2f54b12fa7ed0df02efb9903709a72746cf5e` |
| `export_4bf980d85ca669a9c60f28c55406de50` | `replay_sensitivity_summary` | `xlsx` | `replay_20260705223013_39d7d508606d7e8782962ead` | 75 | `35c7d0b5bb72ac4a6e6fecab2af9f96d072d99d25dbe311309b8658f29d414d4` |
| `export_3657f7bfc5714549a1bb12b7decb4d7a` | `replay_sensitivity_scenarios` | `csv` | `replay_20260705223013_39d7d508606d7e8782962ead` | 75 | `6fd47e06a46cbb87a32e4779d7f980b79832ca044ba2bd89de03e094265e354b` |
| `export_5945bc06d6369f58c5739b18b024e0ed` | `replay_sensitivity_metrics` | `json` | `replay_20260705223013_39d7d508606d7e8782962ead` | 75 | `764ac0cb64230ed8c009b8a472ccbfecb2dd0c79e230502b1ca6461a7623fe2e` |

## 10. Commands And Tests Run

Passed:

- `make doctor` with expected `FMP_API_KEY missing` warning in the verification shell.
- `make db-migrate`.
- `make db-inspect`.
- `make db-query-diagnostics`.
- `make evidence-db-audit` final: `CLEAN`, fixture rows `0`.
- `make test-db-smoke`.
- `make evidence-guard-test`: 2 passed.
- `make backend-test`: 132 passed, 1 warning.
- `make backend-lint`.
- `make backend-typecheck`.
- `make replay-sensitivity-test`: 5 passed.
- `make model-review-test`: 6 passed.
- `make research-cycle-test`: 4 passed.
- `make export-test`: 5 passed.
- `make scheduler-test`: 15 passed, 1 warning.
- `make api-smoke-postgres`: sequential rerun passed, 1 passed.
- `make repository-parity-test`: sequential rerun passed, 6 passed.
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm check`.
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm build`.
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm test`: passed with no matching Vitest files.
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm lint`.
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm --filter @amd/web test:e2e`: 11 passed.
- `python3 -m compileall services/quant-engine/app services/quant-engine/tests`.
- `git diff --check`.
- concrete FMP key scan: 0 hits outside ignored `.env.local`.
- tracked `.env.local` scan: none.
- runtime/export/source query secret scan: 0 hits.

## 11. Code And Docs Changes Made

Phase 22 added diagnostic documentation only and generated supported sensitivity exports. No runtime model-selection, activation, broker, WebSocket, or gate code was changed for this phase.

Added:

- `docs/status/PHASE_22_PLAN_2026-07-05.md`
- `docs/status/PHASE_22_SENSITIVITY_FAILURE_DECOMPOSITION_2026-07-05.md`
- `docs/status/PHASE_22_ROBUST_SUBSET_DISCOVERY_2026-07-05.md`
- `docs/status/PHASE_22_TRIAGE_TABLES_2026-07-05.md`
- `docs/status/PHASE_22_CANDIDATE_FILTER_RESEARCH_PLAN_2026-07-05.md`
- `docs/status/PHASE_22_COMPLETION_2026-07-05.md`

Updated:

- `docs/HANDOFF.md`
- `docs/live-data-research-cycle-results.md`

## 12. Critical Blockers

- The current challenger is rejected by validation, calibration/watch, model-review, proposal, and full-grid sensitivity evidence.
- No full-grid robust subset exists.
- Same-bar ambiguity is a major failure source, but realized ambiguity cannot be used as a live forward-looking filter.
- `docs/status/PHASE_21U_COMPLETION_2026-07-05.md` remains absent; Phase 22 recorded this as a documentation gap.

## 13. Remaining Risks

- The positive score cohorts may be overfit or dependent on current evidence distribution until revalidated out-of-sample.
- The `15min` ten-am reversal pocket has insufficient robustness and negative worst cases.
- Signal-time ambiguity proxies require explicit leakage checks.
- The current replay engine records intrabar policy labels, but the three path policies produced identical aggregate outcomes in Phase 22 diagnostics.

## 14. Paths To Phase 22 Docs

- `docs/status/PHASE_22_PLAN_2026-07-05.md`
- `docs/status/PHASE_22_SENSITIVITY_FAILURE_DECOMPOSITION_2026-07-05.md`
- `docs/status/PHASE_22_ROBUST_SUBSET_DISCOVERY_2026-07-05.md`
- `docs/status/PHASE_22_TRIAGE_TABLES_2026-07-05.md`
- `docs/status/PHASE_22_CANDIDATE_FILTER_RESEARCH_PLAN_2026-07-05.md`
- `docs/status/PHASE_22_COMPLETION_2026-07-05.md`
- `docs/HANDOFF.md`
- `docs/live-data-research-cycle-results.md`

## 15. Exact Next Recommended Phase

`PHASE 23 - Diagnostic Candidate Filter Experiment for 15min Ten-AM Reversal and Ambiguity Suppression`

Phase 23 must remain research-only unless all governance gates pass in a future phase. It must not activate models or claim profitability.
