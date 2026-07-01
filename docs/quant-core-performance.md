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
- Candidate market replay pre-indexes bars by `(symbol, interval)` and feature rows by `(symbol, interval, timestamp)`, then processes sorted candidates. Current replay complexity is `O(b log b + f + c * h + t)`, where `b` is loaded bars, `f` is features, `c` is candidates, `h` is the forward hold window, and `t` is simulated trades.
- Backtest metrics are linear in simulated trades: `O(t)`.
- Walk-forward validation is `O(w * t)` for `w` windows and `t` trades unless window filtering is indexed later.

## Current Bottlenecks

- Feature building recomputes all history for a symbol when called by the scanner.
- Label simulation scans forward bars per candidate.
- Replay scans forward bars per candidate inside the configured hold window. It avoids per-candidate database queries, but it is still Python-loop based.
- Walk-forward validation filters trades per window without an interval index.
- Feature, label, replay, sensitivity, comparison, and validation workflows now persist through repositories. Phase 7 records replay audit hashes/fingerprints, blocks stale replay inputs by default, and respects requested symbol/interval/range scopes, but warmup expansion and multi-day replay invalidation are still conservative.
- Replay sensitivity multiplies replay cost by the configured scenario grid. The default grid is intentionally compact enough for local research, and smoke tests use a reduced grid.

## Phase 2 Efficiency Decisions

- Rolling state is scoped by symbol, interval, and session to prevent leakage.
- Scanner now caches per-symbol context buffers instead of scoring a single synthetic quote bar.
- Pure quant tests use synthetic in-memory data and do not require external services.
- FMP calls are not expanded beyond quote, batch quote, intraday bars, and daily bars.
- Replay loads bars, features, and candidate signals in batches before simulation, then persists simulated trades in bulk.
- Replay trade queries are paginated by run ID and ordered by signal timestamp, symbol, and setup.

## Next Optimizations

1. Expand dirty windows with exact warmup lookbacks instead of relying on caller-supplied ranges.
2. Add replay-specific candidate batching by session date for very large symbol universes.
3. Use Polars/Pandas grouped transforms once tests lock down leakage and replay behavior.
4. Promote high-volume `bars` and `simulated_trades` paths to Timescale hypertables when production volume justifies it.
5. Add Timescale compression/retention policies for old raw bars, replay trades, and sensitivity scenarios after export reproducibility is proven.
