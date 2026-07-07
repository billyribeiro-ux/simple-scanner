# Adaptive Market Decoder Handoff

Report status date: 2026-07-06

## Phase 28 Trend Continuation Short Diagnostic

Phase 28 completed the pre-registered `trend continuation short` diagnostic with status `PHASE_28_STATUS = ACCEPTED_REJECTED_BY_SENSITIVITY`. It remained research-only: no model was activated, no proposal was approved, no validation/calibration/sensitivity gate was loosened, no threshold or filter was selected from OOS outcomes, no future labels or future outcomes were used for filters, no realized same-bar ambiguity was used as a live filter, no broker/order/WebSocket production path was used, and no profitability claim is made.

The pre-registered filter spec was `phase28_trend_continuation_short_diagnostic.v1`, hash `9bcac6111f0c6e079b20c6160386d4ad2f78c4c9755cbbad788992350903162b`, source ID `phase28_tcs_13dcd7f09159fc3c`. The primary cohort was `trend continuation short`, side `SHORT`, all symbols in the clean evidence DB, intervals `1min`, `5min`, and `15min` evaluated separately, RTH, minimum RR `1.0`, with no primary symbol, regime, time-bucket, score, or ambiguity exclusions.

The chronological split and leakage checks passed for every interval. OOS candidates were 87 for `1min`, 89 for `5min`, and 189 for `15min`; the `1min` and `5min` OOS samples remained below 100 candidates and had broad-parent reliance proxies above 50%, while `15min` had 189 OOS candidates and a lower 22.22% broad-parent proxy.

Primary results:

| Interval | Portfolio avg R | Portfolio PF | Portfolio robustness | Counterfactual avg R | Counterfactual PF | Counterfactual robustness | Decision |
|---|---:|---:|---:|---:|---:|---:|---|
| `1min` | `0.161701` | `1.308001` | `0.00` | `0.111022` | `1.203147` | `0.00` | `REJECTED_BY_SENSITIVITY` |
| `5min` | `0.168638` | `1.350594` | `0.44` | `0.170699` | `1.350681` | `0.00` | `REJECTED_BY_SENSITIVITY` |
| `15min` | `-0.058462` | `0.888915` | `0.00` | `-0.064282` | `0.873549` | `0.00` | `REJECTED_BY_SENSITIVITY` |

Every interval failed portfolio or counterfactual full-grid sensitivity. The `1min` and `5min` positive zero-cost baselines were fragile under sensitivity; `15min` was negative before sensitivity. Exploratory symbol/regime/time-bucket/same-bar diagnostics are recorded as diagnostic-only and must not be promoted into live filters from this phase.

Phase 28 generated 9 exports:

- `export_f00b2408e06695c97dcbff7ba0bc366d` - filter spec.
- `export_9dd83209406e88bc97e9d4df1aa339f9` - data sufficiency.
- `export_867286944863d5e13a282bb0a7544275` - split/leakage.
- `export_6b761552056a1173e890e10a5ab74ebe` - primary results.
- `export_3d55ecc7ca0e1b813cf6347a28cb6b86` - exploratory results.
- `export_5ff966cce536fdec7af9f26bec515508` - comparison.
- `export_8a5679bc9bf94442d090179abb7e7ad6` - decision.
- `export_f98c0a35f5bce38b2869a2b80ff686ce` - 450 sensitivity scenario rows.
- `export_35de7fe0f9b479e5df2ef64eb25c3bb3` - export manifest.

Final post-test evidence audit remained `CLEAN`, fixture rows `0`, active models `0`, dirty windows `none`, total rows `212002`, exports `340`, replay runs `72`, sensitivity runs `68`, and sensitivity scenarios `4248`. The required first-read file `docs/status/PHASE_21U_COMPLETION_2026-07-05.md` remains missing from the checkout and is still treated as an upstream documentation gap.

Phase 28 reports:

- `docs/status/PHASE_28_PLAN_2026-07-06.md`
- `docs/status/PHASE_28_FILTER_SPEC_2026-07-06.md`
- `docs/status/PHASE_28_DATA_SUFFICIENCY_2026-07-06.md`
- `docs/status/PHASE_28_SPLIT_AND_LEAKAGE_2026-07-06.md`
- `docs/status/PHASE_28_PRIMARY_RESULTS_2026-07-06.md`
- `docs/status/PHASE_28_EXPLORATORY_RESULTS_2026-07-06.md`
- `docs/status/PHASE_28_COMPARISON_2026-07-06.md`
- `docs/status/PHASE_28_DECISION_2026-07-06.md`
- `docs/status/PHASE_28_COMPLETION_2026-07-06.md`

Exact next recommended work: do not activate the current trend-continuation-short formulation. Either select another signal family through a pre-registered research plan or design a materially new trend-continuation-short hypothesis with a new spec hash and training-only rationale.

## Phase 27 Ten-AM Discard And Signal-Family Post-Mortem

Phase 27 completed the formal discard/post-mortem for the current 15min `ten_am_reversal_zone` specialist with status `PHASE_27_STATUS = ACCEPTED_TEN_AM_DISCARDED_NEXT_FAMILY_SELECTED`. It remained research-only: no model was activated, no proposal was approved, no validation/calibration/sensitivity gate was loosened, no threshold was selected from OOS outcomes, no stale gate was bypassed, no broker/order/WebSocket production path was used, and no profitability claim is made.

The current Ten-AM specialist is discarded. Phase 26 killed it by solving the selected-count objection and still failing: Policy A selected 145 OOS actionable candidates, portfolio avg R was `-0.053513`, counterfactual avg R was `-0.057926`, and both portfolio and counterfactual full-grid robustness were `0.00`. All Phase 26 policies A-H failed full-grid sensitivity. Exact specialist evidence remains weak, but only as a secondary cause: 79 exact specialist cells, 7 with 5+ outcomes, 0 with 10+ outcomes, and 113 of 145 OOS candidates broad-parent-reliant.

The signal-family post-mortem preserves the weak-family findings from Phase 22: `NVDA` and `SPY` were the heaviest symbol contributors, longs were worse than shorts, `power_hour` and `afternoon_continuation` were weak, `chop` had the largest total regime loss, and `trend_long` was weak by average R. Current Ten-AM may only be revisited through a materially redesigned, pre-registered hypothesis with a new spec hash.

The next research lead is `trend continuation short`, and only as a diagnostic candidate family. It was the only setup family with positive source replay attribution in Phase 22: 715 observed trades, total `3.960479R`, avg `0.005539R`, PF `1.009968`, win rate `41.40%`, same-bar rate `5.73%`. It is not activation-ready, because no full-grid robust subset was found and the observed edge is tiny.

Phase 27 reports:

- `docs/status/PHASE_27_PLAN_2026-07-06.md`
- `docs/status/PHASE_27_TEN_AM_HISTORY_2026-07-06.md`
- `docs/status/PHASE_27_FAILURE_ATTRIBUTION_2026-07-06.md`
- `docs/status/PHASE_27_SIGNAL_FAMILY_POST_MORTEM_2026-07-06.md`
- `docs/status/PHASE_27_RESEARCH_RULES_2026-07-06.md`
- `docs/status/PHASE_27_NEXT_SIGNAL_FAMILY_SELECTION_2026-07-06.md`
- `docs/status/PHASE_27_TEN_AM_DISCARD_RECORD_2026-07-06.md`
- `docs/status/PHASE_27_COMPLETION_2026-07-06.md`

Exact next recommended phase: `PHASE 28 - Pre-Registered Trend Continuation Short Diagnostic`. Keep it research-only unless a future explicit activation phase passes chronological OOS validation, calibration, model review, proposal lifecycle, and full-grid sensitivity.

## Phase 26 Broader Ten-AM Evidence-Density Result

Phase 26 completed the pre-registered broader 15min `ten_am_reversal_zone` evidence-density experiment with status `PHASE_26_STATUS = ACCEPTED_DISCARD_TEN_AM`. It remained research-only: no model was activated, no proposal was approved, no threshold was selected from OOS outcomes, no stale gate was bypassed, no broker/order/WebSocket production path was used, and no profitability claim is made.

The broader all-actionable OOS cohort selected 145 candidates versus the current TAKE/WATCH reference slice's 2 candidates, so the sparse action-policy sample problem was solved for this diagnostic. The broader cohort did not survive validation: Policy A all-actionable counterfactual avg R was `-0.057926`, portfolio avg R was `-0.053513`, and both portfolio and counterfactual full-grid robustness were `0.00`. Training-only score q75/q90 policies selected 135 OOS candidates and were more negative. Pre-ceiling/evidence/time-bucket q75 policies selected 35 OOS candidates and remained negative. The TAKE/WATCH reference stayed `-1.000000R` across 2 candidates.

Evidence density remains weak at the specialist exact-cell level: 79 exact specialist cells, 7 with 5+ observed outcomes, 0 with 10+ observed outcomes, and 113 of 145 OOS candidates broad-parent-reliant. However, Phase 26's primary finding is not just evidence sparsity: the broader Ten-AM cohort itself is negative and sensitivity-blocked.

