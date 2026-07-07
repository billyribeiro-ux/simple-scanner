# Phase 22 Robust Subset Discovery

Date: 2026-07-05
Status: COMPLETE_DIAGNOSTIC_REJECTION

## Scope

This report searches for candidate subsets that remained robust across the Phase 21W full sensitivity grid. It is research-only. No subset in this report is an activation candidate.

Subset research pass criteria used for triage:

- at least 5 trades in the scenario subset;
- average R greater than 0;
- profit factor at least 1.0.

Full-grid robust subset criteria:

- all 75 scenarios present for the interval/purpose scope;
- all 75 scenario subset rows pass the research criteria;
- no negative worst-case scenario in that scope.

## Result

Full-grid robust groups found: `0`.

No symbol, setup, side, time bucket, or regime subset survived all 75 scenarios in any interval/purpose scope. Therefore:

- no subset passed full-grid robustness and failed validation/calibration;
- no subset passed validation but failed sensitivity;
- no subset can be treated as activation-grade evidence;
- the current challenger remains rejected.

## Exploratory Positive Pockets

These are not robust. They are only candidates for a future specialist-filter experiment.

| Dimension | Value | Interval | Purpose | Scenario pass rate | Avg scenario avg R | Worst scenario avg R | Avg trades/scenario |
|---|---|---|---|---:|---:|---:|---:|
| `time_bucket` | `ten_am_reversal_zone` | `15min` | counterfactual | 68.00% | 0.086835 | -0.424572 | 82.00 |
| `time_bucket` | `ten_am_reversal_zone` | `15min` | portfolio | 64.00% | 0.108785 | -0.353597 | 23.88 |

The `15min` ten-am reversal zone is the only repeatable positive-looking pocket, but it still failed 24/75 counterfactual scenarios and 27/75 portfolio scenarios. Its worst scenarios remained negative, so it is not robust.

## Score-Audit Pockets

Score-audit cohorts showed positive observed source replay outcomes, but they do not have full-grid grade/action sensitivity proof and the model-level calibration audit remained rejected.

| Score group | Observed trades joined | Total R | Avg R | Profit factor | Win rate | Same-bar rate |
|---|---:|---:|---:|---:|---:|---:|
| `TAKE` action | 212 | 198.436310 | 0.936020 | 5.563002 | 78.30% | 1.42% |
| `WATCH` action | 918 | 369.454852 | 0.402456 | 1.946271 | 57.08% | 2.29% |
| `SUPPRESS` action | 12194 | -1883.725407 | -0.154480 | 0.760975 | 34.40% | 7.25% |
| `A-` grade | 58 | 40.603975 | 0.700069 | 3.463719 | 68.97% | 5.17% |
| `B+` grade | 154 | 157.832335 | 1.024885 | 6.844052 | 81.82% | 0.00% |
| `B` grade | 387 | 190.147067 | 0.491336 | 2.298530 | 61.24% | 1.03% |
| `C` grade | 531 | 179.307785 | 0.337679 | 1.734868 | 54.05% | 3.20% |
| `NO_TRADE` grade | 12194 | -1883.725407 | -0.154480 | 0.760975 | 34.40% | 7.25% |

Interpretation: the scorer did separate some better observed replay outcomes, but Phase 21W governance still rejected the challenger because validation, calibration, drift/watch, and full-grid sensitivity gates did not all pass. Positive score cohorts are a future research lead, not proof of readiness.

## Worst Full-Grid Subsets

| Dimension | Value | Scenario rows | Scenario pass rate | Avg scenario avg R | Worst scenario avg R | Avg trades/scenario |
|---|---|---:|---:|---:|---:|---:|
| `time_bucket` | `power_hour` | 450 | 0.00% | -0.584285 | -0.976579 | 484.54 |
| `symbol` | `SPY` | 450 | 0.00% | -0.552555 | -1.000000 | 537.40 |
| `setup` | `opening range breakdown short` | 450 | 0.00% | -0.539117 | -0.983480 | 355.44 |
| `setup` | `liquidity sweep reversal long` | 450 | 0.00% | -0.539098 | -0.937500 | 81.94 |
| `time_bucket` | `afternoon_continuation` | 450 | 0.00% | -0.516713 | -0.999972 | 495.02 |
| `setup` | `failed breakdown long` | 450 | 0.00% | -0.510970 | -0.933367 | 107.66 |
| `setup` | `opening range breakout long` | 450 | 0.00% | -0.485401 | -0.993902 | 456.85 |
| `side` | `LONG` | 450 | 0.00% | -0.462444 | -0.974791 | 1199.78 |

## Research Decision

`PHASE_22_ROBUST_SUBSET_STATUS = NO_FULL_GRID_ROBUST_SUBSET_FOUND`

There is enough concentration to justify one future specialist-filter experiment focused on:

- `15min` `ten_am_reversal_zone`;
- training-fold-only score action/grade cohorts;
- signal-time ambiguity-risk suppression;
- exclusion or downweighting of the worst time buckets, symbols, and setup families.

That future experiment must regenerate artifacts, rerun validation/calibration/drift/review, rerun full-grid sensitivity, record a strict dry-run, and keep active models at `0`.

