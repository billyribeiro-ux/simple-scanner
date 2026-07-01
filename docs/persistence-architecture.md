# Persistence Architecture

Status date: 2026-07-01

## Summary

The API route `_MEMORY` workflow state has been replaced with repository-backed persistence. The local-first API runtime uses SQLite at `data/local_repo.sqlite3` when no database URL is configured, and it uses PostgreSQL/TimescaleDB when `DATABASE_URL` points at a migrated Postgres database. Phase 5 verifies the same persisted API vertical slice against both backends.

This is still a scanner, research, validation, backtest, model metadata, signal, and export platform. It is not a broker, not an order router, and not a profitability engine.

## Runtime Stores

- Local default: `data/local_repo.sqlite3`, ignored by git along with SQLite WAL sidecars.
- Configured SQLite: `sqlite:///...` paths, including `AMD_SQLITE_PATH` for local test/runtime overrides.
- PostgreSQL runtime: sync SQLAlchemy/psycopg repository store against Alembic revision `0002_phase5_indexes` on local host port `15432`.
- Export artifacts: `exports/`, ignored except `.gitkeep`.
- Model artifacts: `model_artifacts/`, ignored except `.gitkeep`.
- FMP secrets: `FMP_API_KEY` from environment or ignored env files only.

## Repository Registry

The repository registry lives in `services/quant-engine/app/db/repositories.py`.

It exposes concrete repositories for:

- `symbols`
- `bars`
- `features`
- `candidate_signals`
- `labels`
- `validation_reports`
- `model_runs`
- `active_models`
- `live_signals`
- `scanner_runs`
- `provider_requests`
- `exports`
- `daily_reviews`

The implementation is synchronous and transaction-scoped for both SQLite and PostgreSQL. API routes call the repository registry directly because the local V1 workload is small; async network I/O remains isolated in FMP provider calls.

`RepositoryRegistry.info()` returns a safe backend descriptor used by `/health`, `/config`, and `make doctor`. It reports backend type, runtime mode, sanitized database URL kind, and local SQLite path without printing connection strings.

Backend selection is explicit:

- no `DATABASE_URL`: SQLite local runtime;
- `sqlite:///...`: SQLite configured runtime;
- Postgres URL: PostgreSQL runtime after schema and revision checks;
- Postgres init failure: hard failure unless `AMD_ALLOW_SQLITE_FALLBACK=true`;
- explicit fallback: SQLite runtime mode `sqlite-fallback-from-postgres` with a non-secret reason.

## API Source Of Truth

`services/quant-engine/app/api/routes.py` no longer keeps route-level `_MEMORY` state. Current conversions:

- `/data/ingest` writes bars and provider request accounting.
- `/data/bars` reads persisted bars.
- `/features/build` reads persisted bars and writes persisted features.
- `/labels/build` reads bars/features and writes candidate signals plus labels.
- `/models/train` reads persisted labels/features and writes model runs/artifact metadata.
- `/models/validate` writes validation reports.
- `/models/activate` requires an accepted persisted validation report before activating.
- `/backtest/run` reads persisted labels and writes a persisted report with purpose `backtest`.
- `/signals/live` and `/signals/history` read persisted live signals.
- `/exports/*` read persisted signals and write export metadata.
- `/review/daily` reads persisted signals and writes daily review payloads.

SSE streaming still uses an in-process queue because it is transient delivery plumbing, not the durable source of truth.

## Scanner Persistence

The live scanner now:

- creates a persisted scanner run on start;
- loads an active model from `active_models` before falling back to model artifacts;
- checks persisted `1min` bars for context before requesting FMP historical bars;
- persists fetched context bars during a real scanner run;
- persists each scored signal to `live_signals`;
- records FMP quote and historical-bar provider requests without logging secrets.

Direct unit scoring through `ScannerState.score_quote` remains deterministic and does not use persisted context unless a scanner run is active.

## Activation Guard

Model activation is repository-gated:

1. A model run must exist.
2. A validation report for that model version must exist.
3. The latest validation report must have `activation_decision = accepted`.
4. Activation writes `active_models` and updates the model run active flag and stored model payloads.

Training metrics alone do not silently activate a model.

## Tables

The aligned table set is:

- `symbols`
- `bars`
- `features`
- `candidate_signals`
- `labels`
- `validation_reports`
- `validation_windows`
- `model_runs`
- `model_artifacts`
- `active_models`
- `live_signals`
- `closed_signals`
- `scanner_runs`
- `provider_requests`
- `exports`
- `daily_reviews`

## Current Limits

- Postgres is implemented for the repository contract, but heavy query planning and Timescale hypertable policy tuning remain future work.
- SQLite remains the local default for no-configuration development.
- No live FMP smoke was executed because `FMP_API_KEY` is not loaded in the process environment or ignored env files.
- No broker execution, order routing, WebSocket entitlement path, options, gamma, Greeks, or internals were added.
