# Phase 24 Artifact Rebuild

`PHASE_24_ARTIFACT_REBUILD_STATUS = COMPLETED_FROM_REAL_PERSISTED_BARS`

Artifacts were rebuilt from the expanded persisted FMP bars. No stale gate was bypassed.

## Rebuild Counts

| Artifact | Count |
|---|---:|
| Bars read for feature rebuild | 3,564 |
| Features written | 3,564 |
| Candidate rows written | 5,133 |
| Label rows written | 1,855 |
| Feature dirty windows cleared | 256 |
| Candidate dirty windows cleared | 256 |
| Label dirty windows cleared | 256 |
| Replay dirty windows cleared | 132 |
| Dirty windows after rebuild | 0 |

## Expanded Baseline Replays

| Purpose | Replay ID | Trades | Avg R | Full-grid sensitivity | Robustness |
|---|---|---:|---:|---|---:|
| Portfolio | `replay_20260706181047_b0fdc7ee603396c41bc181b0` | 1,063 | -0.179516 | `sensitivity_b08ba7c84d118d2e325e9e4406e28388` | 0.00 |
| Counterfactual | `replay_20260706181050_dcc34871f61eda7937dca55d` | 3,322 | -0.160676 | `sensitivity_9824f9f427eb1aeb80b9a2c00e9746a2` | 0.00 |

Both expanded baseline sensitivity runs completed the full default 75-scenario grid and failed robustness. This does not approve activation.

## Freshness And Dry Run

- Freshness report: `freshness_e8ee87ff192c840166144de76f59651e`, status `READY`, dirty windows `0`.
- Strict research-cycle dry-run: `research_cycle_418dee617dd11a6041c8b6ed8bfe20a5`, `allow_stale=false`, blocked `false`.
- Dry-run warnings: `missing_bar_windows_detected`, `provider_request_errors_detected`; these are recorded as warnings, not activation blockers for the dry-run plan.
