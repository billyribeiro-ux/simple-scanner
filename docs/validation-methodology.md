# Validation Methodology

Validation must answer whether a signal process has out-of-sample expectancy, not whether it can overfit the past.

Required rules:

- Chronological train/test splits only.
- Walk-forward validation for model versions.
- No random shuffling across time.
- No features that require future bars at decision time.
- Minimum sample checks by symbol/setup/regime.
- Report no-trade suppression rate.

Metrics include trade count, win rate, precision, recall where applicable, average R, median R, expectancy, profit factor, max drawdown, MFE, MAE, average time in trade, target hit rate, stop hit rate, and calibration/Brier score when probabilities are available.

## Backtest And Validation Modes

V1 now keeps two modes explicit:

- `label_derived`: default validation and activation path. It uses leakage-safe labels for fast evidence and model training.
- `candidate_market_replay`: optional replay validation path. It uses explicitly selected persisted replay metrics from raw-bar candidate replay and stores validation reports with purpose `replay_validation`.
- `replay_aware_walk_forward`: replay-aware model-selection path. It scores candidates chronologically using only replay outcome rows available before each validation candidate timestamp and stores reports with purpose `replay_aware_validation`.

Model activation responses include the `validation_mode` used. If replay validation is requested without `replay_run_id`, `replay_filter`, or `allow_latest_replay_fallback=true`, the report is rejected with `replay_run_selection_required`. Replay validation does not remove the default label-derived guard; it is an explicit additional gate.

Replay validation selection fields:

- `replay_run_id`: exact replay run.
- `replay_filter`: JSON filter that deterministically selects the newest matching replay run.
- `allow_latest_replay_fallback`: explicit opt-in to the previous latest-run behavior.
- `allow_stale_replay_validation`: explicit opt-in to validate with a stale replay run.

Sensitivity-aware validation fields:

- `require_sensitivity`
- `sensitivity_run_id`
- `minimum_robustness_score`

When a sensitivity run is provided, replay validation rejects runs with mismatched replay IDs, failed sensitivity gates, or robustness below the requested threshold.

## Phase 2 Implementation Status

Implemented in code:

- `app/validation/engine.py` creates chronological splits and walk-forward windows.
- Embargo checks flag train/validation/test overlap.
- Validation reports include summary metrics, per-window metrics, per-symbol/setup/regime/time-bucket metrics, leakage warnings, activation decision, and rejection reasons.
- Activation gates reject weak models on minimum trades, average R, profit factor, drawdown, excessive concentration, leakage warnings, or validation failure.

Still partial:

- Replay validation is only as trustworthy as the selected replay window and assumptions; review `config_hash`, `input_fingerprint`, and sensitivity flags before using it for model activation decisions.
- Replay-aware validation is deterministic and no-leakage, but V1 uses persisted replay outcome rows instead of a separate counterfactual replay mode for every skipped portfolio-overlap candidate.
- Calibration/Brier scoring is not real until a probability model exists.
## Phase 9 Replay-Aware Windows

`replay_aware_walk_forward` now accepts explicit training, validation, and test replay run IDs plus optional train/validation/test timestamp windows and `embargo_minutes`. It can require counterfactual training data, require portfolio validation data, and require a calibration audit.

Validation scores candidates with training-only evidence and persists replay run IDs, candidate counts, embargo metadata, and calibration requirements in the validation report. Weak score ordering can be rejected through calibration audit gates.

## Phase 11 Proposal Gate

Champion/challenger comparison requires an accepted validation report for the challenger before a proposal can be recommended for activation. Research cycles can pass explicit `validation_report_ids` so the comparison is reproducible from persisted IDs instead of whatever report is latest at query time.

Proposal activation still calls the existing model activation service. `APPROVED_FOR_ACTIVATION` is not enough; the activation request must include `confirm_manual_activation=true`, the challenger model must exist, and the accepted validation guard must pass for the selected validation mode.
