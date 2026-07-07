# Phase 20 Completion Report - 2026-07-04

`PHASE_20_STATUS = ACCEPTED_RESEARCH_CYCLE_RECORDED`

Phase 20 completed live-data research-cycle execution, replay-aware inactive model review, and challenger proposal generation on top of a repaired and regenerated Phase 19D runtime. The challenger was not activated. The final research cycle and proposal correctly remained blocked/rejected because validation and review gates did not pass.

## Guardrails

- Model activation remained disabled. No `confirm_manual_activation` path was used.
- Broker execution, order routing, options execution, and production WebSocket ingestion were not used.
- `allow_stale=true` was not used to bypass research-cycle gates.
- No profitability claim is made. Any model output is diagnostic research evidence only.
- The FMP key was supplied only through one-shot runtime environment use during live regeneration. It was not written to tracked files, reports, exports, logs, or `.env.local`.

## Recovery Note

During Phase 20 verification, a mutating parity test contaminated the default Postgres evidence database with repository-parity fixture data. That polluted database was not used for certification. The default `adaptive_market_decoder` database was dropped, recreated, migrated fresh, and regenerated from live FMP data before the final Phase 20 run.

After recovery, mutating tests were run only against isolated or temporary databases. The final evidence database was inspected and secret-scanned after the final Phase 20 run without running additional mutating tests against it.

## Phase 19D Regenerated Base

Live FMP seed and artifact rebuild were rerun for `SPY`, `QQQ`, `AAPL`, and `NVDA` across `1day`, `1min`, `5min`, and `15min`.

- FMP endpoint review: `READY`, 8 reviewed accessible endpoints.
- Seed dry-run: `status=dry_run`, `would_block=false`.
- Live seed: `ingestion_4fc0db6c7e60361dfb4bfda94a9428b0`, `COMPLETED`, fetched `3964`, inserted `3964`, updated `0`.
- Idempotent seed rerun: `ingestion_2a38804e2754949d34830c5adad5fe7c`, `COMPLETED`, fetched `3964`, inserted `0`, updated `3964`.
- Feature rebuild: `3960` bars read, `3960` features written.
- Candidate rebuild: `3960` features read, `4846` candidates written.
- Label rebuild: `3960` bars/features read, `578` labels written.
- Session cleanup rebuild: final features `3960`, candidates `4905`, labels `611`.
- Replay rebuilds: 6 total replay runs, `4530` simulated trades.
- Freshness: default historical wall-clock report remained `BLOCKED`; research-scope freshness was `READY`.
- Strict Phase 19D dry-run: `research_cycle_3e41837161c45d3deb235347cc7df8ce`, blocked `false`.
- Dirty windows after regeneration: `0`.

## Final Data After-State

Final database: `adaptive_market_decoder`.

| Artifact | Count / Status |
| --- | ---: |
| Bars | 3960 |
| Bars by interval | `1day=8`, `1min=3120`, `5min=624`, `15min=208` |
| Features | 3960 |
| Candidate signals | 4905 |
| Labels | 611 |
| Replay runs | 6 |
| Simulated trades | 4530 |
| Dirty windows | 0 |
| Invalid bars | 0 |
| Duplicate bars | 0 |
| Missing bar windows detected | 12 |
| Provider request errors recorded | 42 |
| Provider capability warnings | 0 |
| Evidence cells | 421 |
| Score audits | 3756 |
| Active default model | none |
| Active replay-aware model | none |
| Latest validation | `report_0091f7e03f0bd9d674ff6fdb75219b0e`, `rejected` |
| Latest research cycle | `research_cycle_ece57ebd9e3f0efa4d4fa48c0518b821`, `BLOCKED` |
| Latest proposal | `proposal_e800968cc4ba52a648f6bc00430d306b`, `REJECTED`, `REJECT_CHALLENGER` |
| Export records | 33 |

The bounded Phase 20 research window used `3956` real FMP bars: `1day=4`, `1min=3120`, `5min=624`, `15min=208`.

## Replay Inputs

The replay-aware model used clean regenerated Phase 19D replay evidence:

