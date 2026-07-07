# Phase 25 Base Vs Selected Comparison

`PHASE_25_BASE_VS_SELECTED_STATUS = RECORDED_DIAGNOSTIC_ONLY`

| group_id | candidate_count | portfolio_trades | portfolio_average_r | portfolio_robustness | counterfactual_trades | counterfactual_average_r | counterfactual_robustness |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all_oos | 145 | 57 | -0.053513 | 0.000000 | 145 | -0.057926 | 0.000000 |
| selected_take | 2 | 2 | -1.000000 | 0.000000 | 2 | -1.000000 | 0.000000 |
| selected_watch | 0 | None | None | None | None | None | None |
| suppressed | 143 | 57 | -0.053513 | 0.000000 | 143 | -0.044750 | 0.000000 |
| top_score_quartile | 37 | 16 | -0.843750 | 0.000000 | 37 | -0.864865 | 0.000000 |
| top_score_decile | 15 | 7 | -1.000000 | 0.000000 | 15 | -1.000000 | 0.000000 |
| phase23_like_current_take_watch | 2 | 2 | -1.000000 | 0.000000 | 2 | -1.000000 | 0.000000 |

Not monotonic in a useful way: TAKE is negative, WATCH has no samples, and suppressed/base cohorts remain weak.

No filter is promoted from these OOS outcomes.
