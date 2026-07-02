# Data Model

Core storage is designed around PostgreSQL with TimescaleDB when available. If the Timescale extension is not available, the same tables function as plain PostgreSQL tables. Phase 13 advances Alembic to revision `0009_phase13_scheduler`, adding bounded scheduler jobs and scheduler job events on top of Phase 11 research-governance persistence. The API repository runtime supports both SQLite local storage and PostgreSQL.

## Tables

- `symbols`: normalized symbol metadata and active flag.
- `bars`: interval OHLCV bars with UTC/ET timestamps, source, ingestion time, and quality flags.
- `features`: per-symbol timestamp feature payloads with feature-set version and data-quality flags.
- `candidate_signals`: deterministic setup candidates emitted before labeling/scoring.
- `labels`: leakage-safe hypothetical trade outcomes.
- `validation_reports`: validation or backtest report summaries, leakage warnings, activation decision, and rejection reasons.
- `validation_windows`: walk-forward or chronological validation windows tied to a validation report.
- `model_runs`: model versions, training windows, feature set, label config, activation state.
- `model_artifacts`: model artifact metadata and local path tracking.
- `model_evidence_cells`: replay-aware evidence cells by model version, hierarchy level, dimensions, sample metrics, robustness, fragility, and evidence grade.
- `candidate_score_audits`: persisted replay-aware meta-scorer audits with score components, suppression reasons, evidence keys used, and warnings.
- `active_models`: the current active model pointer by model type and strategy scope.
- `live_signals`: current signal/trade-plan rows with all required live output fields.
- `closed_signals`: completed signal outcomes and realized R.
- `scanner_runs`: scanner start/stop status, symbols, threshold, active model version, and run stats.
- `daily_reviews`: end-of-day review artifacts and recommendations.
- `provider_requests`: redacted request accounting and provider health.
- `exports`: generated CSV/XLSX/JSON artifact metadata, including file SHA-256 and workbook sheets when available.
- `replay_runs`: candidate-to-trade replay run metadata, config, filters, backend, simulation type, metrics, warnings, config hash, input fingerprint, candidate fingerprint, stale-window status, and JSON payload.
- `replay_sensitivity_runs`: replay sensitivity summary, config, robustness score, fragility flags, gate results, and JSON payload.
- `replay_sensitivity_scenarios`: per-scenario slippage/spread/intrabar sensitivity metrics and JSON payload.
- `backtest_comparisons`: label-derived vs replay comparison summaries and JSON payload.
- `simulated_trades`: taken and skipped candidate replay rows with signal timestamp, entry/exit assumptions, prices, R metrics, MFE/MAE, ambiguity policy, status, skip reason, and JSON payload.
- `pipeline_build_windows`: stale/dirty metadata by artifact type, symbol, interval, session date, version, and affected timestamp range for features, candidates, labels, and replay awareness.
- `research_cycles`: reproducible daily/manual/ad-hoc governance cycles with config hash, input fingerprint, data-quality/stale-window summaries, source IDs, status transitions, backend, database revision, and non-secret provenance.
- `research_cycle_artifacts`: source references and payload snapshots created or reused during a research cycle.
- `champion_challenger_comparisons`: diagnostic champion-vs-challenger deltas, gates, readiness, recommendation, warnings, and context.
- `model_proposals`: proposal lifecycle state, champion/challenger IDs and metrics, evidence summaries, pass/fail gates, approval metadata, and explicit activation metadata.
- `model_decision_ledger`: append-only model-governance decisions for cycles, proposals, activation requests, blocked activations, and activations.
- `scheduler_jobs`: bounded local research-preparation queue state, payloads, results, warnings, failure reasons, and optional research cycle links.
- `scheduler_job_events`: append-only scheduler job lifecycle events with redacted metadata.

## Signal Fields

Signals include timestamp, ticker, side, entry/stop/targets, R metrics, confidence, grade, setup type, market and ticker regime, reasons, warnings, historical sample metrics, model metadata, status, exit fields, and realized R.

## Phase 7 Indexes And Constraints

