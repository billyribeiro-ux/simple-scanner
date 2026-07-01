# Phase 7 Replay Sensitivity Report

Status date: 2026-07-01

## Implemented

- Added `app/backtesting/sensitivity.py`.
- Added persisted `replay_sensitivity_runs` and `replay_sensitivity_scenarios`.
- Added sensitivity APIs for create, get, scenario listing, and replay-run listing.
- Added sensitivity exports for summary XLSX, scenario CSV/XLSX, and metrics JSON.
- Added sensitivity-aware replay validation gates through `require_sensitivity`, `sensitivity_run_id`, and `minimum_robustness_score`.

## Default Grid

- Slippage bps: `0, 1, 2, 5, 10`
- Spread bps: `0, 1, 2, 5, 10`
- Intrabar policies: `conservative`, `open_high_low_close`, `open_low_high_close`
- Same-bar policy default: `conservative_stop_first`

## Outputs

Sensitivity runs persist:

- scenario metrics
- worst, median, and best cases
- robustness score
- fragility flags
- gate results
- source replay config hash and fingerprints when available

Sensitivity is a robustness audit only. It is not calibrated ML, live execution, or a profitability claim.

## Verified Commands

```text
cd services/quant-engine && PYTHONPATH=. .venv/bin/python -m pytest tests/quant/test_replay_sensitivity.py -q
3 passed

cd services/quant-engine && PYTHONPATH=. .venv/bin/python -m pytest tests/test_exports.py -q
3 passed

cd services/quant-engine && PYTHONPATH=. .venv/bin/python -m pytest tests/test_persisted_api_smoke.py::test_persisted_api_vertical_slice_sqlite -q
1 passed, 1 warning

cd services/quant-engine && PYTHONPATH=. .venv/bin/python -m pytest tests/test_persisted_api_smoke.py::test_persisted_api_vertical_slice_postgres -q
1 passed, 1 warning
```
