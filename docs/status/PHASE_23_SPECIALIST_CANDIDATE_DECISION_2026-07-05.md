# Phase 23 Specialist Candidate Decision

## Status

`PHASE_23_STATUS = ACCEPTED_NO_ROBUST_FILTER`

Phase 23 found no robust filter suitable for a future specialist candidate. Positive subsets remain diagnostic only.

## Decision Table

| Filter | Classification | Candidates | Validation trades | Validation avg R | Portfolio robustness | Counterfactual robustness | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| `P23_FILTER_A_BASE_15M_TEN_AM` | `BLOCKED_BY_SENSITIVITY` | 82 | 34 | `0.358861` | `0.44` | `0.00` | no activation |
| `P23_FILTER_B_AMBIGUITY_SUPPRESSED` | `BLOCKED_BY_SENSITIVITY` | 42 | 21 | `0.319474` | `0.20` | `0.00` | no activation |
| `P23_FILTER_C_WEAK_FAMILY_SUPPRESSED` | `BLOCKED_BY_LOW_SAMPLE` | 14 | 8 | `-0.062500` | `0.28` | `0.28` | no activation |
| `P23_FILTER_D_TAKE_WATCH_SLICE` | `BLOCKED_BY_LOW_SAMPLE` | 9 | 6 | `1.500000` | `1.00` | `1.00` | no activation |

## Rationale

- Filter A preserves enough validation sample, but counterfactual sensitivity robustness is `0.00` and worst-case average R is negative.
- Filter B reduces same-bar ambiguity but worsens grid robustness and small-cost behavior.
- Filter C is too small and still sensitivity-blocked.
- Filter D passes sensitivity but has only 9 candidates and 6 validation trades. That is not enough to classify as a future specialist experiment.

No proposal was approved, no model was activated, no broker execution occurred, and no profitability claim is made.

## Export

| Export | ID | SHA-256 |
|---|---|---|
| JSON decision | `export_95d9d40b9270df356a7fa87857302200` | `3ff1356109968abd0bef02d0307fce138fb71dc84d2b320c7aaf82c882c31f7e` |
| JSON leakage/split report | `export_3ee161a1e325e1c650a21e034cb335ad` | `8e70d7bb67a940ed772e123f3e64ba22ecb20c732eeb554f1a97f24796a9e927` |

