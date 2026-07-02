# Phase 13 Scheduler Status

Status date: 2026-07-01

## Summary

Phase 13 adds a bounded, non-autonomous scheduler for local research preparation. It persists jobs and events, exposes API/UI status, and keeps all model approval and activation guardrails outside the scheduler.

This is not a background daemon, not an autonomous loop, not a broker integration, and not a trading execution path.

## Supported Jobs

- `data_quality_report`
- `research_cycle_dry_run`
- `research_cycle_run`
- `export_research_cycle`
- `export_operations_status`

## Persistence

- Alembic revision: `0009_phase13_scheduler`
- Tables: `scheduler_jobs`, `scheduler_job_events`
- SQLite bootstrap creates both tables and indexes.
- Postgres migration creates both tables and indexes when Docker/Postgres is reachable.
- Existing local SQLite files are compatibility-patched before replay `config_hash` indexes are created, so `make scheduler-status` can run against older local DBs.

## API

- `POST /scheduler/jobs`
- `GET /scheduler/jobs`
- `GET /scheduler/jobs/{job_id}`
- `POST /scheduler/jobs/{job_id}/run`
- `POST /scheduler/jobs/run-pending`
- `POST /scheduler/jobs/{job_id}/cancel`
- `GET /scheduler/jobs/{job_id}/events`
- `GET /operations/scheduler-status`

`run-pending` defaults to `3` jobs and is hard-capped at `10` jobs per request.

## UI

- `/operations` shows scheduler queue summary.
- `/operations/scheduler` lists jobs, queue counts, latest job state, create-job controls, and bounded run-pending controls.
- `/operations/scheduler/{job_id}` shows payload, result, warnings, and events.

The scheduler page gates initial buttons until hydration so Playwright and operators cannot click SSR-rendered controls before handlers are attached.

## FMP Gating

`refresh_data=false` is the default. If any scheduler payload asks for `refresh_data=true` and `FMP_API_KEY` is missing, the job becomes `BLOCKED` with reason `fmp_api_key_required_for_refresh_data`. No provider request is attempted.

## Guardrails

The scheduler never:

- approves proposals;
- rejects proposals;
- activates proposals;
- calls model activation;
- changes the active scanner model;
- connects to brokers;
- routes orders;
- places trades;
- runs an uncontrolled background worker.

## Verification

Passed:

- `make scheduler-test`: 11 passed, 1 warning.
- `make scheduler-status`: printed non-secret SQLite queue status.
- `make backend-test`: 102 passed, 2 skipped, 1 warning.
- `make api-smoke-sqlite`: 1 passed, 1 warning.
- `make api-smoke-postgres`: 1 skipped because Postgres is unreachable.
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm --filter @amd/web test:e2e`: 9 passed.

Postgres migration/inspection remains blocked by Docker socket unavailability.
