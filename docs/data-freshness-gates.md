# Data Freshness Gates

Phase 16 persists data freshness reports from local data only. The report combines:

- latest bars by symbol and interval;
- latest durable quote snapshots;
- dirty pipeline windows from bar upserts;
- operator-reviewed FMP capability readiness;
- missing/stale items and recommendations.

## Run A Freshness Check

```bash
curl -s -X POST http://localhost:8000/data/freshness/check \
  -H 'content-type: application/json' \
  -d '{"symbols":["SPY","AAPL"],"intervals":["1day","1min","5min","15min"],"persist":true}'
```

Read the latest persisted report:

```bash
curl -s http://localhost:8000/data/freshness/latest
```

Default thresholds:

- `1min`: 30 minutes
- `5min`: 90 minutes
- `15min`: 180 minutes
- `1day`: 2880 minutes
- quotes: 900 seconds

## Research Cycle Behavior

Research cycle planning now includes a freshness report. Research cycles use the cycle end timestamp as the freshness age reference so historical clean windows are not treated as stale merely because wall-clock time has advanced. Operator/API freshness checks use current time. If the report is `BLOCKED` or `STALE`, research cycles block by default. Setting `allow_stale=true` allows the cycle to proceed with explicit warnings such as `allow_stale_data_freshness_stale`.

Quote freshness is not mandatory for research cycles unless the cycle config sets `require_quote_freshness=true`. Capability-review freshness gating is opt-in for research cycles through `require_reviewed_capabilities_for_research=true`.

## Scheduler

`data_freshness_check` runs without `FMP_API_KEY` because it reads persisted local data.

```bash
curl -s -X POST http://localhost:8000/scheduler/jobs \
  -H 'content-type: application/json' \
  -d '{"job_type":"data_freshness_check","payload":{"symbols":["SPY"],"intervals":["1min"],"persist":true}}'
```

A `BLOCKED` freshness result makes the scheduler job terminal status `BLOCKED`; this is intentional operator feedback, not an execution failure.

## Phase 17 Operator Result

On 2026-07-03, `FMP_API_KEY` was missing and no live seed ran. A local freshness check persisted `BLOCKED` with warnings for missing required data and capability review not ready. This verifies the local gate path, not real-data freshness.

Real-data freshness, real incremental duplicate avoidance, and real-data research-cycle freshness behavior remain unverified until bounded live seed succeeds.
