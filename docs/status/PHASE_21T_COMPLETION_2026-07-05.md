# Phase 21T Completion Report - 2026-07-05

## 1. Executive Summary

`PHASE_21T_STATUS = PARTIAL_BLOCKED`

Phase 21T expanded the clean evidence database from live FMP REST data for `SPY`, `QQQ`, `AAPL`, and `NVDA`; rebuilt downstream artifacts from persisted bars; recorded freshness and strict research-cycle dry-run evidence; trained and reviewed an expanded challenger; generated hashed exports; and re-audited the evidence DB as clean.

The phase is not accepted as a full challenger recovery. FMP returned only six RTH dates for `1min` despite bounded multi-window requests, and the challenger remained rejected by validation, calibration, model-review, comparison, and proposal gates. No model was activated, no broker execution was used, no WebSocket production ingestion was used, stale gates were not bypassed, no secrets were exposed, and no profitability claim is made.

## 2. Phase 21T Status

- Status: `PARTIAL_BLOCKED`
- Evidence DB: `adaptive_market_decoder_evidence`
- DB role: `evidence`
- Alembic revision: `0012_phase16_fmp_freshness`
- Final evidence audit: `CLEAN`
- Fixture-like rows: `0`
- Active models: `0`
- Dirty windows: `none`

## 3. Data Expansion Result

FMP was accessed only through runtime environment or ignored `.env.local`. The key was not committed, exported, logged, or placed in query strings.

Capability review covered eight REST endpoints and was `ok` with all latest rows reviewed accessible: `quote`, `quote_short`, `batch_quote`, `batch_quote_short`, `historical_eod_full`, `intraday_1min`, `intraday_5min`, and `intraday_15min`.

Live seed windows:

- `2026-06-18T13:30:00+00:00` to `2026-06-22T19:59:00+00:00`: `ingestion_2afbc605111ecaefa01a13fa450510cd`, 2404 fetched, 2400 inserted, 4 updated.
- `2026-06-23T13:30:00+00:00` to `2026-06-27T19:59:00+00:00`: `ingestion_9572060015dad11e79d3085ab426d74f`, 4804 fetched, 4800 inserted, 4 updated.
- `2026-06-28T13:30:00+00:00` to `2026-07-02T19:59:00+00:00`: `ingestion_c39f5b6ce1009948805ef4520717ef7b`, 6364 fetched, 2400 inserted, 3964 updated.
- Incremental rerun: `ingestion_cebbfd68034d90851bb1f44b758af758`, 1976 fetched, 0 inserted, 1976 updated.

Final bars by interval:

| Interval | Rows | RTH Dates |
|---|---:|---:|
| `1day` | 40 | 10 |
| `1min` | 9360 | 6 |
| `5min` | 3120 | 10 |
| `15min` | 1040 | 10 |

Provider limitation: `1min` rows were available for only six RTH dates across the requested bounded windows. `1day`, `5min`, and `15min` reached the 10-day target.

## 4. Artifact Rebuild Result

Downstream artifacts were rebuilt from persisted real bars:

- Bars: `13560`
- Features: `13560`
- Candidate signals: `16725`
- Labels: `2209`
- Replay runs: `18`
- Simulated trades: `25048`
- Sensitivity runs: `12`
- Sensitivity scenarios: `474`

Phase 21T replay IDs:

- `replay_20260705143752_33726551f81599994d55da1b` - `candidate_market_replay`, `1min`
- `replay_20260705143759_30a05915b7d9ab1dc2a0566c` - `model_training_counterfactual`, `1min`
- `replay_20260705144208_82503a09e00e1d0da0a7e81a` - `candidate_market_replay`, `5min`
- `replay_20260705144210_55307ab8666f790369db26b2` - `model_training_counterfactual`, `5min`
- `replay_20260705144213_53d13af7e89dbd3fb9df183b` - `candidate_market_replay`, `15min`
- `replay_20260705144213_95d4666a1f5446141889eb5b` - `model_training_counterfactual`, `15min`

