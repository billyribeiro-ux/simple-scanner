# Adaptive Market Decoder Handoff

Report status date: 2026-07-02

## Executive State

Phase 14 restores Docker/Postgres verification and adds bounded scheduler worker leases for request-bound job hardening. Node `24.18.0` remains the target runtime and frontend target-runtime gates use pnpm `11.9.0` through Corepack. Python `3.14.6` is installed, `services/quant-engine/.venv` exists on Python `3.14.6`, Postgres/TimescaleDB and Redis are healthy through Docker Compose, and Alembic now verifies at `0010_phase14_scheduler_worker`.

This remains a local-first scanner, research, validation, backtest, signal, and export platform only. It is not a broker, auto-trader, order router, self-learning system, or profitability system.

## Runtime Pins

- Node target: `24.18.0`
- Package manager: `pnpm@11.9.0` through Corepack
- Python target: `3.14.6`, documented as the latest stable Python release for this project as of June 30, 2026
- Target Node is available through NVM; use `source "$HOME/.nvm/nvm.sh" && nvm use 24.18.0`
- Homebrew Node `25.3.0` exists but is not used for acceptance and currently fails before Corepack because a `simdjson` dynamic library is missing
- Current local Python: `python3.14` and Homebrew `python3` report `3.14.6`
- Backend venv: `services/quant-engine/.venv` on Python `3.14.6`

## Exact Setup Commands

```bash
source "$HOME/.nvm/nvm.sh"
nvm use 24.18.0
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack prepare pnpm@11.9.0 --activate
make frontend-doctor
make help
make doctor
make setup-backend
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm install --frozen-lockfile
make db-up
make db-migrate
make db-inspect
make db-query-diagnostics
```

The local Postgres/Timescale container is mapped to host port `15432` because this machine already has another Postgres on `5432` and another Docker project on `55432`.

## Exact Verification Commands

```bash
make quant-test
make backend-test
make backend-lint
make backend-typecheck
make api-smoke
make api-smoke-sqlite
make api-smoke-postgres
make repository-parity-test
make replay-test
make replay-sensitivity-test
make replay-window-test
make model-review-test
make research-cycle-test
make research-status-test
make scheduler-test
make scheduler-status
make scheduler-worker-once
make scheduler-recover-stale
make export-test
make db-query-diagnostics
make fmp-smoke
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm check
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm build
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm test
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm lint
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm --filter @amd/web test:e2e
python3 -m compileall services/quant-engine/app services/quant-engine/tests
git diff --check
```

`make fmp-smoke` is optional and gated. It skips with a non-secret message when `FMP_API_KEY` is not configured.

## Persistence Contract

The FastAPI repository backend is selected explicitly:

- no `DATABASE_URL`: SQLite local repository at `data/local_repo.sqlite3`, or `AMD_SQLITE_PATH` when set;
- `sqlite:///...`: SQLite repository at the configured path;
- Postgres URL: PostgreSQL repository runtime through sync SQLAlchemy/psycopg against the migrated schema;
- failed Postgres init: hard failure by default;
- `AMD_ALLOW_SQLITE_FALLBACK=true`: explicit SQLite fallback reported as `sqlite-fallback-from-postgres`.

The persisted contract now includes replay audit, sensitivity, replay-aware model-selection, counterfactual calibration, and Phase 10 operational review state:

