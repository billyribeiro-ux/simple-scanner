# Operator Daily Procedure

Status date: 2026-07-02

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
4. If stale windows block the cycle, rebuild data/features/labels/replay artifacts or explicitly decide whether `allow_stale=true` is acceptable.
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

The 2026-07-03 live FMP attempt was blocked because `FMP_API_KEY` was missing from the runtime shell. Treat provider readiness as blocked until a runtime key is configured, smoke passes, required endpoints are reviewed accessible, and a bounded live seed succeeds.
