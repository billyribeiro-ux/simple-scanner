# Meta-Scoring Methodology

Status date: 2026-07-01

## Summary

The replay-aware meta-scorer is deterministic and explainable. It converts replay evidence into a `signal_quality_score`, grade, action, expected R estimate, component scores, penalties, suppression reasons, reason codes, warning codes, and evidence keys used.

The score is not a calibrated win probability. It is a ranking and suppression score for candidate research/scanner decisions.

## Output Contract

Each score includes:

- `signal_quality_score` / `meta_score`
- `grade`: `A+`, `A`, `A-`, `B+`, `B`, `C`, or `NO_TRADE`
- `action`: `TAKE`, `WATCH`, or `SUPPRESS`
- `expected_r_estimate`
- risk, evidence, robustness, regime, ticker, time-bucket, and sample-confidence component scores
- fragility, stale-data, label-vs-replay divergence, and ambiguity penalties
- `suppression_reasons`
- `positive_reason_codes`
- `warning_codes`
- `evidence_cell_keys_used`
- `model_version`
- `scoring_config_version`

## Scoring Inputs

Inputs are candidate signal payload, feature snapshot, active replay-aware model config, evidence cells, stale status, sensitivity flags, label-vs-replay divergence flags, and data-quality flags.

Core score components:

- replay expectancy lower bound
- profit factor
- observed outcome sample size
- sensitivity robustness
- drawdown
- reward/risk plan quality
- regime and time-bucket agreement
- ticker evidence behavior
- same-bar ambiguity rate
- label-vs-replay divergence
- stale-window status
- data-quality flags

## Suppression Rules

The scorer suppresses candidates for critical conditions, including:

- no evidence
- insufficient observed outcomes
- negative expectancy after shrinkage
- profit factor below threshold
- low sensitivity robustness
- stale replay evidence when stale blocking is enabled
- excessive same-bar ambiguity dependency
- severe label-vs-replay divergence
- critical data-quality flags
- invalid risk plan
- reward/risk below threshold
- setup blocked by active config
- regime blocked by active config

Suppression lowers the grade to `NO_TRADE` and caps the score. The scanner must not emit high-confidence signals without replay evidence.

## Scanner Behavior

When an active `replay_aware_baseline` model exists, the scanner scores generated candidates through the replay-aware meta-scorer and persists score audits. When no replay-aware model is active, it falls back to the prior baseline and adds `no_replay_aware_model_active` to warnings.

## Limits

The meta-score is not a fill model, not a broker instruction, and not a proof of future returns. Replay remains OHLCV-based and assumption-driven; sensitivity and divergence flags are risk controls, not guarantees.
## Phase 9 Update

Meta-score audits now carry `outcome_source`, and score calibration audits can evaluate whether `signal_quality_score`, grade buckets, and TAKE/WATCH/SUPPRESS actions rank replay outcomes monotonically. The audit is ranking validation only; the score is still not a calibrated probability.

Activation can require a calibration audit. Scanner output reports calibration status through reasons/warnings and suppresses TAKE when a calibration-required active model is missing or failing calibration.

## Phase 11 Governance Use

Champion/challenger comparisons use meta-score-derived model metrics as one diagnostic input alongside validation, calibration, drift, review, data quality, stale windows, concentration, and stability gates. A better meta-score alone is never enough to activate a challenger.

Model proposals preserve champion metrics, challenger metrics, delta metrics, and pass/fail gates. Recommendations are human-review artifacts, not scanner mutations. Proposals with `KEEP_CHAMPION`, `REJECT_CHALLENGER`, or `BLOCK_ALL_CHANGES` recommendations cannot be approved for activation.
