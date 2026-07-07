# Phase 21T Governance Review Report - 2026-07-05

`GOVERNANCE_STATUS = BLOCKED_REJECT_CHALLENGER`

## Challenger

- Model version: `amd-replay-aware-20260702-144429`
- Active: `false`
- Evidence cells total after Phase 21T: `1562`
- Candidate score audits total after Phase 21T: `20380`

## Validation

- Report: `report_cf53a27dbd47245b319e8a55f490182b`
- Decision: `rejected`
- Rejection reasons:
  - `minimum_selected_candidate_sample_not_met`
  - `out_of_sample_expectancy_not_positive`
  - `profit_factor_below_threshold`

The full and medium expanded validation paths exceeded practical runtime before persisting because evidence-cube rebuild work scaled poorly on the expanded sample. A bounded 15-minute validation slice persisted and still rejected the challenger.

## Calibration And Drift

- Calibration audit: `calibration_6c40fa2999b92e0c68a252e1634b5c11`
- Calibration warnings: `score_concentrated_in_one_bucket`, `severe_regime_instability`, `too_few_high_grade_samples`
- Calibration rejection reasons: `minimum_high_grade_samples_not_met`, `take_does_not_outperform_watch`
- Drift report: `calibration_drift_3836049826a9239e3a0fc36842ba2c5e`
- Drift severity: `REVIEW`

## Model Review

- Review: `model_review_9262300c8d3fffe75e0ff0e98ebe90d3`
- Readiness: `BLOCK`
- Diagnostic only: `true`
- Model activation unchanged: `true`

## Research Cycle And Proposal

- Research cycle: `research_cycle_938bf1f9375fecb54a7cfb1ebf00c255`
- Cycle status: `BLOCKED`
- Comparison: `champion_challenger_635360662a088fdf74510924504c67f8`
- Recommended action: `REJECT_CHALLENGER`
- Proposal: `proposal_c34d0341e050a30bcdd815ffc0b0fa70`
- Proposal status: `REJECTED`
- Readiness: `BLOCK`

The proposal required approval but was rejected by gates. No activation occurred.
