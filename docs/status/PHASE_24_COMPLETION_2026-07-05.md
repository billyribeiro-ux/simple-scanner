# Phase 24 Completion

`PHASE_24_STATUS = ACCEPTED_NEEDS_MORE_DATA`

Phase 24 completed the pre-registered 15min specialist evidence expansion and out-of-sample cohort validation. It expanded real FMP bars to 33 RTH dates, rebuilt downstream artifacts from persisted bars, recorded freshness and a strict research-cycle dry-run, ran the pre-registered validation, generated hashed exports, and reran tests/scans. No model was activated, no proposal was approved, no broker/order path was used, no production WebSocket ingestion was used, no stale gate was bypassed, no secrets were exposed, and no profitability claim is made.

## Final Result

The specialist hypothesis remains research-only. The expanded base cohort exists, but the stricter signal-time TAKE/WATCH rule selected only 2 OOS candidates, both losses. The result is sample-size blocked and also fails validation, sensitivity, and calibration evidence.

| Item | Result |
|---|---|
| Final status | `ACCEPTED_NEEDS_MORE_DATA` |
| Filter spec hash | `220cbea95476458b0cfd7c78ec4f297dd6bd404f5c101cbafdcda3661d741d5d` |
| Expanded 15min RTH dates | 33 |
| Expanded 1day RTH dates | 33 |
| Base 15min ten-am candidates | 330 |
| OOS scored candidates | 145 |
| Selected TAKE/WATCH candidates | 2 |
| Portfolio avg R / robustness | `-1.000000` / `0.00` |
| Counterfactual avg R / robustness | `-1.000000` / `0.00` |
| Calibration | rejected, `minimum_high_grade_samples_not_met` |
| Active models | 0 |
| Dirty windows | 0 |
| Final evidence audit | `CLEAN`, total rows `206851`, fixture rows `0` |

## Exports

| Export | ID | Rows | Hash |
|---|---|---:|---|
| Validation JSON | `export_c3a5db447522ad7a5bfc6ad228c8c0e5` | 1 | `2d85bd8278895c2736cf141411712021a03dd92cca79e414c0accc27b32af2ca` |
| Selected candidates CSV | `export_c5eb96410e81309e4196a791d1e06969` | 2 | `fda8cb425f246ad24f416bec5c800428774bba15f8e8044630e0e7ac4b0ea6ec` |
| Replay CSV | `export_70d38ebe2dee697ef37acdcb09a6a4ab` | 2 | `625f3ed0b4abef3b51c6b084a3965beb7e6d37e227c873d1c2461481cf4dfbf0` |
| Exploratory CSV | `export_018612b083b4fa670fabdd18dcf07278` | 6 | `c9c67e2ead00242e12c0f0ad44150caa90a2e1763ae54d234df03bac67ab1da9` |
| Workbook | `export_69f5d984065ef5955eeb87931aac530b` | 10 | `405d5af9ce42e801d88f0b279c919b8e714cd6fccb9cca309ff1a45f8ebd0a7d` |

## Verification

- `make doctor` - passed, with expected shell-level `FMP_API_KEY` warning because the key was loaded by app settings from ignored `.env.local`.
- `make db-migrate` - passed.
- `make db-inspect` - passed.
- `make db-query-diagnostics` - passed, dirty windows none.
- `make evidence-db-audit` - preflight passed; final rerun recorded in report pack.
- `make test-db-smoke` - passed.
- `make evidence-guard-test` - passed.
- `make backend-test` against isolated test DB - 132 passed.
- `make backend-lint` - passed.
- `make backend-typecheck` - passed.
- Targeted replay/model/research/export/scheduler/FMP/freshness tests - passed.
- `corepack pnpm check`, `lint`, `test`, `build`, and web e2e - passed.
- `python3 -m compileall` for backend app/tests and Phase 24 work script - passed.
- `git diff --check` - passed.
- Secret scan across source/docs/exports/output/frontend build areas - passed: exact key hits `0`, query-string key hits `0`, suspicious assignments `0`.

## Documentation

- `docs/status/PHASE_24_PLAN_2026-07-05.md`
- `docs/status/PHASE_24_FILTER_SPEC_2026-07-05.md`
- `docs/status/PHASE_24_DATA_EXPANSION_2026-07-05.md`
- `docs/status/PHASE_24_ARTIFACT_REBUILD_2026-07-05.md`
- `docs/status/PHASE_24_PRE_REGISTERED_VALIDATION_2026-07-05.md`
- `docs/status/PHASE_24_EXPLORATORY_COMPARISONS_2026-07-05.md`
- `docs/status/PHASE_24_SPECIALIST_DECISION_2026-07-05.md`
- `docs/status/PHASE_24_COMPARISON_2026-07-05.md`
- `docs/status/PHASE_24_COMPLETION_2026-07-05.md`

Next phase should not activate this specialist. The useful next research action is either a larger future OOS accumulation or a different pre-registered signal-time scoring rule that does not use validation outcomes.
