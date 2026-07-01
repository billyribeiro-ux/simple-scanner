# Phase 11 Model Proposal Status

Status date: 2026-07-01

Model proposal lifecycle is implemented with SQLite/Postgres parity, proposal approval, rejection, explicit activation, and append-only decision-ledger events.

Implemented routes:

- `GET /research/model-proposals`
- `GET /research/model-proposals/{proposal_id}`
- `POST /research/model-proposals/{proposal_id}/approve`
- `POST /research/model-proposals/{proposal_id}/reject`
- `POST /research/model-proposals/{proposal_id}/activate`
- `GET /research/decision-ledger`
- `GET /operations/research-status`

Guardrails verified:

- proposal approval does not activate;
- activation without `confirm_manual_activation=true` is blocked;
- rejected proposals cannot activate;
- `BLOCK` readiness proposals cannot activate;
- `KEEP_CHAMPION`, `REJECT_CHALLENGER`, and `BLOCK_ALL_CHANGES` recommendations cannot be approved or activated;
- explicit activation still uses accepted validation gates;
- ledger events are written for proposal creation, approval, rejection, activation request, blocked activation, and activation.

Remaining limits: proposal review is API-first in Phase 11. A dedicated operator UI and role-based actor identity are future work.
