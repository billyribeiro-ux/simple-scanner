# Phase 18 Completion

Status date: 2026-07-03

## Summary

Phase 18 completed runtime-key FMP bring-up and real-data seed verification. The FMP key was kept runtime-only. All required REST endpoints were accessible and reviewed. Bounded seed ingestion and incremental refresh ran on real FMP data. Freshness remains `STALE`, so research cycles block by default unless `allow_stale=true` is an explicit operator decision.

No broker execution, order routing, automatic model activation, self-learning behavior, WebSocket production ingestion, or profitability claim was added.

## Runtime

- Node target: `24.18.0`
- pnpm target: `11.9.0`
- Python target: `3.14.6`
- `make doctor`: passed under Node `24.18.0`; only warning was missing `DATABASE_URL`, so SQLite local persistence is used unless Postgres is configured.
- `make frontend-doctor`: passed under Node `24.18.0`; warning was secret-shaped identifiers for expected secret-handling code paths.
- Docker Postgres and Redis: running and healthy.
- Alembic: `0012_phase16_fmp_freshness`

Official version checks used during this phase:

- Python source releases list Python `3.14.6` dated June 10, 2026.
- Node release blog lists Node.js `24.18.0 (LTS)` dated June 24, 2026.
- pnpm release notes list pnpm `11.9` dated June 23, 2026.

## Live FMP

- `make fmp-smoke`: passed; eight required endpoints accessible.
- `make fmp-live-smoke`: passed; eight required endpoints accessible.
- Persisted review summary: `READY`
- Reviewed accessible endpoint count: 8
- Latest reviewed sample counts: quote 1, quote-short 1, batch quote 4, batch quote-short 4, EOD 6, 1min 1170, 5min 468, 15min 156.

See `docs/status/PHASE_18_LIVE_FMP_ENDPOINT_MATRIX_2026-07-03.md`.

## Real Data

- Initial full seed: `ingestion_67f0fb86daeb3de661eb7d4d91d39c79`, `COMPLETED`, 12009 fetched, 12009 inserted, 41 provider requests, 0 errors.
- Current bar rows: 11999
- Current quote snapshots: 10
- Current provider request records: 182
- Post-fix incremental runs: `ingestion_97a9a4a054f4585fffc19aa0d540ed74` and `ingestion_4907dd2706ac17c9e11192e0f66628f5`, each `COMPLETED`, 1976 fetched, 0 inserted, 1976 updated, 12 provider requests.
- Bar count for the post-fix incremental verification stayed flat at 4784 before and after both runs.

See `docs/status/PHASE_18_REAL_SEED_INGESTION_2026-07-03.md`.

## Freshness And Research

- Default-universe freshness: `STALE`, 0 missing, 40 stale groups, 400 dirty windows.
- Latest research-cycle-scope freshness: `STALE`, 0 missing, 12 stale groups, 160 dirty windows.
- Research cycle `research_cycle_032e2882c97523fdfc28d9821afa8162` dry-run blocked on `stale_artifacts_present`.
- Default research-cycle run blocked.
- `allow_stale=true` run completed diagnostically with `model_activation_unchanged=true` and `recommended_action=BLOCK_ALL_CHANGES`.

See `docs/status/PHASE_18_FRESHNESS_RESULTS_2026-07-03.md`.

## Exports

Final regenerated exports:

| Export | Rows | SHA-256 |
| --- | ---: | --- |
| `exports/fmp_entitlement_review_20260703T125106.json` | 8 | `03ae4eea50bf2444b6610f9cce25ca1230a8d5446727754468a554f52c4c44de` |
| `exports/fmp_capability_matrix_20260703T125106.json` | 8 | `6182c42e3dd8b8e0abf245ba39f7c1f34296eeab5d0159a944e3b83071ff27c2` |
| `exports/fmp_quote_snapshots_20260703T125106.csv` | 10 | `c2dfdce368cb42203fdf5d0eb1f02891be94902ddb909953230d555dbd0e7242` |
| `exports/fmp_seed_ingestion_20260703T125106.json` | 2 | `2851988d982dafebdf3df4333d304dbca2b9e3b0be6068b4da0017bd1abc3026` |
| `exports/data_freshness_report_20260703T125106.json` | 10 | `410638f6f0bfbc4c2d22047f533d940b67c49c92980f1c298ecbec1ab63f2863` |
| `exports/fmp_data_coverage_20260703T125106.json` | 40 | `1763b36bfe04998cf20b2feed2474afbcc92149481ed6373c4af855e337e437a` |

Exports are ignored runtime artifacts and are not committed.

## Verification

Passed:

- `make frontend-doctor`
- `make doctor`
- `docker compose config`
- `make db-migrate`
- `make db-inspect`
- `make db-query-diagnostics`
- `make fmp-entitlement-test`
- `make fmp-ingestion-test`
- `make fmp-seed-test`
- `make data-quality-test`
- `make data-freshness-test`
- `make scheduler-test`
- `make export-test`
- `make quant-test`
- `make backend-test`
- `make backend-lint`
- `make backend-typecheck`
- `make api-smoke-sqlite`
- `make api-smoke-postgres`
- `make repository-parity-test`
- `make fmp-smoke`
- `make fmp-live-smoke`
- `corepack pnpm check`
- `corepack pnpm build`
- `corepack pnpm test`
- `corepack pnpm lint`
- `corepack pnpm --filter @amd/web test:e2e`
- `services/quant-engine/.venv/bin/python -m compileall services/quant-engine/app`

Expected non-failing warnings:

- `DATABASE_URL` missing in `make doctor`, so local SQLite persistence is active for API fallback.
- `frontend-doctor` reports secret-shaped identifiers in source because redaction/config code references secret names.
- Starlette `httpx` deprecation warning in backend tests.

## Code Change

Phase 18 includes one narrow fix: FMP bar ingestion now reports actual insert/update counts after idempotent upserts. This was discovered by live incremental verification and covered by a targeted test assertion.
