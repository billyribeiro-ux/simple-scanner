# Phase 19 Completion - 2026-07-03

Phase 19 completed the live-data artifact-readiness repair cycle against persisted Phase 18 FMP data. The work added exact dirty-window audit/rebuild support, local-only rebuild endpoints, scheduler jobs, exports, and tests.

## Code Changes

- Added exact `pipeline_build_windows.mark_window_built(...)` support.
- Added `ArtifactReadinessService` for dirty-window audits, feature rebuild, candidate rebuild, label rebuild, replay rebuild, freshness recheck, research-cycle dry run, and sanitized JSON exports.
- Added API endpoints:
  - `GET /pipeline/dirty-windows`
  - `POST /pipeline/rebuild/features`
  - `POST /pipeline/rebuild/candidates`
  - `POST /pipeline/rebuild/labels`
  - `POST /pipeline/rebuild/replay`
  - `POST /pipeline/rebuild/live-data-readiness`
- Added scheduler job types:
  - `rebuild_features`
  - `rebuild_candidates`
  - `rebuild_labels`
  - `run_replay`
- Stopped future `1day` bars from creating replay dirty windows because candidate market replay is intraday-only in V1.
- Added Phase 19 regression tests for exact multi-session cleanup, API normalization of `APPL` to `AAPL`, bounded scheduler rebuild dispatch, and daily replay dirty-window prevention.

## Real-Data Result

- Initial audit: 560 dirty windows.
- Final audit: 0 dirty windows.
- Default freshness: `STALE` because historical bars are stale relative to July 3 wall-clock thresholds.
- Research-scope freshness: `READY`.
- Strict research-cycle dry run: passed with `allow_stale=false`.
- Diagnostic `allow_stale=true`: not run.
- Model activation: unchanged.
- Broker/order/trading capability: absent.

## Verification

Passed on 2026-07-03:

```bash
make doctor
make db-migrate
make db-inspect
make db-query-diagnostics
make quant-test
make backend-test
make backend-lint
make backend-typecheck
make api-smoke-sqlite
make api-smoke-postgres
make repository-parity-test
make data-freshness-test
make fmp-entitlement-test
make fmp-ingestion-test
make fmp-seed-test
make scheduler-test
make export-test
make replay-test
make replay-sensitivity-test
services/quant-engine/.venv/bin/python -m pytest services/quant-engine/tests/quant/test_phase19_artifact_readiness.py -q
python3 -m compileall services/quant-engine/app services/quant-engine/tests
git diff --check
```

Frontend target-runtime gates passed after prepending the NVM Node `24.18.0` bin directory so Corepack resolved pnpm `11.9.0`:

```bash
PATH="/Users/billyribeiro/.nvm/versions/node/v24.18.0/bin:$PATH" COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm check
PATH="/Users/billyribeiro/.nvm/versions/node/v24.18.0/bin:$PATH" COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm build
PATH="/Users/billyribeiro/.nvm/versions/node/v24.18.0/bin:$PATH" COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm test
PATH="/Users/billyribeiro/.nvm/versions/node/v24.18.0/bin:$PATH" COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm lint
PATH="/Users/billyribeiro/.nvm/versions/node/v24.18.0/bin:$PATH" COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm --filter @amd/web test:e2e
```

Raw shell `corepack ...` commands failed before the NVM path correction because the shell default did not expose Corepack and Homebrew Node `25.3.0` has a missing `simdjson` dynamic library. `make frontend-doctor` passed and confirmed Node `24.18.0`, Corepack, pnpm `11.9.0`, SvelteKit `2.68.0`, and strict TypeScript.

Secret scan passed across tracked files, generated frontend output, exports, local data, and model artifact folders: the provided FMP key value was absent. Runtime exports and local databases remain ignored and were not committed.

## References

- `docs/status/PHASE_19_DIRTY_WINDOW_AUDIT_2026-07-03.md`
- `docs/status/PHASE_19_REBUILD_RESULTS_2026-07-03.md`
- `docs/status/PHASE_19_RESEARCH_CYCLE_DRY_RUN_2026-07-03.md`
- `docs/live-data-artifact-readiness.md`
