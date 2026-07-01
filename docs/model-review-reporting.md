# Model Review Reporting

Status date: 2026-07-01

Model review reports combine model metadata, validation reports, calibration audits, calibration drift reports, replay window summaries, sensitivity IDs, comparisons, and unresolved warnings into an advisory readiness status.

## Readiness Statuses

- `PASS`: no blocking diagnostic issues were found.
- `WATCH`: weaker evidence or drift history requires monitoring.
- `REVIEW`: human review is required before activation.
- `BLOCK`: validation rejection, blocking drift, or required missing calibration prevents readiness.

The service never calls model activation and sets `model_activation_unchanged=true` in report summaries and exports.

## API And Exports

- `POST /models/{model_version}/review-report`
- `GET /models/{model_version}/review-reports`
- `GET /models/review-reports/{review_report_id}`
- `POST /exports/model-review.xlsx`
- `POST /exports/model-review.json`

The workbook includes `Summary`, `Readiness`, `Readiness Reasons`, `Unresolved Warnings`, `Validation Reports`, `Calibration Audits`, `Drift Reports`, and `Model Summary`.
