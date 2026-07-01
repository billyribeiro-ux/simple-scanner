# Adaptive Market Decoder

Adaptive Market Decoder is a local-first trading research and live signal platform for a small, high-liquidity symbol universe. It produces evidence-based trade plans only; it does not place orders or integrate with brokers.

## Requirements

- Node.js `24.18.0`
- pnpm via Corepack
- Python `3.14.6`, the latest stable Python release as of June 30, 2026
- Docker for PostgreSQL/TimescaleDB and Redis
- Optional FMP API key in `FMP_API_KEY` for live provider smoke and live scanner use

## Setup

```bash
cp .env.example .env.local
# edit .env.local and set FMP_API_KEY
source "$HOME/.nvm/nvm.sh"
nvm use 24.18.0
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack prepare pnpm@11.5.2 --activate
make frontend-doctor
make doctor
make setup-backend
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm install --frozen-lockfile
make db-up
make db-migrate
make db-inspect
make api-smoke
make api-smoke-postgres
make repository-parity-test
```

`make doctor` does not print secrets. It reports whether `FMP_API_KEY` and `DATABASE_URL` are present.

## Run

```bash
make dev
```

Frontend: `http://localhost:5173`

Backend: `http://localhost:8000`

## Commands

```bash
corepack pnpm install
corepack pnpm dev
corepack pnpm build
corepack pnpm check
corepack pnpm test
corepack pnpm lint
corepack pnpm --filter @amd/web test:e2e

make doctor
make frontend-doctor
make setup-backend
make quant-test
make ingest
make features
make labels
make train
make validate
make backtest
make scanner
make export
make db-inspect
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
make db-query-diagnostics
make export-test
make fmp-smoke
make test
```

`make quant-test` runs pure deterministic quant tests without FMP, Docker, Redis, Postgres, or internet. If the backend venv is missing, it falls back to `python3` for this pure test path only. Full backend runtime still targets Python `3.14.6`.

`make api-smoke` runs the default SQLite persisted FastAPI vertical slice with a mocked provider. `make api-smoke-postgres` runs the same API workflow against the migrated local Postgres/TimescaleDB compose database. Neither smoke path requires FMP, internet, or secrets.

`make replay-test` runs the candidate-to-trade market replay unit tests. `make replay-sensitivity-test` runs replay audit/sensitivity tests. `make replay-window-test` runs multi-window replay orchestration tests. `make model-review-test` runs calibration drift, model review, and data quality tests. `make export-test` verifies replay, sensitivity, signal, calibration, drift, review, and window-set export generation.

`make research-cycle-test` runs the controlled research cycle, champion/challenger, proposal lifecycle, and activation guard tests. `make research-status-test` runs the operations research-status, decision-ledger, and Phase 11 export subset.

`make fmp-smoke` is optional and runs live FMP REST checks only when `FMP_API_KEY` is configured. Otherwise it skips with a non-secret message.

## Persistence Contract

FastAPI selects the repository backend explicitly:

- no `DATABASE_URL`: SQLite at `data/local_repo.sqlite3`, or `AMD_SQLITE_PATH` when set;
- `sqlite:///...`: SQLite at the configured path;
- `postgres://`, `postgresql://`, or `postgresql+...`: PostgreSQL repository runtime against the migrated schema;
- failed Postgres initialization: fail loudly unless `AMD_ALLOW_SQLITE_FALLBACK=true`;
- explicit fallback: SQLite with runtime mode `sqlite-fallback-from-postgres` and a non-secret fallback reason.

`GET /health`, `GET /config`, and `make doctor` report safe fields such as `persistence_backend`, `runtime_mode`, `database_configured`, `database_reachable`, `fallback_enabled`, and `fallback_reason`. They do not print passwords, API keys, or full database URLs.

## Typical Workflow

