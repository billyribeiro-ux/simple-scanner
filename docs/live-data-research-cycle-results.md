# Live Data Research Cycle Results - 2026-07-06

`LIVE_DATA_RESEARCH_STATUS = BLOCKED_BY_GOVERNANCE`

This document records the accepted Phase 20 research-cycle result and the Phase 21 diagnostic update. It was missing before Phase 21 and is created now to close the documentation gap.

## Phase 26 Broader Ten-AM Evidence-Density Experiment

Phase 26 status is `ACCEPTED_DISCARD_TEN_AM`.

The pre-registered broader 15min `ten_am_reversal_zone` experiment tested all actionable candidates and training-only score threshold slices without activation, proposal approval, OOS threshold selection, stale-gate bypass, broker/order execution, WebSocket production ingestion, or profitability claims.

Result: broader scoring solved the TAKE/WATCH sample-size issue but not the edge issue. The all-actionable policy selected 145 OOS candidates versus 2 current TAKE/WATCH candidates, but counterfactual avg R was `-0.057926`, portfolio avg R was `-0.053513`, and both full-grid robustness scores were `0.00`. Training score q75/q90 selected 135 OOS candidates and was more negative. Pre-ceiling/evidence/time-bucket q75 selected 35 OOS candidates and remained negative. TAKE/WATCH reference remained `-1.000000R`.

Evidence density still shows exact-cell weakness: 79 specialist exact cells, 7 with 5+ observed outcomes, 0 with 10+ observed outcomes, and 113 broad-parent-reliant OOS candidates. The final decision is `DISCARD_TEN_AM_HYPOTHESIS` for the current formulation. Exact next phase: `PHASE 27 - Ten-AM Hypothesis Discard And Signal-Family Failure Post-Mortem`.

## Phase 20 Result

The strict live-data research cycle used `allow_stale=false`, did not refresh data during the cycle, did not activate a model, and ended blocked by governance gates.

| Field | Value |
|---|---|
| Research cycle | `research_cycle_ece57ebd9e3f0efa4d4fa48c0518b821` |
| Status | `BLOCKED` |
| Recommended action | `REJECT_CHALLENGER` |
| Proposal | `proposal_e800968cc4ba52a648f6bc00430d306b` |
| Proposal status | `REJECTED` |
| Challenger | `amd-replay-aware-20260702-195615` |
| Validation report | `report_0091f7e03f0bd9d674ff6fdb75219b0e` |
| Calibration audit | `calibration_a22adf288c34de793f37e474515b377a` |
| Model review | `model_review_ae563bded0b1a0ab4eedbb35e99e4d66` |
| Comparison | `champion_challenger_d7ff387488ea651b063c1a4c809c342e` |
| Portfolio replay | `replay_20260704195543_48a6b35debfd62244361ea09` |
| Counterfactual replay | `replay_20260704195544_df74191456eb8e03eaec364e` |

## Gate Result

The comparison gate result was:

- `calibration_pass=true`
- `stale_window_pass=true`
- `data_quality_pass=true`
- `drift_pass=true`
- `validation_pass=false`
- `model_review_pass=false`
- `all_passed=false`

The exact persisted rejection path was validation rejection, model-review block, comparison failure, proposal rejection, and research-cycle block.

## Validation And Calibration

Validation rejected the challenger for:

- `minimum_selected_candidate_sample_not_met`
- `single_setup_profit_concentration_too_high`
- `single_symbol_profit_concentration_too_high`

Calibration did not reject the challenger. It passed monotonicity and TAKE outperformed WATCH in joined counterfactual evidence, but it emitted `score_concentrated_in_one_bucket`.

## Phase 21 Diagnostic Update

Phase 21 collected diagnostic evidence and created:

- `docs/status/PHASE_21_GATE_ATTRIBUTION_2026-07-04.md`
- `docs/status/PHASE_21_SAMPLE_CONCENTRATION_2026-07-04.md`
- `docs/status/PHASE_21_EVIDENCE_IMPROVEMENT_PLAN_2026-07-04.md`
- `docs/status/PHASE_21_COMPLETION_2026-07-04.md`

