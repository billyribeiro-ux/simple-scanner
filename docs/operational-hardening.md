# Operational Hardening

Status date: 2026-07-01

## Scope

Phase 13 hardens replay-aware model selection operations with a target frontend runtime check, a thin operator UI, a complete local runbook, Docker/Postgres recovery documentation, and a bounded non-autonomous scheduler for research preparation. It does not add broker execution, order routing, options data, market internals, WebSockets, calibrated ML, self-learning behavior, automatic model deployment, or profitability claims.

## Frontend Runtime

Target frontend acceptance requires Node `24.18.0` and pnpm `11.9.0`.

```bash
source "$HOME/.nvm/nvm.sh"
nvm use 24.18.0
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack prepare pnpm@11.9.0 --activate
make frontend-doctor
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm check
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm build
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm test
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm lint
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm --filter @amd/web test:e2e
```

Root package scripts and Playwright web-server startup call `corepack pnpm` internally so nested commands stay on the pinned package manager.

## Operator UI Guardrails

- `/operations` and `/research/status` are read-only status surfaces.
- `/operations/scheduler` and `/operations/scheduler/{job_id}` expose bounded queue controls only.
- `/research/cycles` creates/dry-runs/runs governance cycles but does not activate models.
- `/research/proposals/{proposal_id}` keeps approval and activation separate.
- The activation button is disabled until proposal status is `APPROVED_FOR_ACTIVATION`, the operator checks an explicit confirmation box, and the phrase `ACTIVATE SCANNER MODEL` is typed.
- Frontend calls use `PUBLIC_API_BASE_URL` as the only public API override and never require provider or database secrets.

## Database Revision

Postgres/Timescale targets Alembic revision:

```text
0009_phase13_scheduler
```

`make db-inspect` expects the Phase 13 table set, replay sensitivity/comparison indexes, replay-aware evidence/score-audit indexes, calibration/drift/window/review/research-governance indexes, scheduler indexes, JSON columns, and `bars` as a Timescale hypertable when the extension is available.

Expected verified result after migration:

```text
alembic_version=0009_phase13_scheduler
missing_tables=none
missing_indexes=none
missing_constraints=none
missing_columns=none
missing_json_columns=none
extensions=plpgsql,timescaledb
timescale_hypertables=bars
```

## Phase 10 Tables

- `replay_sensitivity_runs`
- `replay_sensitivity_scenarios`
- `backtest_comparisons`
- `model_evidence_cells`
- `candidate_score_audits`
- `model_calibration_audits`
- `model_calibration_bins`
- `model_comparisons`
- `replay_window_sets`
- `replay_window_results`
- `model_calibration_drift_reports`
- `model_calibration_drift_windows`
- `model_review_reports`

The existing `replay_runs` table also stores audit fields such as `config_hash`, `input_fingerprint`, `candidate_fingerprint`, and `stale_window_status_json`.

## Phase 11 Tables

- `research_cycles`
- `research_cycle_artifacts`
- `champion_challenger_comparisons`
- `model_proposals`
- `model_decision_ledger`

Research cycles are diagnostic governance records. They persist status transitions, stale/data-quality state, explicit evidence IDs, config hash, input fingerprint, database revision, backend, warnings, and non-secret provenance.

Model proposals separate approval from activation. Approval writes proposal and ledger state only. Activation requires a separate explicit request with `confirm_manual_activation=true` and the existing validation guard. Rejected, blocking, keep-champion, reject-challenger, and block-all-changes proposals cannot activate.

## Phase 13 Tables

- `scheduler_jobs`
- `scheduler_job_events`

Scheduler jobs persist queue status, payloads, results, warnings, optional research cycle IDs, failed reasons, and timestamps. Scheduler events persist job lifecycle audit records. Both stores redact secret-like fields and never hold FMP keys or database credentials.

The scheduler default pending-run bound is `3` jobs and the hard cap is `10` jobs per request. There is no uncontrolled background daemon, no infinite loop, and no auto-run toggle.

## Diagnostics

Use:

```bash
make db-diagnostics
make db-query-diagnostics
```

These run `scripts/db_query_diagnostics.py` and print non-secret row counts, dirty-window counts, recent replay hashes, replay window sets, calibration drift reports, model review reports, research cycles, model proposals, decision-ledger rows, scheduler jobs, and Timescale hypertable status. The script assembles the local development database URL from component environment values instead of storing a literal password-shaped URL.

## Exports

Export records now include:

- `file_sha256`
- `workbook_sheets` for XLSX outputs
- row count
- source run ID
- source simulation type when available
- config hash and input fingerprint when available
- filters and warnings

Replay sensitivity exports:

- `POST /exports/sensitivity-summary.xlsx`
- `POST /exports/sensitivity-scenarios.csv`
- `POST /exports/sensitivity-scenarios.xlsx`
- `POST /exports/sensitivity-metrics.json`

The sensitivity summary workbook includes `Summary`, `Scenario Metrics`, `Worst Case`, `Median Case`, `Best Case`, `Fragility Flags`, `Gate Results`, `Config`, and `Warnings`.

Phase 11 exports:

- `POST /exports/research-cycle.xlsx`
- `POST /exports/research-cycle.json`
- `POST /exports/model-proposal.xlsx`
- `POST /exports/model-proposal.json`
- `POST /exports/champion-challenger-comparison.xlsx`

All Phase 11 exports read persisted source IDs, write to ignored export paths, persist export metadata with `file_sha256`, and must contain no secrets.

Phase 13 operator export:

- `export_operations_status` scheduler job writes operator status JSON and records export metadata with `file_sha256`.

Scheduler jobs CSV/XLSX and operator status XLSX are deferred until the queue shape stabilizes.

Replay-aware exports:

- `POST /exports/replay-aware-model-summary.xlsx`
- `POST /exports/evidence-cells.csv`
- `POST /exports/evidence-cells.xlsx`
- `POST /exports/score-audits.csv`
- `POST /exports/score-audits.xlsx`
- `POST /exports/replay-aware-validation.xlsx`

Phase 10 exports:

- `POST /exports/replay-window-set.xlsx`
- `POST /exports/calibration-drift.xlsx`
- `POST /exports/calibration-drift.json`
- `POST /exports/calibration-drift-windows.csv`
- `POST /exports/calibration-drift-windows.xlsx`
- `POST /exports/model-review.xlsx`
- `POST /exports/model-review.json`

Model evidence cells, score audits, and exports must contain no FMP keys, database passwords, or raw secret-bearing environment values.

## Remaining Operational Limits

- Timescale compression and retention policies are not enabled yet.
- FMP live entitlement remains unverified unless `FMP_API_KEY` is configured outside the repo and `make fmp-smoke` is run.
- Replay still uses OHLCV assumptions, not order book or queue simulation.
