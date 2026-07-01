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

## Phase 2 Implementation Status

Implemented in code:

- `app/validation/engine.py` creates chronological splits and walk-forward windows.
- Embargo checks flag train/validation/test overlap.
- Validation reports include summary metrics, per-window metrics, per-symbol/setup/regime/time-bucket metrics, leakage warnings, activation decision, and rejection reasons.
- Activation gates reject weak models on minimum trades, average R, profit factor, drawdown, excessive concentration, leakage warnings, or validation failure.

Still partial:

- Validation currently operates over simulated/label-derived trades; the next phase should wire it to persisted model runs and raw candidate-to-trade simulations.
- Calibration/Brier scoring is not real until a probability model exists.