After the Phase 21 snapshot was collected, two regression targets contaminated the default Postgres database with parity fixtures. The current database is blocked as certification evidence until restored or regenerated. The on-disk Phase 20 exports remain present and their hashes were verified.

No activation occurred for the Phase 20 challenger. The current parity proposal/model rows in Postgres are test artifacts and must not be interpreted as live-data approval.

## Phase 24 Pre-Registered Specialist Expansion

Phase 24 status is `ACCEPTED_NEEDS_MORE_DATA`. The clean evidence store was expanded from real FMP REST bars to 33 RTH dates for `SPY`, `QQQ`, `AAPL`, and `NVDA` on `15min` and `1day`. Downstream artifacts were rebuilt from persisted bars and the final dirty-window count is `0`.

The pre-registered 15min `ten_am_reversal_zone` TAKE/WATCH hypothesis used filter spec hash `220cbea95476458b0cfd7c78ec4f297dd6bd404f5c101cbafdcda3661d741d5d`. A discovery-trained inactive scorer selected only 2 OOS TAKE candidates from 145 scored post-embargo candidates. Portfolio and counterfactual replay averages were both `-1.000000`, full-grid robustness was `0.00` for both, and calibration rejected the slice for `minimum_high_grade_samples_not_met`.

Strict dry-run `research_cycle_418dee617dd11a6041c8b6ed8bfe20a5` used `allow_stale=false`, freshness was `READY`, and no activation/proposal/broker/WebSocket/profitability action occurred.

## Phase 25 Specialist Scorer Diagnostics

Phase 25 status is `ACCEPTED_EVIDENCE_TOO_SPARSE`. The diagnostic run analyzed the persisted Phase 24 score audits for the inactive model `amd-replay-aware-20260611-181743` and did not activate a model, approve a proposal, change thresholds, bypass stale gates, or claim profitability.

The OOS score distribution was `SUPPRESS=143`, `TAKE=2`, `WATCH=0` across 145 candidates. Suppression was driven by `negative_expectancy_after_shrinkage=143`, `profit_factor_below_threshold=112`, and `same_bar_ambiguity_dependency_too_high=10`. WATCH was zero because the scorer only emits WATCH for unsuppressed below-TAKE candidates, and no such candidate existed.

Evidence sparsity was material: 128 OOS candidates had exact evidence-cell matches, but every OOS candidate used parent/backoff cells and 113 relied on broad parent evidence because exact specialist evidence was absent or below 5 observed outcomes. Only 7 of 79 specialist exact cells had at least 5 observed outcomes.

Diagnostic OOS replays showed that the base cohort was weak and the selected slice was worse: all-OOS counterfactual avg R was `-0.057926` across 145 trades, selected TAKE counterfactual avg R was `-1.000000` across 2 trades, and full-grid robustness was `0.00`. The current Phase 23-like TAKE/WATCH equivalent is the same 2-candidate Phase 24 slice, not the prior 9-candidate low-sample result.

Final evidence audit after Phase 25 reports/tests remained `CLEAN`, fixture rows `0`, active models `0`, dirty windows `none`, total rows `208163`, exports `321`, replay runs `48`, sensitivity runs `44`, and sensitivity scenarios `2448`.

## Phase 21S Clean Store Update

Phase 21S created the clean evidence database `adaptive_market_decoder_evidence` after archiving the contaminated default database, then regenerated clean live-data and governance evidence from bounded FMP data. The final clean database audits `CLEAN` with `0` fixture-like rows and contains 3960 bars, 3960 features, 4846 candidates, 578 labels, 12 replay runs, 6 sensitivity runs, 1 replay-aware model run, 421 evidence cells, 3723 score audits, 1 validation report, 1 model review, 2 rejected proposals, 6 decision-ledger rows, and 94 export rows.

