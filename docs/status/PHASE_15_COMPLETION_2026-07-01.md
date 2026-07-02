# Phase 15 Completion

Status date: 2026-07-01

## What Changed

Phase 15 adds safe live FMP entitlement verification, header-only REST client hardening, persisted capability checks, persisted ingestion runs, bounded quote/EOD/intraday ingestion, provider/source data-quality coverage, scheduler FMP jobs, operator UI pages, exports, and tests.

## FMP Key Status

The system reports only present/missing. Live entitlement is unknown until `FMP_API_KEY` is present and a smoke or capability check is run.

## Endpoint Matrix

Configured endpoint keys: `quote`, `quote_short`, `batch_quote`, `batch_quote_short`, `historical_eod_full`, `intraday_1min`, `intraday_5min`, `intraday_15min`. Optional keys: `intraday_30min`, `intraday_1hour`, `intraday_4hour`, `websocket_us_stocks_probe`.

Runtime accessibility in this shell: `UNKNOWN/SKIPPED_NO_KEY` because `FMP_API_KEY` is not configured. Mocked entitlement tests cover accessible, skipped, ingestion, export, route, and scheduler-blocked paths without a real key.

## REST Client Status

The client uses `apikey` header auth only, strips query-string API keys, captures request IDs, latency, HTTP status, response shape, sample count, and safe error classes.

## Ingestion Status

FMP quote snapshot, EOD bars, intraday bars, and incremental intraday refresh are implemented with bounded symbols/date ranges and persisted ingestion run summaries.

## Scheduler Status

Allowed FMP scheduler jobs block with `fmp_api_key_required` when the runtime key is missing and do not activate models or call broker/order paths.

## Data Quality Status

`GET /data/quality-report` now includes source breakdown, latest bars, provider request summary, ingestion run summary, and provider capability warnings.

## UI Status

Added `/operations/provider`, `/operations/data`, and an FMP provider card on `/operations`.

## WebSocket Probe Status

Disabled by default. Phase 15 adds only an optional entitlement probe path gated by `AMD_ENABLE_FMP_WS_PROBE=true` and `FMP_API_KEY`; no production WebSocket ingestion or tick persistence was added.

## SQLite/Postgres Status

SQLite bootstrap, SQLAlchemy schema, Alembic revision `0011_phase15_fmp_provider`, db inspection expectations, and repository parity tests include `provider_capability_checks` and `ingestion_runs`.

## Tests Added

`tests/quant/test_phase15_fmp_provider.py` covers header auth, no-key capability persistence, ingestion idempotency, exports, scheduler blocking, API routes, and data quality coverage. Playwright smoke covers provider/data pages.

## Commands Run

Passed:

- `source "$HOME/.nvm/nvm.sh" && nvm use 24.18.0 && node --version`
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm --version`
- `make frontend-doctor`
- `make help`
- `source "$HOME/.nvm/nvm.sh" && nvm use 24.18.0 && make doctor`
- `make setup-backend`
- `docker compose config`
- `docker compose up -d postgres redis`
- `docker compose ps`
- `make db-migrate`
- `make db-inspect`
- `make db-query-diagnostics`
- `make quant-test`
- `make backend-test`
- `make backend-lint`
- `make backend-typecheck`
- `make api-smoke`
- `make api-smoke-sqlite`
- `make api-smoke-postgres`
- `make repository-parity-test`
- `make replay-test`
- `make replay-sensitivity-test`
- `make replay-window-test`
- `make model-review-test`
- `make research-cycle-test`
- `make research-status-test`
- `make scheduler-test`
- `make scheduler-status`
- `make scheduler-worker-once`
- `make scheduler-recover-stale`
- `make export-test`
- `make fmp-entitlement-test`
- `make fmp-ingestion-test`
- `make data-quality-test`
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm install --frozen-lockfile`
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm check`
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm build`
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm test`
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm lint`
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm --filter @amd/web test:e2e`
- `python3 -m compileall services/quant-engine/app services/quant-engine/tests`
- `git diff --check`
- secret scans over source and generated frontend output for runtime-key values, assigned secrets, and keyed URL patterns

Skipped:

- `make fmp-smoke` and `make fmp-live-smoke` because `FMP_API_KEY` is missing in this shell.

Fixed during verification:

- Shortened Alembic revision id to `0011_phase15_fmp_provider` because the first id exceeded the deployed Alembic version column length.
- Tightened a Playwright text locator that matched both intro copy and the `Latest bars` heading.

## Blockers

No implementation blockers remain. Live FMP endpoint entitlement cannot be claimed until a runtime-only `FMP_API_KEY` is configured and the smoke/capability checks are run.

## Remaining Risks

Live entitlement cannot be claimed without running the smoke with `FMP_API_KEY` present. Missing-window estimates remain interval-gap based and not exchange-calendar-perfect.

## Next Phase

Phase 16 should add operator-reviewed live entitlement results, deeper data freshness alerts, and optional quote table persistence if V1 needs durable quote snapshots.
