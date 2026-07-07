# Phase 19A Completion - Execution Evidence Reconciliation

Date: 2026-07-04

## Final Certification Status

`PHASE_19_STATUS = EVIDENCE_PENDING`

Phase 19 is present in committed code and committed documentation at HEAD `a52145b9f655682c94969a36ddffa9da63630e37` (`feat: add phase 19 artifact readiness`). The committed Phase 19 docs report a successful July 3 artifact rebuild and strict dry run.

However, the actual ignored runtime evidence from that July 3 run was not present in this checkout. The current local SQLite database is newly created and empty, the `exports/` directory contains only `.gitkeep`, and the local Postgres migration path is blocked. Therefore Phase 19 cannot be certified complete from this runtime.

## Evidence Source

- Repository: `/Users/billyribeiro/Desktop/simple-scanner/simple-scanner`
- Branch: `main`
- Tracking: `main...origin/main`
- HEAD: `a52145b9f655682c94969a36ddffa9da63630e37`
- Latest commit: `a52145b feat: add phase 19 artifact readiness`
- Working tree before doc updates: clean, with ignored generated/runtime artifacts only after checks.
- Runtime evidence available in this checkout: fresh empty SQLite DB, no Phase 19 export files, Postgres compose database not migrated.

## Git State

Commands run:

- `git status --short --branch`: `## main...origin/main`
- `git log --oneline -10`: latest commit `a52145b feat: add phase 19 artifact readiness`
- `git rev-parse HEAD`: `a52145b9f655682c94969a36ddffa9da63630e37`
- `git diff --stat`: no output before doc updates
- `git diff --check`: passed

Phase 19 changes appear committed in `a52145b`, but runtime artifacts needed for independent certification are ignored and absent.

## Runtime And Database Status

`make doctor` completed with warnings:

- Node `24.18.0`: ok
- Corepack/pnpm `11.9.0`: ok
- Python target file: `3.14.6`
- Installed `python3.14`: `3.14.4`, warning
- Backend venv: created during Phase 19A using Python `3.14.4`, warning against target `3.14.6`
- `DATABASE_URL`: absent, SQLite fallback active
- `FMP_API_KEY`: absent, live FMP refresh blocked
- Docker daemon and compose: available

Docker:

- `docker compose config`: passed and showed Postgres on host port `15432`, Redis on host port `6379`.
- `docker compose up -d postgres redis`: failed to start Redis because host port `6379` was already allocated by another container.
- `docker compose ps`: Postgres `adaptive-market-decoder-postgres` was running and healthy on `15432`; Redis for this project was not running.

Postgres:

- `make db-migrate`: failed at migration `0008_phase11_research_governance.py` with `DuplicateTable: relation "research_cycles" already exists`.
- `make db-inspect`: failed because `alembic_version` did not exist.
- `make db-query-diagnostics`: failed because `alembic_version` did not exist.
- Read-only `psql` inspection after the failed migration showed zero public tables and no `alembic_version`.

SQLite:

- `data/local_repo.sqlite3` exists from this Phase 19A check run.
- Runtime row counts are all zero for `bars`, `quote_snapshots`, `pipeline_build_windows`, `features`, `candidate_signals`, `labels`, `replay_runs`, `simulated_trades`, `data_freshness_reports`, `research_cycles`, and `exports`.
- This SQLite DB does not contain the July 3 Phase 19 operational evidence.

## Dirty-Window Audit Before/After

Committed Phase 19 docs report:

- Initial audit: 560 dirty windows.
- Initial dirty windows by artifact: 140 `features`, 140 `candidates`, 140 `labels`, 140 `replay`.
- Final audit: 0 dirty windows.
- Daily `1day` replay windows: 40 marked clean as `candidate_market_replay_is_intraday_only`.

Runtime verification in this checkout:

- Current SQLite `pipeline_build_windows`: 0 rows.
- Current SQLite dirty windows: 0 rows.
- No Phase 19 dirty-window export files are present under `exports/`.

Conclusion: committed docs contain before/after values, but current runtime cannot independently prove them.

## Feature Rebuild Evidence

Committed Phase 19 docs report:

- 11999 persisted bars read.
- 11999 features written.
- 140 feature dirty windows cleared.
- No FMP calls.

Runtime verification in this checkout:

- Current SQLite `bars`: 0.
- Current SQLite `features`: 0.
- Feature rebuild evidence export is absent from `exports/`.

Conclusion: feature rebuild evidence is documentary only in this checkout.

## Candidate Rebuild Evidence

Committed Phase 19 docs report:

- 11999 features read.
- 14976 candidate rows written on final all-interval pass.
- 7711 actionable candidates observed.
- 140 candidate dirty windows cleared.

Runtime verification in this checkout:

- Current SQLite `features`: 0.
- Current SQLite `candidate_signals`: 0.
- Candidate rebuild evidence export is absent from `exports/`.

Conclusion: candidate rebuild evidence is documentary only in this checkout.

