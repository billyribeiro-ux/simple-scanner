# Phase 9 Counterfactual Replay Status

Status date: 2026-07-01

Implemented.

## What Changed

- Added `model_training_counterfactual` simulation type.
- Added replay config fields for replay purpose, portfolio constraint enforcement, symbol overlap enforcement, invalid-candidate capture, and candidate-quality labeling.
- Counterfactual mode reuses the existing candidate market replay OHLCV simulator but disables portfolio max-open, symbol/setup overlap, and cooldown state mutation by default.
- Counterfactual runs persist under `replay_runs`; per-trade counterfactual metadata persists in `simulated_trades.metadata_json`.
- Replay metrics now include candidate-quality warnings, valid/invalid/observed counts, concurrency buckets, overlap density, and `is_portfolio_pnl = false` for counterfactual runs.

## Safety Notes

Counterfactual replay answers what each valid candidate would have done independently. It is not executable portfolio P/L and must not be used as a broker/order-routing instruction.

## Verified By

- `services/quant-engine/tests/quant/test_phase9_counterfactual_calibration.py`
- expanded persisted API smoke
- repository parity after Alembic `0006_phase9_calibration`
