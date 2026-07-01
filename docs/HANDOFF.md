# Adaptive Market Decoder Handoff

Report status date: 2026-07-01

## Executive State

Phase 8 replay-aware baseline model selection is complete in source. Python `3.14.6` is installed through Homebrew, `services/quant-engine/.venv` exists on Python `3.14.6`, Docker Postgres/TimescaleDB plus Redis are the required database runtime, Alembic upgrades the target database to `0005_phase8_replay_aware_models`, and the persisted FastAPI vertical-slice smoke test covers label-derived backtests, explicit replay validation, replay sensitivity, label-vs-replay comparison, replay-aware training, evidence retrieval, candidate scoring, score audits, replay-aware validation/activation, and exports with a mocked provider and no FMP key.

This remains a local-first scanner, research, validation, backtest, signal, and export platform only. It is not a broker, auto-trader, order router, self-learning system, or profitability system.

## Runtime Pins

- Node target: `24.18.0`
- Package manager: `pnpm@11.5.2` through Corepack
- Python target: `3.14.6`, documented as the latest stable Python release for this project as of June 30, 2026
- Current local Node: `25.3.0`, which triggers an expected target warning
- Current local Python: `python3.14` and Homebrew `python3` report `3.14.6`
- Backend venv: `services/quant-engine/.venv` on Python `3.14.6`

## Exact Setup Commands

```bash
make help
make doctor
make setup-backend
corepack pnpm install
make db-up
make db-migrate
make db-inspect
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
make export-test
make fmp-smoke
corepack pnpm check
corepack pnpm build
corepack pnpm test
corepack pnpm lint
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

Phase 7 and Phase 8 persist replay audit, sensitivity, and replay-aware model-selection state:

- `replay_runs`: one row per candidate market replay run with config, filters, simulation type, metrics, warnings, backend, config hash, input fingerprint, candidate fingerprint, and stale-window status.
- `simulated_trades`: one row per taken or skipped candidate, including execution assumptions, entry/exit prices, realized R, MFE/MAE, skip reason, and ambiguity policy.
- `pipeline_build_windows`: dirty/stale metadata for feature, candidate, label, and replay rebuild awareness by artifact, symbol, interval, session date, version, and timestamp range.
- `replay_sensitivity_runs`: sensitivity run summaries, robustness scores, fragility flags, worst/median/best cases, and gate results.
- `replay_sensitivity_scenarios`: scenario-level slippage/spread/intrabar metrics.
- `backtest_comparisons`: persisted label-derived vs replay comparison reports.
- `model_evidence_cells`: replay-aware evidence cube cells with hierarchy level, dimensions, observed counts, shrinkage/backoff metrics, fragility flags, stale warnings, and provenance.
- `candidate_score_audits`: deterministic replay-aware score/audit rows with action, grade, component scores, penalties, evidence keys, warning codes, and suppression reasons.

Safe status fields are exposed through `GET /health`, `GET /config`, and `make doctor`: `persistence_backend`, `runtime_mode`, `database_configured`, `database_reachable`, `fallback_enabled`, and `fallback_reason`. Full database URLs, passwords, and API keys are never returned.

## What Is Safe To Trust

- Deterministic quant feature/label/backtest/model baseline tests.
- Repository-backed API route state instead of route-level `_MEMORY`.
- SQLite local API persistence and reinitialization survival for bars, features, labels, replay runs/trades, model runs, active model, scanner runs/signals, exports, and daily reviews.
- Postgres API persistence and reinitialization survival for the same vertical slice after `make db-migrate`.
- Alembic migration and schema inspection success against local Postgres/TimescaleDB on host port `15432` when the database is at revision `0005_phase8_replay_aware_models`; `bars` is verified as a Timescale hypertable when the extension is available.
- SQLite/Postgres repository parity for symbols, bars, features, labels, replay runs/trades, sensitivity runs/scenarios, comparisons, pipeline build windows, replay-aware evidence cells, candidate score audits, models, scanner runs, signals, provider requests, exports, and daily reviews.
- CSV/XLSX/JSON export generation from persisted signals, replay runs/trades, replay sensitivity runs, replay-aware model summaries, evidence cells, score audits, replay-aware validation reports, and daily reviews, with file hashes and workbook sheets recorded.
- Activation guard requiring a persisted accepted validation report; replay-aware models specifically require accepted `replay_aware_walk_forward` validation.
- Secret redaction behavior and absence of the supplied FMP key from repo files.

## What Is Not Safe To Trust Yet

- Live FMP entitlement coverage. The live smoke was not run because `FMP_API_KEY` is not loaded into the process environment or ignored env files.
- Market replay as execution-grade reality. Replay is now auditable and sensitivity-tested, but fills are still simulated from OHLCV with conservative same-bar rules, configurable slippage/spread, and no true market depth.
- Model calibration. V1 remains a statistical evidence baseline, not a calibrated ML classifier.
- Live trading readiness. No broker execution or order routing exists.

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

- Local Node is `25.3.0`, while the project target is `24.18.0`. Corepack pnpm still runs, but frontend commands emit the expected engine warning.
- Optional live FMP smoke requires `FMP_API_KEY` to be configured outside the committed repo.

## Exact Next Recommended Phase

Phase 10: calibration drift reporting, larger replay-window orchestration, and optional backend/CLI reporting polish.

The next phase should expand calibration drift diagnostics, add richer multi-window replay selection/reporting, consider Timescale compression/retention policies if volume requires them, and optionally expose Phase 9 artifacts in the frontend without changing execution boundaries. Do not add broker execution, WebSocket scope, options data, self-learning language, or profitability claims.

## Phase 8 Replay-Aware Model Selection

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

Safe to trust: deterministic replay outcome dataset rules, persisted evidence cells, shrinkage/backoff hierarchy, score audits, replay-aware activation guard, and SQLite/Postgres persistence once migration `0005_phase8_replay_aware_models` is applied.

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
