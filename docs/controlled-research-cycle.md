# Controlled Research Cycle

Status date: 2026-07-01

## Purpose

The controlled research cycle turns new persisted evidence into a reproducible review package. It is a governance workflow, not autonomous learning. It may inspect data quality, stale windows, replay artifacts, validations, calibrations, drift, reviews, champion/challenger comparisons, and proposals. It never routes orders and never silently activates a model.

## API

- `POST /research/cycles`
- `GET /research/cycles`
- `GET /research/cycles/{research_cycle_id}`
- `POST /research/cycles/{research_cycle_id}/dry-run`
- `POST /research/cycles/{research_cycle_id}/run`
- `GET /research/cycles/{research_cycle_id}/artifacts`
- `POST /research/cycles/{research_cycle_id}/export`

## Reproducibility

Each cycle stores `config_hash`, `input_fingerprint`, `git_commit` when available, `database_revision`, `persistence_backend`, symbols, intervals, date range, session, stale-window state, warnings, source IDs, and a summary. Secrets are redacted before persistence.

## Guardrails

- `refresh_data=false` by default.
- `refresh_data=true` blocks cleanly when `FMP_API_KEY` is missing.
- Stale build windows block by default unless `allow_stale=true`.
- Dry-run returns plan and warnings without activation.
- Cycle run records `model_activation_unchanged=true`.
- Cycle run can produce a proposal, but proposal approval and activation are separate explicit actions.

## Exports

Use `POST /exports/research-cycle.xlsx` or `POST /exports/research-cycle.json` with `run_id` set to the cycle ID. The workbook includes Summary, Cycle Config, Data Quality, Stale Windows, Replay Windows, Counterfactual Replay, Portfolio Replay, Sensitivity, Calibration, Drift, Model Review, Champion vs Challenger, Proposal, Warnings, Artifacts, and Provenance.
