# Phase 26 Data Sufficiency

Status date: 2026-07-06

`PHASE_26_DATA_SUFFICIENCY_STATUS = BROADER_SAMPLE_SUFFICIENT_COHORT_NEGATIVE`

Source ID: `phase26_537f582b33387bf5`

## Coverage

| Metric | Value |
|---|---:|
| 15min RTH days | 33 |
| 15min bars | 3432 |
| Ten-AM rows including no-trade rows | 437 |
| 15min Ten-AM actionable candidates | 330 |
| Training candidates | 178 |
| Embargo candidates | 7 |
| OOS candidates | 145 |
| OOS RTH days | 13 |

## Candidate Mix

| Dimension | Counts |
|---|---|
| Symbol | AAPL 67, NVDA 91, QQQ 83, SPY 89 |
| Side | LONG 165, SHORT 165 |
| Regime | chop 39, mean_reversion 55, mixed_uncertain 7, trend_long 128, trend_short 101 |
| Time bucket | ten_am_reversal_zone 330 |

Top setup counts:

| Setup | Count |
|---|---:|
| failed breakout short | 59 |
| liquidity sweep reversal short | 59 |
| failed breakdown long | 53 |
| liquidity sweep reversal long | 53 |
| VWAP reclaim long | 29 |
| opening range breakout long | 22 |
| VWAP loss short | 21 |
| opening range breakdown short | 17 |
| previous day low loss short | 9 |
| previous day high reclaim long | 8 |

## Evidence Density

| Metric | Value |
|---|---:|
| Specialist exact evidence cells | 79 |
| Specialist exact cells with 5+ observed outcomes | 7 |
| Specialist exact cells with 10+ observed outcomes | 0 |
| OOS exact evidence-cell matches | 128 |
| OOS parent/backoff used | 145 |
| OOS broad-parent-reliant candidates | 113 |
| OOS broad-parent reliance rate | 77.93% |

## Days Needed

Estimates use the current OOS selection rate across 13 OOS RTH days.

| Policy | 30 selected | 50 selected | 100 selected |
|---|---:|---:|---:|
| A all actionable | 3 total days, +0 | 5 total days, +0 | 9 total days, +0 |
| B training score q75 | 3 total days, +0 | 5 total days, +0 | 10 total days, +0 |
| C training score q90 | 3 total days, +0 | 5 total days, +0 | 10 total days, +0 |
| D pre-ceiling q75 | 12 total days, +0 | 19 total days, +6 | 38 total days, +25 |
| E pre-ceiling q90 | 65 total days, +52 | 109 total days, +96 | 217 total days, +204 |
| F evidence quality q75 | 12 total days, +0 | 19 total days, +6 | 38 total days, +25 |
| G time bucket q75 | 12 total days, +0 | 19 total days, +6 | 38 total days, +25 |
| H current TAKE/WATCH reference | 195 total days, +182 | 325 total days, +312 | 650 total days, +637 |

## Sufficiency Finding

The broader 15min Ten-AM cohort has enough OOS count to test the broad hypothesis now: policies A, B, and C produce 135-145 OOS selections. The exact specialist evidence cells remain sparse, however: only 7 exact cells have 5+ observed outcomes and none have 10+. The broader sample-size problem is solved, but the evidence-density and validation problem is not.
