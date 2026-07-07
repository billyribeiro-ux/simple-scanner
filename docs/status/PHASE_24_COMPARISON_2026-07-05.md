# Phase 24 Comparison

`PHASE_24_COMPARISON_STATUS = RECORDED_NO_SPECIALIST_CANDIDATE`

## Phase 23 To Phase 24

| Metric | Phase 23 | Phase 24 |
|---|---:|---:|
| 15min ten-am actionable base candidates | 82 | 330 |
| Split method | 48 discovery / 34 validation | 178 discovery / 7 embargo / 82 validation / 63 holdout |
| TAKE/WATCH selected candidates | 9 | 2 |
| Portfolio avg R for selected slice | 1.500000 | -1.000000 |
| Counterfactual avg R for selected slice | 1.500000 | -1.000000 |
| Portfolio robustness | 1.00 | 0.00 |
| Counterfactual robustness | 1.00 | 0.00 |
| Decision | Low-sample blocked | Needs more data with validation/sensitivity/calibration rejection evidence |

Phase 24 replaced Phase 23's diagnostic persisted-score slice with a stricter discovery-trained scorer. That stricter signal-time rule did not expand the TAKE/WATCH cohort; it reduced the out-of-sample selected set to 2 candidates and both failed.

## Expanded Baseline

The expanded all-candidate 15min baseline also remained weak:

- Portfolio replay `replay_20260706181047_b0fdc7ee603396c41bc181b0`: avg R `-0.179516`, robustness `0.00`.
- Counterfactual replay `replay_20260706181050_dcc34871f61eda7937dca55d`: avg R `-0.160676`, robustness `0.00`.

The comparison does not support activation.
