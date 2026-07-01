# Model Proposal Lifecycle

Status date: 2026-07-01

## Purpose

Model proposals convert champion/challenger evidence into a controlled human-review record. They are not automatic deployments.

## Statuses

- `DRAFT`
- `PROPOSED`
- `REVIEW_REQUIRED`
- `REJECTED`
- `APPROVED_FOR_ACTIVATION`
- `ACTIVATED`
- `SUPERSEDED`

## Recommended Actions

- `KEEP_CHAMPION`
- `REVIEW_CHALLENGER`
- `APPROVE_CHALLENGER_FOR_ACTIVATION`
- `REJECT_CHALLENGER`
- `BLOCK_ALL_CHANGES`

Only eligible challenger proposals can be approved for activation. Proposals recommending `KEEP_CHAMPION`, `REJECT_CHALLENGER`, or `BLOCK_ALL_CHANGES` are blocked from approval and activation.

## API

- `GET /research/model-proposals`
- `GET /research/model-proposals/{proposal_id}`
- `POST /research/model-proposals/{proposal_id}/approve`
- `POST /research/model-proposals/{proposal_id}/reject`
- `POST /research/model-proposals/{proposal_id}/activate`

Approval records `approved_by` and `approved_at`, but does not activate. Activation requires a separate call with `confirm_manual_activation=true` and the existing validation guard. Rejected proposals and `BLOCK` readiness proposals cannot activate.

## Exports

Use `POST /exports/model-proposal.xlsx` or `POST /exports/model-proposal.json` with `run_id` set to the proposal ID. The workbook includes Summary, Recommended Action, Readiness, Champion, Challenger, Delta Metrics, Gates, Rejection Reasons, Approval History, Artifacts, and Provenance.

## Operator UI

Phase 12 exposes proposals through `/research/proposals` and `/research/proposals/{proposal_id}`. The list page is review/export oriented. The detail page shows evidence summary, champion metrics, challenger metrics, delta metrics, pass/fail gates, rejection reasons, related artifact IDs, and proposal-scoped decision-ledger rows.

Approval and activation remain separate UI actions. The approve button calls only `POST /research/model-proposals/{proposal_id}/approve`. The activation panel stays disabled unless the proposal status is `APPROVED_FOR_ACTIVATION`, the operator checks the explicit confirmation box, and the operator types `ACTIVATE SCANNER MODEL`. Only then does the UI send `confirm_manual_activation=true`.
