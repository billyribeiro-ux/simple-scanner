# Phase 22 Sensitivity Failure Decomposition

Date: 2026-07-05
Status: COMPLETE_DIAGNOSTIC

## Scope

This report decomposes the Phase 21W full-grid sensitivity failure across cost, path, interval, replay purpose, and same-bar ambiguity dimensions. It uses only persisted Phase 21W replay and sensitivity evidence from `adaptive_market_decoder_evidence`.

No model was activated, no proposal was approved, no stale gate was bypassed, and no profitability claim is made.

## Source Runs

All six source runs were `CHUNKED_FULL_GRID`, `COMPLETE`, `75/75` scenarios, `full_default_grid_complete=true`, and `partial_grid_disclosure=false`.

| Interval | Purpose | Sensitivity run | Scenario pass count | Baseline avg R | Baseline PF | Best avg R | Worst avg R | High-cost delta |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `1min` | portfolio | `sensitivity_ab486e2337c9de415328f76cecf1c4c7` | 0/75 | -0.064168 | 0.896834 | -0.064168 | -0.967995 | -0.610678 |
| `1min` | counterfactual | `sensitivity_4747000982a7dd1c24c48798b27d0970` | 0/75 | -0.087211 | 0.861505 | -0.087211 | -0.943494 | -0.589124 |
| `5min` | portfolio | `sensitivity_df6e25965262b6d29d8bb6ad9aa0bcde` | 0/75 | -0.116468 | 0.814970 | -0.116468 | -0.823555 | -0.409657 |
| `5min` | counterfactual | `sensitivity_d1fa1d06e2ac1151f5b20d96db8fefc8` | 0/75 | -0.137221 | 0.782513 | -0.137221 | -0.759394 | -0.365919 |
| `15min` | portfolio | `sensitivity_7b270b48d0b1e8580a696a60d82c859e` | 0/75 | -0.145227 | 0.752779 | -0.145227 | -0.660877 | -0.292641 |
| `15min` | counterfactual | `sensitivity_90441b99f44ddd04caeddcbaa244419f` | 0/75 | -0.174658 | 0.704234 | -0.174658 | -0.625826 | -0.256016 |

## Primary Finding

The failure is not a narrow high-cost artifact. Every zero-cost conservative baseline already had negative average R and profit factor below 1.0, so the challenger failed before slippage/spread stress was applied. Costs then made an already-negative profile materially worse.

## Cost Attribution

| Dimension | Value | Scenario rows | Scenario pass rate | Avg scenario avg R | Avg PF | Avg trades | Avg same-bar count |
|---|---:|---:|---:|---:|---:|---:|---:|
| slippage bps | 0 | 90 | 0.00% | -0.232844 | 0.655742 | 2241.67 | 113.00 |
| slippage bps | 1 | 90 | 0.00% | -0.290190 | 0.583444 | 2245.53 | 93.00 |
| slippage bps | 2 | 90 | 0.00% | -0.350392 | 0.512155 | 2254.00 | 79.17 |
| slippage bps | 5 | 90 | 0.00% | -0.518830 | 0.339189 | 2316.37 | 58.87 |
| slippage bps | 10 | 90 | 0.00% | -0.725686 | 0.166133 | 2538.67 | 42.57 |
| spread bps | 0 | 90 | 0.00% | -0.331332 | 0.554187 | 2289.83 | 97.53 |
| spread bps | 1 | 90 | 0.00% | -0.358581 | 0.521036 | 2302.20 | 87.70 |
| spread bps | 2 | 90 | 0.00% | -0.385702 | 0.488468 | 2305.40 | 81.93 |
| spread bps | 5 | 90 | 0.00% | -0.458480 | 0.407537 | 2321.20 | 65.67 |
| spread bps | 10 | 90 | 0.00% | -0.583846 | 0.285435 | 2377.60 | 53.77 |

Isolated cost effects under conservative path:

