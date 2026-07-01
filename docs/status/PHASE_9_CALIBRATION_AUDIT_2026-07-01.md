# Phase 9 Calibration Audit Status

Status date: 2026-07-01

Implemented.

## What Changed

- Added `app/models/calibration_audit.py`.
- Added `model_calibration_audits`, `model_calibration_bins`, and `model_comparisons` persistence.
- Added create/list/get/bins API routes for calibration audits.
- Added calibration audit XLSX, bins CSV/XLSX, and metrics JSON exports.
- Added activation gates for required calibration, monotonic score bins, TAKE/WATCH separation, high-grade samples, rank correlation, and warning count.
- Added scanner suppression when a calibration-required replay-aware model has missing or failed calibration.

## Safety Notes

This audit checks score ordering against replay outcomes. It is not probability calibration and not a profitability claim.

## Verified By

- targeted calibration audit tests;
- expanded API smoke for audit routes and exports;
- SQLite/Postgres schema inspection and parity.
