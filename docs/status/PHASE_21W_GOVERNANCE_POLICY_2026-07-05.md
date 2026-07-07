# Phase 21W Governance Policy

Date: 2026-07-05
Status: ENFORCED

## Activation-Grade Sensitivity

Required sensitivity now distinguishes diagnostic sensitivity from activation-grade sensitivity.

Activation-grade sensitivity requires all of:

- `grid_version` and `grid_hash` recorded.
- `coverage_mode` of `FULL_GRID` or `CHUNKED_FULL_GRID`.
- `planned_scenario_count=75`.
- `completed_scenario_count=75`.
- `remaining_scenario_count=0`.
- `completion_status=COMPLETE`.
- `full_default_grid_complete=true`.
- `partial_grid_disclosure=false`.

Model review and replay-aware validation still require `pass_fail=pass` for promotion-sensitive review. A complete full-grid run can satisfy the sensitivity-completion requirement while still blocking promotion on robustness failure.

## Diagnostic Sensitivity

These modes remain diagnostic and cannot satisfy required activation-grade sensitivity:

- `TIERED_ESSENTIAL`
- `SAMPLED`
- `PARTIAL_TIMEOUT`
- incomplete `CHUNKED_FULL_GRID`
- scenario-group-only invocation results

Partial diagnostic runs persist progress and can be resumed, but they remain blocked for activation-grade review.

## Guardrails Preserved

Phase 21W did not activate a model, approve a challenger, loosen validation/calibration/sensitivity gates, bypass freshness gates, write fixtures into evidence DB, use broker execution, add order routing/options/WebSocket production ingestion/black-box ML, expose secrets, or make profitability claims.

