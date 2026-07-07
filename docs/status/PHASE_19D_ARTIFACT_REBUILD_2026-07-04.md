# Phase 19D Artifact Rebuild - 2026-07-04

`PHASE_19_STATUS = ACCEPTED`

Phase 19D rebuilt derived artifacts from persisted live FMP bars only. No synthetic parity-test rows were retained in the certification database.

## Rebuild Order

1. Features from real persisted bars
2. Candidate signals from rebuilt features
3. Labels from bars/features/candidates
4. `candidate_market_replay`
5. `model_training_counterfactual` replay
6. Freshness reports
7. Strict research-cycle dry-run with `allow_stale=false`

## Feature Rebuild

| Pass | Bars Read | Features Written |
|---|---:|---:|
| 1-minute first | 3120 | 3120 |
| All intervals | 3960 | 3960 |
| Session-aligned cleanup | 1980 | 1980 |

Final feature count: 3960.

## Candidate And Label Rebuild

| Pass | Bars Read | Features Read | Candidates Generated | Labels Written |
|---|---:|---:|---:|---:|
| 1-minute first | 3120 | 3120 | 3723 | 554 |
| All intervals | 3960 | 3960 | 4846 | 267 |
| Session-aligned cleanup | 1980 | 1980 | 2465 | 408 |

Final candidate signal count: 4909.

Final label count: 778.

The session-aligned cleanup reran builders on exact session windows after incremental refresh updated July 2 bars. This used repository build services and cleared the stale markers without bypassing stale gates.

## Replay Rebuild

| Replay | Interval | Run ID | Bars | Features | Candidates | Trades |
|---|---|---|---:|---:|---:|---:|
| `candidate_market_replay` | `1min` | `replay_20260704192729_6beec3610b794d914108bf5d` | 3120 | 3120 | 1610 | 405 |
| `model_training_counterfactual` | `1min` | `replay_20260704192730_df74191456eb8e03eaec364e` | 3120 | 3120 | 1610 | 1608 |
| `candidate_market_replay` | `5min` | `replay_20260704192732_c6b8ded646b5c976671ac122` | 624 | 624 | 472 | 123 |
| `model_training_counterfactual` | `5min` | `replay_20260704192733_2f94c54d5b711681971df741` | 624 | 624 | 472 | 470 |
| `candidate_market_replay` | `15min` | `replay_20260704192733_09d7d213c3c2397d2e0e0081` | 208 | 208 | 183 | 52 |
| `model_training_counterfactual` | `15min` | `replay_20260704192733_71458e5a319d72b85cb12204` | 208 | 208 | 183 | 178 |

The mandatory research scope is the 1-minute pair. The 5-minute and 15-minute replay passes were run to clean the complete seeded intraday interval set.

## Final Artifact State

- Bars: 3960
- Features: 3960
- Candidate signals: 4909
- Labels: 778
- Replay runs: 6
- Simulated trades: 4530
- Dirty windows: 0

No model was activated and no broker execution path was used.
