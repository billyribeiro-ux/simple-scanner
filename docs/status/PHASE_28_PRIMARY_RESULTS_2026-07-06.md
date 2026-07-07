# Phase 28 Primary Results

Status date: 2026-07-06

`PHASE_28_PRIMARY_RESULTS_STATUS = RECORDED_REJECTED_BY_SENSITIVITY`

Source ID: `phase28_tcs_13dcd7f09159fc3c`

Spec hash: `9bcac6111f0c6e079b20c6160386d4ad2f78c4c9755cbbad788992350903162b`

## Primary Cohort

The primary cohort was pre-registered as `trend continuation short`, side `SHORT`, all symbols in the clean evidence DB, intervals `1min`, `5min`, and `15min` evaluated separately, with no primary symbol, regime, time-bucket, score, or ambiguity exclusions.

Counterfactual replay is candidate-quality evidence only. It is not executable portfolio P/L.

## Portfolio Replay

| Interval | Replay run | OOS candidates | Trades | Avg R | Median R | Total R | PF | Win rate | Max DD R | Same-bar |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `1min` | `replay_20260707145551_63c139924925d9a1fecea3d6` | 87 | 40 | 0.161701 | -1.000000 | 6.468023 | 1.308001 | 47.50% | -12.000000 | 1/40 = 2.50% |
| `5min` | `replay_20260707145601_34fda880748c6ac0060e8ff9` | 89 | 35 | 0.168638 | -0.307860 | 5.902345 | 1.350594 | 45.71% | -7.647209 | 4/35 = 11.43% |
| `15min` | `replay_20260707145604_8ad43606db5101a7530cecfb` | 189 | 78 | -0.058462 | -0.676105 | -4.560024 | 0.888915 | 41.03% | -14.257854 | 6/78 = 7.69% |

## Counterfactual Replay

| Interval | Replay run | OOS candidates | Trades | Avg R | Median R | Total R | PF | Win rate | Max DD R | Same-bar |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `1min` | `replay_20260707145553_0fa4e8271f193d8d470873ff` | 87 | 86 | 0.111022 | -1.000000 | 9.547905 | 1.203147 | 45.35% | -23.000000 | 2/86 = 2.33% |
| `5min` | `replay_20260707145601_6b867698c9216f4fd8d69bf8` | 89 | 88 | 0.170699 | -0.162735 | 15.021498 | 1.350681 | 48.86% | -19.183688 | 5/88 = 5.68% |
| `15min` | `replay_20260707145605_46e5409418002ad0f72380eb` | 189 | 186 | -0.064282 | -0.574903 | -11.956516 | 0.873549 | 43.01% | -37.499712 | 11/186 = 5.91% |

## Full-Grid Sensitivity

Each replay ran the full default 75-scenario grid.

| Interval | Purpose | Sensitivity run | Pass/fail | Robustness | Passed | Failed | Worst avg R | Worst PF | Key flags |
|---|---|---|---|---:|---:|---:|---:|---:|---|
| `1min` | Portfolio | `sensitivity_e59e3d13e2d7d74025ff19c62762c5cc` | fail | 0.00 | 0 | 75 | -0.673913 | 0.225000 | non-positive expectancy; PF not robust; robustness below threshold; same-bar path affected |
| `1min` | Counterfactual | `sensitivity_0674c2bfee34ec075e5091d1707745c0` | fail | 0.00 | 0 | 75 | -0.622093 | 0.267123 | non-positive expectancy; PF not robust; robustness below threshold; same-bar path affected |
| `5min` | Portfolio | `sensitivity_64e22ec30dd805200870837402e23e04` | fail | 0.44 | 33 | 42 | -0.380148 | 0.464076 | robustness below threshold; same-bar path affected |
| `5min` | Counterfactual | `sensitivity_798b713f5fcc90ebb1d3fd393d2743ed` | fail | 0.00 | 0 | 75 | -0.363921 | 0.493025 | robustness below threshold; same-bar path affected |
| `15min` | Portfolio | `sensitivity_1a75b509b4a4a06a42741a605025fcd8` | fail | 0.00 | 0 | 75 | -0.504789 | 0.280992 | non-positive expectancy; PF not robust; robustness below threshold; same-bar path affected |
| `15min` | Counterfactual | `sensitivity_0bd27236348751249b0c4ffee3f6a112` | fail | 0.00 | 0 | 75 | -0.522210 | 0.255063 | non-positive expectancy; PF not robust; robustness below threshold; same-bar path affected |

## Validation And Calibration Diagnostics

| Interval | Validation status | Validation reasons | Calibration status | Calibration warnings | Decision |
|---|---|---|---|---|---|
| `1min` | rejected | `full_grid_sensitivity_failed` | diagnostic_rejected | `sensitivity_robustness_below_threshold` | `REJECTED_BY_SENSITIVITY` |
| `5min` | rejected | `full_grid_sensitivity_failed` | diagnostic_rejected | `sensitivity_robustness_below_threshold` | `REJECTED_BY_SENSITIVITY` |
| `15min` | rejected | `counterfactual_oos_expectancy_not_positive`; `portfolio_oos_expectancy_not_positive`; `full_grid_sensitivity_failed` | diagnostic_rejected | `sensitivity_robustness_below_threshold` | `REJECTED_BY_SENSITIVITY` |

## Primary Conclusion

The baseline `1min` and `5min` replays were positive, but every interval failed the required full-grid sensitivity standard. The `15min` interval was negative in both portfolio and counterfactual replay before sensitivity.

Primary decision: `REJECTED_BY_SENSITIVITY`.

No activation, proposal approval, gate loosening, OOS filter selection, broker execution, production WebSocket ingestion, or profitability claim occurred.