Phase 26 generated 16 replay runs, 16 full-grid sensitivity runs, 1200 scenarios, and 10 export records under source ID `phase26_537f582b33387bf5`. The report pack export is `export_2ccdec26381eabeec675c9eb3070a20f`, SHA-256 `a0c3ba33376a81edb0607d434b23376b6cd8bf6b8aedd4943419617352291c9c`, with sheets `Filter Spec`, `Data Sufficiency`, `Days Needed`, `Split Leakage`, `Policy Evaluation`, `Sensitivity Results`, `Phase25 Comparison`, `Decision`, and `Replay Sources`.

Exact next recommended phase: `PHASE 27 - Ten-AM Hypothesis Discard And Signal-Family Failure Post-Mortem`. Do not continue current 15min Ten-AM as a specialist challenger unless a future effort is a materially redesigned, pre-registered hypothesis.

## Phase 25 Specialist Scorer Diagnostics Result

Phase 25 completed on 2026-07-05 with status `ACCEPTED_EVIDENCE_TOO_SPARSE`. It diagnosed the Phase 24 15min `ten_am_reversal_zone` scorer failure without activation, proposal approval, gate loosening, stale bypass, broker/order execution, production WebSocket ingestion, secret exposure, or profitability claims.

The inactive Phase 24 model `amd-replay-aware-20260611-181743` scored 145 OOS candidates and produced `SUPPRESS=143`, `TAKE=2`, `WATCH=0`. The zero-WATCH result is explained by suppression gates: this scorer emits WATCH only when there are no suppression reasons and score is below the TAKE threshold. All below-TAKE OOS candidates had suppression reasons.

Persisted suppression reasons were concrete: `negative_expectancy_after_shrinkage=143`, `profit_factor_below_threshold=112`, and `same_bar_ambiguity_dependency_too_high=10`. Evidence diagnostics found 128 exact evidence-cell matches but 113 broad-parent-reliant OOS candidates; only 7 of 79 specialist exact cells had at least 5 observed outcomes. The all-OOS counterfactual replay averaged `-0.057926R` across 145 trades with robustness `0.00`; the selected TAKE slice averaged `-1.000000R` across 2 trades with robustness `0.00`. The top-score quartile and decile were worse than the base cohort.

Phase 25 exports were recorded with source ID `phase25_81b88a7a49d13e87`; latest workbook export is `export_80c537f96b4d166e550c47cab63e156f`, SHA-256 `780d34d73b01362d8b34effab96a5e14b4c5be184a385faddbee95fdbcafa728`. Final evidence audit remained `CLEAN`, fixture rows `0`, active models `0`, dirty windows `none`, total rows `208163`, exports `321`, replay runs `48`, sensitivity runs `44`, sensitivity scenarios `2448`.

Exact next phase should be `PHASE 26 - Pre-register a broader 15min Ten-AM evidence-density experiment or wait for more 15min days before retesting`. It must remain research-only and must not use OOS outcomes to choose thresholds.

## Phase 22 Sensitivity Failure Attribution Result

Phase 22 completed on 2026-07-05 with status `ACCEPTED_DIAGNOSTIC_REJECTION`. It started from the accepted Phase 21W full-grid rejection and diagnosed why the full sensitivity grid failed. The evidence database remained `adaptive_market_decoder_evidence`, Alembic `0012_phase16_fmp_freshness`, with final audit `CLEAN`, fixture rows `0`, active models `0`, dirty windows `none`, and 238 export rows after Phase 22 diagnostic exports.

The Phase 21W challenger `amd-replay-aware-20260702-164145` remains rejected and inactive. All six full-grid sensitivity runs stayed `COMPLETE`, `75/75`, `pass_fail=fail`, and `robustness_score=0.0`. Phase 22 found the failure was broad: all zero-cost conservative baselines already had negative average R and profit factor below 1.0; slippage and spread worsened the result; same-bar ambiguity was materially harmful; non-ambiguous trades were still negative.

No full-grid robust subset was found. The only research-only pockets were `15min` `ten_am_reversal_zone` counterfactual and portfolio cohorts, but both failed worst-case scenarios. Score `TAKE` and `WATCH` cohorts were positive in observed replay but lack full-grid grade/action sensitivity proof and do not override rejected calibration/governance.

Phase 22 generated required reports:

- `docs/status/PHASE_22_PLAN_2026-07-05.md`
- `docs/status/PHASE_22_SENSITIVITY_FAILURE_DECOMPOSITION_2026-07-05.md`
- `docs/status/PHASE_22_ROBUST_SUBSET_DISCOVERY_2026-07-05.md`
- `docs/status/PHASE_22_TRIAGE_TABLES_2026-07-05.md`
- `docs/status/PHASE_22_CANDIDATE_FILTER_RESEARCH_PLAN_2026-07-05.md`
- `docs/status/PHASE_22_COMPLETION_2026-07-05.md`

The exact next phase should be `PHASE 23 - Diagnostic Candidate Filter Experiment for 15min Ten-AM Reversal and Ambiguity Suppression`. It must remain research-only, derive filters from signal-time/training-fold evidence, rerun validation/calibration/review/full-grid sensitivity, keep active models at `0`, and avoid broker execution, stale bypass, and profitability claims.

## Phase 21T Clean Evidence Expansion Result

Phase 21T completed on 2026-07-05 with status `PARTIAL_BLOCKED`. The clean evidence database `adaptive_market_decoder_evidence` remained the certification store, migrated at Alembic `0012_phase16_fmp_freshness`, with `AMD_DB_ROLE=evidence`, `0` fixture-like rows, `0` active models, and `dirty_windows=none` after cleanup and final audit.

Live FMP REST expansion ran for `SPY`, `QQQ`, `AAPL`, and `NVDA` over `1day`, `1min`, `5min`, and `15min`. The evidence store now contains 13560 bars, 13560 features, 16725 candidate signals, 2209 labels, 18 replay runs, 25048 simulated trades, 12 sensitivity runs, 474 sensitivity scenarios, 1562 evidence cells, 20380 score audits, 2 validation reports, 2 model reviews, 3 rejected proposals, and 158 export rows. The `1day`, `5min`, and `15min` intervals reached 10 RTH dates; FMP returned only six RTH dates for `1min`, so the 10-day 1-minute target remains provider-depth blocked.

Expanded challenger `amd-replay-aware-20260702-144429` remains inactive. Validation report `report_cf53a27dbd47245b319e8a55f490182b` rejected the challenger; calibration audit `calibration_6c40fa2999b92e0c68a252e1634b5c11` rejected it; model review `model_review_9262300c8d3fffe75e0ff0e98ebe90d3` stayed `BLOCK`; research cycle `research_cycle_938bf1f9375fecb54a7cfb1ebf00c255` ended `BLOCKED`; proposal `proposal_c34d0341e050a30bcdd815ffc0b0fa70` ended `REJECTED` with recommended action `REJECT_CHALLENGER`. No broker execution, production WebSocket ingestion, stale-gate bypass, activation, or profitability claim occurred.

Export manifest `exports/phase21t_export_manifest_20260705.json` was recorded as `export_9d7693a6f36bf21cb64ed7e32e03eed0` with SHA-256 `5901918df1860f0f0002441d4303f8adf7cf9cd4db029daf8f357936566130ee`. The exact next phase should be `PHASE 21U - Validation Scaling and 1-Minute Provider Coverage Recovery Plan`.

## Phase 21S Clean Evidence Store Result

Phase 21S completed on 2026-07-04 with status `ACCEPTED`. The contaminated default evidence database `adaptive_market_decoder` was archived before any clean-store work to `data/raw/phase21s/adaptive_market_decoder_contaminated_phase21s_2026-07-04.pgdump` with SHA-256 `6a8cb438e766f2ab59a398f8bcd9790ecebe1c1fa656465d163524d180b1b7ec` and size `413076 bytes`.

A separate clean evidence database, `adaptive_market_decoder_evidence`, was created, migrated to Alembic `0012_phase16_fmp_freshness`, inspected successfully, regenerated from bounded live FMP data, and audited `CLEAN` with `0` fixture-like rows after tests. Final clean evidence counts include 3960 bars, 4 quote snapshots, 3960 features, 4846 candidate signals, 578 labels, 12 replay runs, 6 sensitivity runs, 421 evidence cells, 3723 score audits, 1 validation report, 1 model review, 2 rejected proposals, 6 decision ledger rows, and 94 export rows.

The clean challenger `amd-replay-aware-20260702-133838` remains inactive. Governance cycle `research_cycle_2aa5a1efb11f49113c5b31508e31283a` ended `BLOCKED`; proposal `proposal_bbf68aeec5410239d265279e372bf7b8` ended `REJECTED` with `REJECT_CHALLENGER`. Sensitivity was regenerated and failed robustness gates, supporting rejection rather than activation. The exact next phase should analyze why the clean challenger failed validation, calibration, and sensitivity gates without activation, gate loosening, or profitability claims.

## Executive State

