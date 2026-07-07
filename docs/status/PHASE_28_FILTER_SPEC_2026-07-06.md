# Phase 28 Filter Spec

Status date: 2026-07-06

`PHASE_28_FILTER_SPEC_STATUS = PRE_REGISTERED`

Spec version: `phase28_trend_continuation_short_diagnostic.v1`

Spec hash: `9bcac6111f0c6e079b20c6160386d4ad2f78c4c9755cbbad788992350903162b`

## Purpose

This spec pre-registers the Phase 28 primary cohort before OOS evaluation. The experiment is a setup-family diagnostic for `trend continuation short`. It is not model activation, not proposal approval, and not a profitability claim.

## Primary Cohort

| Field | Value |
|---|---|
| Setup family | `trend continuation` |
| Setup type | `trend continuation short` |
| Side | `SHORT` |
| Symbols | All symbols currently in the clean evidence DB |
| Intervals | `1min`, `5min`, `15min` |
| Interval handling | Evaluate each interval separately; do not blend interval readiness |
| Session | `rth` |
| Minimum reward/risk | Existing replay default `1.0` |
| Additional primary filters | None |

## Primary Exclusions

No symbol is excluded in the primary cohort. No regime, time-bucket, score-action, or ambiguity-risk filter is used in the primary cohort.

Any symbol-specific, regime-specific, time-bucket-specific, score-action, or same-bar ambiguity analysis is exploratory only and cannot be used as activation evidence.

## Chronological Split Rule

For each interval:

1. Query primary candidates using only signal-time identifiers: setup type, side, symbol, interval, timestamp.
2. Sort candidates chronologically.
3. Assign the first 60% of candidates to discovery/training.
4. Set `training_end` to the timestamp of the last training candidate.
5. Apply a 60-minute embargo.
6. Assign OOS candidates to the first candidates after `training_end + 60 minutes`.

The split rule uses candidate timestamps only and does not inspect OOS outcomes.

## Replay And Sensitivity Policy

For each interval and split:

- run `candidate_market_replay` on the OOS window;
- run `model_training_counterfactual` on the OOS window;
- run the full default 75-scenario sensitivity grid for portfolio and counterfactual;
- report portfolio and counterfactual separately.

## Leakage Controls

Forbidden in filters and thresholds:

- OOS outcomes;
- future labels;
- future outcomes;
- realized same-bar ambiguity as a live filter;
- OOS-derived thresholds;
- post-hoc symbol exclusions;
- post-hoc regime exclusions;
- post-hoc time-bucket exclusions;
- broker/order execution results.

## Decision Labels

The final Phase 28 decision must use one of:

- `FUTURE_SPECIALIST_EXPERIMENT`
- `NEEDS_MORE_DATA`
- `DISCARD`
- `REJECTED_BY_SENSITIVITY`
- `REJECTED_BY_VALIDATION`
- `REJECTED_BY_CALIBRATION`
- `EDGE_TOO_SMALL`
- `EVIDENCE_TOO_SPARSE`

Future specialist experiment does not mean activation.
