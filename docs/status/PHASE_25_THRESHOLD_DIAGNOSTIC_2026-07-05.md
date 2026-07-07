# Phase 25 Threshold Diagnostic

`PHASE_25_THRESHOLD_DIAGNOSTIC_STATUS = DIAGNOSTIC_ONLY`

Current TAKE threshold: `70.0`.
Suppressed score ceiling: `35.0`.
Explicit WATCH threshold: `None`.

WATCH occurs only when suppression_reasons is empty and score is below take_score_threshold.

| threshold_source | threshold | oos_score_count_at_or_above | oos_unsuppressed_count_at_or_above | oos_pre_ceiling_count_at_or_above |
| --- | --- | --- | --- | --- |
| current_take_threshold | 70.000000 | 2 | 2 | 5 |
| training_score_q75 | 35.000000 | 135 | 2 | 145 |
| training_score_q90 | 35.000000 | 135 | 2 | 145 |
| training_pre_ceiling_q75 | 53.729132 | 2 | 2 | 35 |
| training_pre_ceiling_q90 | 69.735132 | 2 | 2 | 6 |

The zero-WATCH result is caused by suppression reasons on every below-TAKE candidate, not by a separate WATCH cutoff. No threshold change is recommended without a future pre-registered test.