| Replay | Type | Trades | Stale Status | Config Hash | Input Fingerprint |
| --- | --- | ---: | --- | --- | --- |
| `replay_20260704195543_48a6b35debfd62244361ea09` | `candidate_market_replay` | 1610 | clean | `e4e6a27526fe2cea047798e77def1a50681fb37fe3c1a53d026b2ea754708175` | `16e582758e849dd5f113cfb7ec87c5bc0f8c9058ae78ac131c5dd35e0160e898` |
| `replay_20260704195544_df74191456eb8e03eaec364e` | `model_training_counterfactual` | 1610 | clean | `99310a3e7b793c6753b1b95268edd545119f602d871cbe7197842e8c5bb06c13` | `7e9c059199ddcf67f9e240515b85276aac17b68f98322ae7e404e67754338427` |

## Inactive Challenger Training

Trained model: `amd-replay-aware-20260702-195615`.

- Activation state: inactive.
- Activation decision: rejected.
- Rejection reason: `validation_required`.
- Outcome source: `mixed_allowed`.
- Candidate outcome rows: `3220`.
- Observed outcomes: `2013`.
- Counterfactual observed outcomes: `1608`.
- Portfolio observed outcomes: `405`.
- Evidence cells: `421`.
- Training config hash: `a013020b5fad6c171078a5c653480744ab11ea99673a02f6e5598f67b0592859`.
- Training warning: `some_training_replay_runs_missing_sensitivity`.

Training diagnostics recorded average R `-0.15275366005849633`, median R `-1`, total R `-307.4931176977531`, profit factor `0.7676299529394439`, and win rate `0.34078489816194735`. These are retrospective research diagnostics only and are not a profitability claim.

## Candidate Scoring

- Score status: `ok`.
- Candidates scored: `3756`.
- Action counts: `SUPPRESS=3561`, `TAKE=89`, `WATCH=106`.
- Grade counts: `NO_TRADE=3561`, `A-=13`, `B+=76`, `B=75`, `C=31`.

## Replay-Aware Validation

Validation report: `report_0091f7e03f0bd9d674ff6fdb75219b0e`.

- Decision: rejected.
- Rejection reasons: `minimum_selected_candidate_sample_not_met`, `single_setup_profit_concentration_too_high`, `single_symbol_profit_concentration_too_high`.
- Training split: July 1, 2026, `13:30-19:59`, counterfactual replay.
- Validation split: July 2, 2026, `13:30-19:59`, portfolio replay.
- Validation candidates: `953`.
- Scored candidates: `953`.
- Selected candidates: `1`.
- Suppressed candidates: `952`.
- Observed outcome count: `1`.
- No-future-leakage enforcement: true.
- Embargo bars: `1`.
- Window ID: `replay-aware-wf-2e8c1f8e49ee8abc`.

The validation rejection is expected: the selected validation sample was far too small, and concentration gates failed.

## Calibration Audit

Calibration audit: `calibration_a22adf288c34de793f37e474515b377a`.

- Scored outcome count: `1608`.
- Rank correlation: `0.28240938872186594`.
- Monotonicity pass: true.
- Rejection reasons: none.
- Warning: `score_concentrated_in_one_bucket`.
- Provenance method: `score_audit_replay_outcome_join`.
- Joined rows: `1608`.
- Score audit rows: `3756`.
- Outcome rows: `1610`.
- Probability calibration: false; this is rank/ordering calibration only.

## Model Review, Comparison, and Proposal

- Model review: `model_review_ae563bded0b1a0ab4eedbb35e99e4d66`, readiness `BLOCK`, reason `validation_rejected`.
- Generic model comparison: `model_comparison_b10a994c29409a8ff79141df39e16419`, diagnostic only.
- Direct champion/challenger comparison: `champion_challenger_55114da3840f82134efb1b39eb6b1f25`, readiness `BLOCK`, recommended action `REJECT_CHALLENGER`.
- Direct proposal: `proposal_ca9d2a25a6eda708ea88e1706e4313ab`, status `REJECTED`, recommended action `REJECT_CHALLENGER`, rejection reason `comparison_gates_failed`.

Champion/challenger gates:

| Gate | Result |
| --- | --- |
| Calibration | pass |
| Stale inputs | pass |
| Data quality | pass |
| Replay-aware validation | fail |
| Model review | fail |
| All gates | fail |

## Strict Research Cycle

Controlled research cycle: `research_cycle_ece57ebd9e3f0efa4d4fa48c0518b821`.

- Cycle status: `BLOCKED`.
- Comparison ID: `champion_challenger_d7ff387488ea651b063c1a4c809c342e`.
- Proposal ID: `proposal_e800968cc4ba52a648f6bc00430d306b`.
- Proposal status: `REJECTED`.
- Recommended action: `REJECT_CHALLENGER`.
- Diagnostic only: true.
- Model activation unchanged: true.
- Artifact count: `3`.
- Warnings: `Research cycle completed without model activation.`, `missing_bar_windows_detected`, `provider_request_errors_detected`.

