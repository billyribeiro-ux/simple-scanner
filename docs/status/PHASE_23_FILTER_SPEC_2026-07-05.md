# Phase 23 Filter Spec - Diagnostic Candidate Filter Experiment

## Status

`PHASE_23_FILTER_SPEC_STATUS = VERSIONED_SIGNAL_TIME_ONLY`

This filter specification is research-only. It does not activate a model, approve a proposal, bypass stale gates, use broker execution, use WebSocket production ingestion, or claim profitability.

## Source Scope

| Field | Value |
|---|---|
| Symbols | `SPY`, `QQQ`, `AAPL`, `NVDA` |
| Interval | `15min` |
| Time bucket | `ten_am_reversal_zone` |
| Source portfolio replay | `replay_20260705223012_afc4202e318c155d012444f6` |
| Source counterfactual replay | `replay_20260705223013_39d7d508606d7e8782962ead` |
| Source bars/features/candidates | `1040` / `1040` / `1452` |
| Base 15min ten-am actionable candidates | `82` |
| Filter spec hash | `be9de3e9bbe516f882174df8eeebee19f0f66f970e7177f2e1ea287b3289a106` |

## Chronological Split

| Field | Value |
|---|---|
| Method | `chronological_60pct_discovery_60min_embargo` |
| Split cutoff | `2026-06-26T14:15:00+00:00` |
| Embargo end | `2026-06-26T15:15:00+00:00` |
| Discovery candidates | `48` |
| Validation candidates | `34` |

## Ambiguity Proxy

Thresholds were selected from discovery distribution only, with no realized R, labels, future bars, or same-bar replay ambiguity.

| Proxy | Discovery threshold |
|---|---:|
| `range_atr_q75` | `1.016960928379706` |
| `wick_ratio_total_q75` | `0.8117408906882483` |
| `abs_distance_from_vwap_q25` | `0.00088718822051033` |
| `or_edge_proximity_pct_q25` | `0.0004824174466346247` |
| `risk_pct_q25` | `0.0008864014748590606` |

Rule: exclude an ambiguity-risk candidate only when two or more predeclared signal-time ambiguity flags are present.

## Filters

| Filter | Rule |
|---|---|
| `P23_FILTER_A_BASE_15M_TEN_AM` | 15min ten-am reversal-zone actionable candidates only |
| `P23_FILTER_B_AMBIGUITY_SUPPRESSED` | Filter A minus candidates with two or more signal-time ambiguity flags |
| `P23_FILTER_C_WEAK_FAMILY_SUPPRESSED` | Filter B minus predeclared weak setup families |
| `P23_FILTER_D_TAKE_WATCH_SLICE` | Filter A plus persisted non-active replay-aware score action `TAKE` or `WATCH` |

Weak setup families: `VWAP reclaim long`, `failed breakdown long`, `failed breakout short`, `liquidity sweep reversal long`, `opening range breakout long`, `opening range breakdown short`, `trend continuation long`.

## Leakage Controls

Forbidden for filter construction: future bars, future labels, realized replay R, realized same-bar ambiguity, validation outcomes, broker state, and production execution data.

Allowed for filter construction: persisted candidate row fields, persisted feature row fields at the same signal timestamp, candidate warning/reason codes, and persisted non-active score audit action for the diagnostic TAKE/WATCH slice.

## Export

| Export | ID | SHA-256 |
|---|---|---|
| JSON filter spec | `export_08ec04d59c71552a9b21015e98bbfe47` | `d826b338b94d4aeff3596f35e9418418f6bd2308463f414133ff1bba07a1e4d3` |

