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

## Operator UI

Phase 12 exposes cycles through `/research/cycles` and `/research/cycles/{research_cycle_id}`. The create form defaults to RTH, `refresh_data=false`, `allow_stale=false`, all V1 intervals, and `max_window_count=20`. User-entered `APPL` is normalized to `AAPL` before the create request.

Dry-run, run, and export are separate buttons. The UI displays backend responses and does not activate models from the cycle page. Cycle detail shows `model_activation_unchanged`, config hash, input fingerprint, stale-window status, data-quality status, artifacts, warnings, and export metadata without showing unsafe local paths.

## Scheduler Preparation

Phase 13 can queue `research_cycle_dry_run` and `research_cycle_run` jobs from `/operations/scheduler` or the scheduler API. These jobs are synchronous, bounded, operator-triggered, and persisted with events. A scheduler-run cycle still records `model_activation_unchanged=true`; it can create evidence and proposals, but approval and activation remain separate manual actions.

Scheduler payloads default to `refresh_data=false`. If any nested payload asks for `refresh_data=true` and `FMP_API_KEY` is missing, the job becomes `BLOCKED` before any provider request is attempted.