1. Set `FMP_API_KEY` in your shell or ignored env file.
2. Start services with `make db-up`.
3. Ingest bars through the Training page or `POST /data/ingest`.
4. Build features and labels.
5. Train and validate a model.
6. Activate only a passing model.
7. Run `POST /backtest/run` for label-derived evidence, or `POST /backtest/replay` for candidate-to-trade market replay.
8. For replay validation, pass an explicit `replay_run_id` or `replay_filter`.
9. Run replay sensitivity and label-vs-replay comparison before treating replay evidence as model-selection input.
10. Generate replay window sets, calibration drift reports, and model review reports when comparing model readiness across time.
11. Start the scanner.
12. Export live signals, replay summaries/trades, sensitivity artifacts, drift/model-review artifacts, history, backtests, or daily reviews.

## Backtest Modes

- `label_derived`: the existing fast evidence mode that simulates from leakage-safe labels.
- `candidate_market_replay`: replay mode that starts from persisted candidates, enters at next-bar open, replays raw bars chronologically, records skipped candidates, computes metrics from simulated trades, and persists provenance hashes/fingerprints.
- `model_training_counterfactual`: independent per-candidate replay for candidate-quality evidence. It disables portfolio overlap/cooldown/max-open constraints by default and is not portfolio P/L.

Replay exports are available through `POST /exports/replay-summary.xlsx`, `POST /exports/replay-trades.csv`, and `POST /exports/replay-trades.xlsx` with `run_id` set to the replay run ID.

Replay sensitivity exports are available through `POST /exports/sensitivity-summary.xlsx`, `POST /exports/sensitivity-scenarios.csv`, `POST /exports/sensitivity-scenarios.xlsx`, and `POST /exports/sensitivity-metrics.json` with `run_id` set to the sensitivity run ID.

## Replay-Aware Baseline Model

Phase 8 adds `model_type = replay_aware_baseline`. Train it from explicit persisted replay runs:

```bash
curl -s -X POST http://localhost:8000/models/train \
  -H 'content-type: application/json' \
  -d '{"model_type":"replay_aware_baseline","symbols":["AAPL"],"intervals":["1min"],"training_start":"2026-06-01T13:30:00+00:00","training_end":"2026-06-01T19:59:00+00:00","replay_run_ids":["{replay_run_id}"],"minimum_observed_outcomes":5,"minimum_cell_sample_size":5}'
```

Validate and activate through `replay_aware_walk_forward`:

```bash
curl -s -X POST 'http://localhost:8000/models/validate?model_version={model_version}&validation_mode=replay_aware_walk_forward'
curl -s -X POST 'http://localhost:8000/models/activate?model_version={model_version}&validation_mode=replay_aware_walk_forward'
```

Evidence and score audits:

```bash
curl -s http://localhost:8000/models/{model_version}/evidence
curl -s -X POST http://localhost:8000/models/{model_version}/score-candidates \
  -H 'content-type: application/json' \
  -d '{"candidate_ids":["{candidate_id}"],"persist_audit":true}'
curl -s http://localhost:8000/models/{model_version}/score-audits
```

Replay-aware exports:

- `POST /exports/replay-aware-model-summary.xlsx`
- `POST /exports/evidence-cells.csv`
- `POST /exports/evidence-cells.xlsx`
- `POST /exports/score-audits.csv`
- `POST /exports/score-audits.xlsx`
- `POST /exports/replay-aware-validation.xlsx`

The replay-aware score is an explainable evidence score, not a calibrated probability or profitability claim.

## Phase 9 Counterfactual And Calibration

Run counterfactual replay by posting to `/backtest/replay` with `replay_purpose = model_training_counterfactual`. Train `replay_aware_baseline` with `outcome_source = counterfactual_preferred`, `counterfactual_replay_run_ids`, and optional `portfolio_replay_run_ids`.

Calibration audits:

- `POST /models/{model_version}/calibration-audit`
- `GET /models/{model_version}/calibration-audits`
- `GET /models/calibration-audits/{calibration_audit_id}`
- `GET /models/calibration-audits/{calibration_audit_id}/bins`

Diagnostic comparisons:

- `POST /models/compare`
- `POST /backtest/compare-counterfactual-vs-portfolio`
- `GET /backtest/counterfactual-comparisons/{comparison_id}`

Calibration exports:

- `POST /exports/calibration-audit.xlsx`
- `POST /exports/calibration-bins.csv`
- `POST /exports/calibration-bins.xlsx`
- `POST /exports/calibration-metrics.json`
- `POST /exports/model-comparison.xlsx`

