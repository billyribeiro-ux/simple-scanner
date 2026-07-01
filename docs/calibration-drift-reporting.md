# Calibration Drift Reporting

Status date: 2026-07-01

Calibration drift reports compare persisted Phase 9 calibration audits across time or replay windows. They are operational diagnostics, not calibrated probabilities, trading signals, or activation decisions.

## Inputs

- calibration audits for a model version
- optional replay window results
- optional replay runs for stale-source checks
- thresholds such as minimum recent high-grade samples and rank-correlation drop

## Signals Reported

- rank-correlation series and deterioration
- score/grade/action bin average-R drift
- monotonicity failures
- high-grade expectancy turning negative
- TAKE underperforming WATCH
- calibration warning spikes
- stale replay/window contamination
- too-few recent high-grade samples

Severity is `INFO`, `WATCH`, `REVIEW`, or `BLOCKING`. `BLOCKING` means the model should go through human review before activation; no automatic activation or deactivation occurs.

## API And Exports

- `POST /models/{model_version}/calibration-drift`
- `GET /models/{model_version}/calibration-drift`
- `GET /models/calibration-drift/{drift_report_id}`
- `GET /models/calibration-drift/{drift_report_id}/windows`
- `POST /exports/calibration-drift.xlsx`
- `POST /exports/calibration-drift.json`
- `POST /exports/calibration-drift-windows.csv`
- `POST /exports/calibration-drift-windows.xlsx`

Drift exports record source IDs, severity, row count, file hash, and workbook sheets.
