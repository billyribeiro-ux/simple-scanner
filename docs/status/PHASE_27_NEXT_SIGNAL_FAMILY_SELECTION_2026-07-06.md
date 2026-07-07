# Phase 27 Next Signal Family Selection

Status date: 2026-07-06

`PHASE_27_NEXT_SIGNAL_FAMILY_SELECTION_STATUS = RESEARCH_LEAD_SELECTED_NOT_ACTIVATION_READY`

## Decision

The next candidate family worth investigating is `trend continuation short`.

This is a research lead only. It is not an activation candidate, not a model proposal, and not a profitability claim.

## Why This Family

Phase 22 setup attribution showed only one setup family with positive source replay attribution:

| Candidate family | Observed trades | Total R | Avg R | PF | Win rate | Same-bar rate | Decision |
|---|---:|---:|---:|---:|---:|---:|---|
| `trend continuation short` | 715 | `3.960479` | `0.005539` | `1.009968` | `41.40%` | `5.73%` | Select as next research lead only. |

This family is chosen because it has:

- enough observed source replay trades to justify a diagnostic;
- the least-bad setup-family attribution, with slight positive total and average R;
- lower ambiguity than failed breakdown/breakout and liquidity-sweep reversal families;
- non-overlap with the discarded 15min Ten-AM specialist premise;
- signal-time definability from existing candidate-engine rules.

## Why It Is Not Ready

`trend continuation short` is not activation-ready:

- Phase 22 found no full-grid robust subset.
- The observed edge is tiny: avg `0.005539R`, PF `1.009968`.
- Broad short-side attribution is still negative: shorts total `-559.765603R`, avg `-0.086290R`, PF `0.861688`.
- Symbol and time-bucket interactions remain weak, especially `SPY`, `NVDA`, `power_hour`, and `afternoon_continuation`.
- No current calibration report proves this family can produce enough high-grade OOS candidates.
- No Phase 27 filter is selected from OOS outcomes.

## Candidates Not Selected

| Candidate | Reason not selected |
|---|---|
| Current 15min Ten-AM | Formally discarded by Phase 26. Positive early pocket failed OOS and full-grid robustness. |
| Score TAKE/WATCH cohort | Positive observed replay, but insufficient full-grid grade/action proof and later Ten-AM score policies failed. |
| `opening_drive` time bucket | Slight positive source attribution, but it is a time bucket rather than a setup family and has tiny average edge. |
| `VWAP loss short` | Less negative than many weak families, but still negative in source replay and Phase 24 selected VWAP-loss shorts both lost. |
| Long-side continuation/reversal families | Longs were worse than shorts and several long setup families were materially negative. |

## Required Next Experiment Shape

The next phase should pre-register a `trend continuation short` diagnostic before running OOS:

- define interval scope;
- define symbols and whether `SPY` / `NVDA` are isolated or excluded by training-only criteria;
- define time-bucket handling before OOS;
- define training/embargo/OOS split chronologically;
- define minimum OOS selected count and OOS trade count;
- require full 75-scenario sensitivity for portfolio and counterfactual;
- require calibration audit with enough high-grade samples;
- require model review and governance rejection/acceptance to remain separate from research results;
- keep active models at `0` unless a future explicitly approved activation phase passes every gate.

## Phase 27 Status Implication

Because a next research lead is selected, the appropriate final status is:

`PHASE_27_STATUS = ACCEPTED_TEN_AM_DISCARDED_NEXT_FAMILY_SELECTED`
