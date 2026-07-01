# Replay Calibration Audit

Status date: 2026-07-01

## Purpose

Phase 7 makes `candidate_market_replay` runs auditable before any future model-selection work relies on replay outcomes. Replay remains a research simulator. It does not place orders, route orders, model queue position, prove profitability, or connect to a broker.

## Replay Provenance

Every persisted replay run now includes:

- `config_hash`
- `input_fingerprint`
- `candidate_fingerprint`
- `replay_config_version`
- `feature_set_version`
- `candidate_config_version`
- `label_config_version`
- source bar, feature, and candidate counts
- taken and skipped candidate counts
- repository backend
- database migration revision marker
- git commit when available
- stale window status and stale window IDs

Fingerprints are deterministic for identical controlled data/config. They include replay config, sorted candidate identity/context, OHLCV bar fingerprints, feature fingerprints, and version metadata. They intentionally exclude API keys, database URLs, passwords, environment variables, and local secret values.

## Stale Gates

`POST /backtest/replay` rejects dirty feature/candidate windows by default. To run anyway, pass `allow_stale=true`; the replay persists stale status and a warning.

Replay validation rejects stale replay runs by default. To override, pass `allow_stale_replay_validation=true` to `/models/validate`.

Use `GET /pipeline/status` to inspect dirty artifact windows.

## Explicit Validation

`POST /models/validate?validation_mode=candidate_market_replay` now requires one of:

- `replay_run_id`
- `replay_filter` as JSON
- `allow_latest_replay_fallback=true`

Without one of those, validation rejects with `replay_run_selection_required`.

## Sensitivity Audit

Replay sensitivity reruns the source replay over slippage/spread/intrabar assumptions and persists the results:

- `POST /backtest/replay/{replay_run_id}/sensitivity`
- `GET /backtest/replay/sensitivity/{sensitivity_run_id}`
- `GET /backtest/replay/sensitivity/{sensitivity_run_id}/scenarios`
- `GET /backtest/replay/{replay_run_id}/sensitivity`

Default grids:

- slippage bps: `0, 1, 2, 5, 10`
- spread bps: `0, 1, 2, 5, 10`
- intrabar policies: `conservative`, `open_high_low_close`, `open_low_high_close`

The engine records worst/median/best scenarios, robustness score, fragility flags, and gate results. Sensitivity is a stress test, not a claim of live tradability.

## Label Vs Replay Comparison

`POST /backtest/compare-label-vs-replay` persists a comparison between leakage-safe label-derived metrics and candidate replay metrics. It reports deltas and material disagreement flags for trade count, average R, win rate, and related summary fields.

## Phase 8 Consumption

`replay_aware_baseline` consumes Phase 7 audit outputs:

- replay provenance hashes and input fingerprints are stored in the model payload;
- stale replay runs block training and replay-aware validation unless explicitly allowed;
- sensitivity robustness and fragility flags become evidence and scoring inputs;
- label-vs-replay material disagreement flags penalize or suppress candidates;
- score audits and exports must remain secret-free.

The replay-aware model is deterministic evidence selection. It does not convert replay into execution-grade fills, live tradability, or profitability claims.
## Phase 9 Update

Phase 9 implements score calibration audits. The audit joins persisted score audits to replay outcomes, computes score/grade/action bins, monotonicity, rank correlation, bucket separation, stability by symbol/setup/regime/time, warnings, and rejection reasons.

The audit is available through `/models/{model_version}/calibration-audit`, persists to `model_calibration_audits` and `model_calibration_bins`, and exports to XLSX/CSV/JSON. It remains a replay-ranking diagnostic, not probability calibration or profitability proof.
