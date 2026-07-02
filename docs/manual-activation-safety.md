# Manual Activation Safety

Status date: 2026-07-01

Manual activation updates scanner model state only. It does not trade, route orders, connect to brokers, or bypass backend validation.

## Required Separation

Approval and activation are separate backend calls and separate UI controls:

- `POST /research/model-proposals/{proposal_id}/approve`
- `POST /research/model-proposals/{proposal_id}/activate`

The approve button never calls activation. Playwright coverage verifies this.

## UI Confirmation

The activation control is disabled unless all of these are true:

- proposal status is `APPROVED_FOR_ACTIVATION`;
- the operator checks the explicit manual confirmation box;
- the operator types `ACTIVATE SCANNER MODEL`.

Only then does the frontend send:

```json
{
  "confirm_manual_activation": true
}
```

The backend can still block the request for validation, calibration, readiness, recommendation, or proposal-state reasons. The UI displays the backend response.

## Backend Guards

Activation remains governed by the existing model activation service. Replay-aware scanner models require accepted `replay_aware_walk_forward` validation when that validation mode is requested. Rejected proposals, blocking readiness, keep-champion recommendations, reject-challenger recommendations, and block-all-changes recommendations cannot activate.

## Scheduler Boundary

The Phase 13 scheduler is intentionally outside the activation path. Scheduler jobs can create or run research-cycle preparation work, but they never call proposal approval, proposal rejection, proposal activation, or model activation. The scheduler UI exposes queue run/cancel controls only.

## Non-Goals

No automatic activation, scheduled activation, broker execution, order routing, WebSocket trading feed, options data, self-learning claim, or profitability claim is introduced in Phase 13.
