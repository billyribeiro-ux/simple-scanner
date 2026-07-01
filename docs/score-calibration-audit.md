# Score Calibration Audit

Status date: 2026-07-01

The score calibration audit checks whether replay-aware scores rank observed replay outcomes. It is not probability calibration and does not claim profitability.

## Inputs

- persisted `candidate_score_audits`;
- replay outcome rows from counterfactual or portfolio replay;
- optional validation report ID;
- explicit replay run IDs;
- outcome source policy.

## Outputs

The audit persists to `model_calibration_audits` and `model_calibration_bins`:

- score bins: `0-20`, `20-40`, `40-60`, `60-75`, `75-85`, `85-100`;
- grade bins;
- action bins;
- sample count, average R, win rate, profit factor, drawdown;
- monotonicity pass/fail;
- rank correlation;
- A/B/C and TAKE/WATCH/SUPPRESS separation;
- stability by symbol, setup, regime, and time bucket;
- warnings and rejection reasons.

## Warnings

Phase 9 emits warnings including:

- `high_score_negative_expectancy`;
- `grade_order_not_monotonic`;
- `take_bucket_underperforms_watch`;
- `too_few_high_grade_samples`;
- `score_concentrated_in_one_bucket`;
- `high_score_depends_on_one_symbol`;
- `high_score_depends_on_one_setup`;
- `severe_regime_instability`;
- `high_same_bar_ambiguity_in_top_bucket`;
- `sensitivity_fragility_in_top_bucket`.

## Gates

Activation can require a calibration audit and reject when:

- an audit is missing;
- score bins are not monotonic when monotonicity is required;
- TAKE does not outperform WATCH when required;
- high-grade samples are below minimum;
- rank correlation is below threshold;
- warnings exceed the configured maximum.

Scanner output respects the active model’s calibration requirement. If a required audit is missing or failed, actionable TAKE output is suppressed and `calibration_required_or_failed` is emitted.