Phase 21R completed on 2026-07-04 with status `PARTIAL_BLOCKED`. The database role contract and mutating regression isolation are repaired: evidence uses `DATABASE_URL` with `AMD_DB_ROLE=evidence`, Postgres tests use `TEST_DATABASE_URL` with `AMD_DB_ROLE=test`, and evidence-mode fixture guards reject known `parity-*`, `test-*`, `smoke-*`, and `fixture-*` IDs unless an explicit non-certification override is set. `make api-smoke-postgres`, `make repository-parity-test`, `make evidence-guard-test`, backend tests, backend lint/typecheck, frontend check/build/test/lint/e2e, and compileall passed.

The default Postgres evidence DB remains archived contaminated evidence, not certification evidence. Phase 21R audit found database `adaptive_market_decoder` at Alembic `0012_phase16_fmp_freshness` with `2609` total rows and `29` fixture-like rows. Use `adaptive_market_decoder_evidence` for Phase 21S clean certification evidence.

Phase 21 diagnostics completed on 2026-07-04 with status `DIAGNOSTICS_COMPLETE_CURRENT_DB_BLOCKED`. The Phase 20 challenger rejection was attributed to validation sample scarcity and concentration: validation report `report_0091f7e03f0bd9d674ff6fdb75219b0e` rejected for `minimum_selected_candidate_sample_not_met`, `single_setup_profit_concentration_too_high`, and `single_symbol_profit_concentration_too_high`. Model review `model_review_ae563bded0b1a0ab4eedbb35e99e4d66` stayed `BLOCK`; proposals `proposal_e800968cc4ba52a648f6bc00430d306b` and `proposal_ca9d2a25a6eda708ea88e1706e4313ab` stayed `REJECTED` with `REJECT_CHALLENGER`. Calibration did not reject, but warned `score_concentrated_in_one_bucket`.

Important: after the Phase 21 diagnostic snapshot was collected, `make api-smoke-postgres` and `make repository-parity-test` contaminated the default Postgres database with `parity-*` fixtures. Phase 21R repaired the test-isolation bug, but the already contaminated current Postgres evidence database remains blocked until clean restoration or regeneration.

Phase 20 is accepted as of 2026-07-04 for live-data research-cycle execution, replay-aware inactive model review, and challenger proposal recording. The default evidence database was regenerated from live FMP bars after a test-contamination incident, then Phase 20 was rerun from the clean Phase 19D after-state. The challenger model `amd-replay-aware-20260702-195615` remains inactive and was rejected for activation because replay-aware validation and model-review gates failed. The strict research cycle `research_cycle_ece57ebd9e3f0efa4d4fa48c0518b821` was recorded with `allow_stale=false` and ended `BLOCKED`; proposal `proposal_e800968cc4ba52a648f6bc00430d306b` ended `REJECTED` with recommended action `REJECT_CHALLENGER`. See `docs/status/PHASE_20_COMPLETION_2026-07-04.md`.

Phase 19D is accepted as of 2026-07-04 for bounded runtime FMP data regeneration and artifact-readiness certification. The run used an ignored local runtime key source, reviewed the required FMP REST endpoints, seeded SPY, QQQ, AAPL, and NVDA for July 1-2, rebuilt derived artifacts from real persisted bars, recorded freshness reports, recorded a strict research-cycle dry-run with `allow_stale=false`, and generated hashed exports. Models remain inactive, broker execution remains absent, production WebSocket ingestion remains unused, and no profitability claim is made.

Phase 19 completed live-data artifact-readiness repair on top of the Phase 18 FMP seed. `FMP_API_KEY` was not used for the rebuild path. Dirty windows went from 560 to 0 after feature, candidate, label, replay, and daily replay not-applicable cleanup. Default freshness is still `STALE` because the bars are historical relative to July 3, 2026 wall-clock age thresholds. Research-scope freshness is `READY`, and the strict research-cycle dry run passed with `allow_stale=false`; no diagnostic `allow_stale=true` run was needed.

Phase 18 completed runtime-key FMP bring-up and real-data seed verification. `FMP_API_KEY` was supplied only through the runtime environment and was not written to tracked files, docs, exports, logs, provider metadata, or frontend bundles. All eight required FMP REST endpoints are `ACCESSIBLE` with HTTP 200, the latest rows are reviewed `REVIEWED_ACCESSIBLE`, and review summary is `READY`. Bounded live seed persisted real quote snapshots, EOD bars, and intraday bars.

Node `24.18.0` remains the target runtime and frontend target-runtime gates use pnpm `11.9.0` through Corepack. Python `3.14.6` is installed, `services/quant-engine/.venv` exists on Python `3.14.6`, and Alembic verifies at `0012_phase16_fmp_freshness`.

This remains a local-first scanner, research, validation, backtest, signal, and export platform only. It is not a broker, auto-trader, order router, self-learning system, or profitability system.

## Phase 19 Live-Data Artifact Readiness Result

Runtime result on 2026-07-03:

- Initial dirty-window audit: 560 dirty windows, with 140 each for `features`, `candidates`, `labels`, and `replay`.
- Feature rebuild: 11999 persisted bars read, 11999 features written, 140 feature windows cleared.
- Candidate rebuild: final all-interval pass read 11999 features, wrote 14976 candidate rows, and cleared 140 candidate windows.
- Label rebuild: final all-interval pass read 14976 candidate rows, wrote 2088 label rows, and cleared 140 label windows. Skipped or unobserved candidates were not counted as losses.
- Small replay scope: `SPY,QQQ,AAPL,NVDA`, `1min`, strict stale inputs clean.
- Optional default intraday replay: all default symbols on `1min,5min,15min`.
- Daily replay cleanup: 40 `1day` replay windows marked clean as `candidate_market_replay_is_intraday_only`; future `1day` bar upserts no longer create replay dirty windows.
- Final dirty-window audit: 0 dirty windows.
- Default freshness: `STALE`, warnings only `freshness_stale_required_data`.
- Research-scope freshness: `READY`, no warnings.
- Strict research dry run: `research_cycle_b3e371c34dccba95c8eb29ff3e657bca`, blocked `false`, diagnostic run not needed.

Detailed records:

- `docs/status/PHASE_19_COMPLETION_2026-07-03.md`
- `docs/status/PHASE_19_DIRTY_WINDOW_AUDIT_2026-07-03.md`
- `docs/status/PHASE_19_REBUILD_RESULTS_2026-07-03.md`
- `docs/status/PHASE_19_RESEARCH_CYCLE_DRY_RUN_2026-07-03.md`
- `docs/live-data-artifact-readiness.md`

## Phase 19A Evidence Reconciliation Result

Phase 19A on 2026-07-04 found the Phase 19 implementation and committed reports at HEAD `a52145b9f655682c94969a36ddffa9da63630e37`, but did not find the ignored July 3 runtime artifacts in the checkout. `data/local_repo.sqlite3` was created fresh during audit and has 0 bars, features, candidates, labels, replay runs, freshness reports, research cycles, and exports. `exports/` contains only `.gitkeep`.

Certification status is `PHASE_19_STATUS = EVIDENCE_PENDING`. Postgres migration is blocked, Redis compose startup is blocked by host port `6379`, and local Python is `3.14.4` while the documented target is `3.14.6`. See `docs/status/PHASE_19A_COMPLETION_2026-07-04.md`.

## Phase 19B Runtime Recovery Result

Phase 19B on 2026-07-04 did not recover the original July 3 DB/export artifacts and did not regenerate Phase 19. Final status is `PHASE_19_STATUS = BLOCKED_INFRA`, with secondary `BLOCKED_NO_DATA`.

Current blockers:

- Postgres migration fails because `0001_initial.py` creates current metadata, then later migrations duplicate tables such as `research_cycles`.
- Python `3.14.6` is unavailable; current `python3.14` and backend venv are `3.14.4`.
- Current SQLite has 0 bars and 0 quote snapshots.
- `FMP_API_KEY` is absent, so no bounded live seed/refresh can run.

See `docs/status/PHASE_19B_COMPLETION_2026-07-04.md`.

## Phase 18 Live FMP Verification Result

Runtime-key verification completed on 2026-07-03:

- `make fmp-smoke` and `make fmp-live-smoke` returned `ACCESSIBLE` for `quote`, `quote_short`, `batch_quote`, `batch_quote_short`, `historical_eod_full`, `intraday_1min`, `intraday_5min`, and `intraday_15min`.
- Latest reviewed sample counts: quote 1, quote-short 1, batch quote 4, batch quote-short 4, EOD 6, 1min 1170, 5min 468, 15min 156.
- Capability review summary: `READY`, 8 reviewed accessible, 0 blocked, 0 missing, 0 unreviewed.
- Initial full live seed: `ingestion_67f0fb86daeb3de661eb7d4d91d39c79`, `COMPLETED`, 12009 fetched, 12009 inserted, 41 provider requests, 0 errors.
- Current persisted bars: 11999.
- Current quote snapshots: 10.
- Current provider request records: 182.
- Post-fix incremental runs `ingestion_97a9a4a054f4585fffc19aa0d540ed74` and `ingestion_4907dd2706ac17c9e11192e0f66628f5` each fetched 1976 bars, inserted 0, updated 1976, and kept bar count flat.
- Default-universe freshness: `STALE`, 0 missing, 40 stale groups, 400 dirty windows.
- Latest research-cycle-scope freshness: `STALE`, 0 missing, 12 stale groups, 160 dirty windows.
- Research cycle `research_cycle_032e2882c97523fdfc28d9821afa8162` dry-run and default run blocked on `stale_artifacts_present`; `allow_stale=true` completed diagnostically with `model_activation_unchanged=true`, `proposal_status=REVIEW_REQUIRED`, and `recommended_action=BLOCK_ALL_CHANGES`.

