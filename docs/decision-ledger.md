# Decision Ledger

Status date: 2026-07-01

## Purpose

The decision ledger is an append-only model-governance audit trail. It records why a cycle, proposal, or activation decision happened without storing secrets.

## Decision Types

- `CYCLE_CREATED`
- `CYCLE_COMPLETED`
- `PROPOSAL_CREATED`
- `PROPOSAL_APPROVED`
- `PROPOSAL_REJECTED`
- `MODEL_ACTIVATION_REQUESTED`
- `MODEL_ACTIVATED`
- `MODEL_ACTIVATION_BLOCKED`
- `CHAMPION_RETAINED`

## API

```bash
curl -s 'http://localhost:8000/research/decision-ledger?proposal_id={proposal_id}'
curl -s 'http://localhost:8000/research/decision-ledger?research_cycle_id={research_cycle_id}'
curl -s 'http://localhost:8000/research/decision-ledger?decision_type=MODEL_ACTIVATION_BLOCKED'
```

Supported filters include model version, proposal ID, research cycle ID, decision type, and start/end timestamps.

## Rules

Normal operation appends rows and does not mutate old decisions. Ledger payloads include reason codes, evidence references, actor strings, previous/current model versions, and metadata. They must not include FMP keys, database passwords, full provider credentials, or frontend-exposed secrets.

## Operator UI

Phase 12 exposes the ledger at `/research/decision-ledger`. Filters include model version, proposal ID, research cycle ID, decision type, start timestamp, and end timestamp. Rows link back to proposal and cycle detail pages when IDs are present and show reason codes, evidence refs, actor, status, and timestamp.

## Scheduler Events

Phase 13 scheduler operations use `scheduler_job_events` for queue audit events instead of model-governance decision rows. If a scheduler-run research cycle creates a proposal, the cycle/proposal services still write normal decision-ledger events. Queue events must remain non-secret and cannot represent approval or activation decisions.
