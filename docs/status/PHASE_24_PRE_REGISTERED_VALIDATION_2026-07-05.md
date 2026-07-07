# Phase 24 Pre-Registered Validation

`PHASE_24_PRE_REGISTERED_VALIDATION_STATUS = NEEDS_MORE_DATA_WITH_REJECTION_EVIDENCE`

The expanded base 15min ten-am cohort grew from Phase 23's 82 candidates to 330 candidates. The stricter Phase 24 signal-time scorer selected only 2 post-embargo TAKE candidates.

## Scoring Model

- Model version: `amd-replay-aware-20260611-181743`
- Model type: replay-aware deterministic evidence baseline
- Active: `false`
- Candidate outcome rows: 1,729
- Evidence cells: 865
- Training replay IDs: `replay_20260706181740_7e64266c3134dfb513184caf`, `replay_20260706181741_3fe1d8cebbfdb4fdbdecc78d`
- Warning: `some_training_replay_runs_missing_sensitivity`
- Rejection reason: `validation_required`

## OOS Score Result

| Action | Count |
|---|---:|
| `SUPPRESS` | 143 |
| `TAKE` | 2 |
| `WATCH` | 0 |

## Pre-Registered Replay Result

| Purpose | Replay ID | Trades | Avg R | Profit factor | Sensitivity ID | Robustness | Worst avg R |
|---|---|---:|---:|---:|---|---:|---:|
| Portfolio | `r24_prereg_p_f949d7230c32` | 2 | -1.000000 | 0.000000 | `s24_prereg_p_f949d7230c32` | 0.00 | -1.000000 |
| Counterfactual | `r24_prereg_c_f949d7230c32` | 2 | -1.000000 | 0.000000 | `s24_prereg_c_f949d7230c32` | 0.00 | -1.000000 |

Both pre-registered sensitivity runs completed the full default grid: 75 scenarios, 0 passes, 75 failures.

## Concentration

The selected cohort was only two short `VWAP loss short` candidates: one `AAPL`, one `SPY`, on `2026-06-25` and `2026-06-29`. Max setup concentration was `1.00`; max symbol and day concentration were each `0.50`.

## Calibration

- Calibration audit: `calibration_e2e0661d5b36ca23f485cd70b7fea585`
- Scored outcomes: 2
- Monotonicity: pass
- Rank correlation: 0.0
- Rejection reason: `minimum_high_grade_samples_not_met`
- Warnings: `high_score_depends_on_one_setup`, `high_score_depends_on_one_symbol`, `high_score_negative_expectancy`, `too_few_high_grade_samples`
