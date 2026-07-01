# Phase 6 Replay Validation Status

Date: 2026-07-01

## Summary

Phase 6 adds explicit validation modes:

- `label_derived`: default V1 validation and activation guard.
- `candidate_market_replay`: optional replay-metric validation from persisted candidate market replay runs.

The default remains `label_derived` so existing guarded activation behavior is preserved.

## Implemented Behavior

`POST /models/validate` accepts `validation_mode`. With `label_derived`, it validates simulated label-derived trades as before. With `candidate_market_replay`, it reads the latest persisted replay run and creates a validation report with purpose `replay_validation`.

`POST /models/activate` accepts `validation_mode`. It looks for an accepted validation report in the corresponding validation purpose:

- `validation` for `label_derived`;
- `replay_validation` for `candidate_market_replay`.

Activation responses include the validation mode used.

## Failure Behavior

If replay validation is requested before any replay run exists, validation writes a rejected report with `rejection_reasons = ["no_replay_run_available"]`. Activation then fails because there is no accepted replay validation report.

If replay metrics fail the existing activation decision gates, replay validation is rejected and cannot activate the model for replay mode.

## What This Proves

- Label-derived validation remains the safe default.
- Replay validation is explicit and cannot be confused with label-derived evidence.
- A rejected replay validation report prevents replay-mode activation.
- Activation records the validation mode used.

## What This Does Not Prove

- It does not prove live trading performance.
- It does not calibrate model probabilities.
- It does not select a specific replay run by ID yet.
- It does not prove FMP entitlement or WebSocket behavior.
- It does not add broker execution, order routing, options, Greeks, IV, or market internals.

## Next Work

Phase 7 should add replay-run selection for validation, replay window metadata, slippage/spread sensitivity gates, and a clearer comparison report between label-derived and candidate-market-replay metrics.