## Label Rebuild Evidence

Committed Phase 19 docs report:

- 14976 candidate rows read.
- 2088 label rows written.
- 140 label dirty windows cleared.
- Skipped/unobserved candidates were not counted as losses.

Runtime verification in this checkout:

- Current SQLite `candidate_signals`: 0.
- Current SQLite `labels`: 0.
- Label rebuild evidence export is absent from `exports/`.

Conclusion: label rebuild evidence is documentary only in this checkout.

## Replay Rebuild Evidence

Committed Phase 19 docs report:

- Small replay scope: `SPY,QQQ,AAPL,NVDA`, `1min`.
- Small replay IDs: `replay_20260703132342_48a6b35debfd62244361ea09`, `replay_20260703132343_df74191456eb8e03eaec364e`.
- Default intraday replay IDs: `replay_20260703132536_549bebf359fa0e6d9261108a`, `replay_20260703132540_d77a7add68d69518dc6b1c4a`.
- Daily replay cleanup: 40 `1day` replay windows marked not applicable.

Runtime verification in this checkout:

- Current SQLite `replay_runs`: 0.
- Current SQLite `simulated_trades`: 0.
- Replay report exports are absent from `exports/`.

Conclusion: replay rebuild evidence is documentary only in this checkout.

## Freshness Before/After

Phase 18 baseline:

- Default-universe freshness: `STALE`, 0 missing groups, 40 stale groups, 400 dirty windows.
- Research-cycle-scope freshness: `STALE`, 0 missing groups, 12 stale groups, 160 dirty windows.
- Strict research cycle blocked on `stale_artifacts_present`.
- Diagnostic `allow_stale=true` completed with `model_activation_unchanged=true`, `proposal_status=REVIEW_REQUIRED`, `recommended_action=BLOCK_ALL_CHANGES`.

Committed Phase 19 docs report:

- Default wall-clock freshness after rebuild: `STALE`, warning `freshness_stale_required_data`.
- Research historical-reference freshness after rebuild: `READY`, no warnings.
- Dirty-window blocker removed.

Runtime verification in this checkout:

- Current SQLite `data_freshness_reports`: 0.
- Freshness export is absent from `exports/`.

Conclusion: freshness improvement is recorded in committed docs but not independently provable from the current runtime.

## Strict Research-Cycle Dry Run

Committed Phase 19 docs report:

- Symbols: `SPY,QQQ,AAPL,NVDA`
- Interval: `1min`
- Window: `2026-07-01T13:30:00+00:00` through `2026-07-02T19:59:00+00:00`
- `allow_stale=false`
- `refresh_data=false`
- Research cycle: `research_cycle_b3e371c34dccba95c8eb29ff3e657bca`
- Result: `ok`
- Strict blocked: `false`
- Diagnostic `allow_stale=true`: not run
- Model activation: unchanged

Runtime verification in this checkout:

- Current SQLite `research_cycles`: 0.
- Research-cycle dry-run export is absent from `exports/`.

Conclusion: strict dry-run pass is documented but not independently provable from current runtime rows.

## Export Verification

Committed docs list the expected Phase 19 exports and SHA-256 hashes:

- `phase19_dirty_window_audit_20260703T132337_ca95334fb939.json`
- `phase19_dirty_window_audit_20260703T132707_ab43f50a2625.json`
- `phase19_feature_rebuild_report_20260703T132340_9a603451ed54.json`
- `phase19_candidate_rebuild_report_20260703T132535_b53a870c1991.json`
- `phase19_label_rebuild_report_20260703T132536_fb4fa48ac8b0.json`
- `phase19_replay_report_20260703T132544_d8beb5f13450.json`
- `phase19_replay_report_20260703T132706_24c375e58c47.json`
- `phase19_freshness_report_20260703T132707_7628fa1fd58c.json`
- `phase19_research_cycle_dry_run_report_20260703T132707_b35201ab340d.json`

Runtime verification:

- `exports/` contains only `.gitkeep`.
- Current SQLite `exports`: 0 rows.
- Export hashes cannot be independently verified from this checkout.

## Commands Run And Results

Passed:

