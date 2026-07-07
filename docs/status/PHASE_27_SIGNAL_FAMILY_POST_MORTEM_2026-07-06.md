# Phase 27 Signal-Family Post-Mortem

Status date: 2026-07-06

`PHASE_27_SIGNAL_FAMILY_POST_MORTEM_STATUS = COMPLETE`

This post-mortem uses Phase 22-26 evidence to identify weak signal families and the least-bad next research lead. These are attribution findings only. They are not activation recommendations.

## Setup Families

Phase 22 source replay attribution shows broad weakness across the current candidate engine. The table below uses observed source replay trades from the six Phase 21W replay runs; Phase 22 already classified those tables as diagnostic, not profitability evidence.

| Setup family | Observed trades | Total R | Avg R | PF | Win rate | Same-bar rate | Phase 27 disposition |
|---|---:|---:|---:|---:|---:|---:|---|
| `opening range breakdown short` | 2,076 | `-298.322595` | `-0.143701` | `0.778967` | `34.54%` | `4.38%` | Block or strong downweight until redesigned. Worst setup by total loss. |
| `opening range breakout long` | 2,637 | `-261.698292` | `-0.099241` | `0.841210` | `36.63%` | `5.20%` | Downweight; do not promote as standalone specialist. |
| `VWAP reclaim long` | 2,318 | `-184.820884` | `-0.079733` | `0.869742` | `37.53%` | `0.78%` | Downweight; low ambiguity does not offset negative expectancy. |
| `trend continuation long` | 678 | `-118.698393` | `-0.175071` | `0.712262` | `36.28%` | `3.83%` | Block pending redesign; weak by average R. |
| `failed breakdown long` | 615 | `-111.585974` | `-0.181441` | `0.728265` | `32.85%` | `25.37%` | Block unless a signal-time ambiguity proxy is redesigned and pre-registered. |
| `failed breakout short` | 681 | `-104.000485` | `-0.152717` | `0.768633` | `33.92%` | `22.61%` | Block unless ambiguity-risk mechanics are redesigned. |
| `liquidity sweep reversal long` | 477 | `-100.769649` | `-0.211257` | `0.688747` | `31.87%` | `24.95%` | Block; high ambiguity plus weak expectancy. |
| `liquidity sweep reversal short` | 527 | `-65.000485` | `-0.123341` | `0.809664` | `35.10%` | `21.06%` | Block or redesign; high ambiguity. |
| `VWAP loss short` | 2,293 | `-57.818571` | `-0.025215` | `0.958128` | `39.38%` | `2.05%` | Retest only as part of a pre-registered short-side diagnostic; not standalone ready. |
| `trend continuation short` | 715 | `3.960479` | `0.005539` | `1.009968` | `41.40%` | `5.73%` | Select as next research lead only, because it is the only setup family with positive source replay attribution; it still lacks full-grid proof. |

## Symbols

| Symbol | Observed trades | Total R | Avg R | PF | Phase 27 disposition |
|---|---:|---:|---:|---:|---|
| `NVDA` | 3,618 | `-457.184007` | `-0.126364` | `0.801233` | Isolate/downweight; worst total R. |
| `SPY` | 3,042 | `-444.535404` | `-0.146133` | `0.772717` | Isolate/downweight; worst average R and second-worst total R. |
| `QQQ` | 3,346 | `-229.914621` | `-0.068713` | `0.888028` | Still negative; do not treat as safe. |
| `AAPL` | 3,393 | `-225.661698` | `-0.066508` | `0.890800` | Still negative; do not treat as safe. |

## Sides

| Side | Observed trades | Total R | Avg R | PF | Phase 27 disposition |
|---|---:|---:|---:|---:|---|
| `LONG` | 6,912 | `-797.530128` | `-0.115383` | `0.815757` | Downweight broadly; long-side family is worse. |
| `SHORT` | 6,487 | `-559.765603` | `-0.086290` | `0.861688` | Less bad, not robust. Research only. |

## Time Buckets And Regimes

| Bucket / regime | Observed trades | Total R | Avg R | PF | Phase 27 disposition |
|---|---:|---:|---:|---:|---|
| `power_hour` | 2,778 | `-719.188186` | `-0.258887` | `0.625701` | Block or strong downweight. |
| `afternoon_continuation` | 2,824 | `-414.350265` | `-0.146725` | `0.774282` | Downweight. |
| `opening_drive` time bucket | 1,229 | `2.007740` | `0.001634` | `1.002769` | Watchlist only; tiny edge and not a setup family. |
| `ten_am_reversal_zone` | 1,197 | `22.757556` | `0.019012` | `1.032735` | Discard current 15min specialist despite positive source attribution because Phase 23-26 failed robustness and OOS validation. |
| `chop` | 7,458 | `-678.768369` | `-0.091012` | `0.855095` | Major total-loss contributor; downweight or redesign regime interaction. |
| `trend_long` | 1,685 | `-341.230133` | `-0.202510` | `0.687827` | Weak by average R; block long-trend continuation specialists until redesigned. |

## Score Impact

Phase 22 score cohorts were directionally useful but not promotion-grade:

| Action | Observed trades | Total R | Avg R | PF | Same-bar rate | Interpretation |
|---|---:|---:|---:|---:|---:|---|
| `TAKE` | 212 | `198.436310` | `0.936020` | `5.563002` | `1.42%` | Positive observed replay, but no full-grid grade/action proof and rejected governance. |
| `WATCH` | 918 | `369.454852` | `0.402456` | `1.946271` | `2.29%` | Positive observed replay, but not enough for promotion. |
| `SUPPRESS` | 12,194 | `-1883.725407` | `-0.154480` | `0.760975` | `7.25%` | Suppression was directionally useful but not enough to produce an accepted challenger. |

## Recommendations

- Block or strongly downweight `power_hour`, `opening range breakdown short`, high-ambiguity reversal failures, and weak long-side families in future research specs.
- Do not use realized same-bar ambiguity as a live filter. Any ambiguity suppression must come from signal-time proxies and training-fold evidence.
- Do not treat score TAKE/WATCH observed replay as activation proof. It can only motivate a future pre-registered score-cohort diagnostic with full-grid sensitivity and calibration.
- Select `trend continuation short` as the next research lead because it is the only setup family with positive source replay attribution and adequate sample size. It is still not activation-ready and must be tested as a new pre-registered hypothesis.
