# Phase 19B Completion - Runtime Evidence Recovery Or Regeneration

Date: 2026-07-04

## Final Status

`PHASE_19_STATUS = BLOCKED_INFRA`

Secondary data status: `BLOCKED_NO_DATA`

Phase 19B did not recover the original July 3 runtime artifacts and did not regenerate Phase 19. The runtime still cannot provide certifiable Phase 19 evidence because Postgres migrations are blocked, Python is below the documented target version, and the current SQLite runtime has no real bars or quote snapshots. Since `FMP_API_KEY` is absent, bounded live refresh cannot run.

## Evidence Recovery Result

Recovery status: `NOT_RECOVERED`

- Expected Phase 19 export filenames were not found.
- Expected Phase 19 replay/research IDs were found only in committed docs.
- `exports/` contains only `.gitkeep`.
- Current SQLite does not contain July 3 Phase 19 rows.
- Docker did not reveal a recoverable older project volume with Phase 19 evidence.

See `docs/status/PHASE_19B_EVIDENCE_RECOVERY_2026-07-04.md`.

## Runtime Repair Result

Runtime repair status: `BLOCKED_INFRA`

- Python: only `3.14.4` is available; target is `3.14.6`.
- Redis: `adaptive-market-decoder-redis` is healthy in-container, but host `6379` remains owned by another container.
- Postgres: container is healthy, but `make db-migrate` fails at `0008_phase11_research_governance.py` with duplicate `research_cycles`.
- Postgres public app tables: 0.
- `alembic_version`: absent.

Observed migration root cause: `0001_initial.py` uses current `metadata.create_all`, which creates later-phase tables before later migrations try to create them again.

See `docs/status/PHASE_19B_RUNTIME_REPAIR_2026-07-04.md`.

## Data Availability Result

Data status: `BLOCKED_NO_DATA`

Current SQLite runtime:

- `bars`: 0
- `quote_snapshots`: 0
- `pipeline_build_windows`: 0
- `features`: 0
- `candidate_signals`: 0
- `labels`: 0
- `replay_runs`: 0
- `simulated_trades`: 0
- `data_freshness_reports`: 0
- `research_cycles`: 0
- `exports`: 0

`FMP_API_KEY` is absent. `make fmp-smoke` skipped safely with all eight required endpoints marked `SKIPPED_NO_KEY`; no provider refresh or seed ran.

## Rebuild Evidence

No regenerated rebuild evidence exists.

| Artifact | Phase 19B Result |
| --- | --- |
| Dirty-window audit | not regenerated |
| Features | blocked by no persisted bars |
| Candidate signals | blocked by no rebuilt features |
| Labels | blocked by no bars/features/candidates |
| Replay | blocked by no bars/features/candidates |
| Freshness after-state | not regenerated |
| Strict research-cycle dry run | not regenerated |
| Diagnostic `allow_stale=true` | not run |
| Exports | not generated |

## Freshness Before/After

Before remains the Phase 18 baseline:

- Default-universe freshness: `STALE`, 0 missing groups, 40 stale groups, 400 dirty windows.
- Research-cycle-scope freshness: `STALE`, 0 missing groups, 12 stale groups, 160 dirty windows.

After Phase 19B:

- No accepted regenerated after-state exists.
- No strict dry-run result exists.

## Commands Run

Runtime/git:

- `git status --short --branch`: repository on `main...origin/main` with Phase 19A/19B docs uncommitted.
- `git log --oneline -10`: latest committed Phase 19 code is `a52145b feat: add phase 19 artifact readiness`.
- `git rev-parse HEAD`: `a52145b9f655682c94969a36ddffa9da63630e37`.
- `git diff --stat`: docs-only Phase 19A/19B changes.
- `git diff --check`: passed.
- `make doctor`: completed with warnings for Python `3.14.4` vs target `3.14.6`, missing `DATABASE_URL`, and missing `FMP_API_KEY`.
- `python3.14 --version`: `Python 3.14.4`.
- `services/quant-engine/.venv/bin/python --version`: `Python 3.14.4`.

Docker/database:

- `docker compose config`: passed.
- `docker compose up -d postgres redis`: Postgres running; Redis running/healthy in-container.
- `docker compose ps`: Postgres healthy on host `15432`; Redis healthy but no host port published in `docker ps`.
- `make db-migrate`: failed with duplicate `research_cycles`.
- `make db-inspect`: failed because `alembic_version` is absent.
- `make db-query-diagnostics`: failed because `alembic_version` is absent.

