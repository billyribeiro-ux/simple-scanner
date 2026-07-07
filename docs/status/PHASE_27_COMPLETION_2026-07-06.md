# Phase 27 Completion

Status date: 2026-07-06

`PHASE_27_STATUS = ACCEPTED_TEN_AM_DISCARDED_NEXT_FAMILY_SELECTED`

## Executive Summary

Phase 27 formally discards the current 15min `ten_am_reversal_zone` specialist hypothesis and records the failure chain from Phase 22 through Phase 26. The decisive evidence is Phase 26: the all-actionable OOS policy selected 145 candidates, solving the current TAKE/WATCH selected-count problem, but portfolio avg R was `-0.053513`, counterfactual avg R was `-0.057926`, and full-grid robustness was `0.00` for both.

This phase remained research-only. No model was activated, no proposal was approved, no validation/calibration/sensitivity gate was loosened, no OOS threshold was selected, no stale gate was bypassed, no broker/order path was used, no production WebSocket ingestion was used, and no profitability claim is made.

## Ten-AM Discard Decision

`TEN_AM_DISCARD_DECISION = DISCARD_CURRENT_15MIN_TEN_AM_HYPOTHESIS`

Current 15min Ten-AM must not continue as a specialist challenger. It may only be revisited through a materially redesigned, pre-registered hypothesis with a new spec hash.

## Failure Attribution

| Failure class | Result | Evidence |
|---|---|---|
| Evidence sparsity | Yes, secondary. | 79 exact specialist cells, 7 with 5+ outcomes, 0 with 10+ outcomes, 113 of 145 OOS candidates broad-parent-reliant. |
| Negative cohort expectancy | Yes, primary. | Phase 26 all-actionable OOS: portfolio avg `-0.053513`; counterfactual avg `-0.057926`. |
| Sensitivity failure | Yes, primary. | All Phase 26 policies A-H failed full-grid sensitivity with robustness `0.00` in portfolio and counterfactual. |
| Calibration / high grade | Failed. | Phase 24 selected only 2 TAKE candidates; calibration rejected for `minimum_high_grade_samples_not_met`. |
| Governance | Rejected. | Model reviews stayed blocking, proposals stayed rejected, active models stayed `0`. |

## Signal-Family Lessons

Weak families remain broad, not isolated to Ten-AM. Phase 22 attribution showed heavy losses from `NVDA` and `SPY`, longs worse than shorts, `power_hour` and `afternoon_continuation` weak, `chop` largest by regime total loss, and `trend_long` weak by average R. High-ambiguity reversal/failure families should be blocked or redesigned using signal-time proxies only.

## Next Family Recommendation

Next research lead: `trend continuation short`.

This is not activation-ready. It is selected only because Phase 22 showed it was the only setup family with positive source replay attribution: 715 observed trades, total `3.960479R`, avg `0.005539R`, PF `1.009968`, win rate `41.40%`, same-bar rate `5.73%`. No full-grid robust subset was found, and the observed edge is tiny. The next phase must pre-register the diagnostic before OOS evaluation.

## Proposal And Activation Status

| Item | Status |
|---|---|
| Proposal approved | No |
| Model activated | No |
| Active models | 0 |
| Broker/order path | Not used |
| Production WebSocket ingestion | Not used |
| Profitability claim | None |

## Evidence DB Status

Preflight and final audits used `adaptive_market_decoder_evidence` with `AMD_DB_ROLE=evidence`.

Final post-test evidence audit:

| Metric | Value |
|---|---:|
| Contamination status | `CLEAN` |
| Alembic revision | `0012_phase16_fmp_freshness` |
| Total rows | 210461 |
| Fixture rows | 0 |
| Active models | 0 |
| Missing tables | none |
| Dirty windows | none |

The required `docs/status/PHASE_21U_COMPLETION_2026-07-05.md` first-read document remains missing from the checkout. Phase 27 records it as an upstream documentation gap and does not infer its contents.

## Exports And Report Artifacts

There is no dedicated Phase 27 export route for hypothesis-discard Markdown post-mortems. Markdown reports are the Phase 27 report artifacts. Export IDs are therefore `n/a` for Phase 27 Markdown artifacts; Phase 26 source/export IDs remain referenced where relevant.

Source IDs used:

- Phase 25: `phase25_81b88a7a49d13e87`
- Phase 26: `phase26_537f582b33387bf5`
- Phase 26 report pack: `export_2ccdec26381eabeec675c9eb3070a20f`
- Phase 26 report pack SHA-256: `a0c3ba33376a81edb0607d434b23376b6cd8bf6b8aedd4943419617352291c9c`