| Effect | Value | Avg scenario avg R | Avg PF | Mean delta from zero-cost conservative |
|---|---:|---:|---:|---:|
| slippage | 0 | -0.120826 | 0.802139 | 0.000000 |
| slippage | 1 | -0.186013 | 0.709102 | -0.065187 |
| slippage | 2 | -0.240313 | 0.636827 | -0.119487 |
| slippage | 5 | -0.424680 | 0.425421 | -0.303855 |
| slippage | 10 | -0.684831 | 0.197448 | -0.564005 |
| spread | 0 | -0.120826 | 0.802139 | 0.000000 |
| spread | 1 | -0.153891 | 0.753844 | -0.033066 |
| spread | 2 | -0.186013 | 0.709102 | -0.065187 |
| spread | 5 | -0.278812 | 0.588204 | -0.157986 |
| spread | 10 | -0.424680 | 0.425421 | -0.303855 |

Slippage was the stronger explicit cost driver in this grid. Ten basis points of isolated slippage moved mean average R by `-0.564005`, while ten basis points of isolated spread moved it by `-0.303855`. Spread still mattered, but the replay cost model applies half-spread at entry and exit, so the observed spread effect is roughly half the slippage effect.

## Intrabar And Same-Bar Attribution

| Intrabar path policy | Scenario rows | Scenario pass rate | Avg scenario avg R | Avg PF | Avg trades | Avg same-bar count |
|---|---:|---:|---:|---:|---:|---:|
| `conservative` | 150 | 0.00% | -0.423588 | 0.451333 | 2319.25 | 77.32 |
| `open_high_low_close` | 150 | 0.00% | -0.423588 | 0.451333 | 2319.25 | 77.32 |
| `open_low_high_close` | 150 | 0.00% | -0.423588 | 0.451333 | 2319.25 | 77.32 |

The three recorded intrabar path policies produced identical aggregate results in the current replay implementation. Therefore Phase 22 does not attribute failure to one intrabar ordering variant over another.

Same-bar ambiguity is still a material failure source because the same-bar stop/target policy is `conservative_stop_first`. Source replay trade attribution found:

| Same-bar ambiguous | Observed trades | Total R | Avg R | Profit factor | Win rate |
|---|---:|---:|---:|---:|---:|
| `true` | 917 | -917.000000 | -1.000000 | 0.000000 | 0.00% |
| `false` | 12482 | -440.295730 | -0.035274 | 0.940970 | 39.25% |

Same-bar ambiguous outcomes explain a large portion of the loss, but not all of it. Non-ambiguous trades remained negative, so an ambiguity filter alone is not enough to make the current challenger robust.

## Interval And Purpose Attribution

| Interval | Purpose | Observed trades | Total R | Avg R | Profit factor | Win rate | Same-bar rate |
|---|---|---:|---:|---:|---:|---:|---:|
| `1min` | counterfactual | 7295 | -636.201771 | -0.087211 | 0.861505 | 36.66% | 4.93% |
| `5min` | counterfactual | 2324 | -318.902270 | -0.137221 | 0.782513 | 35.59% | 9.29% |
| `15min` | counterfactual | 942 | -164.527943 | -0.174658 | 0.704234 | 36.20% | 13.06% |
| `1min` | portfolio | 1938 | -124.358366 | -0.064168 | 0.896834 | 37.62% | 5.83% |
| `5min` | portfolio | 605 | -70.463368 | -0.116468 | 0.814970 | 36.03% | 10.91% |
| `15min` | portfolio | 295 | -42.842014 | -0.145227 | 0.752779 | 37.29% | 13.22% |

The highest total R loss came from the `1min` counterfactual because it had the largest sample. The worst average R and weakest profit factor were on `15min` counterfactual, but the sample was smaller. Portfolio replay was less negative than counterfactual replay because portfolio constraints skipped many candidates; that does not convert it into robust evidence.

## Failure Attribution Summary

- Baseline strategy evidence was negative before sensitivity stress.
- Slippage was the largest explicit cost sensitivity driver.
- Spread was a secondary but material cost driver.
- Intrabar path labels did not change metrics in the current replay engine, so no path-order variant explains the failure.
- Same-bar ambiguity materially hurt because conservative stop-first outcomes were uniformly losing.
- Failure was broad across all intervals and both replay purposes.
- The full-grid rejection remains valid activation-grade evidence.

