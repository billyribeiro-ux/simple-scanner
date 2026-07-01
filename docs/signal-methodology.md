# Signal Methodology

V1 combines four evidence layers:

1. Rules engine: detects named setups such as VWAP reclaim/loss, opening-range breakouts/breakdowns, premarket breaks, previous-day level reclaims/losses, liquidity sweeps, continuations, and failed breakouts/breakdowns.
2. Statistical evidence: summarizes historical win rate, average/median R, profit factor, drawdown, MFE/MAE, and time-to-target by symbol, setup, regime, and time window.
3. Model probability: uses a baseline classifier and upgrades to scikit-learn gradient/ensemble style models when enough samples exist.
4. Meta-scorer: blends setup quality, historical evidence, ML probability, regime alignment, relative strength, and ticker personality.

Trade plans are suppressed when evidence is weak, the market regime is hostile, sample size is too small, or live confidence is below the configured threshold.

Default label target is hitting `+1.5R` before `-1R` within `60` minutes. Entries use next-bar open by default to reduce lookahead risk.