The clean Phase 21S challenger is `amd-replay-aware-20260702-133838`. Research cycle `research_cycle_2aa5a1efb11f49113c5b31508e31283a` ended `BLOCKED`; proposal `proposal_bbf68aeec5410239d265279e372bf7b8` ended `REJECTED` with recommended action `REJECT_CHALLENGER`. No activation occurred. Phase 21S status is `ACCEPTED`.

## Phase 21T Clean Expansion Update

Phase 21T expanded the clean evidence store from live FMP REST bars across `SPY`, `QQQ`, `AAPL`, and `NVDA`. Final counts are 13560 bars, 13560 features, 16725 candidates, 2209 labels, 18 replay runs, 12 sensitivity runs, 2 replay-aware model runs, 1562 evidence cells, 20380 score audits, 2 validation reports, 2 model reviews, 3 rejected proposals, 10 decision-ledger rows, and 158 export rows.

The strict research-cycle dry-run `research_cycle_16ad2689f01a0a0d3dd96bd680248377` used `allow_stale=false`, `refresh_data=false`, and did not activate models. The governance cycle `research_cycle_938bf1f9375fecb54a7cfb1ebf00c255` ended `BLOCKED`; proposal `proposal_c34d0341e050a30bcdd815ffc0b0fa70` ended `REJECTED`; comparison `champion_challenger_635360662a088fdf74510924504c67f8` recommended `REJECT_CHALLENGER`.

Phase 21T status is `PARTIAL_BLOCKED`: `1day`, `5min`, and `15min` reached 10 RTH dates, but FMP returned only six RTH dates for `1min`, and the expanded challenger still failed validation, calibration, and model-review gates. No activation occurred.

## Phase 21V Bounded Sensitivity Disclosure Update

Phase 21V starts from the repaired Phase 21U runtime and records bounded sensitivity scaling rather than full-grid sensitivity completion. The evidence database now contains 19800 bars, 19800 features, 23882 candidates, 3032 labels, 26 replay runs, 18 sensitivity runs, 498 sensitivity scenarios, 195 exports, and 0 active models.

The six required `1min`, `5min`, and `15min` portfolio/counterfactual sensitivity runs completed `TIERED_ESSENTIAL` with 4/4 scenarios each. All six are intentionally marked `full_default_grid_complete=false`, `partial_grid_disclosure=true`, and `pass_fail=fail` under full-grid-required governance.

Governance re-run artifacts:

- Model review `model_review_1ef927a48eb24e11886fc3c31f8076e6`: `BLOCK`.
- Comparison `champion_challenger_33c0e399b4679cd3fe0a64149a13553e`: `REJECT_CHALLENGER`.
- Proposal `proposal_3e379a7289fc35875eced05436c4bd35`: `REJECTED`.
- Strict dry-run `research_cycle_750dd3d4bbee9b0a2ae83c2f7c08ae9d`: freshness `READY`, dirty windows `0`, `allow_stale=false`.

Phase 21V status is `ACCEPTED_PARTIAL_SENSITIVITY_DISCLOSED`. It is not model activation, not challenger approval, not full-grid sensitivity acceptance, and not a profitability claim.

## Phase 21W Full-Grid Sensitivity Update

Phase 21W completed the full default replay sensitivity grid for all six required interval/purpose runs. The grid is `replay_sensitivity.full_default_grid.v1`, hash `1f7c8a8a7b14e40768954acf273280866b768d8f5516abbc29c6a3187511201b`, with 75 scenarios per replay.

All six full-grid runs completed `75/75` with `full_default_grid_complete=true` and no partial disclosure:

- `sensitivity_ab486e2337c9de415328f76cecf1c4c7`
- `sensitivity_4747000982a7dd1c24c48798b27d0970`
- `sensitivity_df6e25965262b6d29d8bb6ad9aa0bcde`
- `sensitivity_d1fa1d06e2ac1151f5b20d96db8fefc8`
- `sensitivity_7b270b48d0b1e8580a696a60d82c859e`
- `sensitivity_90441b99f44ddd04caeddcbaa244419f`

