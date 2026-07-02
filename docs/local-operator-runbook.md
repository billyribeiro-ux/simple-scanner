# Local Operator Runbook

Status date: 2026-07-02

Adaptive Market Decoder is a local-first scanner and research platform. It does not route orders, place trades, connect to brokers, automatically approve proposals, automatically activate scanner models, call itself self-learning, or claim profitability.

## Prerequisites

- Node `24.18.0` through NVM.
- pnpm `11.9.0` through Corepack. This is the project pin used after the July 1, 2026 runtime update.
- Python `3.14.6`.
- Backend virtual environment at `services/quant-engine/.venv`.
- Docker Desktop or a reachable Docker daemon.
- Postgres/TimescaleDB on `localhost:15432`.
- Redis on `localhost:6379`.
- Optional `FMP_API_KEY` in the shell or ignored env files only.

## First-Time Setup

```bash
cp .env.example .env.local
source "$HOME/.nvm/nvm.sh"
nvm use 24.18.0
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack prepare pnpm@11.9.0 --activate
make frontend-doctor
make doctor
make setup-backend
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm install --frozen-lockfile
```

Do not put `FMP_API_KEY`, database passwords, or other secrets in tracked files.

## Database Setup

```bash
docker context ls
docker info
docker compose config
make db-up
docker compose ps
make db-migrate
make db-inspect
make db-query-diagnostics
```

Expected local Postgres host port: `15432`.

If Docker is unavailable, use SQLite-local tests and follow `docs/docker-postgres-troubleshooting.md`.

## Start Services

Backend:

```bash
make api-dev
```

Frontend:

```bash
source "$HOME/.nvm/nvm.sh"
nvm use 24.18.0
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack prepare pnpm@11.9.0 --activate
make web-dev
```

Both with database services:

```bash
make dev
```

Open `http://localhost:5173`.

## Operator UI

- `/operations`: health, persistence, research status, and scheduler summary.
- `/operations/scheduler`: bounded scheduler queue and run controls.
- `/operations/scheduler/{job_id}`: job payload, result, warnings, and events.
- `/research/cycles`: create, dry-run, run, and export controlled research cycles.
- `/research/proposals`: review proposals.
- `/research/proposals/{proposal_id}`: approve, reject, or explicitly activate an approved scanner model.
- `/research/decision-ledger`: inspect append-only governance events.

## Daily Operator Flow

1. Open `/operations`.
2. Confirm backend health, persistence backend, stale windows, data quality, proposal queue, and scheduler queue.
3. Open `/operations/scheduler`.
4. Create a `data_quality_report` job or `research_cycle_dry_run` job.
5. Run one queued job or run a bounded pending batch.
6. Review job detail and events.
7. Open `/research/cycles` and inspect created/dry-run cycles.
8. Run a controlled research cycle only when stale/data-quality warnings are acceptable.
9. Review cycle artifacts and proposal evidence.
10. Approve or reject the proposal manually.
11. Activate only from the proposal detail page when appropriate, after approval, explicit checkbox, and typed confirmation phrase.
12. Confirm the decision ledger event.

## Scheduler Commands

```bash
make scheduler-test
make scheduler-status
make scheduler-worker-once
make scheduler-recover-stale
```

Example create job:

```bash
curl -s -X POST http://localhost:8000/scheduler/jobs \
  -H 'content-type: application/json' \
  -d '{"job_type":"data_quality_report","payload":{"symbols":["AAPL","SPY"],"intervals":["1min"]},"created_by":"operator"}'
```

Example bounded run:

```bash
curl -s -X POST http://localhost:8000/scheduler/jobs/run-pending \
  -H 'content-type: application/json' \
  -d '{"max_jobs":3}'
```

Scheduler jobs never approve proposals, activate models, route orders, place trades, or call broker/order routes.

Example one-shot worker run:

```bash
make scheduler-worker-once
```

This leases a bounded number of queued jobs, runs them, releases leases, and exits. Use `make scheduler-recover-stale` to recover expired leases once without leasing new work.

## Recovery Procedures

- Docker socket unavailable: start Docker Desktop, verify `docker context ls`, switch to a valid context if needed, then rerun `docker info`.
- Postgres refuses connection: run `make db-up`, inspect `docker compose ps`, confirm port `15432`, then rerun `nc -zv localhost 15432`.
- Migration fails: keep the error, run `docker compose ps`, then rerun `make db-migrate` after Postgres is healthy.
- Frontend Node mismatch: source NVM and run `nvm use 24.18.0`.
- Backend venv missing: install Python `3.14.6`, then run `make setup-backend`.
- FMP key missing: live FMP smoke and `refresh_data=true` jobs remain blocked until `FMP_API_KEY` is configured outside tracked files.
- Stale windows block a cycle: dry-run first, rebuild the stale artifacts, or run only with explicit `allow_stale=true`.

## Safety Boundaries

- No broker execution.
- No order routing.
- No automatic model activation.
- No automatic scanner model deployment.
- No proposal approval bypass.
- No `confirm_manual_activation=true` bypass.
- No secrets in scheduler payloads, events, status, exports, logs, or frontend bundles.
