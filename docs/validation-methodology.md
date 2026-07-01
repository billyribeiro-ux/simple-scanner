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