Phase 18 included one narrow code fix: FMP bar ingestion now reports actual insert/update counts after idempotent upserts instead of counting every upsert attempt as an insert.

Detailed records:

- `docs/status/PHASE_18_COMPLETION_2026-07-03.md`
- `docs/status/PHASE_18_LIVE_FMP_ENDPOINT_MATRIX_2026-07-03.md`
- `docs/status/PHASE_18_REAL_SEED_INGESTION_2026-07-03.md`
- `docs/status/PHASE_18_FRESHNESS_RESULTS_2026-07-03.md`

## Phase 17 Live FMP Verification Result

During Phase 17, `FMP_API_KEY` was missing in that verification shell. That phase proved the no-key path only and did not establish live entitlement.

Verified on 2026-07-03:

- `make fmp-smoke` and `make fmp-live-smoke` ran and skipped safely.
- Required endpoints `quote`, `quote_short`, `batch_quote`, `batch_quote_short`, `historical_eod_full`, `intraday_1min`, `intraday_5min`, and `intraday_15min` persisted as `SKIPPED_NO_KEY`.
- Capability review summary: `BLOCKED`, with 8 blocked endpoints and 0 reviewed accessible endpoints.
- Seed dry-run: `dry_run`, `would_block=true`, no provider call.
- Freshness report: `BLOCKED`.
- Redacted exports for entitlement review, capability matrix, quote snapshots, seed ingestion, freshness, and data coverage were generated with file hashes.
- Backend, database, frontend, scheduler, export, and secret-scan gates passed.

Live FMP endpoint accessibility, live seed counts, incremental refresh idempotency on real data, and real-data research-cycle freshness behavior remain unverified.

## Phase 16 Operator Flow

1. Set `FMP_API_KEY` safely in the runtime shell or ignored env file. Never commit it.
2. Run live entitlement only when the key is present:

```bash
curl -s -X POST http://localhost:8000/provider/capabilities/check \
  -H 'content-type: application/json' \
  -d '{"symbols":["SPY","QQQ","AAPL","NVDA"]}'
```

3. Review each measured capability row:

```bash
curl -s -X POST http://localhost:8000/provider/capabilities/{check_id}/review \
  -H 'content-type: application/json' \
  -d '{"operator_review_status":"REVIEWED_ACCESSIBLE","reviewed_by":"local-operator"}'
```

4. Check review readiness:

```bash
curl -s http://localhost:8000/provider/capabilities/review-summary
```

5. Run seed dry-run without a provider call:

```bash
curl -s -X POST http://localhost:8000/data/ingest/fmp/seed \
  -H 'content-type: application/json' \
  -d '{"dry_run":true}'
```

6. Run live seed only after key and reviews are ready:

```bash
curl -s -X POST http://localhost:8000/data/ingest/fmp/seed \
  -H 'content-type: application/json' \
  -d '{"dry_run":false}'
```

7. Check freshness:

```bash
curl -s -X POST http://localhost:8000/data/freshness/check \
  -H 'content-type: application/json' \
  -d '{"persist":true}'
curl -s http://localhost:8000/data/freshness/latest
```

Research cycles include a freshness report and block on `BLOCKED` or `STALE` by default. `allow_stale=true` allows execution with explicit warnings. Quote freshness and capability-review gating for research are opt-in with `require_quote_freshness=true` and `require_reviewed_capabilities_for_research=true`.

View `/operations/provider` for entitlement review and seed controls. View `/operations/data` for quote snapshots, freshness, coverage, and ingestion history.

Safe to trust: persisted provider status, operator review metadata, quote snapshots, bars, dirty-window status, mocked regression tests, and Phase 18 live FMP REST entitlement for the runtime key at the time it was measured. Do not treat this as a permanent provider-plan guarantee; rerun entitlement before future live ingestion.

## Phase 19D Runtime FMP Regeneration Result

Runtime result on 2026-07-04:

- Capability review summary: `READY`, 8 reviewed accessible, 0 blocked, 0 unreviewed.
- Live seed run `ingestion_10d4f575c1a12c80363350d1d73adbe9`: `COMPLETED`, 3964 fetched, 3964 inserted, 0 errors.
- Seed rerun `ingestion_98b1d1b1c9206bc49d1b2fb3ddd909b8`: `COMPLETED`, 3964 fetched, 0 inserted, 3964 updated.
- Incremental runs `ingestion_a0fccadf7e35d55612abfc1ba20272f9` and `ingestion_898c297f7b30045dff4d5b111661dabb`: each inserted 0 bars and updated 1976 existing bars.
- Final bars: 3960 total; `1day=8`, `1min=3120`, `5min=624`, `15min=208`.
- Quote snapshots: 4.
- Features/candidates/labels: 3960 / 4909 / 778.
- Replay runs: 6, including mandatory 1-minute `candidate_market_replay` and `model_training_counterfactual`.
- Dirty windows: 0.
- Historical-reference freshness: `READY`; wall-clock freshness is `STALE` because the seed window is historical relative to July 4.
- Strict dry-run: `research_cycle_4e00305e7bd852e64b004c56cd4ce7d2`, `blocked=false`, `allow_stale=false`, `refresh_data=false`.
- Exports: 21 records with file hashes and source IDs.

Detailed records:

- `docs/status/PHASE_19D_COMPLETION_2026-07-04.md`
- `docs/status/PHASE_19D_REAL_DATA_SEED_2026-07-04.md`
- `docs/status/PHASE_19D_ARTIFACT_REBUILD_2026-07-04.md`
- `docs/status/PHASE_19D_REGENERATION_RESULTS_2026-07-04.md`
- `docs/status/PHASE_19D_FINAL_CERTIFICATION_2026-07-04.md`

## Runtime Pins

- Node target: `24.18.0`
- Package manager: `pnpm@11.9.0` through Corepack
- Python target: `3.14.6`, documented as the latest stable Python release for this project as of June 30, 2026
- Target Node is available through NVM; use `source "$HOME/.nvm/nvm.sh" && nvm use 24.18.0`
- Homebrew Node `25.3.0` exists but is not used for acceptance and currently fails before Corepack because a `simdjson` dynamic library is missing
- Current local Python: `python3.14` and Homebrew `python3` report `3.14.6`
- Backend venv: `services/quant-engine/.venv` on Python `3.14.6`

## Exact Setup Commands

```bash
source "$HOME/.nvm/nvm.sh"
nvm use 24.18.0
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack prepare pnpm@11.9.0 --activate
make frontend-doctor
make help
make doctor
make setup-backend
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm install --frozen-lockfile
make db-up
make db-migrate
make db-inspect
make db-query-diagnostics
make test-db-smoke
make evidence-db-audit
```

The local Postgres/Timescale container is mapped to host port `15432` because this machine already has another Postgres on `5432` and another Docker project on `55432`.

## Exact Verification Commands

```bash
make quant-test
make backend-test
make backend-lint
make backend-typecheck
make api-smoke
make api-smoke-sqlite
make api-smoke-postgres
make repository-parity-test
make evidence-guard-test
make replay-test
make replay-sensitivity-test
make replay-window-test
make model-review-test
make research-cycle-test
make research-status-test
make scheduler-test
make scheduler-status
make scheduler-worker-once
make scheduler-recover-stale
make export-test
make fmp-entitlement-test
make fmp-ingestion-test
make fmp-seed-test
make data-quality-test
make data-freshness-test
make fmp-smoke
make fmp-live-smoke
make db-query-diagnostics
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm check
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm build
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm test
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm lint
PLAYWRIGHT_PORT=5174 COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm --filter @amd/web test:e2e
python3 -m compileall services/quant-engine/app services/quant-engine/tests
git diff --check
```

`make fmp-smoke` is optional and gated. It skips with a non-secret message when `FMP_API_KEY` is not configured.

## Persistence Contract

The FastAPI repository backend is selected explicitly:

- no `DATABASE_URL`: SQLite local repository at `data/local_repo.sqlite3`, or `AMD_SQLITE_PATH` when set;
- `sqlite:///...`: SQLite repository at the configured path;
- Postgres URL: PostgreSQL repository runtime through sync SQLAlchemy/psycopg against the migrated schema;
- failed Postgres init: hard failure by default;
- `AMD_ALLOW_SQLITE_FALLBACK=true`: explicit SQLite fallback reported as `sqlite-fallback-from-postgres`.

The persisted contract now includes replay audit, sensitivity, replay-aware model-selection, counterfactual calibration, and Phase 10 operational review state:

