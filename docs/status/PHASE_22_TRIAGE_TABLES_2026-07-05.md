# Phase 22 Triage Tables

Date: 2026-07-05
Status: COMPLETE_DIAGNOSTIC

## Source Replay Triage

The following tables use observed source replay trades from the six Phase 21W replay runs. They are attribution tables, not profitability evidence.

## Symbol Triage

| Symbol | Observed trades | Total R | Avg R | Profit factor | Win rate | Same-bar rate |
|---|---:|---:|---:|---:|---:|---:|
| `NVDA` | 3618 | -457.184007 | -0.126364 | 0.801233 | 35.66% | 6.66% |
| `SPY` | 3042 | -444.535404 | -0.146133 | 0.772717 | 34.62% | 7.59% |
| `QQQ` | 3346 | -229.914621 | -0.068713 | 0.888028 | 37.96% | 7.20% |
| `AAPL` | 3393 | -225.661698 | -0.066508 | 0.890800 | 37.90% | 6.01% |

SPY had the worst average R and second-worst total R. NVDA had the worst total R due to larger sample and broad negative expectancy.

## Setup Triage

| Setup | Observed trades | Total R | Avg R | Profit factor | Win rate | Same-bar rate |
|---|---:|---:|---:|---:|---:|---:|
| `opening range breakdown short` | 2076 | -298.322595 | -0.143701 | 0.778967 | 34.54% | 4.38% |
| `opening range breakout long` | 2637 | -261.698292 | -0.099241 | 0.841210 | 36.63% | 5.20% |
| `VWAP reclaim long` | 2318 | -184.820884 | -0.079733 | 0.869742 | 37.53% | 0.78% |
| `trend continuation long` | 678 | -118.698393 | -0.175071 | 0.712262 | 36.28% | 3.83% |
| `failed breakdown long` | 615 | -111.585974 | -0.181441 | 0.728265 | 32.85% | 25.37% |
| `failed breakout short` | 681 | -104.000485 | -0.152717 | 0.768633 | 33.92% | 22.61% |
| `liquidity sweep reversal long` | 477 | -100.769649 | -0.211257 | 0.688747 | 31.87% | 24.95% |
| `liquidity sweep reversal short` | 527 | -65.000485 | -0.123341 | 0.809664 | 35.10% | 21.06% |
| `VWAP loss short` | 2293 | -57.818571 | -0.025215 | 0.958128 | 39.38% | 2.05% |
| `previous day low loss short` | 195 | -38.583947 | -0.197866 | 0.699160 | 31.79% | 5.13% |
| `previous day high reclaim long` | 187 | -19.956935 | -0.106722 | 0.826175 | 36.90% | 3.74% |
| `trend continuation short` | 715 | 3.960479 | 0.005539 | 1.009968 | 41.40% | 5.73% |

`trend continuation short` was slightly positive in source replay, but it did not survive the full-grid subset search. It should be isolated only as a diagnostic candidate family.

## Side Triage

| Side | Observed trades | Total R | Avg R | Profit factor | Win rate | Same-bar rate |
|---|---:|---:|---:|---:|---:|---:|
| `LONG` | 6912 | -797.530128 | -0.115383 | 0.815757 | 36.24% | 6.70% |
| `SHORT` | 6487 | -559.765603 | -0.086290 | 0.861688 | 36.90% | 7.00% |

Longs contributed more total loss and weaker average R. Shorts were still negative and cannot be treated as robust.

## Time-Bucket Triage

| Time bucket | Observed trades | Total R | Avg R | Profit factor | Win rate | Same-bar rate |
|---|---:|---:|---:|---:|---:|---:|
| `power_hour` | 2778 | -719.188186 | -0.258887 | 0.625701 | 30.09% | 8.46% |
| `afternoon_continuation` | 2824 | -414.350265 | -0.146725 | 0.774282 | 34.35% | 4.67% |
| `lunch_window` | 3284 | -186.534683 | -0.056801 | 0.905671 | 38.34% | 6.58% |
| `off_hours` | 2087 | -61.987893 | -0.029702 | 0.949229 | 40.34% | 6.32% |
| `opening_drive` | 1229 | 2.007740 | 0.001634 | 1.002769 | 40.60% | 9.93% |
| `ten_am_reversal_zone` | 1197 | 22.757556 | 0.019012 | 1.032735 | 41.19% | 6.68% |

