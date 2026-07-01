# Quant Core Performance Notes

Report date: 2026-07-01

## Current Shape

The Phase 2 quant core favors deterministic, testable Python loops over premature vectorization. This is intentional: the priority is no-leakage correctness, inspectability, and synthetic regression coverage.

## Complexity

- Feature building sorts bars by `symbol`, `interval`, and `timestamp`: `O(n log n)`.
- Per-session feature computation is linear in bars after sorting: `O(n)`.
- Same-time-of-day relative volume uses bounded deques by `(symbol, interval, minute_of_day)`: amortized `O(1)` lookup/update.
- Relative strength alignment builds timestamp buckets: `O(n)`.
- Candidate detection is constant time per feature row: `O(n)`.
- Label simulation is linear per candidate over the configured forward window: `O(c * h)`, where `c` is candidate count and `h` is max hold bars.
- Backtest metrics are linear in simulated trades: `O(t)`.
- Walk-forward validation is `O(w * t)` for `w` windows and `t` trades unless window filtering is indexed later.

## Current Bottlenecks

- Feature building recomputes all history for a symbol when called by the scanner.
- Label simulation scans forward bars per candidate.
- Walk-forward validation filters trades per window without an interval index.
- Feature, label, and validation workflows now persist through repositories, but rebuilds are still broad rather than incremental.

## Phase 2 Efficiency Decisions

- Rolling state is scoped by symbol, interval, and session to prevent leakage.
- Scanner now caches per-symbol context buffers instead of scoring a single synthetic quote bar.
- Pure quant tests use synthetic in-memory data and do not require external services.
- FMP calls are not expanded beyond quote, batch quote, intraday bars, and daily bars.

## Next Optimizations

1. Add incremental feature updates for scanner context and recently changed sessions.
2. Narrow label rebuilds by `(symbol, interval, session_date, feature_set_version)`.
3. Add candidate-window query helpers by symbol and timestamp for faster label simulation.
4. Use Polars/Pandas grouped transforms once tests lock down leakage behavior.
5. Store validation trades by window to avoid repeated scans.