- `replay_runs`: one row per candidate market replay run with config, filters, simulation type, metrics, warnings, backend, config hash, input fingerprint, candidate fingerprint, and stale-window status.
- `simulated_trades`: one row per taken or skipped candidate, including execution assumptions, entry/exit prices, realized R, MFE/MAE, skip reason, and ambiguity policy.
- `pipeline_build_windows`: dirty/stale metadata for feature, candidate, label, and replay rebuild awareness by artifact, symbol, interval, session date, version, and timestamp range.
- `replay_sensitivity_runs`: sensitivity run summaries, robustness scores, fragility flags, worst/median/best cases, and gate results.
- `replay_sensitivity_scenarios`: scenario-level slippage/spread/intrabar metrics.
- `backtest_comparisons`: persisted label-derived vs replay comparison reports.
- `model_evidence_cells`: replay-aware evidence cube cells with hierarchy level, dimensions, observed counts, shrinkage/backoff metrics, fragility flags, stale warnings, and provenance.
- `candidate_score_audits`: deterministic replay-aware score/audit rows with action, grade, component scores, penalties, evidence keys, warning codes, and suppression reasons.
- `model_calibration_audits` and `model_calibration_bins`: Phase 9 calibration diagnostics for score, grade, and action buckets.
- `model_comparisons`: persisted model comparison artifacts.
- `replay_window_sets` and `replay_window_results`: generated multi-window replay orchestration boundaries, result IDs, metrics, warnings, and status.
- `model_calibration_drift_reports` and `model_calibration_drift_windows`: advisory drift flags, severity, bin drift, stability metrics, and per-window rows.
- `model_review_reports`: advisory readiness reports with validation/calibration/drift/window references and `model_activation_unchanged=true`.
- `research_cycles`: controlled daily/manual/ad-hoc cycle records with config hash, input fingerprint, stale/data-quality state, explicit artifact IDs, summary, warnings, backend, database revision, and git commit when available.
- `research_cycle_artifacts`: cycle-to-evidence references for data quality, replay windows, validation, reviews, comparisons, proposals, and exports.
- `champion_challenger_comparisons`: diagnostic comparison records with gate results, delta metrics, recommended action, readiness, and warnings.
- `model_proposals`: human-review proposal records with approval status, champion/challenger metrics, gates, rejection reasons, approval actor/time, and activation metadata when explicitly activated.
- `model_decision_ledger`: append-only governance events for cycle creation/completion, proposal transitions, activation requests, blocked activations, and explicit activations.
- `scheduler_jobs`: bounded operator-queued research preparation jobs with status, priority, schedule time, payload, result, warnings, failure reason, and optional research cycle ID.
- `scheduler_job_events`: append-only scheduler job events with event type, message, non-secret metadata, and timestamp.
- `scheduler_jobs` Phase 14 worker fields: `lease_owner`, `lease_expires_at`, `heartbeat_at`, `attempt_count`, `max_attempts`, `timeout_seconds`, and `last_error`.
- `provider_capability_checks`: one row per FMP endpoint entitlement probe with status, HTTP status, response shape, latency, sample count, non-secret entitlement notes, and operator review fields.
- `ingestion_runs`: one row per bounded FMP ingestion request with endpoint keys, symbols, intervals, counts, dirty windows, provider request IDs, warnings, and errors.
- `quote_snapshots`: durable quote snapshot rows from FMP batch quotes with idempotent provider/symbol/timestamp keys and redacted raw fields.
- `data_freshness_reports`: persisted freshness reports for bars, quote snapshots, dirty windows, capability review state, warnings, and recommendations.

Safe status fields are exposed through `GET /health`, `GET /config`, and `make doctor`: `persistence_backend`, `runtime_mode`, `database_configured`, `database_reachable`, `fallback_enabled`, and `fallback_reason`. Full database URLs, passwords, and API keys are never returned.

## What Is Safe To Trust

- Deterministic quant feature/label/backtest/model baseline tests.
- Repository-backed API route state instead of route-level `_MEMORY`.
- SQLite local API persistence and reinitialization survival for bars, features, labels, replay runs/trades, model runs, active model, scanner runs/signals, exports, and daily reviews.
- Postgres API persistence and reinitialization survival for the same vertical slice after `make db-migrate`.
- Alembic migration and schema inspection expectations now target revision `0012_phase16_fmp_freshness`; local Postgres execution must be verified with `make db-migrate` and `make db-inspect`.
- SQLite/Postgres repository parity for symbols, bars, features, labels, replay runs/trades, sensitivity runs/scenarios, comparisons, pipeline build windows, replay-aware evidence cells, candidate score audits, calibration audits, replay window sets/results, drift reports, model review reports, models, scanner runs, signals, provider requests, exports, and daily reviews.
- CSV/XLSX/JSON export generation from persisted signals, replay runs/trades, replay sensitivity runs, replay-aware model summaries, evidence cells, score audits, replay-aware validation reports, calibration reports, replay window sets, calibration drift reports, model review reports, and daily reviews, with file hashes and workbook sheets recorded.
- CSV/XLSX/JSON export generation for research cycles, model proposals, and champion/challenger comparisons from persisted source IDs, with file hashes and workbook sheet names recorded.
- FMP REST client security behavior: header-only auth, no query-string key generation, redacted exceptions/metadata, request IDs, latency capture, endpoint classification, and mocked entitlement/ingestion regression tests.
- Persisted FMP capability checks, operator review metadata, quote snapshots, ingestion runs, provider request accounting, freshness reports, and source-aware data-quality reporting in SQLite and Postgres schema paths.
- Provider/data operator UI route wiring for `/operations/provider` and `/operations/data`, with review, seed, freshness, and quote snapshot controls but no broker execution controls and no frontend secret exposure.
- Approval of a model proposal is separate from activation. Explicit proposal activation requires `confirm_manual_activation=true`, accepted validation, non-blocking readiness, and a proposal recommendation that is eligible for activation.
- The Phase 12 operator UI enforces approval/activation separation with a disabled activation panel until the proposal is approved, the confirmation checkbox is checked, and `ACTIVATE SCANNER MODEL` is typed.
- The scheduler can queue and run data-quality reports, research-cycle dry-runs/runs, research-cycle exports, and operator-status exports; it cannot approve, reject, activate, deploy, route orders, or place trades.
- The Phase 14 one-shot scheduler worker can lease, heartbeat, recover stale leases, release, and complete bounded queued jobs without starting a daemon or autonomous loop.
- Activation guard requiring a persisted accepted validation report; replay-aware models specifically require accepted `replay_aware_walk_forward` validation.
- Secret redaction behavior and absence of the supplied FMP key from repo files.

## What Is Not Safe To Trust Yet

- Freshness readiness. Phase 18 live FMP entitlement and seed succeeded, but freshness is currently `STALE` and dirty pipeline windows remain.
- Permanent FMP entitlement under this machine's key. Phase 18 proved endpoint access at measurement time only; provider plan access and data availability can change.
- Market replay as execution-grade reality. Replay is now auditable and sensitivity-tested, but fills are still simulated from OHLCV with conservative same-bar rules, configurable slippage/spread, and no true market depth.
- Model calibration as a live probability. Calibration/drift reports are operational diagnostics, not calibrated probability estimates.
- Live trading readiness. No broker execution or order routing exists.
- Fully automated adaptation. Research cycles can compare and propose, but they do not silently activate models or mutate scanner behavior.

## Phase 15 FMP Data And Phase 14 Infrastructure

Primary docs:

- `docs/fmp-production-data-pipeline.md`
- `docs/fmp-provider-security.md`
- `docs/fmp-operator-guide.md`
- `docs/research/fmp-live-entitlement-matrix.md`
- `docs/status/PHASE_15_PLAN_2026-07-01.md`
- `docs/status/PHASE_15_COMPLETION_2026-07-01.md`
- `docs/status/PHASE_15_FMP_ENTITLEMENT_2026-07-01.md`
- `docs/status/PHASE_15_DATA_PIPELINE_2026-07-01.md`
- `docs/local-operator-runbook.md`
- `docs/operator-daily-procedure.md`
- `docs/non-autonomous-scheduler.md`
- `docs/docker-postgres-troubleshooting.md`
- `docs/status/PHASE_14_PLAN_2026-07-01.md`
- `docs/status/PHASE_14_COMPLETION_2026-07-01.md`
- `docs/status/PHASE_14_POSTGRES_VERIFICATION_2026-07-01.md`
- `docs/status/PHASE_14_SCHEDULER_WORKER_2026-07-01.md`

Recover Docker/Postgres:

```bash
docker context ls
docker info
docker compose config
make db-up
docker compose ps
nc -zv localhost 15432
make db-migrate
make db-inspect
make db-query-diagnostics
```

Phase 16 keeps the recovered Docker/Postgres/Redis path and adds migration `0012_phase16_fmp_freshness` for operator review fields, quote snapshots, and data freshness reports.

Daily operator setup:

```bash
source "$HOME/.nvm/nvm.sh"
nvm use 24.18.0
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack prepare pnpm@11.9.0 --activate
make doctor
make scheduler-status
make scheduler-worker-once
make scheduler-recover-stale
make api-dev
make web-dev
```

Create and run a bounded scheduler job:

```bash
curl -s -X POST http://localhost:8000/scheduler/jobs \
  -H 'content-type: application/json' \
  -d '{"job_type":"data_quality_report","payload":{"symbols":["AAPL","SPY"],"intervals":["1min"]},"created_by":"operator"}'

curl -s -X POST http://localhost:8000/scheduler/jobs/run-pending \
  -H 'content-type: application/json' \
  -d '{"max_jobs":3}'
```

