# Phase 26 Phase 25 Comparison

Status date: 2026-07-06

`PHASE_26_PHASE25_COMPARISON_STATUS = BROADER_SAMPLE_REJECTED`

Source ID: `phase26_537f582b33387bf5`

| Metric | Phase 25 | Phase 26 |
|---|---:|---:|
| OOS scored/actionable candidates | 145 | 145 |
| Current TAKE/WATCH selected | 2 | 2 |
| Broader all-actionable selected | 145 | 145 |
| Selected-count multiplier vs TAKE/WATCH | n/a | 72.5x |
| All-OOS counterfactual avg R | -0.057926 | -0.057926 |
| Current TAKE/WATCH counterfactual avg R | -1.000000 | -1.000000 |
| All-actionable portfolio robustness | 0.00 | 0.00 |
| All-actionable counterfactual robustness | 0.00 | 0.00 |
| Exact evidence-cell matches | 128 | 128 |
| Broad-parent-reliant OOS candidates | 113 | 113 |
| Exact specialist cells with 5+ outcomes | 7 | 7 |
| Exact specialist cells with 10+ outcomes | not recorded | 0 |
| Active models | 0 | 0 |

Phase 26 answers the Phase 25 uncertainty: the sparse current TAKE/WATCH action policy is not the only problem. The broader all-actionable OOS cohort has enough count for a diagnostic test, but its OOS expectancy remains negative and the full-grid sensitivity result remains 0.00 robustness.
