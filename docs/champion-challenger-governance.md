# Champion/Challenger Governance

Status date: 2026-07-01

## Purpose

Champion/challenger comparison is a diagnostic review step between persisted model evidence and model proposal creation. It compares the active champion against a challenger or, when no champion exists, evaluates the challenger against minimum gates.

## Inputs

- champion model version
- challenger model version
- explicit validation report IDs when supplied
- calibration audit IDs
- calibration drift report IDs
- model review report IDs
- stale-window status
- data-quality summary
- replay, counterfactual, portfolio, and sensitivity source IDs through cycle context

## Outputs

The persisted comparison stores champion metrics, challenger metrics, delta metrics, better/worse flags, pass/fail gates, recommended action, readiness status, warnings, and context.

## Rules

- Comparison never activates a model.
- Missing challenger recommends `KEEP_CHAMPION` or `BLOCK_ALL_CHANGES`.
- `BLOCK` readiness recommends rejection.
- Passing gates with a stronger challenger can recommend `APPROVE_CHALLENGER_FOR_ACTIVATION`.
- A worse challenger can recommend `KEEP_CHAMPION`.

Use `POST /exports/champion-challenger-comparison.xlsx` with `run_id` set to the comparison ID for the workbook report.

## Operator UI

Phase 12 surfaces comparison evidence through proposal detail pages rather than adding a separate comparison workbench. Operators review champion, challenger, delta, readiness, and gate summaries on `/research/proposals/{proposal_id}` before approving or rejecting a proposal. Comparison exports remain available from proposal/cycle context when the persisted comparison ID is known.
