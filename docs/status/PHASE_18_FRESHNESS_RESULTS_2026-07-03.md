# Phase 18 Freshness Results

Status date: 2026-07-03

## Result

Real FMP data exists locally, but freshness is not `READY`. The latest relevant reports are `STALE` because required bars are stale relative to strict wall-clock thresholds and pipeline build windows remain dirty after real bar upserts.

This is an expected safety gate, not a failed provider entitlement result.

## Default Universe Freshness

After endpoint review was restored to `READY`, a default-universe freshness check persisted:

- Freshness report: `freshness_6433ebca9abebe945f9d2ede6ad3a685`
- Status: `STALE`
- Missing required data: 0
- Stale required data groups: 40
- Dirty windows: 400
- Warnings: `freshness_dirty_pipeline_windows`, `freshness_stale_required_data`
- Recommendations: 3

## Research-Cycle Freshness

The controlled research-cycle gate over `SPY,QQQ,AAPL,NVDA` and `1min,5min,15min` persisted a narrower latest freshness report:

- Freshness report: `freshness_58830eb27b2e92978aebd9bd0b8a2344`
- Status: `STALE`
- Missing required data: 0
- Stale required data groups: 12
- Dirty windows: 160
- Warnings: `freshness_dirty_pipeline_windows`, `freshness_stale_required_data`

Research-cycle behavior:

- Research cycle: `research_cycle_032e2882c97523fdfc28d9821afa8162`
- Dry-run status: `dry_run`
- Dry-run blocked: true
- Dry-run block reason: `stale_artifacts_present`
- Default run status: `blocked`
- Default run block reason: `stale_artifacts_present`
- `allow_stale=true` run status: `completed`
- `allow_stale=true` summary: `model_activation_unchanged=true`, `proposal_status=REVIEW_REQUIRED`, `recommended_action=BLOCK_ALL_CHANGES`

`allow_stale=true` completed only as a diagnostic/research artifact path. It did not activate a model and did not create trading authority.

## Scheduler Freshness Evidence

Scheduler jobs exercised the same non-autonomous gates:

| Job type | Job ID | Terminal status | Result status |
| --- | --- | --- | --- |
| `fmp_capability_check` | `scheduler_job_a863e19ed3baa7010dcba4de143239de` | `COMPLETED` | `ok` |
| `fmp_seed_ingestion` dry-run | `scheduler_job_7c8a70368b1bd8fec7c0cf2149331668` | `COMPLETED` | `dry_run` |
| `fmp_seed_ingestion` live | `scheduler_job_dd5ac4a53835950a1e76ec25332e6a03` | `COMPLETED` | `COMPLETED` |
| `data_freshness_check` | `scheduler_job_68db749f588e496dcdea4d9469ccbe58` | `COMPLETED` | `STALE` |
| `fmp_incremental_intraday_refresh` | `scheduler_job_b86e112a8c5d3c51752f6c93a09bc9f6` | `COMPLETED` | `COMPLETED` |

The scheduler did not approve proposals, activate models, route orders, or place trades.
