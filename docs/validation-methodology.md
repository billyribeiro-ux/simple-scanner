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
- `candidate_market_replay`: optional replay validation path. It uses persisted replay metrics from raw-bar candidate replay and stores validation reports with purpose `replay_validation`.

Model activation responses include the `validation_mode` used. If replay validation is requested and no replay run exists, the report is rejected with `no_replay_run_available`. Replay validation does not remove the default label-derived guard; it is an explicit additional gate.

## Phase 2 Implementation Status

Implemented in code:

- `app/validation/engine.py` creates chronological splits and walk-forward windows.
- Embargo checks flag train/validation/test overlap.
- Validation reports include summary metrics, per-window metrics, per-symbol/setup/regime/time-bucket metrics, leakage warnings, activation decision, and rejection reasons.
- Activation gates reject weak models on minimum trades, average R, profit factor, drawdown, excessive concentration, leakage warnings, or validation failure.

Still partial:

- Replay validation currently uses the latest persisted replay run for the requested mode; future work should support selecting a specific replay run, model version, and out-of-sample replay window.
- Calibration/Brier scoring is not real until a probability model exists.
