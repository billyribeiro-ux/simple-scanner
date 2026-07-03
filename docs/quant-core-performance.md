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
- Replay-aware evidence aggregation is linear in candidate outcome rows times the small fixed hierarchy depth: `O(r * h)`, where `r` is outcome rows and `h = 6`.
- Replay-aware scoring resolves at most six evidence cells per candidate and blends them in memory: `O(h)`.
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
- Replay-aware model training loads replay runs/trades/features/candidates in batches, persists evidence cells in bulk, and scanner scoring caches evidence cells by active model version.

## Next Optimizations

1. Expand dirty windows with exact warmup lookbacks instead of relying on caller-supplied ranges.
2. Add replay-specific candidate batching by session date for very large symbol universes.
3. Use Polars/Pandas grouped transforms once tests lock down leakage and replay behavior.
4. Promote high-volume `bars` and `simulated_trades` paths to Timescale hypertables when production volume justifies it.
5. Add Postgres indexes for high-volume evidence-cell dimensions and score-audit filters if model history grows beyond local V1 scale.
6. Add Timescale compression/retention policies for old raw bars, replay trades, score audits, and sensitivity scenarios after export reproducibility is proven.
7. Move evidence aggregation to Polars/Pandas or a database grouped query when replay outcome row count makes Python aggregation the bottleneck.

## Phase 9 Performance Notes

- Counterfactual replay reuses the batched replay path and avoids per-candidate database queries. Complexity remains bounded by sorted bars/features plus per-candidate hold-window scans.
- Candidate overlap context is computed in memory by symbol/interval. This is acceptable for local V1, but high-volume candidate sets should move overlap-density calculations to grouped vectorized code.
- Calibration audit joins score audits to outcome rows in memory, then groups into score, grade, action, symbol, setup, regime, and time buckets. This is linear in loaded audits/outcomes plus small fixed bin counts.
- Model comparison loads persisted model/report/audit payloads and sorts model summaries; it is diagnostic-only and not on the scanner hot path.

## Phase 11 Performance Notes

- Research cycle planning calls data-quality reporting, stale-window status, and latest-bar scans. This is acceptable for the default small symbol universe, but `_latest_bars` is currently one repository query per symbol/interval and should become a grouped query before larger universes.
- Champion/challenger comparison loads persisted model, validation, calibration, drift, and model-review payloads. It is not on the scanner hot path and should remain bounded by explicit artifact IDs.
- Proposal creation and decision-ledger writes are constant-size metadata operations.
- Research-cycle XLSX exports read persisted artifacts and write multiple sheets. They are operator reports, not hot-path scanner work.
- Dry-run should be used before expensive windows. It estimates dirty-window/rebuild work and can block stale data before training or replay.
- V1 artifact reuse is explicit-ID based. Future optimization should add config-hash lookup for replay/window/calibration/review artifacts and a `force=true` override rather than rerunning matching expensive work.
- Future live data refresh should remain gated by `FMP_API_KEY` and should write provider request accounting without secrets.

## Phase 13 Scheduler Performance Notes

- Scheduler jobs are synchronous and operator-triggered in V1. There is no background daemon, infinite loop, or unbounded polling.
- `run-pending` defaults to `3` jobs and is hard-capped at `10` jobs per request.
- Research-cycle jobs still rely on the existing cycle bounds such as `max_window_count`; operators should dry-run before expensive replay/window work.
- Job lists and events are paginated by `limit` and `offset`.
- Job payloads/results should remain compact metadata and artifact references, not large raw market-data blobs.
- Phase 14 added explicit leases, heartbeats, attempt counts, stale recovery, and a bounded one-shot worker command before increasing throughput.
- Future performance work should add payload/result size limits and artifact reuse by config hash before widening scheduler job volume.

## Phase 14 Scheduler Worker Performance Notes

- `make scheduler-worker-once` leases at most `3` jobs by default and is hard-capped by the same `10` job bound.
- Lease acquisition uses the persisted queue order and avoids long-lived polling.
- Heartbeat and release events add small constant-size writes per job.
- Stale recovery scans only expired `RUNNING` jobs with a bounded limit.
- The worker remains an operator command, not a hot-path scanner or autonomous loop.

## Phase 15 FMP Data Performance Notes

FMP ingestion is deliberately bounded: 10 symbols per job, `1min/5min/15min` intervals, and a conservative five-day intraday default. Bar writes use the existing idempotent upsert key and mark downstream feature/label/replay windows dirty. REST polling remains the default live-data path.

## Phase 16 Freshness Performance Notes

Freshness checks query latest bars, quote snapshots, dirty windows, and capability summaries from local persistence. They do not call FMP. Seed ingestion remains bounded to 10 symbols and five intraday days.
