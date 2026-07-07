# Phase 26 Policy Evaluation

Status date: 2026-07-06

`PHASE_26_POLICY_EVALUATION_STATUS = ALL_PRIMARY_POLICIES_REJECTED`

Source ID: `phase26_537f582b33387bf5`

All policies were evaluated against frozen training-only thresholds. Policy H is the current TAKE/WATCH policy and is reference-only.

| Policy | Threshold | Train selected | OOS selected | Portfolio trades | Portfolio avg R | Counterfactual trades | Counterfactual avg R | PF cf | Robustness p/c | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| A all actionable | none | 178 | 145 | 57 | -0.053513 | 145 | -0.057926 | 0.904474 | 0.00 / 0.00 | REJECTED_BY_SENSITIVITY |
| B score q75 | 35.000000 | 150 | 135 | 53 | -0.123590 | 135 | -0.136291 | 0.785872 | 0.00 / 0.00 | REJECTED_BY_SENSITIVITY |
| C score q90 | 35.000000 | 150 | 135 | 53 | -0.123590 | 135 | -0.136291 | 0.785872 | 0.00 / 0.00 | REJECTED_BY_SENSITIVITY |
| D pre-ceiling q75 | 53.729132 | 47 | 35 | 20 | -0.054547 | 35 | -0.205196 | 0.687745 | 0.00 / 0.00 | REJECTED_BY_SENSITIVITY |
| E pre-ceiling q90 | 69.735132 | 19 | 6 | 5 | -0.500000 | 6 | -0.583333 | 0.300000 | 0.00 / 0.00 | REJECTED_BY_SENSITIVITY |
| F evidence quality q75 | 6.415500 | 47 | 35 | 20 | -0.054547 | 35 | -0.205196 | 0.687745 | 0.00 / 0.00 | REJECTED_BY_SENSITIVITY |
| G time bucket q75 | 18.682600 | 45 | 35 | 20 | -0.054547 | 35 | -0.205196 | 0.687745 | 0.00 / 0.00 | REJECTED_BY_SENSITIVITY |
| H current TAKE/WATCH | TAKE/WATCH | 7 | 2 | 2 | -1.000000 | 2 | -1.000000 | 0.000000 | 0.00 / 0.00 | REJECTED_BY_SENSITIVITY |

## Full-Grid Sensitivity

Every Phase 26 replay was run through the full 75-scenario default grid. Phase 26 added 16 replay runs, 16 sensitivity runs, and 1200 sensitivity scenarios.

| Policy | Portfolio sensitivity | Counterfactual sensitivity | Worst result |
|---|---|---|---|
| A | fail, robustness 0.00 | fail, robustness 0.00 | rejected by full-grid sensitivity |
| B | fail, robustness 0.00 | fail, robustness 0.00 | rejected by full-grid sensitivity |
| C | fail, robustness 0.00 | fail, robustness 0.00 | rejected by full-grid sensitivity |
| D | fail, robustness 0.00 | fail, robustness 0.00 | rejected by full-grid sensitivity |
| E | fail, robustness 0.00 | fail, robustness 0.00 | rejected by full-grid sensitivity |
| F | fail, robustness 0.00 | fail, robustness 0.00 | rejected by full-grid sensitivity |
| G | fail, robustness 0.00 | fail, robustness 0.00 | rejected by full-grid sensitivity |
| H | fail, robustness 0.00 | fail, robustness 0.00 | reference policy only |

## Interpretation

Scoring all actionable candidates improves sample size versus the TAKE/WATCH slice, but it does not improve validation quality. The broader cohort is still negative OOS and not robust under full-grid sensitivity.
