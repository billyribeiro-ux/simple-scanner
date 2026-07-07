# Phase 28 Exploratory Results

Status date: 2026-07-06

`PHASE_28_EXPLORATORY_RESULTS_STATUS = RECORDED_DIAGNOSTIC_ONLY`

Source ID: `phase28_tcs_13dcd7f09159fc3c`

Spec hash: `9bcac6111f0c6e079b20c6160386d4ad2f78c4c9755cbbad788992350903162b`

## Guardrail

These diagnostics were evaluated after the primary results were recorded. They are not activation evidence and cannot be used to choose live filters, symbol exclusions, regime exclusions, time-bucket exclusions, or same-bar ambiguity filters for Phase 28.

Same-bar ambiguity is realized replay evidence only. It is explicitly not a live filter.

## `1min` Exploratory Attribution

| Dimension | Group | Trades | Avg R | Total R | PF | Same-bar rate |
|---|---|---:|---:|---:|---:|---:|
| Symbol | AAPL | 21 | -0.021528 | -0.452095 | 0.962325 | 0.00% |
| Symbol | NVDA | 48 | 0.197917 | 9.500000 | 1.380000 | 4.17% |
| Symbol | QQQ | 17 | 0.029412 | 0.500000 | 1.050000 | 0.00% |
| Regime | chop | 15 | 0.597868 | 8.968023 | 2.793605 | 0.00% |
| Regime | mean_reversion | 6 | -1.000000 | -6.000000 | 0.000000 | 16.67% |
| Regime | opening_drive | 20 | 0.375000 | 7.500000 | 1.833333 | 0.00% |
| Regime | trend_short | 45 | -0.020447 | -0.920118 | 0.965922 | 2.22% |
| Time bucket | afternoon_continuation | 1 | -1.000000 | -1.000000 | 0.000000 | 0.00% |
| Time bucket | lunch_window | 1 | 1.500000 | 1.500000 | n/a | 0.00% |
| Time bucket | off_hours | 23 | -0.215308 | -4.952095 | 0.669860 | 0.00% |
| Time bucket | opening_drive | 23 | 0.413043 | 9.500000 | 1.950000 | 0.00% |
| Time bucket | power_hour | 13 | 0.346154 | 4.500000 | 1.750000 | 7.69% |
| Time bucket | ten_am_reversal_zone | 25 | 0.000000 | 0.000000 | 1.000000 | 4.00% |
| Same-bar | false | 84 | 0.137475 | 11.547905 | 1.256620 | 0.00% |
| Same-bar | true | 2 | -1.000000 | -2.000000 | 0.000000 | 100.00% |

## `5min` Exploratory Attribution

| Dimension | Group | Trades | Avg R | Total R | PF | Same-bar rate |
|---|---|---:|---:|---:|---:|---:|
| Symbol | AAPL | 23 | -0.175320 | -4.032365 | 0.718171 | 0.00% |
| Symbol | NVDA | 38 | 0.125563 | 4.771380 | 1.257531 | 10.53% |
| Symbol | QQQ | 23 | 0.577499 | 13.282483 | 2.660310 | 4.35% |
| Symbol | SPY | 4 | 0.250000 | 1.000000 | 1.500000 | 0.00% |
| Regime | chop | 2 | 0.250000 | 0.500000 | 1.500000 | 50.00% |
| Regime | mean_reversion | 21 | -0.036645 | -0.769537 | 0.931947 | 4.76% |
| Regime | opening_drive | 3 | 0.666667 | 2.000000 | 3.000000 | 0.00% |
| Regime | trend_long | 9 | 0.443355 | 3.990196 | 2.136872 | 0.00% |
| Regime | trend_short | 53 | 0.175488 | 9.300838 | 1.357482 | 5.66% |
| Time bucket | afternoon_continuation | 5 | -0.500000 | -2.500000 | 0.375000 | 0.00% |
| Time bucket | lunch_window | 22 | -0.065582 | -1.442807 | 0.889165 | 0.00% |
| Time bucket | off_hours | 26 | 0.589171 | 15.318448 | 2.914806 | 3.85% |
| Time bucket | opening_drive | 4 | 0.875000 | 3.500000 | 4.500000 | 0.00% |
| Time bucket | power_hour | 8 | -0.529646 | -4.237171 | 0.293805 | 50.00% |
| Time bucket | ten_am_reversal_zone | 23 | 0.190566 | 4.383028 | 1.405173 | 0.00% |
| Same-bar | false | 83 | 0.241223 | 20.021498 | 1.529175 | 0.00% |
| Same-bar | true | 5 | -1.000000 | -5.000000 | 0.000000 | 100.00% |

## `15min` Exploratory Attribution

| Dimension | Group | Trades | Avg R | Total R | PF | Same-bar rate |
|---|---|---:|---:|---:|---:|---:|
| Symbol | AAPL | 60 | -0.212558 | -12.753490 | 0.640749 | 8.33% |
| Symbol | NVDA | 60 | -0.097879 | -5.872761 | 0.801225 | 5.00% |
| Symbol | QQQ | 42 | 0.142393 | 5.980501 | 1.329765 | 7.14% |
| Symbol | SPY | 24 | 0.028718 | 0.689235 | 1.060597 | 0.00% |
| Regime | chop | 4 | 0.345136 | 1.380544 | 5.836873 | 0.00% |
| Regime | mean_reversion | 39 | -0.026377 | -1.028718 | 0.946146 | 10.26% |
| Regime | trend_long | 12 | -0.294372 | -3.532467 | 0.533857 | 0.00% |
| Regime | trend_short | 131 | -0.066991 | -8.775875 | 0.870158 | 5.34% |
| Time bucket | afternoon_continuation | 44 | -0.193344 | -8.507135 | 0.681847 | 0.00% |
| Time bucket | lunch_window | 70 | 0.087561 | 6.129241 | 1.196107 | 1.43% |
| Time bucket | off_hours | 38 | -0.111498 | -4.236919 | 0.756818 | 2.63% |
| Time bucket | power_hour | 34 | -0.157109 | -5.341702 | 0.720887 | 26.47% |
| Same-bar | false | 175 | -0.005466 | -0.956516 | 0.988552 | 0.00% |
| Same-bar | true | 11 | -1.000000 | -11.000000 | 0.000000 | 100.00% |

## Exploratory Read

The exploratory tables show pockets that looked better at baseline, such as `5min` QQQ and off-hours, but these are post-primary diagnostics only. They do not override the primary full-grid sensitivity rejection and must not be promoted into a Phase 28 activation filter.

Any future specialist experiment would need a new pre-registered spec, training-only rationale, chronological OOS split, calibration checks, and full-grid sensitivity before decision.
