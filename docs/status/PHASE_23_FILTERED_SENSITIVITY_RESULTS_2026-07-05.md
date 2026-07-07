# Phase 23 Filtered Sensitivity Results

## Status

`PHASE_23_FILTERED_SENSITIVITY_STATUS = FULL_GRID_RECORDED`

Each Phase 23 replay received the full default sensitivity grid: 75 scenarios, `full_default_grid_complete=true`, no partial disclosure. These are diagnostic research runs and do not activate models.

## Full-Grid Results

| Filter | Purpose | Sensitivity ID | Scenarios | Robustness | Pass/fail | Worst avg R | Avg scenario avg R | Blocking flags |
|---|---|---|---:|---:|---|---:|---:|---|
| `P23_FILTER_A_BASE_15M_TEN_AM` | portfolio | `s23_a15tam_p_85ebb9a8182a` | 75 | `0.44` | fail | `-0.447610` | `-0.016258` | robustness, same-bar |
| `P23_FILTER_A_BASE_15M_TEN_AM` | counterfactual | `s23_a15tam_c_85ebb9a8182a` | 75 | `0.00` | fail | `-0.424572` | `0.086835` | robustness, same-bar |
| `P23_FILTER_B_AMBIGUITY_SUPPRESSED` | portfolio | `s23_bamb_p_dfafad1f2f02` | 75 | `0.20` | fail | `-0.583347` | `-0.309016` | small-cost expectancy, PF, robustness |
| `P23_FILTER_B_AMBIGUITY_SUPPRESSED` | counterfactual | `s23_bamb_c_dfafad1f2f02` | 75 | `0.00` | fail | `-0.481363` | `-0.155274` | small-cost expectancy, PF, robustness, same-bar |
| `P23_FILTER_C_WEAK_FAMILY_SUPPRESSED` | portfolio | `s23_cweak_p_072557a91c8c` | 75 | `0.28` | fail | `-0.311882` | `-0.048129` | small-cost expectancy, PF, robustness |
| `P23_FILTER_C_WEAK_FAMILY_SUPPRESSED` | counterfactual | `s23_cweak_c_072557a91c8c` | 75 | `0.28` | fail | `-0.389149` | `-0.103972` | small-cost expectancy, PF, robustness |
| `P23_FILTER_D_TAKE_WATCH_SLICE` | portfolio | `s23_dtw_p_caa35696a924` | 75 | `1.00` | pass | `0.532262` | `1.106085` | none |
| `P23_FILTER_D_TAKE_WATCH_SLICE` | counterfactual | `s23_dtw_c_caa35696a924` | 75 | `1.00` | pass | `0.962368` | `1.261982` | none |

## Interpretation

Filters A, B, and C do not survive sensitivity. Filter D passes the grid but is blocked by sample size: 9 total candidates, 3 discovery candidates, and 6 validation trades. It is therefore insufficient for a future specialist candidate under Phase 23 rules.

## Export

| Export | ID | SHA-256 |
|---|---|---|
| JSON sensitivity results | `export_e56e4fd3ef25eec3175c592ff527ddca` | `85a2780d6b5165746e19413feefd75168e6441f67b3e523214aa63a91cc1ffd9` |
| CSV sensitivity results | `export_6e219ae6c9286d4714472e9a4e0b36c3` | `7749dab39a95933c2a1e1c50443ec92d18c074ec652ade618285c54e1f48952d` |