Inspect scheduler status:

```bash
curl -s http://localhost:8000/operations/scheduler-status
curl -s http://localhost:8000/scheduler/jobs
curl -s http://localhost:8000/scheduler/jobs/{job_id}
curl -s http://localhost:8000/scheduler/jobs/{job_id}/events
make scheduler-status
make scheduler-worker-once
make scheduler-recover-stale
```

Confirm the scheduler does not activate models:

- Review `services/quant-engine/app/services/scheduler.py`; supported jobs never call proposal approve/reject/activate or model activation services.
- Run `make scheduler-test`; tests assert research-cycle jobs leave the active champion unchanged.
- In the UI, `/operations/scheduler` and `/operations/scheduler/{job_id}` expose create/run/cancel queue controls only, with no activation controls.

## Phase 12 Operator UI

Start the backend and frontend:

```bash
make api-dev
source "$HOME/.nvm/nvm.sh"
nvm use 24.18.0
COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack prepare pnpm@11.9.0 --activate
make web-dev
```

Open `http://localhost:5173`.

Routes:

- `/operations`: backend health, persistence, active model, latest cycle/proposal, stale windows, data quality, and warnings.
- `/research`: safe governance hub.
- `/research/cycles`: create, dry-run, run, and export research cycles. Defaults keep `refresh_data=false`, `allow_stale=false`, and `run_now=false`.
- `/research/cycles/{research_cycle_id}`: inspect cycle summary, config hash, input fingerprint, artifacts, warnings, and export metadata.
- `/research/proposals`: list proposals and export proposal reports.
- `/research/proposals/{proposal_id}`: review evidence, approve, reject, and explicitly activate an approved scanner model.
- `/research/decision-ledger`: filter by model version, proposal ID, research cycle ID, decision type, and time range.
- `/research/status`: read-only governance status.

Manual activation flow:

1. Open `/research/proposals/{proposal_id}`.
2. Review evidence, gates, and ledger history.
3. Click `Approve proposal` if appropriate. This does not activate.
4. In the explicit activation panel, check the manual confirmation box and type `ACTIVATE SCANNER MODEL`.
5. Click `Activate approved scanner model`. The frontend sends `confirm_manual_activation=true`, and the backend guard can still block.

What is safe to trust: UI route wiring, typed API client calls, no frontend secret exposure, approval-not-activation behavior, explicit activation confirmation, and mocked e2e coverage.

What is not safe to trust: live FMP entitlement, Postgres verification in this run, or any assumption that UI approval guarantees backend activation.

## Phase 11 Research Cycle Operations

Create a cycle:

```bash
curl -s -X POST http://localhost:8000/research/cycles \
  -H 'content-type: application/json' \
  -d '{"cycle_date":"2026-07-01","cycle_type":"daily","symbols":["AAPL","SPY"],"intervals":["1min"],"start":"2026-06-01T13:30:00Z","end":"2026-06-01T20:00:00Z","challenger_model_version":"{model_version}","allow_stale":false}'
```

Dry-run without training or activation:

```bash
curl -s -X POST http://localhost:8000/research/cycles/{research_cycle_id}/dry-run
```

Run the controlled cycle:

```bash
curl -s -X POST http://localhost:8000/research/cycles/{research_cycle_id}/run \
  -H 'content-type: application/json' \
  -d '{"allow_stale":true}'
```

Inspect cycle state and artifacts:

```bash
curl -s http://localhost:8000/research/cycles
curl -s http://localhost:8000/research/cycles/{research_cycle_id}
curl -s 'http://localhost:8000/research/cycles/{research_cycle_id}/artifacts?limit=500'
curl -s -X POST http://localhost:8000/research/cycles/{research_cycle_id}/export
```

Review a proposal:

```bash
curl -s http://localhost:8000/research/model-proposals
curl -s http://localhost:8000/research/model-proposals/{proposal_id}
```

Approve a proposal without activating it:

```bash
curl -s -X POST http://localhost:8000/research/model-proposals/{proposal_id}/approve \
  -H 'content-type: application/json' \
  -d '{"actor":"research_lead"}'
```

Explicitly activate an approved proposal:

```bash
curl -s -X POST http://localhost:8000/research/model-proposals/{proposal_id}/activate \
  -H 'content-type: application/json' \
  -d '{"actor":"research_lead","confirm_manual_activation":true,"validation_mode":"replay_aware_walk_forward"}'
```

Reject a proposal:

```bash
curl -s -X POST http://localhost:8000/research/model-proposals/{proposal_id}/reject \
  -H 'content-type: application/json' \
  -d '{"actor":"research_lead","reason_codes":["manual_rejection"]}'
```

Query the decision ledger and operations status:

```bash
curl -s 'http://localhost:8000/research/decision-ledger?proposal_id={proposal_id}'
curl -s http://localhost:8000/operations/research-status
```

Safe to trust in Phase 11: persisted cycle IDs, artifact references, config hashes, input fingerprints, stale/data-quality blocks, explicit approval records, explicit activation records, and SQLite/Postgres parity for the controlled governance flow.

Not safe to trust in Phase 11: proposal recommendations as profitability claims, automatic deployment decisions, live fill assumptions, or any claim that the platform is self-learning.

## Backtest Modes

Label-derived evidence remains available and explicit:

```bash
curl -s -X POST http://localhost:8000/backtest/run \
  -H 'content-type: application/json' \
  -d '{"symbols":["AAPL"],"start":"2026-06-01T13:30:00+00:00","end":"2026-06-01T19:59:00+00:00"}'
```

The response includes `simulation_type = label_derived`.

Candidate market replay uses persisted bars, features, and candidate signals:

```bash
curl -s -X POST http://localhost:8000/backtest/replay \
  -H 'content-type: application/json' \
  -d '{"symbols":["AAPL"],"intervals":["1min"],"start":"2026-06-01T13:30:00+00:00","end":"2026-06-01T19:59:00+00:00","max_hold_minutes":60,"minimum_reward_risk":1.0}'
```

The response includes `simulation_type = candidate_market_replay`, `replay_run_id`, `summary_metrics`, `config_hash`, `input_fingerprint`, `candidate_fingerprint`, and `trades_written`. Query the run and paginated trades with:

```bash
curl -s http://localhost:8000/backtest/replay/{replay_run_id}
curl -s 'http://localhost:8000/backtest/replay/{replay_run_id}/trades?limit=500&offset=0'
```

Replay validation now requires explicit selection unless fallback is intentionally enabled:

```bash
curl -s -X POST 'http://localhost:8000/models/validate?validation_mode=candidate_market_replay&replay_run_id={replay_run_id}'
```

Run sensitivity and label-vs-replay comparison with:

```bash
curl -s -X POST http://localhost:8000/backtest/replay/{replay_run_id}/sensitivity
curl -s -X POST http://localhost:8000/backtest/compare-label-vs-replay \
  -H 'content-type: application/json' \
  -d '{"replay_run_id":"{replay_run_id}"}'
```

Export replay outputs with:

```bash
curl -s -X POST http://localhost:8000/exports/replay-summary.xlsx \
  -H 'content-type: application/json' \
  -d '{"kind":"replay-summary","run_id":"{replay_run_id}"}'
curl -s -X POST http://localhost:8000/exports/replay-trades.csv \
  -H 'content-type: application/json' \
  -d '{"kind":"replay-trades","run_id":"{replay_run_id}"}'
curl -s -X POST http://localhost:8000/exports/replay-trades.xlsx \
  -H 'content-type: application/json' \
  -d '{"kind":"replay-trades","run_id":"{replay_run_id}"}'
curl -s -X POST http://localhost:8000/exports/sensitivity-summary.xlsx \
  -H 'content-type: application/json' \
  -d '{"kind":"sensitivity-summary","run_id":"{sensitivity_run_id}"}'
```

## Current Blockers

- Live FMP smoke, live endpoint entitlement classification, live seed ingestion, real-data incremental refresh, and real-data freshness proof require `FMP_API_KEY` to be configured outside the committed repo.
- Frontend acceptance still requires using Node `24.18.0` through NVM because the Homebrew Node `25.3.0` binary on this machine fails before Corepack.

## Exact Next Recommended Phase

Phase 18 should load `FMP_API_KEY` into the runtime environment outside tracked files, rerun Phase 17 live entitlement, review measured endpoint rows honestly, run bounded live seed only if review summary is `READY`, run incremental intraday refresh twice, run freshness and research-cycle checks, export clean reports, and rerun secret scans. Do not add broker execution, order routing, automatic activation, production WebSocket ingestion, options data, self-learning language, autonomous scheduling, or profitability claims.

## Phase 8 Replay-Aware Model Selection Historical Notes

Train a replay-aware baseline model from persisted replay runs:

```bash
curl -s -X POST http://localhost:8000/models/train \
  -H 'content-type: application/json' \
  -d '{"model_type":"replay_aware_baseline","symbols":["AAPL"],"intervals":["1min"],"training_start":"2026-06-01T13:30:00+00:00","training_end":"2026-06-01T19:59:00+00:00","replay_run_ids":["{replay_run_id}"],"minimum_observed_outcomes":5,"minimum_cell_sample_size":5}'
```

