# Operator UI Guide

Status date: 2026-07-01

The Phase 13 UI is a thin governance and operator surface. It does not connect to brokers, route orders, provide execution controls, or automatically activate scanner models.

## Start

Backend:

```bash
make api-dev
```

Frontend:

```bash
source "$HOME/.nvm/nvm.sh"
nvm use 24.18.0
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack prepare pnpm@11.9.0 --activate
make web-dev
```

Open `http://localhost:5173`.

## Routes

- `/operations`: backend health, persistence status, active model, latest cycle/proposal, stale windows, data quality, scheduler queue summary, and warnings.
- `/operations/scheduler`: bounded queue for data-quality, research-cycle dry-run/run, research-cycle export, and operator-status export jobs.
- `/operations/scheduler/{job_id}`: scheduler job payload, result, warnings, and persisted events.
- `/research`: safe governance hub.
- `/research/cycles`: list and create research cycles, then dry-run, run, or export.
- `/research/cycles/{research_cycle_id}`: inspect one cycle, artifacts, warnings, stale-window state, data quality, and export metadata.
- `/research/proposals`: review model proposals and export proposal workbooks.
- `/research/proposals/{proposal_id}`: inspect evidence, approve, reject, or explicitly activate an approved scanner model.
- `/research/decision-ledger`: filter append-only governance decisions.
- `/research/status`: read-only research governance status.

## Research Cycles

Use `/research/cycles` to create a cycle. Defaults are intentionally conservative:

- session `rth`;
- `refresh_data=false`;
- `allow_stale=false`;
- intervals `1min`, `5min`, and `15min`;
- `max_window_count=20`;
- `run_now=false`.

The form normalizes `APPL` to `AAPL`. Dry-run and run are separate actions. Cycle runs record that model activation is unchanged.

## Proposals

Use `/research/proposals/{proposal_id}` to review evidence before approving or rejecting. Approval records manual review only. It never activates a model.

Activation lives in a separate confirmation panel and requires:

- proposal status `APPROVED_FOR_ACTIVATION`;
- the explicit confirmation checkbox;
- the typed phrase `ACTIVATE SCANNER MODEL`;
- backend guard success after sending `confirm_manual_activation=true`.

The page displays blocked backend responses instead of hiding them.

## Scheduler

Use `/operations/scheduler` for bounded local preparation jobs. The page has no automatic loop, no activation controls, no broker controls, and no trading execution language.

Safe actions:

- create a queued job;
- run one queued job;
- run a bounded pending batch;
- cancel a queued job;
- inspect events and warnings.

Jobs requesting `refresh_data=true` block when `FMP_API_KEY` is missing. The UI only shows non-secret status and backend block reasons.

## Ledger

Use `/research/decision-ledger` to filter by model version, proposal ID, research cycle ID, decision type, and time range. Rows link back to cycle and proposal detail pages when IDs are present.

## Phase 15 Provider/Data UI

- `/operations/provider`: key status, capability matrix, smoke, bounded quote/EOD/intraday/incremental actions, latest ingestion runs, and redacted action results.
- `/operations/data`: data coverage, latest bars, dirty/missing windows, ingestion history, provider request summary, and data-quality payload.
- `/operations`: FMP provider status card linking to provider and data pages.

These pages are data operations only. They do not contain broker execution, order routing, or automatic activation controls.

## Phase 16 Provider/Data UI

`/operations/provider` adds capability review controls, review summary status, and seed dry-run/live buttons. `/operations/data` adds freshness checks and quote snapshot tables. `/operations` shows the latest freshness status.
