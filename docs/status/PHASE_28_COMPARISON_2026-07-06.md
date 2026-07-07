# Phase 28 Comparison

Status date: 2026-07-06

`PHASE_28_COMPARISON_STATUS = RECORDED_RESEARCH_ONLY`

Source ID: `phase28_tcs_13dcd7f09159fc3c`

Spec hash: `9bcac6111f0c6e079b20c6160386d4ad2f78c4c9755cbbad788992350903162b`

## Purpose

This report compares the pre-registered `trend continuation short` diagnostic against the Phase 22 source-replay lead, the discarded Ten-AM path, and score TAKE/WATCH observations. The comparison is diagnostic only and does not activate a model.

## Phase 28 Primary Summary

| Interval | Portfolio avg R | Portfolio PF | Portfolio robustness | Counterfactual avg R | Counterfactual PF | Counterfactual robustness | Decision |
|---|---:|---:|---:|---:|---:|---:|---|
| `1min` | 0.161701 | 1.308001 | 0.00 | 0.111022 | 1.203147 | 0.00 | `REJECTED_BY_SENSITIVITY` |
| `5min` | 0.168638 | 1.350594 | 0.44 | 0.170699 | 1.350681 | 0.00 | `REJECTED_BY_SENSITIVITY` |
| `15min` | -0.058462 | 0.888915 | 0.00 | -0.064282 | 0.873549 | 0.00 | `REJECTED_BY_SENSITIVITY` |

## Prior Evidence Anchors

| Anchor | Evidence | Interpretation |
|---|---|---|
| Phase 22 `trend continuation short` source replay | 715 observed trades, total `3.960479R`, avg `0.005539R`, PF `1.009968`, win rate `41.40%`, same-bar rate `5.73%` | Weak positive source-replay attribution only; not full-grid proof. |
| Phase 26 Ten-AM all-actionable | 145 OOS selected, portfolio avg `-0.053513R`, counterfactual avg `-0.057926R`, robustness `0.00` for both | Current Ten-AM hypothesis discarded. |
| Phase 22 score TAKE/WATCH | TAKE avg `0.936020R`, WATCH avg `0.402456R` in observed replay | Positive observed replay without full-grid grade/action proof. |

## Comparison Read

Phase 28 improved on the discarded Ten-AM baseline in the `1min` and `5min` zero-cost primary replays, but the improvement did not survive the required full-grid sensitivity checks. The `15min` interval did not even preserve positive baseline expectancy.

The Phase 22 `trend continuation short` source-replay lead was therefore useful as a research lead, but Phase 28 did not convert it into a robust, actionable specialist. The edge was too fragile under costs, path assumptions, and same-bar policy variation.

## Governance Implication

Phase 28 supports a rejection, not activation:

- no model activation;
- no proposal approval;
- no validation, calibration, or sensitivity gate loosening;
- no OOS outcome-selected filter;
- no realized same-bar live filter;
- no broker/order path;
- no production WebSocket ingestion;
- no profitability claim.

Future research should either move to a new pre-registered signal family or redesign trend-continuation-short with a new spec that is justified without Phase 28 OOS outcome selection.