Research-scope freshness was `READY`, with dirty windows clean. Strict research-cycle dry-run `research_cycle_16ad2689f01a0a0d3dd96bd680248377` used `allow_stale=false`, `refresh_data=false`, and did not activate models.

## 5. Governance Review Result

Expanded challenger: `amd-replay-aware-20260702-144429`

- Validation report: `report_cf53a27dbd47245b319e8a55f490182b`
- Validation decision: `rejected`
- Validation rejection reasons: `minimum_selected_candidate_sample_not_met`, `out_of_sample_expectancy_not_positive`, `profit_factor_below_threshold`
- Calibration audit: `calibration_6c40fa2999b92e0c68a252e1634b5c11`
- Calibration rejection reasons: `minimum_high_grade_samples_not_met`, `take_does_not_outperform_watch`
- Drift report: `calibration_drift_3836049826a9239e3a0fc36842ba2c5e`, severity `REVIEW`
- Model review: `model_review_9262300c8d3fffe75e0ff0e98ebe90d3`, readiness `BLOCK`
- Research cycle: `research_cycle_938bf1f9375fecb54a7cfb1ebf00c255`, status `BLOCKED`
- Comparison: `champion_challenger_635360662a088fdf74510924504c67f8`, recommended action `REJECT_CHALLENGER`
- Proposal: `proposal_c34d0341e050a30bcdd815ffc0b0fa70`, status `REJECTED`, readiness `BLOCK`

The default expanded validation path did not complete in practical runtime because evidence-cube rebuild work scaled poorly on the expanded sample. A bounded 15-minute validation slice was persisted and still rejected the challenger.

## 6. Phase 21S vs 21T Comparison

| Metric | Phase 21S | Phase 21T |
|---|---:|---:|
| Bars | 3960 | 13560 |
| Features | 3960 | 13560 |
| Candidate signals | 4846 | 16725 |
| Labels | 578 | 2209 |
| Replay runs | 12 | 18 |
| Simulated trades | 9060 | 25048 |
| Sensitivity runs | 6 | 12 |
| Sensitivity scenarios | 450 | 474 |
| Evidence cells | 421 | 1562 |
| Score audits | 3723 | 20380 |
| Exports | 94 | 158 |
| Active models | 0 | 0 |
| Fixture rows | 0 | 0 |

Phase 21T materially expanded evidence but did not recover the challenger.

## 7. Proposal And Activation Status

Proposal `proposal_c34d0341e050a30bcdd815ffc0b0fa70` is `REJECTED` with recommended action `REJECT_CHALLENGER`. The pass/fail gates did not all pass: validation, calibration, and model-review gates blocked activation. `active_models` remains `0`.

## 8. Test Isolation Status

Test database isolation remains in force through `TEST_DATABASE_URL=postgresql+psycopg://amd:amd@localhost:15432/adaptive_market_decoder_test` and `AMD_DB_ROLE=test` for mutating Postgres tests.

During verification, one targeted research-cycle command was initially run with the evidence `DATABASE_URL` still present in the shell. That created 85 temporary test rows in the evidence DB, including one accidental active model. Those rows were removed by the exact 2026-07-05 14:59 UTC test window and known test identifiers (`champion`, `challenger`, `phase10-model`). Final post-cleanup audits returned to the Phase 21T after-state: `active_models=0`, `bars=13560`, `dirty_windows=none`, `fixture_rows=0`.

## 9. Export Verification

Export manifest:

- Path: `exports/phase21t_export_manifest_20260705.json`
- Export ID: `export_9d7693a6f36bf21cb64ed7e32e03eed0`
- SHA-256: `5901918df1860f0f0002441d4303f8adf7cf9cd4db029daf8f357936566130ee`
- Export pack count before manifest: `54`
- Final DB export rows: `158`

The manifest records source IDs for ingestion, replay, sensitivity, validation, calibration, drift, model review, research cycle, comparison, and proposal artifacts. Export records include file hashes and source run IDs.

