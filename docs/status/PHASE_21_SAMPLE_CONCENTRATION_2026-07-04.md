# Phase 21 Sample And Concentration Analysis - 2026-07-04

`PHASE_21_SAMPLE_STATUS = INSUFFICIENT_AND_CONCENTRATED`

This analysis uses the Phase 20/21 pre-regression evidence snapshot. Current Postgres is contaminated with parity fixtures and is not used for certification.

## Selected Validation Sample

| Metric | Value |
|---|---:|
| Validation candidates | 953 |
| Selected candidates | 1 |
| Suppressed candidates | 952 |
| Observed selected outcomes | 1 |
| Selected average R | 1.5000 |
| Selected median R | 1.5000 |
| Selected profit factor | 99.0 |
| Selected max drawdown R | 0.0 |
| Same-bar ambiguous selected trades | 0 |
| Required selected trades for activation criteria | 30 |

The one selected trade was positive, but one trade cannot support activation. The validation rejection `minimum_selected_candidate_sample_not_met` is correct.

## Concentration

The selected validation evidence was fully concentrated:

| Dimension | Selected Evidence |
|---|---|
| Symbol | `QQQ`: 1/1 |
| Setup | `VWAP loss short`: 1/1 |
| Day | `2026-07-02`: 1/1 |
| Time bucket | `power_hour`: 1/1 |
| Regime | `chop`: 1/1 |
| Side | Single short-side selected trade inferred from setup |

The validation rejections `single_setup_profit_concentration_too_high` and `single_symbol_profit_concentration_too_high` are directly supported by the selected-candidate breakdown.

## Broader Candidate And Score Samples

| Evidence | Count | Interpretation |
|---|---:|---|
| Counterfactual observed outcomes | 1,608 | Large enough for candidate-quality analysis, not executable P/L. |
| Portfolio observed outcomes | 405 | Enough to review portfolio constraints, but weak overall performance. |
| Evidence cells | 421 | Evidence exists, but selected validation sample remains too small. |
| Score audits | 3,756 | Enough to audit score behavior. |
| A-grade outcomes | 13 | Above the calibration audit minimum of 5, but still thin for activation confidence. |
| TAKE outcomes | 89 | TAKE outperformed WATCH in calibration, but validation selected only 1 trade. |

Calibration did not reject. The sample problem is specifically out-of-sample selected validation scarcity and concentration.

## Ambiguity And Sensitivity

| Risk | Evidence |
|---|---|
| Same-bar ambiguity | Portfolio 30/405 = 7.41%; counterfactual 87/1608 = 5.41%; selected validation 0/1. This did not cause rejection. |
| Slippage/spread fragility | No sensitivity runs were attached to the challenger. This produced warning `some_training_replay_runs_missing_sensitivity`, not the primary rejection. |
| Replay windows | One replay-aware validation window only: train on 2026-07-01 and validate on 2026-07-02. This is too few windows for reconsideration. |

## Minimum Additional Evidence Needed

Activation criteria require at least 30 selected validation trades. The current validation split selected 1 trade across one validation trading day. At that observed selection rate, the minimum additional selected trades needed is 29.

Using the observed rate of 1 selected trade per validation day, the absolute minimum additional validation horizon is 29 more trading days. That is only a mathematical lower bound, not a recommendation to activate at 30 trades.

For a reconsideration-quality evidence pack, collect and rebuild at least:

- 30 additional RTH trading days for SPY, QQQ, AAPL, and NVDA.
- 8 to 10 non-overlapping replay-aware validation windows.
- At least 30 selected validation trades after gates, not before gates.
- At least 5 selected validation trades per symbol before any symbol-specific claim.
- At least 5 selected validation trades per major setup before any setup-specific claim.
- No single symbol, setup, day, regime, or time bucket dominating validation profit beyond existing governance limits.
- Sensitivity evidence for all candidate-market and counterfactual replay windows.

If selection remains near 1 trade per day, collect more than 30 days rather than lowering thresholds. Gate thresholds should not be loosened just to pass.

## Conclusion

The rejection was driven by too few selected validation trades and total concentration of the one selected outcome. The evidence is not broad enough across symbols, setups, days, regimes, time buckets, or windows. The challenger should remain rejected.
