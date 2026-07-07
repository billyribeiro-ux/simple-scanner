# Phase 26 Filter And Threshold Spec

Status date: 2026-07-06

`PHASE_26_FILTER_THRESHOLD_SPEC_STATUS = PRE_REGISTERED`

Spec version: `phase26_broader_15min_ten_am_evidence_density.v1`

Spec hash: `ff4df70e7d98246d4f4bde977e3aedd632db3dcc6a5a2fdce038fab3c93d4cf4`

This spec freezes Phase 26 before OOS evaluation. Phase 26 is a broader 15min Ten-AM evidence-density research experiment, not model activation.

## Cohort

- `interval = 15min`
- `time_bucket = ten_am_reversal_zone`
- candidate universe: all actionable candidate setups
- primary action filter: none
- current TAKE/WATCH policy: reference only

## Excluded Filters

Phase 26 must not use:

- future outcomes;
- future labels;
- realized same-bar ambiguity as a live filter;
- OOS-derived thresholds;
- contaminated rows;
- test fixtures;
- broker/order execution fields;
- options, gamma, Greeks, IV, market internals, Level 2, dark-pool, or order-book data.

## Threshold Policy

Thresholds are computed only on the discovery/training portion and frozen before OOS evaluation. OOS outcomes are used only after policies are frozen, for validation reporting.

Policies:

| Policy | Name | Selection rule |
|---|---|---|
| A | All actionable cohort | Select every OOS 15min Ten-AM actionable candidate. |
| B | Training score top quartile | Select OOS candidates with score at or above the training `signal_quality_score` 75th percentile. |
| C | Training score top decile | Select OOS candidates with score at or above the training `signal_quality_score` 90th percentile. |
| D | Training pre-ceiling-score top quartile | Select OOS candidates with estimated pre-ceiling score at or above the training 75th percentile. |
| E | Training pre-ceiling-score top decile | Select OOS candidates with estimated pre-ceiling score at or above the training 90th percentile. |
| F | Training evidence-quality top quartile | Select OOS candidates with `evidence_quality_score` at or above the training 75th percentile. |
| G | Training time-bucket-score top quartile | Select OOS candidates with `time_bucket_score` at or above the training 75th percentile. |
| H | Current TAKE/WATCH reference | Select OOS candidates with current scorer action in `TAKE` or `WATCH`; reference only, not the primary broader test. |

## Pre-Ceiling Score Estimate

`pre_ceiling_score_estimate` is reconstructed from persisted score-audit components and penalties when available:

`signal_quality_score + ambiguity_penalty + stale_data_penalty + label_vs_replay_divergence_penalty + fragility_penalty + concentration_penalty`

This is diagnostic and uses only signal-time score audit fields, not realized OOS outcomes.

## Split

- method: chronological split;
- embargo: at least 60 minutes between discovery/training and validation/OOS;
- threshold source: discovery/training only;
- OOS labels and replay outcomes are not used for policy selection.

## Acceptance Checks

- every OOS result is labeled with its pre-registered policy;
- the threshold source and frozen threshold value are recorded;
- no threshold is selected or tuned from OOS outcomes;
- active models remain `0`;
- the evidence DB remains clean.
