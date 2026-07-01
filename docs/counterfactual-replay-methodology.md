# Counterfactual Replay Methodology

Status date: 2026-07-01

`model_training_counterfactual` replay estimates independent candidate quality. It is not portfolio P/L, not an execution engine, and not a profitability claim.

## Concepts

- `label_derived`: fast leakage-safe research labels.
- `candidate_market_replay`: portfolio-style candidate replay with overlap, portfolio limits, cooldowns, and execution-style constraints.
- `model_training_counterfactual`: independent candidate replay for model evidence. Valid candidates are measured without portfolio max-open, one-open-per-symbol, setup-overlap, or cooldown suppression.

## Counterfactual Rules

Counterfactual replay keeps the same OHLCV simulation assumptions as candidate market replay:

- next-bar-open entry;
- signal-time stop and target plans;
- conservative same-bar stop-first policy by default;
- slippage, spread, time exits, session exits, MFE, and MAE;
- no future construction of stops or targets.

It does not mutate global portfolio state. An overlapping candidate can receive an observed outcome even if a portfolio replay would have skipped it.

It still skips invalid or unmeasurable candidates:

- invalid risk plans;
- outside-session candidates;
- missing entry/future bars;
- insufficient context;
- stale/data-quality blocks;
- reward/risk below configured minimum.

## Persisted Metadata

Counterfactual runs are stored in `replay_runs` with `simulation_type = model_training_counterfactual` and `replay_purpose = model_training_counterfactual` in config/metrics JSON. `simulated_trades.metadata` stores:

- `replay_purpose`;
- `candidate_quality_mode`;
- `candidate_quality_label = candidate_quality_evidence`;
- `counterfactual_observed`;
- `counterfactual_status = COUNTERFACTUAL_OBSERVED`;
- `portfolio_blocked_in_execution_replay`;
- `concurrent_candidate_count_at_signal`;
- `overlap_density`;
- `overlap_group_id`;
- `concurrency_bucket`.

These JSON metadata fields are intentional; no separate trade columns were added in Phase 9.

## Use

Run from the API with:

```json
{
  "replay_purpose": "model_training_counterfactual",
  "symbols": ["AAPL"],
  "intervals": ["1min"],
  "start": "2026-06-01T13:30:00Z",
  "end": "2026-06-01T20:00:00Z"
}
```

Replay-aware training defaults to `outcome_source = counterfactual_preferred`, so counterfactual outcomes become candidate-quality evidence when available. Portfolio replay remains useful for constraint drag, validation, and deployment analysis.