## 10. Commands And Tests Run

Passed:

- `make doctor`
- `make db-migrate`
- `make db-inspect`
- `make db-query-diagnostics`
- `make evidence-db-audit`
- `make test-db-smoke`
- `make evidence-guard-test`
- `make backend-test` - 127 passed
- `make backend-lint`
- `make backend-typecheck`
- `make api-smoke-postgres`
- `make repository-parity-test`
- `make model-review-test`
- `make research-cycle-test` with clean local-registry env
- `make export-test` with clean local-registry env
- `make scheduler-test` with clean local-registry env
- `corepack pnpm check`
- `corepack pnpm build`
- `corepack pnpm test`
- `corepack pnpm lint`
- `corepack pnpm --filter @amd/web test:e2e` - 11 passed
- `python -m compileall services/quant-engine/app services/quant-engine/tests`
- `git diff --check`
- `git check-ignore .env.local`
- Secret env files untracked check
- Raw FMP key scan outside ignored `.env.local`
- FMP assignment scan excluding the real key
- Provider URL query secret scan, excluding intentional `apikey=super-secret` redaction fixtures in tests
- Provider metadata redaction scan

## 11. Code And Docs Changes Made

No runtime code changes were required for Phase 21T. The phase generated runtime evidence, DB artifacts, export records, and documentation.

Phase 21T documentation added:

- `docs/status/PHASE_21T_DATA_EXPANSION_2026-07-05.md`
- `docs/status/PHASE_21T_ARTIFACT_REBUILD_2026-07-05.md`
- `docs/status/PHASE_21T_GOVERNANCE_REVIEW_2026-07-05.md`
- `docs/status/PHASE_21T_COMPARISON_2026-07-05.md`
- `docs/status/PHASE_21T_COMPLETION_2026-07-05.md`

Runtime summaries and exports:

- `data/raw/phase21t/phase21t_live_expansion_summary.json`
- `data/raw/phase21t/phase21t_artifact_rebuild_summary.json`
- `data/raw/phase21t/phase21t_governance_summary.json`
- `exports/phase21t_export_manifest_20260705.json`

## 12. Critical Blockers

- FMP returned only six RTH dates for `1min`, so the 10-day intraday target is only partially satisfied for that interval.
- Full and medium expanded replay-aware walk-forward validation exceeded practical runtime before persisting.
- The expanded challenger failed validation, calibration, model-review, comparison, and proposal gates.
- Research-cycle data quality reported missing bar windows and provider request errors even though stale-window gates were clean for the rebuilt research scope.

## 13. Remaining Risks

- `1min` provider depth may require different FMP plan support, narrower date chunking, or another reviewed REST source.
- Replay-aware validation needs a scaling pass before expanded validation can run over the full evidence set.
- The current score distribution remains calibration-fragile, with too few high-grade samples.
- Sensitivity robustness remained weak under the bounded grid.

## 14. Paths To Phase 21T Docs

- `docs/status/PHASE_21T_PLAN_2026-07-05.md`
- `docs/status/PHASE_21T_DATA_EXPANSION_2026-07-05.md`
- `docs/status/PHASE_21T_ARTIFACT_REBUILD_2026-07-05.md`
- `docs/status/PHASE_21T_GOVERNANCE_REVIEW_2026-07-05.md`
- `docs/status/PHASE_21T_COMPARISON_2026-07-05.md`
- `docs/status/PHASE_21T_COMPLETION_2026-07-05.md`
- `docs/live-data-research-cycle-results.md`
- `docs/HANDOFF.md`

## 15. Exact Next Recommended Phase

`PHASE 21U - Validation Scaling and 1-Minute Provider Coverage Recovery Plan`

Phase 21U should focus only on provider-depth recovery for `1min`, replay-aware validation scaling, and governance explainability. It must not activate models, approve rejected challengers, loosen gates, bypass stale checks, use broker execution, use production WebSocket ingestion, or claim profitability.