Validate and activate:

```bash
curl -s -X POST 'http://localhost:8000/models/validate?model_version={model_version}&validation_mode=replay_aware_walk_forward'
curl -s -X POST 'http://localhost:8000/models/activate?model_version={model_version}&validation_mode=replay_aware_walk_forward'
```

Score candidates and inspect audits:

```bash
curl -s http://localhost:8000/models/{model_version}/evidence
curl -s -X POST http://localhost:8000/models/{model_version}/score-candidates \
  -H 'content-type: application/json' \
  -d '{"candidate_ids":["{candidate_id}"],"persist_audit":true}'
curl -s http://localhost:8000/models/{model_version}/score-audits
```

When an active `replay_aware_baseline` exists, the scanner uses replay-aware scoring and writes score audits. If none is active, it falls back to the prior baseline and adds `no_replay_aware_model_active` to signal warnings.

Replay-aware exports:

```bash
curl -s -X POST http://localhost:8000/exports/replay-aware-model-summary.xlsx \
  -H 'content-type: application/json' \
  -d '{"kind":"replay-aware-model-summary","run_id":"{model_version}"}'
curl -s -X POST http://localhost:8000/exports/evidence-cells.xlsx \
  -H 'content-type: application/json' \
  -d '{"kind":"evidence-cells","run_id":"{model_version}"}'
curl -s -X POST http://localhost:8000/exports/score-audits.xlsx \
  -H 'content-type: application/json' \
  -d '{"kind":"score-audits","run_id":"{model_version}"}'
curl -s -X POST http://localhost:8000/exports/replay-aware-validation.xlsx \
  -H 'content-type: application/json' \
  -d '{"kind":"replay-aware-validation","run_id":"{report_id}"}'
```

Safe to trust: deterministic replay outcome dataset rules, persisted evidence cells, shrinkage/backoff hierarchy, score audits, replay-aware activation guard, and SQLite/Postgres persistence once migrations are applied through `0012_phase16_fmp_freshness`.

Not safe to trust: `signal_quality_score` as a calibrated probability, replay as live fill proof, portfolio-overlap skipped candidates as losses, or any output as a profitability claim.

## Phase 9 Counterfactual Replay And Calibration

Run counterfactual replay:

```bash
curl -s -X POST http://localhost:8000/backtest/replay \
  -H 'content-type: application/json' \
  -d '{"replay_purpose":"model_training_counterfactual","symbols":["AAPL"],"intervals":["1min"],"start":"2026-06-01T13:30:00Z","end":"2026-06-01T20:00:00Z"}'
```

Train replay-aware evidence from counterfactual outcomes:

```bash
curl -s -X POST http://localhost:8000/models/train \
  -H 'content-type: application/json' \
  -d '{"model_type":"replay_aware_baseline","outcome_source":"counterfactual_preferred","counterfactual_replay_run_ids":["{counterfactual_run_id}"],"portfolio_replay_run_ids":["{portfolio_run_id}"],"require_counterfactual":true,"training_start":"2026-06-01T13:30:00Z","training_end":"2026-06-01T20:00:00Z"}'
```

Run calibration audit:

```bash
curl -s -X POST http://localhost:8000/models/{model_version}/calibration-audit \
  -H 'content-type: application/json' \
  -d '{"replay_run_ids":["{counterfactual_run_id}"],"outcome_source":"counterfactual_only"}'
```

Require calibration for activation:

```bash
curl -s -X POST 'http://localhost:8000/models/activate?model_version={model_version}&validation_mode=replay_aware_walk_forward&calibration_audit_required=true&calibration_audit_id={calibration_audit_id}'
```

Compare counterfactual vs portfolio replay:

```bash
curl -s -X POST http://localhost:8000/backtest/compare-counterfactual-vs-portfolio \
  -H 'content-type: application/json' \
  -d '{"counterfactual_replay_run_id":"{counterfactual_run_id}","portfolio_replay_run_id":"{portfolio_run_id}"}'
```

Scanner behavior: if the active replay-aware model requires calibration and the audit is missing or failed, scanner output suppresses actionable TAKE and emits `calibration_required_or_failed`. Score reasons include model version, outcome source, calibration status, score audit ID, and evidence keys when available.

Safe to trust: persisted replay/config provenance, counterfactual candidate-quality evidence, calibration warnings/rejection reasons, and activation/scanner calibration gates.

Not safe to trust: counterfactual replay as executable portfolio P/L, `signal_quality_score` as calibrated probability, or any replay/calibration metric as a profitability claim.

## Phase 16 FMP Live Data Handoff

Set `FMP_API_KEY` only in the runtime environment or ignored local env files. Do not paste it into commands, docs, committed files, exports, logs, scheduler payloads, or frontend variables.

Run smoke and entitlement checks:

```bash
make fmp-smoke
make fmp-live-smoke
curl -s -X POST http://localhost:8000/provider/capabilities/check \
  -H 'content-type: application/json' \
  -d '{"symbols":["SPY","QQQ","AAPL","NVDA"]}'
```

If the key is missing, smoke and live ingestion skip or block safely with non-secret status. Capability rows persist in `provider_capability_checks`.

Review measured capabilities and check readiness:

```bash
curl -s -X POST http://localhost:8000/provider/capabilities/{check_id}/review \
  -H 'content-type: application/json' \
  -d '{"operator_review_status":"REVIEWED_ACCESSIBLE","reviewed_by":"local-operator"}'
curl -s http://localhost:8000/provider/capabilities/review-summary
```

Run seed dry-run, live seed, and freshness checks:

```bash
curl -s -X POST http://localhost:8000/data/ingest/fmp/seed \
  -H 'content-type: application/json' \
  -d '{"dry_run":true}'
curl -s -X POST http://localhost:8000/data/ingest/fmp/seed \
  -H 'content-type: application/json' \
  -d '{"dry_run":false}'
curl -s -X POST http://localhost:8000/data/freshness/check \
  -H 'content-type: application/json' \
  -d '{"persist":true}'
```

Run bounded ingestion:

```bash
curl -s -X POST http://localhost:8000/data/ingest/fmp/eod \
  -H 'content-type: application/json' \
  -d '{"symbols":["SPY"],"start":"2026-06-01T00:00:00Z","end":"2026-06-05T00:00:00Z"}'

curl -s -X POST http://localhost:8000/data/ingest/fmp/intraday \
  -H 'content-type: application/json' \
  -d '{"symbols":["SPY"],"intervals":["1min"],"start":"2026-06-01T13:30:00Z","end":"2026-06-01T20:00:00Z"}'

curl -s -X POST http://localhost:8000/data/ingest/fmp/incremental-intraday \
  -H 'content-type: application/json' \
  -d '{"symbols":["SPY"],"intervals":["1min","5min","15min"]}'
```

View provider/data status:

- `/operations/provider`
- `/operations/data`
- `GET /operations/provider-status`
- `GET /data/quality-report`

Verify no secrets leaked:

```bash
git grep -n "<known-secret-value>" -- .
git grep -n "apikey=" -- .
```

Safe to trust: header-only client behavior, persisted endpoint status, ingestion run counts, idempotent bar upserts, provider/source coverage, and missing-key skip/block behavior.

Not safe to trust: entitlement without a live check, WebSocket production readiness, quote durability beyond provider request metadata, exchange-calendar-perfect coverage, or any output as a profitability claim.

## Phase 21V Handoff - 2026-07-05

`PHASE_21V_STATUS = ACCEPTED_PARTIAL_SENSITIVITY_DISCLOSED`.

Phase 21V implemented bounded sensitivity scaling and explicit partial/full-grid disclosure from the repaired Phase 21U runtime. The evidence database remains `adaptive_market_decoder_evidence`, audited `CLEAN` with fixture rows `0`, active models `0`, and dirty windows `0`.

Six interval/purpose replay sensitivity runs were rebuilt from current persisted real bars: `1min`, `5min`, and `15min` for both `candidate_market_replay` and `model_training_counterfactual`. Each completed the deterministic `TIERED_ESSENTIAL` four-scenario grid, and each is explicitly disclosed as not full default grid complete.

Governance consumed the Phase 21V sensitivity evidence conservatively:

- Model review `model_review_1ef927a48eb24e11886fc3c31f8076e6`: `BLOCK`.
- Champion/challenger comparison `champion_challenger_33c0e399b4679cd3fe0a64149a13553e`: `REJECT_CHALLENGER`.
- Proposal `proposal_3e379a7289fc35875eced05436c4bd35`: `REJECTED`.
- Strict dry-run `research_cycle_750dd3d4bbee9b0a2ae83c2f7c08ae9d`: freshness `READY`, dirty windows `0`, blocked `false`, `allow_stale=false`.

No model was activated or approved, no broker/order/options/WebSocket production path was used, no stale gate was bypassed, and no profitability claim is made. The consolidated report is `docs/status/PHASE_21V_COMPLETION_2026-07-05.md`.
## Phase 19C Handoff - 2026-07-04

`PHASE_19_STATUS = BLOCKED_NO_DATA`.

