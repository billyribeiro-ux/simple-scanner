# Phase 21T Artifact Rebuild Report - 2026-07-05

`ARTIFACT_REBUILD_STATUS = COMPLETED_WITH_BOUNDED_SENSITIVITY`

## Rebuild Order

Phase 21T rebuilt artifacts in the requested order:

1. Features from persisted real bars.
2. Candidate signals from rebuilt features.
3. Labels from bars, features, and candidates.
4. `candidate_market_replay`.
5. `model_training_counterfactual` replay.
6. Freshness reports.
7. Strict research-cycle dry-run with `allow_stale=false`.

## Final Counts

| Artifact | Rows |
|---|---:|
| Bars | 13560 |
| Features | 13560 |
| Candidate signals | 16725 |
| Labels | 2209 |
| Replay runs | 18 |
| Simulated trades | 25048 |
| Sensitivity runs | 12 |
| Sensitivity scenarios | 474 |
| Pipeline dirty windows | 0 |

## Phase 21T Replays

| Interval | Candidate Market Replay | Counterfactual Replay |
|---|---|---|
| `1min` | `replay_20260705143752_33726551f81599994d55da1b` | `replay_20260705143759_30a05915b7d9ab1dc2a0566c` |
| `5min` | `replay_20260705144208_82503a09e00e1d0da0a7e81a` | `replay_20260705144210_55307ab8666f790369db26b2` |
| `15min` | `replay_20260705144213_53d13af7e89dbd3fb9df183b` | `replay_20260705144213_95d4666a1f5446141889eb5b` |

## Sensitivity Scope

Sensitivity was completed with a bounded grid:

- Slippage bps: `0`, `2`
- Spread bps: `0`, `2`
- Intrabar path policy: `conservative`
- Same-bar stop/target policy: `conservative_stop_first`

The default expanded grid was not practical for the 1-minute expanded sample in this runtime. All six Phase 21T sensitivity runs completed, but robustness remained insufficient for activation.

## Freshness And Strict Dry-Run

Research-scope freshness was `READY`. Strict dry-run `research_cycle_16ad2689f01a0a0d3dd96bd680248377` used `allow_stale=false`, `refresh_data=false`, and did not activate models. Final `db-query-diagnostics` reported `dirty_windows=none`.