- `replay_runs`: one row per candidate market replay run with config, filters, simulation type, metrics, warnings, backend, config hash, input fingerprint, candidate fingerprint, and stale-window status.
- `simulated_trades`: one row per taken or skipped candidate, including execution assumptions, entry/exit prices, realized R, MFE/MAE, skip reason, and ambiguity policy.
- `pipeline_build_windows`: dirty/stale metadata for feature, candidate, label, and replay rebuild awareness by artifact, symbol, interval, session date, version, and timestamp range.
- `replay_sensitivity_runs`: sensitivity run summaries, robustness scores, fragility flags, worst/median/best cases, and gate results.
- `replay_sensitivity_scenarios`: scenario-level slippage/spread/intrabar metrics.
- `backtest_comparisons`: persisted label-derived vs replay comparison reports.
- `model_evidence_cells`: replay-aware evidence cube cells with hierarchy level, dimensions, observed counts, shrinkage/backoff metrics, fragility flags, stale warnings, and provenance.
- `candidate_score_audits`: deterministic replay-aware score/audit rows with action, grade, component scores, penalties, evidence keys, warning codes, and suppression reasons.
- `model_calibration_audits` and `model_calibration_bins`: Phase 9 calibration diagnostics for score, grade, and action buckets.
- `model_comparisons`: persisted model comparison artifacts.
- `replay_window_sets` and `replay_window_results`: generated multi-window replay orchestration boundaries, result IDs, metrics, warnings, and status.
- `model_calibration_drift_reports` and `model_calibration_drift_windows`: advisory drift flags, severity, bin drift, stability metrics, and per-window rows.
- `model_review_reports`: advisory readiness reports with validation/calibration/drift/window references and `model_activation_unchanged=true`.
- `research_cycles`: controlled daily/manual/ad-hoc cycle records with config hash, input fingerprint, stale/data-quality state, explicit artifact IDs, summary, warnings, backend, database revision, and git commit when available.
- `research_cycle_artifacts`: cycle-to-evidence references for data quality, replay windows, validation, reviews, comparisons, proposals, and exports.
- `champion_challenger_comparisons`: diagnostic comparison records with gate results, delta metrics, recommended action, readiness, and warnings.
- `model_proposals`: human-review proposal records with approval status, champion/challenger metrics, gates, rejection reasons, approval actor/time, and activation metadata when explicitly activated.
- `model_decision_ledger`: append-only governance events for cycle creation/completion, proposal transitions, activation requests, blocked activations, and explicit activations.
- `scheduler_jobs`: bounded operator-queued research preparation jobs with status, priority, schedule time, payload, result, warnings, failure reason, and optional research cycle ID.
- `scheduler_job_events`: append-only scheduler job events with event type, message, non-secret metadata, and timestamp.
- `scheduler_jobs` Phase 14 worker fields: `lease_owner`, `lease_expires_at`, `heartbeat_at`, `attempt_count`, `max_attempts`, `timeout_seconds`, and `last_error`.

Safe status fields are exposed through `GET /health`, `GET /config`, and `make doctor`: `persistence_backend`, `runtime_mode`, `database_configured`, `database_reachable`, `fallback_enabled`, and `fallback_reason`. Full database URLs, passwords, and API keys are never returned.

## What Is Safe To Trust

- Deterministic quant feature/label/backtest/model baseline tests.
- Repository-backed API route state instead of route-level `_MEMORY`.
- SQLite local API persistence and reinitialization survival for bars, features, labels, replay runs/trades, model runs, active model, scanner runs/signals, exports, and daily reviews.
- Postgres API persistence and reinitialization survival for the same vertical slice after `make db-migrate`.
- Alembic migration and schema inspection expectations now target revision `0010_phase14_scheduler_worker`; local Postgres execution is verified in this shell.
- SQLite/Postgres repository parity for symbols, bars, features, labels, replay runs/trades, sensitivity runs/scenarios, comparisons, pipeline build windows, replay-aware evidence cells, candidate score audits, calibration audits, replay window sets/results, drift reports, model review reports, models, scanner runs, signals, provider requests, exports, and daily reviews.
- CSV/XLSX/JSON export generation from persisted signals, replay runs/trades, replay sensitivity runs, replay-aware model summaries, evidence cells, score audits, replay-aware validation reports, calibration reports, replay window sets, calibration drift reports, model review reports, and daily reviews, with file hashes and workbook sheets recorded.
- CSV/XLSX/JSON export generation for research cycles, model proposals, and champion/challenger comparisons from persisted source IDs, with file hashes and workbook sheet names recorded.
- Approval of a model proposal is separate from activation. Explicit proposal activation requires `confirm_manual_activation=true`, accepted validation, non-blocking readiness, and a proposal recommendation that is eligible for activation.
- The Phase 12 operator UI enforces approval/activation separation with a disabled activation panel until the proposal is approved, the confirmation checkbox is checked, and `ACTIVATE SCANNER MODEL` is typed.
- The scheduler can queue and run data-quality reports, research-cycle dry-runs/runs, research-cycle exports, and operator-status exports; it cannot approve, reject, activate, deploy, route orders, or place trades.
- The Phase 14 one-shot scheduler worker can lease, heartbeat, recover stale leases, release, and complete bounded queued jobs without starting a daemon or autonomous loop.
- Activation guard requiring a persisted accepted validation report; replay-aware models specifically require accepted `replay_aware_walk_forward` validation.
- Secret redaction behavior and absence of the supplied FMP key from repo files.