The strict cycle was recorded with `allow_stale=false`. It was blocked by model governance gates, not by a stale-gate bypass.

## Export Ledger

All Phase 20 exports were registered with source IDs and SHA-256 hashes.

| Export | Source | Rows | Path | SHA-256 |
| --- | --- | ---: | --- | --- |
| `export_9f574b58d442a12185fc9e70b7860d2e` | `amd-replay-aware-20260702-195615` | 421 | `exports/replay_aware_model_summary_amd-replay-aware-20260702-195615.xlsx` | `ed7eb1d25ac4e94c040659c3aebd458cbbf4a23b2affb25f54593c8b09643740` |
| `export_53b47624cc32ad0879364f6ef8873da4` | `amd-replay-aware-20260702-195615` | 421 | `exports/evidence_cells_amd-replay-aware-20260702-195615.csv` | `84376f45680ad50fb7d39b65e1085520c95a6d75b99ad3660122fa2735de00c0` |
| `export_28a3dae638da630de43c1678a9d2e500` | `amd-replay-aware-20260702-195615` | 421 | `exports/evidence_cells_amd-replay-aware-20260702-195615.xlsx` | `b198252b0deb38cff522090fea444abd04a154a644fb8f6e0f1d9e6b6cee8fac` |
| `export_4ceadc6b3a107419e395e15723145f88` | `amd-replay-aware-20260702-195615` | 3756 | `exports/score_audits_amd-replay-aware-20260702-195615.csv` | `cfaab572aac24cfc18973370d2e0a49e43e0b76274ccda1c455447372af56f61` |
| `export_9dc9376e7e79fec18e42969972bcfaa1` | `amd-replay-aware-20260702-195615` | 3756 | `exports/score_audits_amd-replay-aware-20260702-195615.xlsx` | `26fd873a789b66f5711e8fb9b3da89addf5b1b4228c5ba476600c2d0a5191914` |
| `export_6a84444dacc047c2f2981518d048d6d5` | `report_0091f7e03f0bd9d674ff6fdb75219b0e` | n/a | `exports/replay_aware_validation_report_0091f7e03f0bd9d674ff6fdb75219b0e.xlsx` | `7a813ba16b3cb0b37fc2f8aadd3d5ab402e554ce2a33a2b00aa1b76381efef10` |
| `export_719ce597c046363ce0f556f05f8aec00` | `calibration_a22adf288c34de793f37e474515b377a` | 13 | `exports/calibration_audit_calibration_a22adf288c34de793f37e474515b377a.xlsx` | `734e0a0c80dcfbc5a62f6adacf75176b5f90aa3364fd71337dfbc80826ddba88` |
| `export_fbeba88d0f575c1f6c838ae9348ea9ba` | `calibration_a22adf288c34de793f37e474515b377a` | n/a | `exports/calibration_bins_calibration_a22adf288c34de793f37e474515b377a.csv` | `728f7b126136406041e195db326b389b4e5dffbcb528f00f6d5e7eb59583b28e` |
| `export_609d44a9ce79d4e6bb59515fe31e7951` | `calibration_a22adf288c34de793f37e474515b377a` | n/a | `exports/calibration_bins_calibration_a22adf288c34de793f37e474515b377a.xlsx` | `ec4ed6cab378393a0bc11cbfd347bd44fef21507cfdbaeedd901f8487fbcc82d` |
| `export_6cb2ec9aaac7b93120df39d6f3d2f669` | `calibration_a22adf288c34de793f37e474515b377a` | n/a | `exports/calibration_metrics_calibration_a22adf288c34de793f37e474515b377a.json` | `785252088a8bda91034ab053446a0accae0933b4dc29be035d6498005971559f` |
| `export_650e33f4c8ebc3e33e5e996e406a199c` | `model_review_ae563bded0b1a0ab4eedbb35e99e4d66` | n/a | `exports/model_review_model_review_ae563bded0b1a0ab4eedbb35e99e4d66.xlsx` | `73971c3e1a5387b13865011b53f140a64daeb0e2c31b9abf98db11b764492bed` |
| `export_cb0b380bcf368cb9206224da5e28c71e` | `model_review_ae563bded0b1a0ab4eedbb35e99e4d66` | n/a | `exports/model_review_model_review_ae563bded0b1a0ab4eedbb35e99e4d66.json` | `591f82caea5898d10d3137638c172fed1433924b98016ebe2f62273f7d85650a` |
| `export_094b6ec694949e65d8554e0ffdb9e47d` | `model_comparison_b10a994c29409a8ff79141df39e16419` | n/a | `exports/model_comparison_model_comparison_b10a994c29409a8ff79141df39e16419.xlsx` | `7af033a39d93da160273684f5c7fb8b6410d4960f5b4851cea2582affd5620df` |
| `export_e31e721efa617800f3fa89facf673bbb` | `champion_challenger_55114da3840f82134efb1b39eb6b1f25` | n/a | `exports/champion_challenger_comparison_champion_challenger_55114da3840f82134efb1b39eb6b1f25.xlsx` | `940dfcaf8ad83e0989bd11f87760ff7b641367145b63c94223a1b4e57f4df53b` |
| `export_42068e616d1fd83397ba6d72bc61171d` | `proposal_ca9d2a25a6eda708ea88e1706e4313ab` | n/a | `exports/model_proposal_proposal_ca9d2a25a6eda708ea88e1706e4313ab.xlsx` | `75e716eff83bd9a15b927831bf8f853e27c7162fb6d72b970fd6aaa41b5f1a80` |
| `export_68a4a6b6c744cb039545d95ba417f293` | `proposal_ca9d2a25a6eda708ea88e1706e4313ab` | n/a | `exports/model_proposal_proposal_ca9d2a25a6eda708ea88e1706e4313ab.json` | `5cd6938bdc68de2493bb2d2eec291b3b1e200117f2c3210b0daf601fe6f8b439` |
| `export_0d20fa774402c7c9cc0d1500f725137d` | `research_cycle_ece57ebd9e3f0efa4d4fa48c0518b821` | n/a | `exports/research_cycle_research_cycle_ece57ebd9e3f0efa4d4fa48c0518b821.xlsx` | `3bf199d9004e541762afdad7701cb9a99605fe2305d2a5263d50934cd1cbca9e` |
| `export_9884bb1888c1458261847d38a60774f5` | `research_cycle_ece57ebd9e3f0efa4d4fa48c0518b821` | n/a | `exports/research_cycle_research_cycle_ece57ebd9e3f0efa4d4fa48c0518b821.json` | `46d60b56a849adb3476ad3e6540c62745ed55df3d79bd6e4212c1b3a139b8708` |
| `export_359161592b9bcf4efda67dedb4887504` | `champion_challenger_d7ff387488ea651b063c1a4c809c342e` | n/a | `exports/champion_challenger_comparison_champion_challenger_d7ff387488ea651b063c1a4c809c342e.xlsx` | `4644ce7fc36c348e72c17410948907b6d2c967bbb0a98c10e58b5cc122b52630` |
| `export_8089616ca335b8ed0f870622af88e9b8` | `proposal_e800968cc4ba52a648f6bc00430d306b` | n/a | `exports/model_proposal_proposal_e800968cc4ba52a648f6bc00430d306b.xlsx` | `10a6b2a9e2cf21fa66aae9a5e659fcd6f6dee411e8d13d96aea8f1d9fa770133` |
| `export_5b0df8bc0aa949c5250e3f246909b7cb` | `proposal_e800968cc4ba52a648f6bc00430d306b` | n/a | `exports/model_proposal_proposal_e800968cc4ba52a648f6bc00430d306b.json` | `22a5222ef701743aebcb02bb5916753a69887aae0e475c06732492a799a0ddce` |

## Verification

- `make backend-test`: `125 passed`, `1 warning`.
- `make api-smoke-postgres`: `1 passed` against isolated `phase20_test`.
- `repository-parity-test`: `3 passed` after rerun against a fresh isolated database.
- `make backend-lint`: all checks passed.
- Final database inspection: Alembic `0012`, 44 expected tables, missing tables `none`, Timescale hypertable `bars`.
- Secret scan: `.env.local` absent, runtime `FMP_API_KEY` absent after run, repo high-entropy scan passed, export high-entropy scan passed.

## Certification

Phase 20 is accepted as a completed research-cycle certification because real FMP bars exist, downstream artifacts were rebuilt from those bars, replay-aware inactive challenger evidence was generated, strict validation/calibration/review/comparison/proposal gates were recorded, exports were generated with hashes and source IDs, tests passed, and secret scans passed.

The challenger is rejected for activation. No model is active, no execution system was used, and the platform remains research-only.
