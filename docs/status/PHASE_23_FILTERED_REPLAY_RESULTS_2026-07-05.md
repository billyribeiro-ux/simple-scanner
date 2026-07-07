# Phase 23 Filtered Replay Results

## Status

`PHASE_23_FILTERED_REPLAY_STATUS = RECORDED`

All replay runs were rebuilt from persisted real 15min bars, features, and candidates. No model was activated, no broker path was used, and all configs kept `allow_stale=false`.

## Replay Results

| Filter | Candidates | Purpose | Replay ID | Trades | Avg R | Profit factor | Max DD R | Same-bar ambiguous |
|---|---:|---|---|---:|---:|---:|---:|---:|
| `P23_FILTER_A_BASE_15M_TEN_AM` | 82 | portfolio | `r23_a15tam_p_85ebb9a8182a` | 31 | `0.291635` | `1.604350` | `-5.500000` | 1 |
| `P23_FILTER_A_BASE_15M_TEN_AM` | 82 | counterfactual | `r23_a15tam_c_85ebb9a8182a` | 82 | `0.326617` | `1.725298` | `-13.500000` | 4 |
| `P23_FILTER_B_AMBIGUITY_SUPPRESSED` | 42 | portfolio | `r23_bamb_p_dfafad1f2f02` | 16 | `0.096292` | `1.171963` | `-4.500000` | 0 |
| `P23_FILTER_B_AMBIGUITY_SUPPRESSED` | 42 | counterfactual | `r23_bamb_c_dfafad1f2f02` | 42 | `0.137864` | `1.264172` | `-11.500000` | 2 |
| `P23_FILTER_C_WEAK_FAMILY_SUPPRESSED` | 14 | portfolio | `r23_cweak_p_072557a91c8c` | 10 | `0.250000` | `1.500000` | `-5.000000` | 0 |
| `P23_FILTER_C_WEAK_FAMILY_SUPPRESSED` | 14 | counterfactual | `r23_cweak_c_072557a91c8c` | 14 | `0.250000` | `1.500000` | `-7.000000` | 0 |
| `P23_FILTER_D_TAKE_WATCH_SLICE` | 9 | portfolio | `r23_dtw_p_caa35696a924` | 6 | `1.500000` | `n/a` | `0.000000` | 0 |
| `P23_FILTER_D_TAKE_WATCH_SLICE` | 9 | counterfactual | `r23_dtw_c_caa35696a924` | 9 | `1.500000` | `n/a` | `0.000000` | 0 |

## Split And Score Notes

| Filter | Discovery candidates | Validation candidates | Validation counterfactual trades | Validation avg R | Score actions |
|---|---:|---:|---:|---:|---|
| `P23_FILTER_A_BASE_15M_TEN_AM` | 48 | 34 | 34 | `0.358861` | `SUPPRESS=73`, `TAKE=1`, `WATCH=8` |
| `P23_FILTER_B_AMBIGUITY_SUPPRESSED` | 21 | 21 | 21 | `0.319474` | `SUPPRESS=36`, `TAKE=1`, `WATCH=5` |
| `P23_FILTER_C_WEAK_FAMILY_SUPPRESSED` | 6 | 8 | 8 | `-0.062500` | `SUPPRESS=11`, `TAKE=1`, `WATCH=2` |
| `P23_FILTER_D_TAKE_WATCH_SLICE` | 3 | 6 | 6 | `1.500000` | `TAKE=1`, `WATCH=8` |

The TAKE/WATCH slice is encouraging but low sample. It is not an activation candidate.

## Export

| Export | ID | SHA-256 |
|---|---|---|
| JSON replay results | `export_9e0831fa71fccfadef5e0c15f102f27f` | `5a1acf9038aea8f77152d1c3954b44b8806ac4f316fbbdd74bb823379373f6e5` |
| CSV replay results | `export_f8b5de0c724a8ca11bd8f79f0a36c621` | `8745df98fccd57256a53f77bc6330322f2bf00407099e097436865e50faea050` |