## What Is Not Safe To Trust Yet

- Live FMP entitlement coverage. The live smoke was not run because `FMP_API_KEY` is not loaded into the process environment or ignored env files.
- Market replay as execution-grade reality. Replay is now auditable and sensitivity-tested, but fills are still simulated from OHLCV with conservative same-bar rules, configurable slippage/spread, and no true market depth.
- Model calibration as a live probability. Calibration/drift reports are operational diagnostics, not calibrated probability estimates.
- Live trading readiness. No broker execution or order routing exists.
- Fully automated adaptation. Research cycles can compare and propose, but they do not silently activate models or mutate scanner behavior.

## Phase 14 Operator Runbook, Postgres, And Scheduler

Primary docs:

- `docs/local-operator-runbook.md`
- `docs/operator-daily-procedure.md`
- `docs/non-autonomous-scheduler.md`
- `docs/docker-postgres-troubleshooting.md`
- `docs/status/PHASE_14_PLAN_2026-07-01.md`
- `docs/status/PHASE_14_COMPLETION_2026-07-01.md`
- `docs/status/PHASE_14_POSTGRES_VERIFICATION_2026-07-01.md`
- `docs/status/PHASE_14_SCHEDULER_WORKER_2026-07-01.md`

Recover Docker/Postgres:

```bash
docker context ls
docker info
docker compose config
make db-up
docker compose ps
nc -zv localhost 15432
make db-migrate
make db-inspect
make db-query-diagnostics
```

In this Phase 14 run, `docker info`, `docker compose ps`, `make db-up`, `make db-migrate`, `make db-inspect`, `make db-query-diagnostics`, `make api-smoke-postgres`, and `make repository-parity-test` passed.

Daily operator setup:

```bash
source "$HOME/.nvm/nvm.sh"
nvm use 24.18.0
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack prepare pnpm@11.9.0 --activate
make doctor
make scheduler-status
make scheduler-worker-once
make scheduler-recover-stale
make api-dev
make web-dev
```

Create and run a bounded scheduler job:

```bash
curl -s -X POST http://localhost:8000/scheduler/jobs \
  -H 'content-type: application/json' \
  -d '{"job_type":"data_quality_report","payload":{"symbols":["AAPL","SPY"],"intervals":["1min"]},"created_by":"operator"}'

curl -s -X POST http://localhost:8000/scheduler/jobs/run-pending \
  -H 'content-type: application/json' \
  -d '{"max_jobs":3}'
```

Inspect scheduler status:

```bash
curl -s http://localhost:8000/operations/scheduler-status
curl -s http://localhost:8000/scheduler/jobs
curl -s http://localhost:8000/scheduler/jobs/{job_id}
curl -s http://localhost:8000/scheduler/jobs/{job_id}/events
make scheduler-status
make scheduler-worker-once
make scheduler-recover-stale
```

Confirm the scheduler does not activate models:

- Review `services/quant-engine/app/services/scheduler.py`; supported jobs never call proposal approve/reject/activate or model activation services.
- Run `make scheduler-test`; tests assert research-cycle jobs leave the active champion unchanged.
- In the UI, `/operations/scheduler` and `/operations/scheduler/{job_id}` expose create/run/cancel queue controls only, with no activation controls.

## Phase 12 Operator UI

Start the backend and frontend:

```bash
make api-dev
source "$HOME/.nvm/nvm.sh"
nvm use 24.18.0
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack prepare pnpm@11.9.0 --activate
make web-dev
```

Open `http://localhost:5173`.

Routes:

- `/operations`: backend health, persistence, active model, latest cycle/proposal, stale windows, data quality, and warnings.
- `/research`: safe governance hub.
- `/research/cycles`: create, dry-run, run, and export research cycles. Defaults keep `refresh_data=false`, `allow_stale=false`, and `run_now=false`.
- `/research/cycles/{research_cycle_id}`: inspect cycle summary, config hash, input fingerprint, artifacts, warnings, and export metadata.
- `/research/proposals`: list proposals and export proposal reports.
- `/research/proposals/{proposal_id}`: review evidence, approve, reject, and explicitly activate an approved scanner model.
- `/research/decision-ledger`: filter by model version, proposal ID, research cycle ID, decision type, and time range.
- `/research/status`: read-only governance status.

Manual activation flow:

1. Open `/research/proposals/{proposal_id}`.
2. Review evidence, gates, and ledger history.
3. Click `Approve proposal` if appropriate. This does not activate.
4. In the explicit activation panel, check the manual confirmation box and type `ACTIVATE SCANNER MODEL`.
5. Click `Activate approved scanner model`. The frontend sends `confirm_manual_activation=true`, and the backend guard can still block.

What is safe to trust: UI route wiring, typed API client calls, no frontend secret exposure, approval-not-activation behavior, explicit activation confirmation, and mocked e2e coverage.

What is not safe to trust: live FMP entitlement, Postgres verification in this run, or any assumption that UI approval guarantees backend activation.

## Phase 11 Research Cycle Operations

Create a cycle:

```bash
curl -s -X POST http://localhost:8000/research/cycles \
  -H 'content-type: application/json' \
  -d '{"cycle_date":"2026-07-01","cycle_type":"daily","symbols":["AAPL","SPY"],"intervals":["1min"],"start":"2026-06-01T13:30:00Z","end":"2026-06-01T20:00:00Z","challenger_model_version":"{model_version}","allow_stale":false}'
```

Dry-run without training or activation:

```bash
curl -s -X POST http://localhost:8000/research/cycles/{research_cycle_id}/dry-run
```

Run the controlled cycle:

```bash
curl -s -X POST http://localhost:8000/research/cycles/{research_cycle_id}/run \
  -H 'content-type: application/json' \
  -d '{"allow_stale":true}'
```

Inspect cycle state and artifacts:

```bash
curl -s http://localhost:8000/research/cycles
curl -s http://localhost:8000/research/cycles/{research_cycle_id}
curl -s 'http://localhost:8000/research/cycles/{research_cycle_id}/artifacts?limit=500'
curl -s -X POST http://localhost:8000/research/cycles/{research_cycle_id}/export
```

Review a proposal:

```bash
curl -s http://localhost:8000/research/model-proposals
curl -s http://localhost:8000/research/model-proposals/{proposal_id}
```

Approve a proposal without activating it:

```bash
curl -s -X POST http://localhost:8000/research/model-proposals/{proposal_id}/approve \
  -H 'content-type: application/json' \
  -d '{"actor":"research_lead"}'
```

Explicitly activate an approved proposal:

```bash
curl -s -X POST http://localhost:8000/research/model-proposals/{proposal_id}/activate \
  -H 'content-type: application/json' \
  -d '{"actor":"research_lead","confirm_manual_activation":true,"validation_mode":"replay_aware_walk_forward"}'
```

Reject a proposal:

```bash
curl -s -X POST http://localhost:8000/research/model-proposals/{proposal_id}/reject \
  -H 'content-type: application/json' \
  -d '{"actor":"research_lead","reason_codes":["manual_rejection"]}'
```

Query the decision ledger and operations status:

```bash
curl -s 'http://localhost:8000/research/decision-ledger?proposal_id={proposal_id}'
curl -s http://localhost:8000/operations/research-status
```

Safe to trust in Phase 11: persisted cycle IDs, artifact references, config hashes, input fingerprints, stale/data-quality blocks, explicit approval records, explicit activation records, and SQLite/Postgres parity for the controlled governance flow.

Not safe to trust in Phase 11: proposal recommendations as profitability claims, automatic deployment decisions, live fill assumptions, or any claim that the platform is self-learning.

