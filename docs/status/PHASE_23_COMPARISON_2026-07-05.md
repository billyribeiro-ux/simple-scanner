# Phase 23 Comparison - Phase 22 Baseline Versus Filtered Results

## Status

`PHASE_23_COMPARISON_STATUS = RECORDED_NO_ROBUST_FILTER`

Phase 23 improved some filtered zero-cost average replay metrics, but the only full-grid pass is too small to trust. The comparison does not approve activation.

## Baseline

| Purpose | Replay ID | Baseline avg R | Trades | Sensitivity ID | Robustness |
|---|---|---:|---:|---|---:|
| portfolio | `replay_20260705223012_afc4202e318c155d012444f6` | `-0.145227` | 295 | `sensitivity_7b270b48d0b1e8580a696a60d82c859e` | `0.00` |
| counterfactual | `replay_20260705223013_39d7d508606d7e8782962ead` | `-0.174658` | 942 | `sensitivity_90441b99f44ddd04caeddcbaa244419f` | `0.00` |

## Filter Delta Summary

| Filter | Purpose | Phase 23 avg R | Avg R delta | Phase 23 trades | Robustness | Worst avg R | Sensitivity |
|---|---|---:|---:|---:|---:|---:|---|
| `P23_FILTER_A_BASE_15M_TEN_AM` | portfolio | `0.291635` | `0.436862` | 31 | `0.44` | `-0.447610` | fail |
| `P23_FILTER_A_BASE_15M_TEN_AM` | counterfactual | `0.326617` | `0.501275` | 82 | `0.00` | `-0.424572` | fail |
| `P23_FILTER_B_AMBIGUITY_SUPPRESSED` | portfolio | `0.096292` | `0.241519` | 16 | `0.20` | `-0.583347` | fail |
| `P23_FILTER_B_AMBIGUITY_SUPPRESSED` | counterfactual | `0.137864` | `0.312522` | 42 | `0.00` | `-0.481363` | fail |
| `P23_FILTER_C_WEAK_FAMILY_SUPPRESSED` | portfolio | `0.250000` | `0.395227` | 10 | `0.28` | `-0.311882` | fail |
| `P23_FILTER_C_WEAK_FAMILY_SUPPRESSED` | counterfactual | `0.250000` | `0.424658` | 14 | `0.28` | `-0.389149` | fail |
| `P23_FILTER_D_TAKE_WATCH_SLICE` | portfolio | `1.500000` | `1.645227` | 6 | `1.00` | `0.532262` | pass, low sample |
| `P23_FILTER_D_TAKE_WATCH_SLICE` | counterfactual | `1.500000` | `1.674658` | 9 | `1.00` | `0.962368` | pass, low sample |

## Export

| Export | ID | SHA-256 |
|---|---|---|
| JSON comparison | `export_f970ba6551e36a9203e4b8b48dfe0cb1` | `4f6fed702697ebddd075958a570fdb6be7118125ff93770df9b38e12c551f2d6` |
| XLSX report pack | `export_7bbc12195d37602290209ed3e52411a6` | `683a39357982f03c667e6868a3e984a9e262c5f6065ff26adff5797fd9d20914` |

Workbook sheets: `Filter Spec`, `Replay Results`, `Sensitivity Results`, `Leakage Split`, `Decision`, `Comparison`, `Export Records`.