Activation can require calibration with `calibration_audit_required=true`. If the active replay-aware model requires calibration and the audit is missing or failed, scanner output suppresses actionable TAKE and emits `calibration_required_or_failed`.

## Phase 10 Replay Windows, Drift, And Review

Replay window orchestration:

- `POST /orchestration/replay-window-sets`
- `GET /orchestration/replay-window-sets`
- `GET /orchestration/replay-window-sets/{window_set_id}`
- `GET /orchestration/replay-window-sets/{window_set_id}/results`
- `POST /orchestration/replay-window-sets/{window_set_id}/run`
- `POST /orchestration/replay-window-sets/{window_set_id}/export`

Calibration drift:

- `POST /models/{model_version}/calibration-drift`
- `GET /models/{model_version}/calibration-drift`
- `GET /models/calibration-drift/{drift_report_id}`
- `GET /models/calibration-drift/{drift_report_id}/windows`

Model review reports:

- `POST /models/{model_version}/review-report`
- `GET /models/{model_version}/review-reports`
- `GET /models/review-reports/{review_report_id}`

Data quality:

- `GET /data/quality-report`

Phase 10 exports:

- `POST /exports/replay-window-set.xlsx`
- `POST /exports/calibration-drift.xlsx`
- `POST /exports/calibration-drift.json`
- `POST /exports/calibration-drift-windows.csv`
- `POST /exports/calibration-drift-windows.xlsx`
- `POST /exports/model-review.xlsx`
- `POST /exports/model-review.json`

These artifacts are advisory research and operational review outputs. They do not activate models, route orders, or make profitability claims.

## Phase 11 Controlled Research Governance

Phase 11 adds a controlled daily research review loop:

- `POST /research/cycles` creates a reproducible research cycle.
- `POST /research/cycles/{research_cycle_id}/dry-run` computes stale/data-quality/rebuild warnings without activation.
- `POST /research/cycles/{research_cycle_id}/run` records data quality, stale-window state, explicit evidence artifacts, champion/challenger comparison, and a model proposal.
- `GET /research/model-proposals` and `GET /research/model-proposals/{proposal_id}` inspect proposals.
- `POST /research/model-proposals/{proposal_id}/approve` marks an eligible challenger proposal as approved for activation, but does not activate it.
- `POST /research/model-proposals/{proposal_id}/activate` requires `confirm_manual_activation=true` and the existing activation guard.
- `GET /research/decision-ledger` returns append-only governance decisions.
- `GET /operations/research-status` returns read-only operational research status.

Phase 11 exports:

- `POST /exports/research-cycle.xlsx`
- `POST /exports/research-cycle.json`
- `POST /exports/model-proposal.xlsx`
- `POST /exports/model-proposal.json`
- `POST /exports/champion-challenger-comparison.xlsx`

Research cycles and proposals are diagnostic governance artifacts. They do not silently retrain, silently activate, route orders, call broker APIs, claim profitability, or make the system self-learning.

## Phase 12 Operator Governance UI

Phase 12 adds a thin SvelteKit operator control surface for the Phase 11 governance workflow:

- `/operations`: backend health, persistence status, active model, latest cycle/proposal, stale windows, and data quality.
- `/research`: safe governance hub with no direct activation control.
- `/research/cycles`: list/create controlled research cycles with safe defaults, `APPL` to `AAPL` normalization, dry-run, run, and export actions.
- `/research/cycles/{research_cycle_id}`: cycle detail, stale/data-quality state, artifacts, warnings, and export metadata.
- `/research/proposals`: proposal list and export actions.
- `/research/proposals/{proposal_id}`: evidence review, approve/reject actions, and explicit activation panel.
- `/research/decision-ledger`: filterable append-only decision ledger.
- `/research/status`: read-only research governance status.

Approval and activation remain separate. The proposal detail page requires an approved proposal, an explicit checkbox, and the phrase `ACTIVATE SCANNER MODEL` before it sends `confirm_manual_activation=true`. This updates scanner model state only; it does not trade.

## Default Universe

`AMZN, AAPL, TSLA, SPY, QQQ, IWM, NVDA, GOOGL, BABA, SHOP`

`APPL` is normalized to `AAPL`.