| Markdown artifact | Lines | SHA-256 |
|---|---:|---|
| `docs/status/PHASE_27_PLAN_2026-07-06.md` | 71 | `02a57c6dcd826f57d5bde39d1b2ce623a94f0d2b512a783c9552c7661c01ed3e` |
| `docs/status/PHASE_27_TEN_AM_HISTORY_2026-07-06.md` | 23 | `f7e3e0bc8f189bd8fbcf78f40dcf14343fa740f6ad23afafe7c73fcb01feb08b` |
| `docs/status/PHASE_27_FAILURE_ATTRIBUTION_2026-07-06.md` | 104 | `5735fd4c01d77c78b72448c21499e6a7d62ff109b73e882ed61b3c94dec4cd49` |
| `docs/status/PHASE_27_SIGNAL_FAMILY_POST_MORTEM_2026-07-06.md` | 68 | `e12387c4dd713be1f8c0febe508fba6d243a65739065f9b9eb318ee412682ddd` |
| `docs/status/PHASE_27_RESEARCH_RULES_2026-07-06.md` | 53 | `9492eadb2b5e0c6c0f36c143bb75aaae56205d20210c6cc32fcfd918a2c64b85` |
| `docs/status/PHASE_27_NEXT_SIGNAL_FAMILY_SELECTION_2026-07-06.md` | 68 | `5307572c336519009c99d8e2a1f63716b356f23764ec841a400425b4610d01d9` |
| `docs/status/PHASE_27_TEN_AM_DISCARD_RECORD_2026-07-06.md` | 78 | `e4249609c6144b820d4e6d7a0240605b97bf6ef661809e7bf8034de07829d440` |
| `docs/live-data-research-cycle-results.md` | 194 | `39786dca735bd69b05d6948d1175b56841ddb7cd192b422b3e21c43871be03c6` |
| `docs/HANDOFF.md` | 950 | `027e58e9a00878aeb88b3f1e626fbe70c0d14cedbd58d5237ff75c29396ca5ee` |

Workbook sheets: `n/a` for Phase 27 Markdown artifacts. Phase 26 workbook sheets remain `Filter Spec`, `Data Sufficiency`, `Days Needed`, `Split Leakage`, `Policy Evaluation`, `Sensitivity Results`, `Phase25 Comparison`, `Decision`, and `Replay Sources`.

## Commands And Tests Run

Passed:

- `make doctor` with expected warnings for missing `DATABASE_URL` in the default shell and missing `FMP_API_KEY`.
- `DATABASE_URL=... AMD_DB_ROLE=evidence make db-migrate`
- `DATABASE_URL=... AMD_DB_ROLE=evidence make db-inspect`
- `DATABASE_URL=... AMD_DB_ROLE=evidence make db-query-diagnostics`
- `DATABASE_URL=... AMD_DB_ROLE=evidence make evidence-db-audit`
- `make test-db-smoke`
- `make evidence-guard-test`
- `make backend-test` (`132 passed, 1 warning`)
- `make backend-lint`
- `make backend-typecheck` (`Success: no issues found`, notes only)
- `make replay-sensitivity-test` (`5 passed`)
- `make model-review-test` (`6 passed`)
- `make research-cycle-test` (`4 passed, 2 deselected`)
- `make export-test` (`5 passed`)
- `make scheduler-test` (`15 passed, 1 warning`)
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm check`
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm build`
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm test`
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm lint`
- `PLAYWRIGHT_PORT=5174 COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm --filter @amd/web test:e2e` (`11 passed`)
- `python3 -m compileall services/quant-engine/app services/quant-engine/tests`
- `git diff --check`
- High-signal secret scan across source, docs, exports, work artifacts, scripts, packages, apps, and frontend output (`high_signal_secret_findings=0`)
- Final post-test `evidence-db-audit`

## Docs Changes Made

- Added Phase 27 plan, history, failure-attribution, signal-family post-mortem, research-rules, next-family-selection, discard-record, and completion reports.
- Updated `docs/live-data-research-cycle-results.md` with Phase 27 status.
- Updated `docs/HANDOFF.md` with Phase 27 outcome and exact next recommended phase.

No application code was changed.

## Critical Blockers

- Current 15min Ten-AM is blocked permanently as a continuation candidate.
- Exact specialist cells remain sparse.
- The broad all-actionable Ten-AM cohort is negative OOS.
- Full-grid robustness is `0.00`.
- `docs/status/PHASE_21U_COMPLETION_2026-07-05.md` remains missing as an upstream documentation gap.

## Remaining Risks

- The post-mortem is based on replay evidence and cannot prove live fills.
- `trend continuation short` has only a tiny positive source-replay edge and no full-grid acceptance.
- Future research can still overfit if it mixes Phase 22 attribution with OOS threshold selection; the next phase must pre-register filters and thresholds before OOS replay.

## Exact Next Recommended Phase

`PHASE 28 - Pre-Registered Trend Continuation Short Diagnostic`

The next phase should remain research-only and pre-register the `trend continuation short` diagnostic before OOS evaluation. It must keep active models at `0` unless a future explicit activation phase passes chronological OOS validation, calibration, model review, proposal lifecycle, and full-grid sensitivity.
