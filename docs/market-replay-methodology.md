# Market Replay Methodology

Status date: 2026-07-01

## Purpose

Candidate market replay is the honest execution-style backtest mode for V1. It replays persisted candidate signals through raw OHLCV bars chronologically and computes metrics from simulated trades. It does not use future labels as the outcome shortcut.

This is still a research simulator. It does not place orders, model queue position, guarantee fills, prove profitability, or connect to a broker.

## Simulation Type

- `label_derived`: fast evidence mode based on leakage-safe labels.
- `candidate_market_replay`: Phase 6 replay mode based on persisted candidates, features, and raw bars.

Every replay run and exported replay artifact carries `simulation_type = candidate_market_replay`.

## Inputs

Replay loads data in batches:

- `bars`: raw interval bars by symbol, interval, timestamp, and source.
- `features`: signal-time context such as ATR proxy, regimes, and time buckets.
- `candidate_signals`: deterministic setup candidates and signal-time context.

Replay does not define entries, stops, or targets from future highs/lows, future swings, or future labels.

## Default Execution Assumptions

- Session: regular trading hours by default.
- Entry: next bar open after the candidate timestamp.
- Long slippage/spread: entry is adjusted upward.
- Short slippage/spread: entry is adjusted downward.
- Stop mode: candidate context first, then signal-time feature context, then fixed risk fallback when configured.
- Target mode: candidate targets first, otherwise R multiples.
- Default targets: `1R`, `1.5R`, and `2.5R`.
- Partial exits: off by default for V1.
- Same-bar stop/target ambiguity: conservative stop first.
- Forced time exit: close of the expiration bar after `max_hold_minutes`.
- Session exit: final eligible RTH bar when configured.

## Skip Reasons

Skipped candidates are persisted in `simulated_trades` with `status = SKIPPED` and one of these reasons:

- `missing_entry_bar`
- `outside_session`
- `invalid_risk_plan`
- `insufficient_reward_risk`
- `overlapping_trade`
- `portfolio_trade_limit`
- `cooldown_active`
- `insufficient_context`
- `regime_filter_block`
- `duplicate_candidate`
- `no_future_bars`
- `data_quality_block`

## Risk And Overlap Rules

Defaults are conservative:

- one open trade per symbol;
- no overlapping same setup per symbol until exit;
- portfolio-level max open trade limit;
- deterministic same-timestamp candidate priority;
- optional cooldown after a loss or after any trade.

Candidate priority sorts by timestamp, then higher confidence/score, then higher expected R, then symbol and setup as deterministic tie-breakers.

## Metrics

Metrics are computed from taken simulated trades, while candidate counts and skip rates include skipped candidates. V1 stores:

- total candidates, taken/skipped counts, skip rate, and skip breakdown;
- total, long, short, winning, losing, and breakeven trades;
- win/loss rate, average/median/expectancy/total R;
- gross profit/loss R, profit factor, max drawdown, consecutive wins/losses;
- average/median MFE and MAE;
- target, stop, time-exit, session-exit, and same-bar ambiguity rates;
- average/median time in trade;
- per-symbol, per-setup, per-regime, per-time-bucket, and per-side metrics;
- daily R, trade R, and drawdown series;
- warnings and data-quality summary.

## Persistence And Exports

Replay runs persist to `replay_runs`. Taken and skipped candidates persist to `simulated_trades`. Replay exports read from those persisted rows:

- summary XLSX;
- simulated trades CSV;
- simulated trades XLSX;
- metrics JSON.

The replay summary workbook includes `Summary`, `Trades`, `Skipped Candidates`, `Per Symbol`, `Per Setup`, `Per Regime`, `Per Time Bucket`, `Daily R`, `Drawdown`, `Config`, and `Warnings`.

## Known Limits

- OHLCV bars cannot prove actual intrabar path unless the policy is configured as an assumption.
- Same-bar ambiguity defaults to conservative stop first, which can understate best-case outcomes.
- Slippage and spread are fixed config assumptions, not live microstructure estimates.
- Commission is simple per-share cost.
- The latest replay validation path uses the latest persisted replay run; specific replay-run selection is future work.
- No calibrated ML, self-learning, broker execution, WebSocket entitlement path, options, Greeks, IV, or market internals are in scope.