- `make doctor` completed with warnings for Python version drift, missing `DATABASE_URL`, and missing `FMP_API_KEY`.
- `docker compose config`
- `docker compose ps` after attempted startup showed healthy Postgres.
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
- `make scheduler-status`: ok, SQLite backend, zero queued/running/completed/failed/cancelled jobs.
- `make scheduler-worker-once`: ok, bounded one-shot, zero jobs run.
- `make scheduler-recover-stale`: ok, zero jobs recovered.
- `make export-test`: 5 passed.
- `make replay-test`: 10 passed.
- `make replay-sensitivity-test`: 3 passed.
- `services/quant-engine/.venv/bin/python -m pytest services/quant-engine/tests/quant/test_phase19_artifact_readiness.py -q`: 4 passed.
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm check`: passed.
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm build`: passed.
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm test`: passed with no frontend/shared test files.
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm lint`: passed.
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm --filter @amd/web test:e2e`: 11 passed.
- `python3 -m compileall services/quant-engine/app services/quant-engine/tests`: passed.
- `git diff --check`: passed.

Failed or blocked:

- `docker compose up -d postgres redis`: Postgres started; Redis failed because host port `6379` was already allocated.
- `make db-migrate`: failed at `0008_phase11_research_governance.py` with `DuplicateTable: relation "research_cycles" already exists`.
- `make db-inspect`: failed because `alembic_version` did not exist.
- `make db-query-diagnostics`: failed because `alembic_version` did not exist.
- `make backend-test`: 122 passed, 2 failed; failures were the Postgres API smoke and Postgres repository parity tests blocked by incomplete migrations.
- `make api-smoke-postgres`: failed because Postgres migrations are incomplete.
- `make repository-parity-test`: SQLite parity path passed, Postgres path failed because Postgres migrations are incomplete.

Not run:

- Live FMP smoke/refresh commands. `FMP_API_KEY` was absent and Phase 19A did not require a live provider refresh.
- Actual Phase 19 artifact rebuild against real FMP bars. Current runtime has no persisted bars.

## Secret Scan Result

Environment:

- `FMP_API_KEY`: absent
- `DATABASE_URL`: absent

Targeted scans:

- Source/docs excluding dependency caches found only expected redaction-test/example hits for `apikey=super-secret` and Makefile/docs placeholder `DATABASE_URL` usage.
- Generated frontend output scan found no `FMP_API_KEY`, `DATABASE_URL`, `apikey=`, or `sk-...` patterns.
- `exports/`, `data/`, and `model_artifacts/` scan found no `FMP_API_KEY`, `DATABASE_URL`, `apikey=`, or `sk-...` patterns.

Conclusion: no live secret leak was found in this Phase 19A checkout. This does not verify absent July 3 ignored exports because those files are not present.

## Code And Docs Changes Made

Phase 19A made documentation-only updates:

- Added `docs/status/PHASE_19A_PLAN_2026-07-04.md`.
- Added `docs/status/PHASE_19A_COMPLETION_2026-07-04.md`.
- Added Phase 19A audit addenda to Phase 19 status/runbook docs.

No application code was changed.

## Critical Blockers

1. The July 3 Phase 19 runtime SQLite database and export files are absent from this checkout.
2. Current SQLite runtime is fresh and empty, so it cannot prove Phase 19 rebuild counts, replay run IDs, freshness reports, research-cycle rows, or export metadata.
3. Postgres migration is blocked and Postgres runtime checks fail.
4. Redis compose service cannot start because host port `6379` is already allocated.
5. Local Python is `3.14.4`, while the project target is `3.14.6`.
6. `FMP_API_KEY` is absent, so no live provider refresh could be run. This is acceptable for Phase 19A unless a bounded refresh is explicitly requested, but it limits live-data regeneration.

## Remaining Risks

- The committed Phase 19 documentation may be accurate, but the underlying ignored runtime artifacts cannot be audited here.
- Postgres may need a non-destructive repair or an approved dev-volume reset before Postgres gates can pass.
- Redis port conflict should be resolved or compose should use an alternate host port before declaring full runtime health.
- Python should be upgraded to `3.14.6` before final acceptance if strict runtime parity matters.
- Export metadata with `file_sha256`, source IDs, artifact versions, workbook sheets, and row counts cannot be verified without the actual export files or regenerated real-data artifacts.

## Paths To Phase 19/19A Docs

- `docs/status/PHASE_19A_PLAN_2026-07-04.md`
- `docs/status/PHASE_19A_COMPLETION_2026-07-04.md`
- `docs/status/PHASE_19_PLAN_2026-07-03.md`
- `docs/status/PHASE_19_COMPLETION_2026-07-03.md`
- `docs/status/PHASE_19_DIRTY_WINDOW_AUDIT_2026-07-03.md`
- `docs/status/PHASE_19_REBUILD_RESULTS_2026-07-03.md`
- `docs/status/PHASE_19_RESEARCH_CYCLE_DRY_RUN_2026-07-03.md`
- `docs/live-data-artifact-readiness.md`
- `docs/HANDOFF.md`
- `docs/data-freshness-gates.md`
- `docs/fmp-seed-ingestion.md`
- `docs/operator-daily-procedure.md`
- `docs/data-quality-reporting.md`
- `docs/non-autonomous-scheduler.md`

## Exact Next Recommended Phase

`PHASE 19B - Runtime Evidence Recovery Or Regeneration`

Required goal:

Recover the July 3 ignored runtime DB/export files, or explicitly regenerate Phase 19 from persisted real FMP bars in a healthy runtime. Do not reset any database volume until the operator confirms there is no recoverable evidence to preserve. Resolve the Redis port conflict, repair or reset Postgres with approval, align Python to `3.14.6`, then rerun the strict evidence collection and certify Phase 19 only if real runtime rows and exports match the committed reports.
