# Phase 21W Sensitivity Execution

Date: 2026-07-05
Status: FULL_GRID_COMPLETE_REJECTED_BY_ROBUSTNESS

## Grid

- Grid version: `replay_sensitivity.full_default_grid.v1`
- Grid hash: `1f7c8a8a7b14e40768954acf273280866b768d8f5516abbc29c6a3187511201b`
- Coverage mode: `CHUNKED_FULL_GRID`
- Scenario count per replay: `75`
- Chunk size used: `15` scenarios per invocation
- Partial chunks persisted progress and stayed `completion_status=PARTIAL`.
- Final chunks completed with `completion_status=COMPLETE`, `full_default_grid_complete=true`, and `partial_grid_disclosure=false`.

## Results

| Purpose | Replay run | Trades | Sensitivity run | Planned | Completed | Rows unique | Complete | Pass/fail | Robustness |
|---|---|---:|---|---:|---:|---:|---|---|---:|
| 1min portfolio | `replay_20260705222826_33726551f81599994d55da1b` | 1938 | `sensitivity_ab486e2337c9de415328f76cecf1c4c7` | 75 | 75 | 75 | yes | fail | 0.0 |
| 1min counterfactual | `replay_20260705222903_30a05915b7d9ab1dc2a0566c` | 7295 | `sensitivity_4747000982a7dd1c24c48798b27d0970` | 75 | 75 | 75 | yes | fail | 0.0 |
| 5min portfolio | `replay_20260705223001_2a3bedc9d2abaa0a750aefc2` | 605 | `sensitivity_df6e25965262b6d29d8bb6ad9aa0bcde` | 75 | 75 | 75 | yes | fail | 0.0 |
| 5min counterfactual | `replay_20260705223005_7e38150cc8ad1259cd668e04` | 2324 | `sensitivity_d1fa1d06e2ac1151f5b20d96db8fefc8` | 75 | 75 | 75 | yes | fail | 0.0 |
| 15min portfolio | `replay_20260705223012_afc4202e318c155d012444f6` | 295 | `sensitivity_7b270b48d0b1e8580a696a60d82c859e` | 75 | 75 | 75 | yes | fail | 0.0 |
| 15min counterfactual | `replay_20260705223013_39d7d508606d7e8782962ead` | 942 | `sensitivity_90441b99f44ddd04caeddcbaa244419f` | 75 | 75 | 75 | yes | fail | 0.0 |

All six runs share these fragility flags:

- `expectancy_turns_non_positive_under_small_costs`
- `profit_factor_not_robust_under_small_costs`
- `robustness_score_below_threshold`
- `same_bar_path_assumption_affects_results`

## Blocker

There is no remaining full-grid completion blocker. The remaining blocker is substantive: all six full-grid sensitivity runs failed robustness gates, with `failed_scenario_count=75` and `robustness_score=0.0`. This is activation-grade complete evidence that rejects the challenger; it is not activation approval.

