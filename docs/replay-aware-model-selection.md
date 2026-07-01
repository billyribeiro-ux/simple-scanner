# Replay-Aware Model Selection

Status date: 2026-07-01

## Purpose

The replay-aware baseline model turns persisted `candidate_market_replay` outcomes into deterministic evidence cells and candidate score audits. It is a model-selection and signal-suppression layer only. It is not a broker, not order routing, not self-learning, not calibrated probability, and not a profitability claim.

## Candidate Outcome Dataset

Training starts from persisted replay runs and `simulated_trades` rows. Taken trades are observed outcomes. Skipped candidates are preserved, but skip reasons are interpreted carefully:

- `overlapping_trade`, `portfolio_trade_limit`, `cooldown_active`, `duplicate_candidate`, `missing_entry_bar`, `no_future_bars`, and stale-data skips are unobserved outcomes, not losses.
- `invalid_risk_plan`, `insufficient_context`, `insufficient_reward_risk`, `regime_filter_block`, `outside_session`, and `data_quality_block` can inform suppression rules.
- Stale replay runs are rejected by default unless `allow_stale=true` is explicit.

Rows include candidate ID, replay run ID, symbol, interval, side, setup, timestamp, session date, time bucket, regimes, replay provenance hashes, execution assumptions, prices, realized R, MFE/MAE, ambiguity, sensitivity robustness, fragility flags, label-vs-replay divergence flags, stale status, and data-quality flags.

## Evidence Cube

Evidence cells aggregate replay outcomes by this hierarchy:

1. symbol + side + setup + regime + time bucket
2. symbol + side + setup + regime
3. symbol + side + setup
4. side + setup + regime
5. side + setup
6. side global

Low-sample exact evidence is shrunk toward broader parent evidence. This protects the scanner from treating one lucky symbol/setup/time bucket as durable edge.

Metrics include sample count, observed outcomes, win/loss rate, average/median/expectancy R, total R, profit factor, drawdown, MFE/MAE, target/stop rates, same-bar ambiguity, sensitivity robustness, fragility flags, divergence flags, stale warnings, lower bound R, and evidence quality grade.

## Training

Train through the existing endpoint:

```bash
curl -s -X POST http://localhost:8000/models/train \
  -H 'content-type: application/json' \
  -d '{
    "model_type":"replay_aware_baseline",
    "symbols":["AAPL","SPY"],
    "intervals":["1min"],
    "training_start":"2026-06-01T13:30:00+00:00",
    "training_end":"2026-06-01T19:59:00+00:00",
    "replay_run_ids":["{replay_run_id}"],
    "minimum_observed_outcomes":5,
    "minimum_cell_sample_size":5,
    "shrinkage_strength":20
  }'
```

The model run stores replay run IDs, sensitivity IDs when present, replay config hashes, input fingerprints, candidate fingerprints, scoring config, evidence cell count, metrics summary, and warnings. Evidence cells persist in `model_evidence_cells`.

## Validation And Activation

Replay-aware validation mode is:

```text
replay_aware_walk_forward
```

It scores validation candidates chronologically using only prior replay outcomes. A replay-aware model activates only through an accepted `replay_aware_validation` report:

```bash
curl -s -X POST 'http://localhost:8000/models/validate?model_version={model_version}&validation_mode=replay_aware_walk_forward'
curl -s -X POST 'http://localhost:8000/models/activate?model_version={model_version}&validation_mode=replay_aware_walk_forward'
```

The validation report records selected vs suppressed candidates, selected replay metrics, per-symbol/setup/regime/time-bucket breakdowns, sensitivity summary, stale status, and rejection reasons.

## Scoring And Audits

Score persisted or inline candidates with:

```bash
curl -s -X POST http://localhost:8000/models/{model_version}/score-candidates \
  -H 'content-type: application/json' \
  -d '{"candidate_ids":["{candidate_id}"],"persist_audit":true}'
```

Retrieve evidence and score audits:

```bash
curl -s http://localhost:8000/models/{model_version}/evidence
curl -s http://localhost:8000/models/{model_version}/score-audits
```

Score audits persist the action, grade, component scores, suppression reasons, evidence keys used, warnings, and model/scoring config versions. They must not contain secrets.

## Counterfactual Replay Status

Phase 8 documents the candidate outcome dataset design but does not add an independent counterfactual replay purpose. Portfolio-overlap skips remain unobserved unless a future explicit `model_training_counterfactual` replay mode independently simulates each candidate and labels that output as non-portfolio evidence.
## Phase 9 Update

Replay-aware training now defaults to `outcome_source = counterfactual_preferred`. When `model_training_counterfactual` replay runs are supplied, the evidence cube uses those independent candidate-quality outcomes before falling back to portfolio replay. Portfolio replay outcomes remain separately tracked for constraint analysis.

Training accepts `counterfactual_replay_run_ids`, `portfolio_replay_run_ids`, `require_counterfactual`, `minimum_counterfactual_outcomes`, `maximum_portfolio_only_fraction`, overlap-density filters, and concurrency-bucket filters. Model artifacts record the selected replay IDs, outcome source, counterfactual observed count, portfolio observed count, and portfolio-only fraction.

This remains deterministic evidence scoring, not black-box ML, not self-learning, and not a profitability claim.
