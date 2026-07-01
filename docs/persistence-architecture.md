# Persistence Architecture

Status date: 2026-07-01

## Summary

Phase 3 replaces API route `_MEMORY` workflow state with repository-backed persistence. The local-first API runtime now uses a durable SQLite repository at `data/local_repo.sqlite3` when no PostgreSQL URL is configured. PostgreSQL/TimescaleDB remains the intended production database target, and the SQLAlchemy metadata plus Alembic migration have been aligned to the same table contract.

This is still a scanner, research, validation, backtest, model metadata, signal, and export platform. It is not a broker, not an order router, and not a profitability engine.

## Runtime Stores

- Local API fallback: `data/local_repo.sqlite3`, ignored by git along with SQLite WAL sidecars.
- Production target: PostgreSQL/TimescaleDB through Alembic.
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

The implementation is synchronous and transaction-scoped for local SQLite. API routes may call it directly because the local workload is small and file-backed; async network I/O remains isolated in FMP provider calls.

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
4. Activation writes `active_models` and updates the model run active flag.

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

- SQLite is the local fallback, not the final production persistence engine.
- Alembic migrations were not run because the target Python `3.14.6` backend venv is missing.
- No FMP live ingestion/scanner request was executed because `FMP_API_KEY` is not set in the shell.
- No broker execution, order routing, WebSocket entitlement path, options, gamma, Greeks, or internals were added.