## Backtest Modes

Label-derived evidence remains available and explicit:

```bash
curl -s -X POST http://localhost:8000/backtest/run \
  -H 'content-type: application/json' \
  -d '{"symbols":["AAPL"],"start":"2026-06-01T13:30:00+00:00","end":"2026-06-01T19:59:00+00:00"}'
```

The response includes `simulation_type = label_derived`.

Candidate market replay uses persisted bars, features, and candidate signals:

```bash
curl -s -X POST http://localhost:8000/backtest/replay \
  -H 'content-type: application/json' \
  -d '{"symbols":["AAPL"],"intervals":["1min"],"start":"2026-06-01T13:30:00+00:00","end":"2026-06-01T19:59:00+00:00","max_hold_minutes":60,"minimum_reward_risk":1.0}'
```

The response includes `simulation_type = candidate_market_replay`, `replay_run_id`, `summary_metrics`, `config_hash`, `input_fingerprint`, `candidate_fingerprint`, and `trades_written`. Query the run and paginated trades with:

```bash
curl -s http://localhost:8000/backtest/replay/{replay_run_id}
curl -s 'http://localhost:8000/backtest/replay/{replay_run_id}/trades?limit=500&offset=0'
```

Replay validation now requires explicit selection unless fallback is intentionally enabled:

```bash
curl -s -X POST 'http://localhost:8000/models/validate?validation_mode=candidate_market_replay&replay_run_id={replay_run_id}'
```

Run sensitivity and label-vs-replay comparison with:

```bash
curl -s -X POST http://localhost:8000/backtest/replay/{replay_run_id}/sensitivity
curl -s -X POST http://localhost:8000/backtest/compare-label-vs-replay \
  -H 'content-type: application/json' \
  -d '{"replay_run_id":"{replay_run_id}"}'
```

Export replay outputs with:

```bash
curl -s -X POST http://localhost:8000/exports/replay-summary.xlsx \
  -H 'content-type: application/json' \
  -d '{"kind":"replay-summary","run_id":"{replay_run_id}"}'
curl -s -X POST http://localhost:8000/exports/replay-trades.csv \
  -H 'content-type: application/json' \
  -d '{"kind":"replay-trades","run_id":"{replay_run_id}"}'
curl -s -X POST http://localhost:8000/exports/replay-trades.xlsx \
  -H 'content-type: application/json' \
  -d '{"kind":"replay-trades","run_id":"{replay_run_id}"}'
curl -s -X POST http://localhost:8000/exports/sensitivity-summary.xlsx \
  -H 'content-type: application/json' \
  -d '{"kind":"sensitivity-summary","run_id":"{sensitivity_run_id}"}'
```

## Current Blockers

- Optional live FMP smoke requires `FMP_API_KEY` to be configured outside the committed repo.
- Frontend acceptance still requires using Node `24.18.0` through NVM because the Homebrew Node `25.3.0` binary on this machine fails before Corepack.

## Exact Next Recommended Phase

Phase 15 should focus on artifact reuse and operator ergonomics around research cycles and scheduler outputs. Do not add automatic activation, broker execution, WebSocket scope, options data, self-learning language, autonomous scheduling, or profitability claims.

## Phase 8 Replay-Aware Model Selection Historical Notes

Train a replay-aware baseline model from persisted replay runs:

```bash
curl -s -X POST http://localhost:8000/models/train \
  -H 'content-type: application/json' \
  -d '{"model_type":"replay_aware_baseline","symbols":["AAPL"],"intervals":["1min"],"training_start":"2026-06-01T13:30:00+00:00","training_end":"2026-06-01T19:59:00+00:00","replay_run_ids":["{replay_run_id}"],"minimum_observed_outcomes":5,"minimum_cell_sample_size":5}'
```

Validate and activate:

```bash
curl -s -X POST 'http://localhost:8000/models/validate?model_version={model_version}&validation_mode=replay_aware_walk_forward'
curl -s -X POST 'http://localhost:8000/models/activate?model_version={model_version}&validation_mode=replay_aware_walk_forward'
```

Score candidates and inspect audits:

