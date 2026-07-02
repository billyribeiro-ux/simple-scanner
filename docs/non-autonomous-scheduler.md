# Non-Autonomous Scheduler

Status date: 2026-07-01

The Phase 13 scheduler is a bounded local queue for research-cycle preparation only. It is not an autonomous learning loop, not a trading system, and not a model deployment system.

## Supported Jobs

- `data_quality_report`
- `research_cycle_dry_run`
- `research_cycle_run`
- `export_research_cycle`
- `export_operations_status`

## Job Statuses

- `QUEUED`
- `RUNNING`
- `COMPLETED`
- `FAILED`
- `CANCELLED`
- `BLOCKED`

## Persistence

Jobs persist in `scheduler_jobs`. Events persist in `scheduler_job_events`.

Every job stores:

- non-secret payload;
- result;
- warnings;
- research cycle ID when available;
- status timestamps;
- failure or block reason when applicable.

Every job event stores:

- event ID;
- job ID;
- event type;
- message;
- non-secret metadata;
- created timestamp.

## API

```bash
POST /scheduler/jobs
GET /scheduler/jobs
GET /scheduler/jobs/{job_id}
POST /scheduler/jobs/{job_id}/run
POST /scheduler/jobs/run-pending
POST /scheduler/jobs/{job_id}/cancel
GET /scheduler/jobs/{job_id}/events
GET /operations/scheduler-status
```

`run-pending` is bounded. The default is `3` jobs and the hard cap is `10` jobs per request.

## Guardrails

The scheduler never:

- approves proposals;
- rejects proposals;
- activates proposals;
- calls model activation;
- changes the scanner active model;
- routes orders;
- places trades;
- connects to brokers;
- starts an uncontrolled background daemon;
- runs an infinite loop;
- stores secrets in payloads, results, events, or status responses.

If a job requests `refresh_data=true` and `FMP_API_KEY` is missing, the job becomes `BLOCKED` with `fmp_api_key_required_for_refresh_data`. No provider request is attempted.

## UI

- `/operations/scheduler` lists jobs, queue counts, latest events, create-job controls, run-pending control, and safe run/cancel controls.
- `/operations/scheduler/{job_id}` shows job payload, result, warnings, and events.
- `/operations` includes a compact scheduler queue card.

There is no auto-run toggle and no activation control in scheduler UI.

## Exports

`export_operations_status` writes a JSON operator-status export and records metadata in the existing `exports` table with `file_sha256`. Scheduler jobs XLSX and operator-status XLSX are deferred until the queue shape stabilizes.
