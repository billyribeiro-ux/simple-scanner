# Phase 21W Governance Review

Date: 2026-07-05
Status: BLOCK

## Model Review

Model review: `model_review_e045a9d38fbbaa4a6acf01b1249dc015`

| Field | Value |
|---|---|
| Challenger | `amd-replay-aware-20260702-164145` |
| Readiness | `BLOCK` |
| Validation report | `report_65d036bc0fb422f6de0697fbd4c5111d` |
| Calibration audit | `calibration_70021b4dc0bb829a2fbb92e9d1d386a9` |
| Drift report | `calibration_drift_2245a2352dfa80965c2b9d6632c35034` |
| Sensitivity reports | 6 full-grid complete runs |

Readiness reasons:

- `validation_rejected`
- `too_many_calibration_warnings`
- `calibration_drift_watch`
- `sensitivity_gate_failed`

The Phase 21V reasons `sensitivity_scope_not_full_grid` and partial/full-grid disclosure are resolved by Phase 21W full-grid completion. The challenger remains blocked because the completed full-grid sensitivity evidence failed robustness gates.

## Research-Cycle Dry-Runs

Strict wall-clock dry-run `research_cycle_ee92cc697a1fc3213e95d21149a5bf15` used `allow_stale=false` and `refresh_data=false` and correctly blocked on current freshness `STALE`.

Strict data-cutoff dry-run `research_cycle_e9df73b81c44222b943ab06a5a908758` used:

- `allow_stale=false`
- `refresh_data=false`
- data cutoff `2026-07-02T19:59:00+00:00`
- freshness `READY`
- dirty windows `0`
- blocked `false`

Warnings remained: `missing_bar_windows_detected` and `provider_request_errors_detected`.

