# Phase 24 Filter Spec

`PHASE_24_FILTER_SPEC_STATUS = VERSIONED_SIGNAL_TIME_ONLY`

This specification is research-only. It does not activate a model, approve a proposal, route orders, use broker execution, use production WebSocket ingestion, bypass stale gates, or claim profitability.

## Pre-Registered Filter

- Filter ID: `P24_PRE_REGISTERED_TAKE_WATCH_15M_TEN_AM`
- Filter spec hash: `220cbea95476458b0cfd7c78ec4f297dd6bd404f5c101cbafdcda3661d741d5d`
- Symbols: `SPY`, `QQQ`, `AAPL`, `NVDA`
- Interval: `15min`
- Time bucket: `ten_am_reversal_zone`
- Action rule: `TAKE` or `WATCH` only when produced by the Phase 24 discovery-trained inactive replay-aware scorer.
- Scorer training window: `2026-05-15T00:00:00+00:00` through `2026-06-11T14:00:00+00:00`
- Validation start after embargo: `2026-06-12T14:00:00+00:00`
- Holdout start: `2026-06-24T14:00:00+00:00`
- Embargo: `60` minutes

## Banned Inputs

The filter does not use realized ambiguity, future labels, future outcomes, validation-outcome thresholds, post-hoc symbol filtering, post-hoc side filtering, or broker execution state.

## Split

| Split | Candidates |
|---|---:|
| Discovery | 178 |
| Embargo | 7 |
| Validation | 82 |
| Holdout test | 63 |

The inactive scorer was trained only from discovery-window replay evidence and then applied to the post-embargo validation/holdout candidates.
