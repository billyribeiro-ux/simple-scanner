# Phase 25 Phase 23 Vs Phase 24 Comparison

`PHASE_25_PHASE23_PHASE24_COMPARISON_STATUS = RECORDED`

| metric | phase23 | phase24 |
| --- | --- | --- |
| base actionable candidates | 82 | 330 |
| OOS/validation scored candidates | 34 | 145 |
| TAKE/WATCH selected candidates | 9 | 2 |
| selected TAKE count | 1 | 2 |
| selected WATCH count | 8 | 0 |
| selected portfolio avg R | 1.500000 | -1.000000 |
| selected counterfactual avg R | 1.500000 | -1.000000 |
| selected portfolio robustness | 1.000000 | 0.000000 |
| selected counterfactual robustness | 1.000000 | 0.000000 |
| sample-size classification | low_sample_blocked | needs_more_data_with_rejection_evidence |

Likely. The Phase 23 slice had only 9 total candidates and 6 validation trades; Phase 24 expanded the base cohort, trained the scorer only on discovery evidence, selected only 2 OOS TAKE candidates, and both lost.
