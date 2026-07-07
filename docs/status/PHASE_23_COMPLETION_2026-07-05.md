# Phase 23 Completion - Diagnostic Candidate Filter Experiment

## Final Status

`PHASE_23_STATUS = ACCEPTED_NO_ROBUST_FILTER`

Phase 23 completed the diagnostic candidate-filter experiment for the 15min `ten_am_reversal_zone` pocket. No filtered subset qualified as a robust future specialist candidate. No model was activated, no proposal was approved, no broker/order path was used, no WebSocket production ingestion was used, no stale gate was bypassed, and no profitability claim is made.

## Evidence Base

| Gate | Result |
|---|---|
| Evidence database | `adaptive_market_decoder_evidence` |
| DB role | `evidence` |
| Fixture rows | `0` |
| Active models | `0` |
| Dirty windows | `0` |
| Bars/features/candidates/labels | `19800` / `19800` / `23882` / `3032` |
| Phase 23 replay runs | `8` |
| Phase 23 sensitivity runs | `8` |
| Phase 23 sensitivity scenarios | `600` |
| Final replay/sensitivity/scenario totals | `34` / `32` / `1548` |
| Final export total | `295` |
| Final evidence audit | `CLEAN`, total rows `184006`, fixture rows `0` |

## Results

| Filter | Classification | Reason |
|---|---|---|
| `P23_FILTER_A_BASE_15M_TEN_AM` | `BLOCKED_BY_SENSITIVITY` | Portfolio robustness `0.44`, counterfactual robustness `0.00`, negative worst cases |
| `P23_FILTER_B_AMBIGUITY_SUPPRESSED` | `BLOCKED_BY_SENSITIVITY` | Robustness worsened and small-cost scenarios failed |
| `P23_FILTER_C_WEAK_FAMILY_SUPPRESSED` | `BLOCKED_BY_LOW_SAMPLE` | 14 candidates, 8 validation trades, still sensitivity-blocked |
| `P23_FILTER_D_TAKE_WATCH_SLICE` | `BLOCKED_BY_LOW_SAMPLE` | Full-grid pass, but only 9 candidates and 6 validation trades |

The TAKE/WATCH slice is useful as a research clue only. Its evidence is too small for Phase 23 specialist-candidate acceptance.

## Source IDs

| Artifact | ID |
|---|---|
| Filter spec hash | `be9de3e9bbe516f882174df8eeebee19f0f66f970e7177f2e1ea287b3289a106` |
| Baseline 15min portfolio replay | `replay_20260705223012_afc4202e318c155d012444f6` |
| Baseline 15min counterfactual replay | `replay_20260705223013_39d7d508606d7e8782962ead` |
| Baseline 15min portfolio sensitivity | `sensitivity_7b270b48d0b1e8580a696a60d82c859e` |
| Baseline 15min counterfactual sensitivity | `sensitivity_90441b99f44ddd04caeddcbaa244419f` |
| Phase 23 workbook export | `export_7bbc12195d37602290209ed3e52411a6` |

Workbook sheets: `Filter Spec`, `Replay Results`, `Sensitivity Results`, `Leakage Split`, `Decision`, `Comparison`, `Export Records`.

## Verification

Passed:

- `make evidence-db-audit`
- `make test-db-smoke`
- `make evidence-guard-test`
- `make backend-test` - 132 passed
- `make backend-lint`
- `make backend-typecheck`
- `make replay-sensitivity-test` - 5 passed
- `make model-review-test` - 6 passed
- `make research-cycle-test` - 4 selected passed
- `make export-test` - 5 passed
- `make scheduler-test` - 15 passed
- `make api-smoke-postgres` - 1 passed
- `make repository-parity-test` - 6 passed
- `corepack pnpm check`
- `corepack pnpm test`
- `corepack pnpm lint`
- `corepack pnpm build`
- `corepack pnpm --filter @amd/web test:e2e` - 11 passed
- `python -m compileall -q services/quant-engine/app scripts`
- `git diff --check`
- `pytest services/quant-engine/tests/test_secrets.py` - 2 passed
- tracked-file secret pattern scan - only redaction code, test placeholders, and safe documentation examples found

The e2e suite initially exposed an existing research-cycle form regression where the symbol input could submit the default symbol list. The page was patched to read the current symbol input value at create time and the cycles table was keyed; Svelte autofixer reported no issues afterward, and e2e passed.

## Documentation

Phase 23 report files:

- `docs/status/PHASE_23_PLAN_2026-07-05.md`
- `docs/status/PHASE_23_FILTER_SPEC_2026-07-05.md`
- `docs/status/PHASE_23_FILTERED_REPLAY_RESULTS_2026-07-05.md`
- `docs/status/PHASE_23_FILTERED_SENSITIVITY_RESULTS_2026-07-05.md`
- `docs/status/PHASE_23_SPECIALIST_CANDIDATE_DECISION_2026-07-05.md`
- `docs/status/PHASE_23_COMPARISON_2026-07-05.md`
- `docs/status/PHASE_23_COMPLETION_2026-07-05.md`

One user-facing consolidated markdown report was also created in the Codex output directory.