`make db-inspect` verifies the migration revision plus critical lookup indexes on bars, features, candidate signals, labels, simulated trades, replay runs, replay sensitivity, comparisons, live signals, validation reports, scanner runs, and pipeline build windows. It also verifies the unique constraints that preserve idempotent upserts for bars, features, candidate signals, labels, pipeline build windows, and active model scope.

`simulated_trades` stores skipped candidates in the same table as taken trades with `status = SKIPPED` and a populated `skip_reason`. Metrics are computed from taken simulated trades; candidate counts and skip rates include both taken and skipped rows. Phase 8 replay-aware training preserves skipped rows but treats overlap, portfolio limit, cooldown, duplicate, missing future bars, and stale-data skips as unobserved outcomes rather than losses.

## Phase 9 Update

Alembic is now `0006_phase9_calibration`. New persisted tables are `model_calibration_audits`, `model_calibration_bins`, and `model_comparisons`.

`replay_runs` and `simulated_trades` carry counterfactual replay via existing JSON payloads. Counterfactual runs use `simulation_type = model_training_counterfactual`; per-trade metadata stores replay purpose, candidate-quality label, counterfactual observed status, portfolio-blocked marker, concurrency count, overlap group, and concurrency bucket.

`model_calibration_audits` stores score/grade/action bins, rank correlation, monotonicity, separation metrics, stability metrics, warnings, rejection reasons, and provenance. `model_calibration_bins` stores the bin rows used by exports and audit drilldowns. `model_comparisons` stores diagnostic model comparison payloads and never auto-activates a model.

## Phase 10 Update

Alembic is now `0007_phase10_review`. New persisted tables are `replay_window_sets`, `replay_window_results`, `model_calibration_drift_reports`, `model_calibration_drift_windows`, and `model_review_reports`.

`replay_window_sets` stores generated daily/rolling/anchored/custom windows, replay configuration, model version, summary, warnings, and status. `replay_window_results` stores per-window replay IDs, comparison IDs, calibration IDs, metrics, warnings, and completion state.

`model_calibration_drift_reports` stores advisory drift severity, drift flags, score/grade/action bin drift, stability metrics, linked calibration/window/replay IDs, warnings, and config. `model_calibration_drift_windows` stores per-window drift metrics and flags.

`model_review_reports` stores advisory readiness status, validation/calibration/drift/sensitivity/comparison references, unresolved warnings, and `model_activation_unchanged=true` in summaries. Review reports never activate or deactivate models.

## Phase 11 Update

Alembic is now `0008_phase11_research`. New persisted tables are `research_cycles`, `research_cycle_artifacts`, `champion_challenger_comparisons`, `model_proposals`, and `model_decision_ledger`.

Research cycles store controlled adaptation evidence, not autonomous learning state. A cycle can be `CREATED`, `RUNNING`, `COMPLETED`, `FAILED`, or `BLOCKED`; it records `config_hash`, `input_fingerprint`, explicit artifact IDs, `database_revision`, `persistence_backend`, and warnings without secrets.

Model proposals separate review from activation. `APPROVED_FOR_ACTIVATION` is not active deployment; activation requires a separate explicit call with manual confirmation and the existing validation guard. Proposals with `KEEP_CHAMPION`, `REJECT_CHALLENGER`, or `BLOCK_ALL_CHANGES` recommendations cannot be approved for activation.

The decision ledger is append-only for normal operation. It records evidence references and actor strings, but never API keys, database passwords, or provider secrets.

## Phase 13 Update

Alembic is now `0009_phase13_scheduler`. New persisted tables are `scheduler_jobs` and `scheduler_job_events`.

Scheduler jobs can run data-quality reports, research-cycle dry-runs, controlled research-cycle runs, research-cycle exports, and operator-status exports. They are bounded, synchronous, and operator-triggered in V1. They never approve proposals, reject proposals, activate models, route orders, place trades, or change the active scanner model.

Scheduler payloads, results, events, status responses, and exports are redacted before persistence. A job requesting `refresh_data=true` blocks without provider access when `FMP_API_KEY` is missing.
