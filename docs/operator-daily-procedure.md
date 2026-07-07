# Operator Daily Procedure

Status date: 2026-07-03

This procedure prepares and reviews research artifacts. It does not create trading authority, route orders, or automatically activate models.

## Start Of Day

```bash
source "$HOME/.nvm/nvm.sh"
nvm use 24.18.0
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack prepare pnpm@11.9.0 --activate
make doctor
make scheduler-status
make scheduler-recover-stale
```

If Docker is healthy:

```bash
make db-up
make db-migrate
make db-inspect
make db-query-diagnostics
```

Start the app:

```bash
make api-dev
make web-dev
```

Open `http://localhost:5173`.

## Review Operations

1. Open `/operations`.
2. Check backend status, persistence backend, active model, data quality, stale windows, proposal queue, and scheduler queue.
3. Open `/operations/scheduler`.
4. Create a `data_quality_report` job for the active symbol universe.
5. Run the queued job through the UI/API, or use `make scheduler-worker-once` when a bounded local worker path is preferred.
6. Inspect job events and confirm leases are cleared after terminal status.

## Prepare A Research Cycle

1. Create a `research_cycle_dry_run` job.
2. Run the job.
3. If the job is `BLOCKED`, inspect the reason and warnings.
4. If stale windows block the cycle, run the live-data artifact-readiness audit and rebuild sequence before considering any diagnostic `allow_stale=true` run.
5. If `refresh_data=true` blocks because `FMP_API_KEY` is missing, either configure the key outside tracked files or rerun without refresh.

## Run A Controlled Cycle

1. Create or select a research cycle.
2. Run the cycle manually from `/research/cycles` or through a queued `research_cycle_run` job.
3. Verify the cycle summary includes `model_activation_unchanged=true`.
4. Review artifacts, comparison, proposal, and warnings.

## Proposal Review

1. Open `/research/proposals/{proposal_id}`.
2. Review evidence, readiness, gates, rejection reasons, and decision-ledger rows.
3. Approve or reject manually.
4. Approval does not activate a model.

## Explicit Activation

Only use the proposal detail page. Activation requires:

- proposal status `APPROVED_FOR_ACTIVATION`;
- explicit checkbox;
- typed phrase `ACTIVATE SCANNER MODEL`;
- backend activation guard success.

The scheduler cannot perform this action.

## End Of Day

1. Export relevant cycle/proposal reports.
2. Export operator status through `export_operations_status` if desired.
3. Review `/research/decision-ledger`.
4. Confirm no unexpected failed or blocked scheduler jobs remain.

## Failure Handling

- Docker unavailable: follow `docs/docker-postgres-troubleshooting.md`.
- Postgres unavailable: keep SQLite tests green and do not claim Postgres verification.
- FMP key missing: live FMP smoke and refresh jobs remain gated.
- Scheduler job failed: inspect `/operations/scheduler/{job_id}` events and `failed_reason`.
- Scheduler job stuck in `RUNNING`: run `make scheduler-recover-stale`, then inspect events before retrying.
- Proposal activation blocked: keep the backend response; do not bypass confirmation or validation gates.

## Phase 15 FMP Data Check

1. Open `/operations/provider`.
2. Confirm key status is present or accept the missing-key skip state.
3. Run a capability check before live ingestion.
4. Run EOD or intraday refresh with bounded symbols/date ranges.
5. Open `/operations/data`.
6. Confirm latest bars, provider request summary, dirty windows, and warnings.
7. Rebuild features only after data-quality warnings are understood.

## Phase 16 Daily Freshness Check

Confirm `/operations/provider` review readiness and `/operations/data` freshness status. Run seed dry-run before live seed. Do not run research cycles on `BLOCKED` or `STALE` freshness unless `allow_stale=true` is an intentional operator decision.

## Phase 17 Daily FMP Status

The first 2026-07-03 live FMP attempt was blocked because `FMP_API_KEY` was missing from the runtime shell. That is historical Phase 17 context; Phase 18 superseded it with a runtime-key success path.

## Phase 18 Daily FMP Status

The 2026-07-03 runtime-key FMP rerun passed live entitlement and seed ingestion. Treat provider readiness as `READY` only after rerunning the capability check and confirming all required rows are reviewed accessible.

Current local data state after Phase 18:

- Live FMP seed exists.
- Freshness is `STALE`.
- Dirty pipeline windows remain.
- Research cycles should block by default unless `allow_stale=true` is an explicit diagnostic decision.

Daily next step: run freshness first, rebuild stale artifacts where needed, then run research dry-runs before any full controlled cycle.

## Phase 19 Daily Artifact Readiness

After any FMP seed or incremental refresh, run:

```bash
curl -s 'http://localhost:8000/pipeline/dirty-windows?symbols=AMZN,AAPL,TSLA,SPY,QQQ,IWM,NVDA,GOOGL,BABA,SHOP&intervals=1min,5min,15min,1day&export=true'
```

Then rebuild in order:

1. `POST /pipeline/rebuild/features`
2. `POST /pipeline/rebuild/candidates`
3. `POST /pipeline/rebuild/labels`
4. `POST /pipeline/rebuild/replay`
5. `POST /data/freshness/check`
6. `POST /research/cycles/{research_cycle_id}/dry-run`

Equivalent scheduler jobs are `rebuild_features`, `rebuild_candidates`, `rebuild_labels`, `run_replay`, `data_freshness_check`, and `research_cycle_dry_run`.

Current Phase 19 state:

- Dirty windows: 0.
- Default freshness: `STALE` due wall-clock bar age.
- Research-scope freshness: `READY`.
- Strict research dry run: passed with `allow_stale=false`.

## Phase 19A Daily Audit Note

If this checkout is used after 2026-07-04, do not assume the July 3 runtime evidence is present. Phase 19A found a fresh empty SQLite DB, missing Phase 19 export files, a blocked Postgres migration, and a Redis port conflict. Resolve runtime health and recover or regenerate evidence before treating Phase 19 as certified complete.
## Phase 19C Operator Note - 2026-07-04

Use `make doctor` before any live-data work. The backend venv should report Python `3.14.6`, Redis should report host port `16379` unless explicitly overridden, and Postgres should migrate to `0012_phase16_fmp_freshness`. Phase 19 remains `BLOCKED_NO_DATA` until real bars are restored or FMP seed ingestion runs with an approved key.