Provider/data:

- `make fmp-smoke`: skipped safely because `FMP_API_KEY` is absent.
- SQLite table counts confirmed no real bars, quotes, rebuilt artifacts, replay runs, freshness reports, research cycles, or exports.

## Tests Run

Passed:

- `make quant-test`: 101 passed.
- `make backend-lint`: passed.
- `make backend-typecheck`: passed.
- `make api-smoke-sqlite`: 1 passed.
- `make data-freshness-test`: 6 passed.
- `make fmp-entitlement-test`: 3 passed.
- `make fmp-ingestion-test`: 4 passed.
- `make fmp-seed-test`: 5 passed.
- `make data-quality-test`: 1 passed.
- `make scheduler-test`: 15 passed.
- `make export-test`: 5 passed.
- `make replay-test`: 10 passed.
- `make replay-sensitivity-test`: 3 passed.
- `services/quant-engine/.venv/bin/python -m pytest services/quant-engine/tests/quant/test_phase19_artifact_readiness.py -q`: 4 passed.
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm check`: passed.
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm build`: passed.
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm test`: passed, no frontend/shared test files.
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm lint`: passed.
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm --filter @amd/web test:e2e`: 11 passed.
- `python3 -m compileall services/quant-engine/app services/quant-engine/tests`: passed.

Failed:

- `make backend-test`: 122 passed, 2 failed; failures are Postgres API smoke and Postgres repository parity blocked by incomplete migrations.
- `make api-smoke-postgres`: failed because Postgres migrations are incomplete.
- `make repository-parity-test`: SQLite path passed; Postgres path failed because migrations are incomplete.

## Secret Scan Result

`FMP_API_KEY` and `DATABASE_URL` are absent from the runtime environment.

Targeted scans found no live secret values in source/docs, generated frontend output, exports, data, or model artifact folders. Expected placeholder hits remain limited to redaction tests and documentation examples such as `apikey=super-secret`.

## Code And Docs Changes

No application code was changed.

Docs created:

- `docs/status/PHASE_19B_PLAN_2026-07-04.md`
- `docs/status/PHASE_19B_EVIDENCE_RECOVERY_2026-07-04.md`
- `docs/status/PHASE_19B_RUNTIME_REPAIR_2026-07-04.md`
- `docs/status/PHASE_19B_REGENERATION_RESULTS_2026-07-04.md`
- `docs/status/PHASE_19B_COMPLETION_2026-07-04.md`

Docs updated:

- `docs/status/PHASE_19_COMPLETION_2026-07-03.md`
- `docs/status/PHASE_19_DIRTY_WINDOW_AUDIT_2026-07-03.md`
- `docs/status/PHASE_19_REBUILD_RESULTS_2026-07-03.md`
- `docs/status/PHASE_19_RESEARCH_CYCLE_DRY_RUN_2026-07-03.md`
- `docs/live-data-artifact-readiness.md`
- `docs/HANDOFF.md`

## Critical Blockers

1. Original July 3 Phase 19 runtime evidence is still missing.
2. Postgres migrations are broken on fresh local runtime due duplicate table creation.
3. Python `3.14.6` is not available; current runtime is `3.14.4`.
4. Real bars/quote snapshots are absent from SQLite.
5. `FMP_API_KEY` is absent, so real FMP seed/refresh cannot run.

## Remaining Risks

- Committed Phase 19 docs may be accurate, but they are still not independently certified by recovered runtime artifacts.
- A migration repair is likely needed before Postgres gates can pass.
- If the original July 3 artifacts cannot be recovered, regeneration will require a real FMP runtime key and a healthy database path.
- Redis host-port behavior should be clarified if external Redis access is required.

## Exact Next Recommended Phase

`PHASE 19C - Postgres Migration Repair And Real-Data Regeneration`

Recommended scope:

1. Repair Alembic migration history so `make db-migrate`, `make db-inspect`, `make db-query-diagnostics`, `make api-smoke-postgres`, and `make repository-parity-test` pass on a clean database without destructive assumptions.
2. Install or point the project to Python `3.14.6`.
3. Provide `FMP_API_KEY` through runtime environment only.
4. Regenerate Phase 18 seed and Phase 19 artifact readiness from real data.
5. Certify Phase 19 only after runtime rows and exports exist.
