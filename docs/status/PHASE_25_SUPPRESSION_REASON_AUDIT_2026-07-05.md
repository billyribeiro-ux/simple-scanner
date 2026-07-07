# Phase 25 Suppression Reason Audit

`PHASE_25_SUPPRESSION_REASON_AUDIT_STATUS = RECORDED`

Suppressed OOS candidates: `143`.

| key | count |
| --- | --- |
| negative_expectancy_after_shrinkage | 143 |
| profit_factor_below_threshold | 112 |
| same_bar_ambiguity_dependency_too_high | 10 |

| pathway | count | symbols | setups | sides | median_expected_r | median_sample_count |
| --- | --- | --- | --- | --- | --- | --- |
| negative_expectancy_after_shrinkage+profit_factor_below_threshold \| NVDA \| failed breakdown long \| LONG \| trend_short | 8 | {'NVDA': 8} | {'failed breakdown long': 8} | {'LONG': 8} | -0.639869 | 804.000000 |
| negative_expectancy_after_shrinkage+profit_factor_below_threshold \| NVDA \| liquidity sweep reversal long \| LONG \| trend_short | 8 | {'NVDA': 8} | {'liquidity sweep reversal long': 8} | {'LONG': 8} | -0.639869 | 804.000000 |
| negative_expectancy_after_shrinkage+profit_factor_below_threshold \| NVDA \| failed breakout short \| SHORT \| trend_long | 6 | {'NVDA': 6} | {'failed breakout short': 6} | {'SHORT': 6} | -0.668335 | 920.000000 |
| negative_expectancy_after_shrinkage+profit_factor_below_threshold \| NVDA \| liquidity sweep reversal short \| SHORT \| trend_long | 6 | {'NVDA': 6} | {'liquidity sweep reversal short': 6} | {'SHORT': 6} | -0.668335 | 920.000000 |
| negative_expectancy_after_shrinkage+profit_factor_below_threshold \| AAPL \| failed breakout short \| SHORT \| trend_long | 5 | {'AAPL': 5} | {'failed breakout short': 5} | {'SHORT': 5} | -0.633017 | 920 |
| negative_expectancy_after_shrinkage+profit_factor_below_threshold \| AAPL \| liquidity sweep reversal short \| SHORT \| trend_long | 5 | {'AAPL': 5} | {'liquidity sweep reversal short': 5} | {'SHORT': 5} | -0.633017 | 920 |
| negative_expectancy_after_shrinkage+profit_factor_below_threshold \| AAPL \| VWAP reclaim long \| LONG \| trend_long | 5 | {'AAPL': 5} | {'VWAP reclaim long': 5} | {'LONG': 5} | -0.376305 | 804 |
| negative_expectancy_after_shrinkage \| SPY \| failed breakout short \| SHORT \| trend_long | 4 | {'SPY': 4} | {'failed breakout short': 4} | {'SHORT': 4} | -0.241241 | 920.000000 |
| negative_expectancy_after_shrinkage \| SPY \| liquidity sweep reversal short \| SHORT \| trend_long | 4 | {'SPY': 4} | {'liquidity sweep reversal short': 4} | {'SHORT': 4} | -0.241241 | 920.000000 |
| negative_expectancy_after_shrinkage+profit_factor_below_threshold \| QQQ \| failed breakout short \| SHORT \| mean_reversion | 4 | {'QQQ': 4} | {'failed breakout short': 4} | {'SHORT': 4} | -0.698054 | 920.000000 |

Suppression is mapped to persisted score-audit reasons, features, score components, expected R estimates, evidence keys, sample counts, and evidence grades. No conclusion relies on a vague model label.