Phase 19C repaired the runtime infrastructure but could not regenerate Phase 19 artifacts because no real market bars are present and no `FMP_API_KEY` or approved source is configured. Alembic now migrates clean Postgres from base to head, the backend venv is Python `3.14.6`, and Redis compose defaults to host port `16379` through `REDIS_HOST_PORT`.

Passing gates: `make doctor`, `docker compose config`, `docker compose up -d postgres redis`, `make db-migrate`, `make db-inspect`, `make db-query-diagnostics`, `make api-smoke-postgres`, `make repository-parity-test`, `make backend-lint`, `make backend-typecheck`, `make backend-test`, and `git diff --check`.

Final runtime evidence after cleaning synthetic verification rows: 0 bars, 0 quote snapshots, 0 features, 0 candidates, 0 labels, 0 replay runs, 0 exports, 8 FMP capability rows with `SKIPPED_NO_KEY`, 2 blocked freshness reports, and 1 strict dry-run research cycle. The strict dry-run returned `blocked=true` with `block_reason=data_freshness_blocked`.

Next operator action: configure an approved `FMP_API_KEY` or restore verified real bars, then rerun bounded seed ingestion for SPY, QQQ, AAPL, and NVDA across `1min`, `5min`, `15min`, and `1day`, followed by rebuilds, freshness checks, strict dry-run, and exports. Do not certify Phase 19 from synthetic parity-test rows.
## Phase 19D Handoff - 2026-07-04

`PHASE_19_STATUS = BLOCKED_NO_DATA`.

Phase 19D attempted runtime FMP data regeneration from the repaired Phase 19C runtime. `FMP_API_KEY` was absent from the runtime environment, `.env.local` was absent, and settings reported no key. The bounded seed path was invoked for SPY, QQQ, AAPL, and NVDA over `1day`, `1min`, `5min`, and `15min`, but it persisted `ingestion_e06676225f32a85d1fab59e3d7583c3c` as `BLOCKED` with 0 fetched and 0 inserted rows before any live provider call.

Do not run feature, candidate, label, replay, or model-training-counterfactual rebuilds until real persisted bars exist. The strict Phase 19D dry-run cycle is `research_cycle_a2c1eec149a27c45bc3a26e1cf2b55b4` and is blocked by `data_freshness_blocked`.

Evidence exports:

- `export_9454f20545bb2e14307f7bcac4fa6602`, `fmp_seed_ingestion`, SHA-256 `f41830aeb57abc51b6feb27a5db93045f32a97288999e6b2728f584338f544e2`.
- `export_1be2dae9a9ad47276c6da2fc5722841d`, `data_freshness_report`, SHA-256 `c60a7eb6d39582ed555ff28134a761f26a223ea6fa448a2b46a2ef87e53d85ab`.

## Phase 21W Handoff - 2026-07-05

`PHASE_21W_STATUS = ACCEPTED_FULL_GRID_REJECTION`.

Phase 21W completed resumable full default-grid sensitivity for all six required Phase 21V replay runs. The full grid is versioned as `replay_sensitivity.full_default_grid.v1`, hash `1f7c8a8a7b14e40768954acf273280866b768d8f5516abbc29c6a3187511201b`, with 75 scenarios per replay.

New full-grid sensitivity IDs:

- `1min` portfolio: `sensitivity_ab486e2337c9de415328f76cecf1c4c7`
- `1min` counterfactual: `sensitivity_4747000982a7dd1c24c48798b27d0970`
- `5min` portfolio: `sensitivity_df6e25965262b6d29d8bb6ad9aa0bcde`
- `5min` counterfactual: `sensitivity_d1fa1d06e2ac1151f5b20d96db8fefc8`
- `15min` portfolio: `sensitivity_7b270b48d0b1e8580a696a60d82c859e`
- `15min` counterfactual: `sensitivity_90441b99f44ddd04caeddcbaa244419f`

All six completed `75/75`, `completion_status=COMPLETE`, `full_default_grid_complete=true`, and `partial_grid_disclosure=false`. All six also failed robustness gates with `robustness_score=0.0`; this is complete rejection evidence, not activation approval.

Governance artifacts:

- Model review `model_review_e045a9d38fbbaa4a6acf01b1249dc015`: `BLOCK`.
- Comparison `champion_challenger_819cf89bd41889d5dd73fa8029976363`: `REJECT_CHALLENGER`.
- Proposal `proposal_22b20fc135d1bdc14494ae3887d3248d`: `REJECTED`.
- Strict data-cutoff dry-run `research_cycle_e9df73b81c44222b943ab06a5a908758`: freshness `READY`, dirty windows `0`, blocked `false`, `allow_stale=false`.

Final evidence audit stayed `CLEAN` with fixture rows `0`, active models `0`, and dirty windows `0`. No model activation, broker execution, order routing, WebSocket production ingestion, options data, stale bypass, secret exposure, or profitability claim occurred.

## Phase 23 Handoff - 2026-07-05

`PHASE_23_STATUS = ACCEPTED_NO_ROBUST_FILTER`.

Phase 23 completed the diagnostic candidate-filter experiment focused on 15min `ten_am_reversal_zone` and signal-time ambiguity-risk suppression. It used persisted real bars/features/candidates from the clean evidence database only. The filter spec is `phase23_filter_spec.v1`, hash `be9de3e9bbe516f882174df8eeebee19f0f66f970e7177f2e1ea287b3289a106`.

Phase 23 generated 8 replay runs, 8 full default-grid sensitivity runs, 600 Phase 23 sensitivity scenarios, and 57 new export records. Final evidence audit: `CLEAN`, fixture rows `0`, active models `0`, dirty windows `0`, total rows `184006`, exports `295`.

Filter decisions:

- `P23_FILTER_A_BASE_15M_TEN_AM`: `BLOCKED_BY_SENSITIVITY`.
- `P23_FILTER_B_AMBIGUITY_SUPPRESSED`: `BLOCKED_BY_SENSITIVITY`.
- `P23_FILTER_C_WEAK_FAMILY_SUPPRESSED`: `BLOCKED_BY_LOW_SAMPLE`.
- `P23_FILTER_D_TAKE_WATCH_SLICE`: `BLOCKED_BY_LOW_SAMPLE` despite 75/75 sensitivity pass because it only had 9 candidates and 6 validation trades.

Reports:

- `docs/status/PHASE_23_FILTER_SPEC_2026-07-05.md`
- `docs/status/PHASE_23_FILTERED_REPLAY_RESULTS_2026-07-05.md`
- `docs/status/PHASE_23_FILTERED_SENSITIVITY_RESULTS_2026-07-05.md`
- `docs/status/PHASE_23_SPECIALIST_CANDIDATE_DECISION_2026-07-05.md`
- `docs/status/PHASE_23_COMPARISON_2026-07-05.md`
- `docs/status/PHASE_23_COMPLETION_2026-07-05.md`

No model was activated, no proposal was approved, no broker/order/options path was used, no WebSocket production ingestion was used, no stale gate was bypassed, no secrets were exposed, and no profitability claim is made.

## Phase 24 Handoff

`PHASE_24_STATUS = ACCEPTED_NEEDS_MORE_DATA`.

Phase 24 expanded the clean evidence store for the pre-registered 15min `ten_am_reversal_zone` TAKE/WATCH specialist hypothesis. FMP REST header-auth ingestion covered `SPY`, `QQQ`, `AAPL`, and `NVDA` for `15min` and `1day` from `2026-05-15` through `2026-07-02`, producing 33 RTH dates. The key was loaded through runtime settings from ignored `.env.local`; no key was printed, committed, exported, or placed in a query string.

Artifacts were rebuilt from persisted real bars: final counts are 22,284 bars, 22,284 features, 27,514 candidate signals, 5,007 labels, 40 replay runs, 36 sensitivity runs, 1,848 sensitivity scenarios, and 305 exports. Dirty windows are `0`, active models are `0`, and fixture rows remain `0`.

The Phase 24 filter spec hash is `220cbea95476458b0cfd7c78ec4f297dd6bd404f5c101cbafdcda3661d741d5d`. The expanded base 15min ten-am cohort had 330 actionable candidates. A discovery-trained inactive scorer (`amd-replay-aware-20260611-181743`) scored 145 post-embargo OOS candidates and selected only 2 TAKE candidates, both in holdout. Portfolio replay `r24_prereg_p_f949d7230c32` and counterfactual replay `r24_prereg_c_f949d7230c32` both had avg R `-1.000000`; full-grid sensitivities `s24_prereg_p_f949d7230c32` and `s24_prereg_c_f949d7230c32` both had robustness `0.00`. Calibration audit `calibration_e2e0661d5b36ca23f485cd70b7fea585` rejected the slice with `minimum_high_grade_samples_not_met`.

Freshness report `freshness_e8ee87ff192c840166144de76f59651e` was `READY`; strict dry-run `research_cycle_418dee617dd11a6041c8b6ed8bfe20a5` used `allow_stale=false` and was not blocked, while recording data-quality/provider-history warnings. No model was activated, no proposal was approved, no broker/order path was used, no WebSocket production ingestion was used, no stale gate was bypassed, and no profitability claim is made.
