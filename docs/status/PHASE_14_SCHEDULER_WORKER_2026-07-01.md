# Phase 14 Scheduler Worker - 2026-07-01

Status date: 2026-07-02
Result: IMPLEMENTED AND VERIFIED

## Summary

Phase 14 adds a bounded one-shot local scheduler worker path for jobs that should not depend on a long request lifecycle. It keeps the scheduler non-autonomous: an operator must explicitly run the command, it processes a bounded batch, and it exits.

## Schema

Alembic revision `0010_phase14_scheduler_worker` adds these `scheduler_jobs` columns:

- `lease_owner`
- `lease_expires_at`
- `heartbeat_at`
- `attempt_count`
- `max_attempts`
- `timeout_seconds`
- `last_error`

Indexes:

- `ix_scheduler_jobs_lease_expires`
- `ix_scheduler_jobs_lease_owner`

## Commands

```bash
make scheduler-worker-once
make scheduler-recover-stale
```

`make scheduler-worker-once` leases at most the bounded job count, records heartbeat events, runs jobs, clears leases after terminal status, records release events, and exits.

`make scheduler-recover-stale` recovers expired leases once without leasing new jobs.

## Events

Worker paths can record:

- `JOB_LEASED`
- `JOB_HEARTBEAT`
- `JOB_RELEASED`
- `JOB_STALE_RECOVERED`

Existing lifecycle events such as `JOB_STARTED`, `JOB_COMPLETED`, `JOB_FAILED`, and `JOB_BLOCKED` remain intact.

## Tests

Passed:

- `make scheduler-test`
- `services/quant-engine/tests/quant/test_phase14_scheduler_worker.py`
- `make scheduler-worker-once`
- `make scheduler-recover-stale`
- `make repository-parity-test`
- `make backend-test`

## Guardrails

The worker does not:

- start a daemon;
- run an infinite loop;
- self-schedule;
- approve proposals;
- reject proposals;
- activate models;
- route orders;
- place trades;
- connect to brokers;
- bypass `FMP_API_KEY` gating for `refresh_data=true`.
