# Phase 8 Model Selection Status

Status date: 2026-07-01

## Implemented

- `replay_aware_baseline` model type.
- Candidate outcome dataset builder from persisted replay runs and simulated trades.
- Skip semantics that preserve skipped rows without treating overlap or portfolio-limit skips as losses.
- Evidence cube hierarchy with shrinkage/backoff.
- Deterministic replay-aware meta-scorer with `TAKE`, `WATCH`, and `SUPPRESS` actions.
- Evidence persistence in `model_evidence_cells`.
- Candidate score audit persistence in `candidate_score_audits`.
- Replay-aware training through `POST /models/train`.
- Evidence, scoring, and score-audit APIs.
- Replay-aware chronological validation through `replay_aware_walk_forward`.
- Activation guard requiring accepted replay-aware validation for replay-aware models.
- Scanner preference for active replay-aware models with fallback warning when absent.
- CSV/XLSX exports for model summary, evidence cells, score audits, and validation reports.

## Evidence Hierarchy

The implemented hierarchy is:

1. symbol + side + setup + regime + time bucket
2. symbol + side + setup + regime
3. symbol + side + setup
4. side + setup + regime
5. side + setup
6. side global

Exact cells with low observed outcomes shrink toward broader cells. Tests cover suppression when a tiny positive exact sample conflicts with negative broader evidence.

## Activation Criteria

Replay-aware activation requires:

- an existing model run with `model_type = replay_aware_baseline`;
- a persisted validation report with purpose `replay_aware_validation`;
- `activation_decision = accepted`;
- activation request using `validation_mode = replay_aware_walk_forward`.

## Counterfactual Status

Independent per-candidate counterfactual replay was not implemented. Phase 8 explicitly treats portfolio overlap and portfolio-limit skips as unobserved outcomes and documents `model_training_counterfactual` as the next replay mode to add if the chief architect wants per-candidate evidence outside portfolio constraints.
