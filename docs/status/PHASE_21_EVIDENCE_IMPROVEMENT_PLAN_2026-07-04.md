# Phase 21 Evidence Improvement Plan - 2026-07-04

`PHASE_21_RECOMMENDATION = KEEP_REJECTED_AND_REGENERATE_EVIDENCE`

This plan does not loosen gates, bypass stale guards, activate models, approve proposals, add broker execution, add order routing, add production WebSocket ingestion, add options data, add black-box ML, or claim profitability.

## Immediate Blocker

Before any new certification work, restore or regenerate the default Postgres evidence store. Phase 21 diagnostics were captured before a regression incident, but the current default Postgres database now contains parity fixtures from `make api-smoke-postgres` and `make repository-parity-test`.

Required first fix:

- Update the Postgres smoke and repository parity tests so an explicit `DATABASE_URL` override is honored end to end, or force those tests to use a disposable database/schema.
- Do not run those targets against the default evidence database until isolation is fixed.
- Restore/regenerate live FMP runtime evidence from a clean database before the next certification phase.

## Evidence Gaps And Actions

| Evidence Gap | Action | Acceptance Signal |
|---|---|---|
| Selected validation sample is 1 and minimum is 30 | Collect at least 30 additional RTH trading days and rebuild validation windows. | At least 30 selected validation trades after strict gates. |
| One selected trade is 100% QQQ | Require broader per-symbol validation evidence. | No single-symbol concentration breach; practical target at least 5 selected trades per symbol. |
| One selected trade is 100% `VWAP loss short` | Require broader per-setup validation evidence. | No single-setup concentration breach; practical target at least 5 selected trades per major setup. |
| One validation day and one validation window | Add 8 to 10 non-overlapping replay-aware windows. | Validation evidence spans multiple days and windows with embargo preserved. |
| Missing sensitivity evidence | Run sensitivity for all candidate-market and counterfactual replay windows. | No unresolved `some_training_replay_runs_missing_sensitivity` warning. |
| Score concentration warning | Rebuild score audits over wider data and review score distribution. | Materially populated score bands beyond 20-40 without lowering thresholds. |
| Counterfactual and portfolio replays are both negative expectancy | Compare 1min, 5min, and 15min candidate quality after regeneration. | Candidate-quality and portfolio evidence are reviewed separately; no counterfactual P/L claim. |
| Provider status semantic warning | Normalize data-quality handling of reviewed `ACCESSIBLE` HTTP 200 provider requests. | Provider-request warnings distinguish actual provider failures from reviewed capability success. |
| Export ledger no longer reliable after contamination | Regenerate exports after DB restoration. | Export rows, file hashes, source IDs, and files agree in the clean database. |

## Bounded Regeneration Scope

Use the existing reviewed FMP REST endpoints and runtime-only secret handling. Load `FMP_API_KEY` only from the runtime environment or ignored `.env.local`; do not write secrets to docs, commands, exports, logs, provider metadata, scheduler artifacts, model artifacts, or frontend bundles.

Recommended next evidence run:

1. Start from a clean migrated Postgres database.
2. Seed SPY, QQQ, AAPL, and NVDA for at least 30 additional RTH trading days across `1day`, `1min`, `5min`, and `15min`.
3. Rebuild features from persisted bars only.
4. Rebuild candidates from rebuilt features only.
5. Rebuild labels from bars, features, and candidates.
6. Rebuild `candidate_market_replay` and `model_training_counterfactual` for `1min`, `5min`, and `15min`.
7. Run replay sensitivity for every replay window.
8. Run replay-aware validation with multiple non-overlapping windows and `allow_stale=false`.
9. Run calibration audit without probability-calibration claims.
10. Run model review and champion/challenger comparison.
11. Persist proposal and decision-ledger records without activation.
12. Generate exports with hashes, source IDs, row counts, and workbook sheets.
13. Run tests, `git diff --check`, and secret scans before certification.

## Explicit Non-Recommendations

Do not:

- Lower selected-trade thresholds.
- Ignore concentration gates.
- Treat the one positive selected validation trade as a profitability signal.
- Treat counterfactual replay as executable P/L.
- Bypass model review.
- Approve or activate the challenger.
- Allow stale data by default.
- Add broker or order-routing behavior.

## Next Phase

Recommended next phase: `PHASE_21R - Runtime Evidence Store Restoration And Isolated Regression Repair`.

Phase 21R should restore/regenerate the clean evidence store, repair the test isolation issue, and rerun Phase 20/21 diagnostics from a database that no longer contains parity fixtures.
