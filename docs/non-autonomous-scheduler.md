# Non-Autonomous Scheduler

Status date: 2026-07-02

The scheduler is a bounded local queue for research-cycle preparation only. Phase 14 adds persisted leases and a one-shot local worker command for request-bound job hardening. It is not an autonomous learning loop, not a trading system, and not a model deployment system.

## Supported Jobs

- `data_quality_report`
- `research_cycle_dry_run`
- `research_cycle_run`
- `export_research_cycle`
- `export_operations_status`
- `rebuild_features`
- `rebuild_candidates`
- `rebuild_labels`
- `run_replay`

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
- lease owner, lease expiry, heartbeat, attempt count, timeout, and last non-secret error for the one-shot worker path;
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

## One-Shot Worker

```bash
make scheduler-worker-once
make scheduler-recover-stale
```

`make scheduler-worker-once` leases at most a bounded batch, records a heartbeat, runs those jobs, releases the leases after terminal status, and exits. `make scheduler-recover-stale` recovers expired leases once without leasing new work. Neither command starts a background daemon, cron, infinite loop, or self-scheduling process.

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

## Phase 15 FMP Jobs

Allowed FMP job types are `fmp_capability_check`, `fmp_quote_snapshot`, `fmp_eod_refresh`, `fmp_intraday_refresh`, and `fmp_incremental_intraday_refresh`.

FMP jobs require `FMP_API_KEY`; if it is missing, the job becomes `BLOCKED` with `fmp_api_key_required`. Jobs are bounded to 10 symbols, `1min/5min/15min` intraday intervals, and a conservative five-day intraday span. They persist provider request IDs and ingestion run IDs only. They never approve proposals, activate models, route orders, or place trades.

## Phase 16 FMP Jobs

`fmp_seed_ingestion` supports dry-run without a key and live seed with key/review gates. `data_freshness_check` reads local persisted data and can run without a key. Both jobs are operator-queued, bounded, and never activate models.

## Phase 17 Scheduler Result

The 2026-07-03 Phase 17 run did not execute live FMP scheduler jobs because `FMP_API_KEY` was missing. General scheduler status, one-shot worker, and stale recovery commands passed with zero queued, running, or recovered jobs. Live FMP scheduler verification remains blocked until the runtime key is present and endpoint reviews are ready.

## Phase 19 Artifact Readiness Jobs

Phase 19 added local-only rebuild jobs:

- `rebuild_features`: builds persisted features from persisted bars.
- `rebuild_candidates`: builds persisted candidates from persisted features.
- `rebuild_labels`: builds labels from persisted bars, features, and candidates.
- `run_replay`: runs candidate market replay for intraday intervals, or marks `1day` replay windows as not applicable.

These jobs do not call FMP, require no API key, store no secrets, activate no model, and route no orders. The final Phase 19 run used the same bounded behavior and left dirty windows at 0.

## Phase 19A Audit Result

On 2026-07-04, `make scheduler-test`, `make scheduler-status`, `make scheduler-worker-once`, and `make scheduler-recover-stale` passed against a fresh SQLite runtime with zero queued jobs. This verifies scheduler code behavior, but not the original July 3 Phase 19 scheduler/runtime evidence. Phase 19 remains `EVIDENCE_PENDING` until runtime artifacts are recovered or regenerated.
## Phase 19C Scheduler Note - 2026-07-04

Scheduler and research jobs remain non-autonomous. Phase 19C did not add automatic model activation or execution. Strict research dry-run evidence is blocked by data freshness, and scheduler-driven ingestion still requires an operator-provided FMP key plus reviewed capabilities.
