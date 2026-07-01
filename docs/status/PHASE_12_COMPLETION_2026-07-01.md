# Phase 12 Completion

Status date: 2026-07-01

## What Changed

Phase 12 brings the frontend onto the exact target runtime and adds a thin operator governance UI for controlled research cycles, model proposals, manual activation, decision-ledger review, and research status.

## Files Changed

- Runtime: `.node-version` verified, `package.json`, `apps/web/playwright.config.ts`, `Makefile`, `scripts/frontend_doctor.sh`
- Shared/frontend API: `packages/shared/src/index.ts`, `apps/web/src/lib/api.ts`, `apps/web/src/lib/types.ts`, `apps/web/src/lib/governance.ts`
- UI components: `StatusBadge.svelte`, `JsonPanel.svelte`
- Routes: `/operations`, `/research`, `/research/cycles`, `/research/cycles/[id]`, `/research/proposals`, `/research/proposals/[id]`, `/research/decision-ledger`, `/research/status`
- Tests: `apps/web/tests/governance.spec.ts`
- Docs: README, HANDOFF, runtime setup, governance docs, operator UI guide, manual activation safety, Phase 12 status docs

## Node 24.18.0 Status

Complete. Node `24.18.0` is available through NVM and was used for target-runtime frontend verification.

## Frontend Target Runtime Status

Complete. Exact Corepack commands passed with pnpm `11.5.2`.

## Operator UI Routes

- `/operations`: complete
- `/research`: safe hub complete
- `/research/cycles`: complete
- `/research/cycles/[id]`: complete
- `/research/proposals`: complete
- `/research/proposals/[id]`: complete
- `/research/decision-ledger`: complete
- `/research/status`: complete

## Approval And Activation UX Guardrails

Approval and activation remain separate. Activation is disabled until the proposal is approved, the confirmation checkbox is checked, and the phrase `ACTIVATE SCANNER MODEL` is typed. The frontend sends `confirm_manual_activation=true` only from that explicit activation action.

## Backend Changes

No backend route or activation-guard changes were required.

## Tests Added

`apps/web/tests/governance.spec.ts` covers operations status, research cycle create/dry-run behavior, `APPL` normalization, proposal approve-not-activate behavior, explicit activation confirmation, decision-ledger filters, and absence of secret/execution-control UI labels.

## Commands Run

Passed:

- `node --version`: `v24.18.0`
- `corepack pnpm --version`: `11.5.2`
- `make frontend-doctor`
- `make help`
- `make doctor`: passed with warnings for Docker unavailable, missing optional `DATABASE_URL`, and missing optional `FMP_API_KEY`
- `make setup-backend`
- `docker compose config`
- `make quant-test`: 77 passed
- `make backend-test`: 91 passed, 2 skipped
- `make backend-lint`
- `make backend-typecheck`
- `make api-smoke`
- `make api-smoke-sqlite`
- `make repository-parity-test`: 2 passed, 1 skipped
- `make replay-test`
- `make replay-sensitivity-test`
- `make replay-window-test`
- `make model-review-test`
- `make research-cycle-test`
- `make research-status-test`
- `make export-test`
- `python3 -m compileall services/quant-engine/app services/quant-engine/tests`
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm install --frozen-lockfile`
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm check`
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm build`
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm test`
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm lint`
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm --filter @amd/web test:e2e`: 7 passed
- `git diff --check`
- supplied-key-fragment secret scan

Skipped or blocked:

- `make fmp-smoke`: skipped because `FMP_API_KEY` was not configured in the process environment.
- `docker compose up -d postgres redis`: blocked because Docker socket `/Users/billyribeiro/.docker/run/docker.sock` was unavailable.
- `docker compose ps`: blocked by the same unavailable Docker socket.
- `make db-migrate`, `make db-inspect`, `make db-query-diagnostics`: blocked because Postgres on `localhost:15432` refused connections.
- `make api-smoke-postgres`: skipped because Postgres was unavailable.

## Remaining Risks

- Live FMP entitlement remains unverified until `FMP_API_KEY` is loaded from environment or ignored local env.
- Postgres migration/inspection could not be re-verified in this run because Docker/Postgres was unavailable.
- The UI is intentionally local-first and thin; it depends on backend guard responses for final activation decisions.

## Exact Next Phase

Phase 13 should add a bounded local operator runbook and optional non-autonomous scheduler for daily research cycle preparation, with queue/status visibility only. Keep activation manual and separate.