`power_hour` and `afternoon_continuation` are the largest time-bucket contributors to failure. `ten_am_reversal_zone` is the only time bucket with positive source replay attribution and a partial full-grid research pocket, but it did not survive full-grid robustness.

## Regime Triage

| Market regime | Observed trades | Total R | Avg R | Profit factor | Win rate | Same-bar rate |
|---|---:|---:|---:|---:|---:|---:|
| `chop` | 7458 | -678.768369 | -0.091012 | 0.855095 | 36.67% | 5.86% |
| `trend_long` | 1685 | -341.230133 | -0.202510 | 0.687827 | 33.53% | 5.34% |
| `trend_short` | 2264 | -173.585485 | -0.076672 | 0.874301 | 37.54% | 6.76% |
| `mean_reversion` | 994 | -149.646390 | -0.150550 | 0.759641 | 35.31% | 15.39% |
| `opening_drive` | 970 | -8.687361 | -0.008956 | 0.984919 | 40.10% | 8.04% |
| `mixed_uncertain` | 28 | -5.377991 | -0.192071 | 0.715118 | 32.14% | 21.43% |

`chop` had the largest total loss because of sample size. `trend_long` and `mixed_uncertain` were worst by average R, though `mixed_uncertain` had a very small sample.

## Same-Bar Triage

| Same-bar ambiguous | Observed trades | Total R | Avg R | Profit factor | Win rate |
|---|---:|---:|---:|---:|---:|
| `true` | 917 | -917.000000 | -1.000000 | 0.000000 | 0.00% |
| `false` | 12482 | -440.295730 | -0.035274 | 0.940970 | 39.25% |

Same-bar ambiguous trades are a clear block/downweight candidate for future research, but only through signal-time proxies or training-fold-derived filters. Realized ambiguity itself must not be used as a forward-looking live filter.

## Skip Triage

| Skip reason | Count |
|---|---:|
| `overlapping_trade` | 7724 |
| `missing_entry_bar` | 17 |

The source portfolio replay skipped many overlapping trades. Those skips reduced portfolio loss relative to counterfactual replay but did not create robust portfolio evidence.

## Score-Audit Triage

Score audits loaded for `amd-replay-aware-20260702-164145`: `23732`.
Observed source replay trades joined to score audits: `13324`.

| Action | Observed trades | Total R | Avg R | Profit factor | Win rate | Same-bar rate |
|---|---:|---:|---:|---:|---:|---:|
| `SUPPRESS` | 12194 | -1883.725407 | -0.154480 | 0.760975 | 34.40% | 7.25% |
| `TAKE` | 212 | 198.436310 | 0.936020 | 5.563002 | 78.30% | 1.42% |
| `WATCH` | 918 | 369.454852 | 0.402456 | 1.946271 | 57.08% | 2.29% |

The scorer separated better observed outcomes, but the model-level governance remained blocked. These rows support a future score-cohort experiment only.

## Block / Downweight / Isolate Candidates

| Family | Phase 22 disposition | Reason |
|---|---|---|
| `power_hour` | block or strong downweight in future filter experiment | worst time bucket by total and average R |
| `afternoon_continuation` | downweight | large negative total R and full-grid weakness |
| `SPY` | isolate/downweight | worst symbol by average R, 0/450 scenario subset pass |
| `NVDA` | isolate/downweight | worst symbol by total R |
| `opening range breakdown short` | block/downweight | worst setup by full-grid average and source total loss |
| `liquidity sweep reversal long` | block/downweight | weak full-grid profile and high ambiguity rate |
| `failed breakdown long` / `failed breakout short` | block/downweight unless ambiguity proxy improves | high same-bar rates and negative source outcomes |
| `LONG` side | downweight, not full block | worse than shorts, but shorts also failed |
| `ten_am_reversal_zone` at `15min` | isolate as research-only specialist candidate | best non-robust pocket, failed worst-case grid |
| `TAKE` / `WATCH` score cohorts | isolate as research-only score-cohort candidate | positive observed replay, no full-grid/calibration acceptance |