The sensitivity completion blocker is resolved. The robustness blocker remains: all six full-grid runs have `pass_fail=fail`, `robustness_score=0.0`, and fragility flags for non-positive expectancy, weak profit factor, robustness below threshold, and same-bar path assumption effects.

Governance remains blocked:

- Model review `model_review_e045a9d38fbbaa4a6acf01b1249dc015`: `BLOCK`.
- Comparison `champion_challenger_819cf89bd41889d5dd73fa8029976363`: `REJECT_CHALLENGER`.
- Proposal `proposal_22b20fc135d1bdc14494ae3887d3248d`: `REJECTED`.
- Strict data-cutoff dry-run `research_cycle_e9df73b81c44222b943ab06a5a908758`: freshness `READY`, dirty windows `0`, blocked `false`, `allow_stale=false`.

Phase 21W status is `ACCEPTED_FULL_GRID_REJECTION`. It is not model activation, not challenger approval, and not a profitability claim.

## Phase 22 Sensitivity Failure Attribution Update

Phase 22 status is `ACCEPTED_DIAGNOSTIC_REJECTION`.

Phase 22 attributed the Phase 21W rejection to broad negative baseline expectancy and cost fragility:

- every zero-cost conservative baseline was already negative;
- isolated slippage was the largest cost driver;
- spread was a secondary material cost driver;
- intrabar path labels produced identical aggregate metrics in the current replay implementation;
- same-bar ambiguity was materially harmful, with 917 ambiguous observed trades producing `-917.000000R`;
- non-ambiguous observed trades were still negative, so ambiguity filtering alone cannot certify the challenger.

Full-grid robust subsets found: `0`.

Research-only leads:

- `15min` `ten_am_reversal_zone` counterfactual: 68.00% scenario research pass rate, worst scenario avg R `-0.424572`.
- `15min` `ten_am_reversal_zone` portfolio: 64.00% scenario research pass rate, worst scenario avg R `-0.353597`.
- score `TAKE` and `WATCH` cohorts were positive in observed replay, but do not have full-grid grade/action sensitivity proof and do not override rejected calibration/governance.

Final evidence audit after Phase 22 reports and exports remained `CLEAN`, fixture rows `0`, active models `0`, exports `238`. No activation occurred and no profitability claim is made.

The exact next phase should be `PHASE 23 - Diagnostic Candidate Filter Experiment for 15min Ten-AM Reversal and Ambiguity Suppression`.

## Phase 23 Diagnostic Filter Experiment Update

Phase 23 status is `ACCEPTED_NO_ROBUST_FILTER`.

The 15min `ten_am_reversal_zone` candidate-filter experiment was run from real persisted bars/features/candidates only. Source data for the experiment contained 1040 15min bars, 1040 features, 1452 candidates, and 82 actionable 15min ten-am candidates across `SPY`, `QQQ`, `AAPL`, and `NVDA`.

Four filters were tested with both `candidate_market_replay` and `model_training_counterfactual`, followed by a full 75-scenario default grid for each replay:

- `P23_FILTER_A_BASE_15M_TEN_AM`: sensitivity-blocked.
- `P23_FILTER_B_AMBIGUITY_SUPPRESSED`: sensitivity-blocked.
- `P23_FILTER_C_WEAK_FAMILY_SUPPRESSED`: low-sample and sensitivity-blocked.
- `P23_FILTER_D_TAKE_WATCH_SLICE`: full-grid pass but low-sample blocked with only 9 candidates and 6 validation trades.

The final evidence database audit is `CLEAN`, fixture rows `0`, active models `0`, dirty windows `0`, replay runs `34`, sensitivity runs `32`, sensitivity scenarios `1548`, and exports `295`. No activation, broker execution, stale bypass, or profitability claim occurred.