```bash
curl -s http://localhost:8000/models/{model_version}/evidence
curl -s -X POST http://localhost:8000/models/{model_version}/score-candidates \
  -H 'content-type: application/json' \
  -d '{"candidate_ids":["{candidate_id}"],"persist_audit":true}'
curl -s http://localhost:8000/models/{model_version}/score-audits
```

When an active `replay_aware_baseline` exists, the scanner uses replay-aware scoring and writes score audits. If none is active, it falls back to the prior baseline and adds `no_replay_aware_model_active` to signal warnings.

Replay-aware exports:

```bash
curl -s -X POST http://localhost:8000/exports/replay-aware-model-summary.xlsx \
  -H 'content-type: application/json' \
  -d '{"kind":"replay-aware-model-summary","run_id":"{model_version}"}'
curl -s -X POST http://localhost:8000/exports/evidence-cells.xlsx \
  -H 'content-type: application/json' \
  -d '{"kind":"evidence-cells","run_id":"{model_version}"}'
curl -s -X POST http://localhost:8000/exports/score-audits.xlsx \
  -H 'content-type: application/json' \
  -d '{"kind":"score-audits","run_id":"{model_version}"}'
curl -s -X POST http://localhost:8000/exports/replay-aware-validation.xlsx \
  -H 'content-type: application/json' \
  -d '{"kind":"replay-aware-validation","run_id":"{report_id}"}'
```

Safe to trust: deterministic replay outcome dataset rules, persisted evidence cells, shrinkage/backoff hierarchy, score audits, replay-aware activation guard, and SQLite/Postgres persistence once migrations are applied through `0010_phase14_scheduler_worker`.

Not safe to trust: `signal_quality_score` as a calibrated probability, replay as live fill proof, portfolio-overlap skipped candidates as losses, or any output as a profitability claim.

## Phase 9 Counterfactual Replay And Calibration

Run counterfactual replay:

```bash
curl -s -X POST http://localhost:8000/backtest/replay \
  -H 'content-type: application/json' \
  -d '{"replay_purpose":"model_training_counterfactual","symbols":["AAPL"],"intervals":["1min"],"start":"2026-06-01T13:30:00Z","end":"2026-06-01T20:00:00Z"}'
```

Train replay-aware evidence from counterfactual outcomes:

```bash
curl -s -X POST http://localhost:8000/models/train \
  -H 'content-type: application/json' \
  -d '{"model_type":"replay_aware_baseline","outcome_source":"counterfactual_preferred","counterfactual_replay_run_ids":["{counterfactual_run_id}"],"portfolio_replay_run_ids":["{portfolio_run_id}"],"require_counterfactual":true,"training_start":"2026-06-01T13:30:00Z","training_end":"2026-06-01T20:00:00Z"}'
```

Run calibration audit:

```bash
curl -s -X POST http://localhost:8000/models/{model_version}/calibration-audit \
  -H 'content-type: application/json' \
  -d '{"replay_run_ids":["{counterfactual_run_id}"],"outcome_source":"counterfactual_only"}'
```

Require calibration for activation:

```bash
curl -s -X POST 'http://localhost:8000/models/activate?model_version={model_version}&validation_mode=replay_aware_walk_forward&calibration_audit_required=true&calibration_audit_id={calibration_audit_id}'
```

Compare counterfactual vs portfolio replay:

```bash
curl -s -X POST http://localhost:8000/backtest/compare-counterfactual-vs-portfolio \
  -H 'content-type: application/json' \
  -d '{"counterfactual_replay_run_id":"{counterfactual_run_id}","portfolio_replay_run_id":"{portfolio_run_id}"}'
```

Scanner behavior: if the active replay-aware model requires calibration and the audit is missing or failed, scanner output suppresses actionable TAKE and emits `calibration_required_or_failed`. Score reasons include model version, outcome source, calibration status, score audit ID, and evidence keys when available.

Safe to trust: persisted replay/config provenance, counterfactual candidate-quality evidence, calibration warnings/rejection reasons, and activation/scanner calibration gates.

Not safe to trust: counterfactual replay as executable portfolio P/L, `signal_quality_score` as calibrated probability, or any replay/calibration metric as a profitability claim.
