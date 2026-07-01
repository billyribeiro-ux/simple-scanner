# Signal Methodology

V1 combines four evidence layers:

1. Rules engine: detects named setups such as VWAP reclaim/loss, opening-range breakouts/breakdowns, premarket breaks, previous-day level reclaims/losses, liquidity sweeps, continuations, and failed breakouts/breakdowns.
2. Statistical evidence: summarizes historical win rate, average/median R, profit factor, drawdown, MFE/MAE, and time-to-target by symbol, setup, regime, and time window.
3. Model probability: uses a baseline classifier and upgrades to scikit-learn gradient/ensemble style models when enough samples exist.
4. Meta-scorer: blends setup quality, historical evidence, ML probability, regime alignment, relative strength, and ticker personality.

Trade plans are suppressed when evidence is weak, the market regime is hostile, sample size is too small, or live confidence is below the configured threshold.

Default label target is hitting `+1.5R` before `-1R` within `60` minutes. Entries use next-bar open by default to reduce lookahead risk.

## Phase 2 Implementation Status

Implemented:

- Candidate detection is now explicit in `app/signals/candidates.py`.
- Candidate setups include VWAP reclaim/loss, opening range breakout/breakdown, premarket high/low breaks, previous-day high/low events, liquidity sweep reversals, failed breakouts/breakdowns, and trend continuations.
- Candidate reasons and warnings are deterministic and inspectable.
- Labels use next-bar-open entries by default and future bars only for outcome measurement.
- Same-bar stop/target conflicts use conservative stop-first handling.
- Scanner scoring now requires hydrated historical context and emits `NO_TRADE` when context is insufficient.

Still partial:

- Confidence remains a baseline heuristic, not a calibrated probability.
- No self-learning loop exists yet.
- No broker execution exists or should be inferred.
