# Phase 21 Gate Attribution - 2026-07-04

`PHASE_21_STATUS = DIAGNOSTICS_COMPLETE_CURRENT_DB_BLOCKED`

Phase 21 is diagnostic only. The challenger remains rejected. No model activation, proposal approval, broker execution, order routing, stale-gate bypass, production WebSocket ingestion, black-box ML, or profitability claim occurred.

## Evidence Boundary

This report uses the Phase 20/21 evidence snapshot collected before the regression-command incident. After the diagnostic collection, `make api-smoke-postgres` and `make repository-parity-test` wrote parity fixtures into the default Postgres database because the tests hardcode `adaptive_market_decoder`. Current Postgres now contains `parity-*` artifacts and is not certification evidence until restored.

Missing Phase 20 subreports requested by the architect were not found and are treated as documentation gaps, not inferred evidence:

- `docs/status/PHASE_20_MODEL_TRAINING_2026-07-04.md`
- `docs/status/PHASE_20_VALIDATION_CALIBRATION_2026-07-04.md`
- `docs/status/PHASE_20_MODEL_REVIEW_PROPOSAL_2026-07-04.md`
- `docs/status/PHASE_20_RESEARCH_CYCLE_RUN_2026-07-04.md`
- `docs/live-data-research-cycle-results.md` was missing before Phase 21 and has now been created.

## Artifact IDs

| Artifact | ID |
|---|---|
| Research cycle | `research_cycle_ece57ebd9e3f0efa4d4fa48c0518b821` |
| Challenger model | `amd-replay-aware-20260702-195615` |
| Validation report | `report_0091f7e03f0bd9d674ff6fdb75219b0e` |
| Calibration audit | `calibration_a22adf288c34de793f37e474515b377a` |
| Model review | `model_review_ae563bded0b1a0ab4eedbb35e99e4d66` |
| Cycle champion/challenger comparison | `champion_challenger_d7ff387488ea651b063c1a4c809c342e` |
| Direct champion/challenger comparison | `champion_challenger_55114da3840f82134efb1b39eb6b1f25` |
| Cycle proposal | `proposal_e800968cc4ba52a648f6bc00430d306b` |
| Direct proposal | `proposal_ca9d2a25a6eda708ea88e1706e4313ab` |
| Portfolio replay | `replay_20260704195543_48a6b35debfd62244361ea09` |
| Counterfactual replay | `replay_20260704195544_df74191456eb8e03eaec364e` |
| Counterfactual vs portfolio comparison | `comparison_4ff8bc0505bf9f940764b051b150b9dd` |

## Data Gates

| Gate | Result | Attribution |
|---|---:|---|
| Freshness | PASS | Phase 20 research-scope freshness was `READY`; strict cycle used `allow_stale=false`. |
| Dirty windows | PASS | Pre-regression dirty windows were 0. |
| Invalid/duplicate bars | PASS | Data-quality summary had invalid bars 0 and duplicate bars 0. |
| Missing windows | WARNING | Missing-bar heuristic reported 12 windows; comparison gate still recorded `data_quality_pass=true`. |
| Provider/capability review | WARNING | 42 provider requests were HTTP 200 `ACCESSIBLE`, but data quality counted statuses outside `ok/success/cached` as provider errors. This is a status-normalization issue, not a challenger rejection cause. |

Data gates did not reject the challenger. The persisted comparison gates recorded `stale_window_pass=true` and `data_quality_pass=true`.

## Replay Gates

| Replay | Key Metrics | Attribution |
|---|---|---|
| Portfolio replay | 1,610 candidates, 405 taken, 1,205 skipped, average R -0.1327, PF 0.7956, win rate 0.3481, same-bar ambiguity 30/405. | Not an explicit governance rejection, but weak portfolio replay quality and heavy overlap constrain confidence. |
| Counterfactual replay | 1,610 candidates, 1,608 taken, 2 skipped, average R -0.1578, PF 0.7607, win rate 0.3389, same-bar ambiguity 87/1608. | Candidate-quality evidence only; not executable P/L. Evidence does not show broad positive expectancy. |
| Skip reasons | Portfolio: `overlapping_trade=1204`, `missing_entry_bar=1`; counterfactual: `missing_entry_bar=2`. | High overlap/concurrency is an evidence-quality concern. |
| Sensitivity | No sensitivity runs attached to the challenger. | Model warning: `some_training_replay_runs_missing_sensitivity`; unresolved review warning, not the primary rejection reason. |

Replay gates did not directly reject through the persisted comparison gate, but they explain why evidence remains fragile.

## Evidence And Model Gates

| Gate | Result | Attribution |
|---|---:|---|
| Evidence cells | 421 | Enough cells existed for model construction, but not enough selected validation trades. |
| Observed outcomes | 2,013 mixed observed outcomes | Model included 1,608 counterfactual and 405 portfolio outcomes. |
| Model expectancy | FAIL quality signal | Model metrics: average R -0.1528, median R -1.0, total R -307.4931, PF 0.7676, win rate 0.3408. |
| Model activation decision | REJECTED | Model row stayed inactive with rejection reason `validation_required`. |
| Warnings | UNRESOLVED | `some_training_replay_runs_missing_sensitivity`. |

The model row alone did not activate because validation was required and failed downstream.

## Validation Gates

Validation report `report_0091f7e03f0bd9d674ff6fdb75219b0e` rejected the challenger.

| Gate | Result |
|---|---:|
| Mode | `replay_aware_walk_forward` |
| Train window | 2026-07-01 13:30:00 UTC to 2026-07-01 19:59:00 UTC |
| Validation window | 2026-07-02 13:30:00 UTC to 2026-07-02 19:59:00 UTC |
| Test window | none |
| Training replay IDs | `replay_20260704195544_df74191456eb8e03eaec364e` |
| Validation replay IDs | `replay_20260704195543_48a6b35debfd62244361ea09` |
| Scored candidates | 953 |
| Selected candidates | 1 |
| Suppressed candidates | 952 |
| Observed selected outcomes | 1 |
| Selected R values | `[1.4999999999999198]` |
| Selected average / median R | 1.5000 / 1.5000 |
| Selected PF | 99.0, based on one observed selected trade |
| Selected max drawdown | 0.0 |

Validation rejection reasons:

- `minimum_selected_candidate_sample_not_met`: selected sample was 1; activation criteria require at least 30 selected trades.
- `single_setup_profit_concentration_too_high`: selected evidence was 1/1 in `VWAP loss short`.
- `single_symbol_profit_concentration_too_high`: selected evidence was 1/1 in `QQQ`.

This is the primary persisted rejection cause.

## Calibration Gates

Calibration audit `calibration_a22adf288c34de793f37e474515b377a` did not reject the challenger.

| Gate | Result |
|---|---:|
| Monotonicity | PASS |
| Rank correlation | 0.2824 |
| Rejection reasons | none |
| Warning | `score_concentrated_in_one_bucket` |
| TAKE vs WATCH separation | TAKE average R 0.9748 vs WATCH 0.6038 |
| High-grade sample count | A grade sample size 13 |

Score bins:

| Score Bin | Sample | Avg R | PF | Same-Bar Rate |
|---|---:|---:|---:|---:|
| 0-20 | 0 | 0.0000 | 0.0000 | 0.0000 |
| 20-40 | 1413 | -0.2863 | 0.5976 | 0.0594 |
| 40-60 | 0 | 0.0000 | 0.0000 | 0.0000 |
| 60-75 | 144 | 0.7240 | 3.4245 | 0.0208 |
| 75-85 | 51 | 0.9118 | 4.8750 | 0.0000 |
| 85-100 | 0 | 0.0000 | 0.0000 | 0.0000 |

Action bins:

| Action | Sample | Avg R | PF |
|---|---:|---:|---:|
| TAKE | 89 | 0.9748 | 6.1031 |
| WATCH | 106 | 0.6038 | 2.6842 |
| SUPPRESS | 1413 | -0.2863 | 0.5976 |

Calibration did not cause the proposal rejection. The score concentration warning remains a weakness because 1,413 of 1,608 joined outcomes are in the 20-40 bin.

## Drift And Model Review Gates

| Gate | Result | Attribution |
|---|---:|---|
| Drift | PASS by absence | No drift report was attached; comparison gate recorded `drift_pass=true`. Missing drift evidence is a future evidence gap, not the persisted rejection reason. |
| Model review | BLOCK | `model_review_ae563bded0b1a0ab4eedbb35e99e4d66` readiness status `BLOCK`. |
| Review reasons | FAIL | `validation_rejected`. |
| Unresolved warnings | WARNING | `score_concentrated_in_one_bucket`, `some_training_replay_runs_missing_sensitivity`. |

Model review blocked because validation rejected the challenger.

## Proposal And Decision Gates

Both proposals persisted as rejected:

| Proposal | Status | Readiness | Recommended Action | Rejection Reason |
|---|---|---|---|---|
| `proposal_e800968cc4ba52a648f6bc00430d306b` | `REJECTED` | `BLOCK` | `REJECT_CHALLENGER` | `comparison_gates_failed` |
| `proposal_ca9d2a25a6eda708ea88e1706e4313ab` | `REJECTED` | `BLOCK` | `REJECT_CHALLENGER` | `comparison_gates_failed` |

Comparison gate results:

- `challenger_present=true`
- `calibration_pass=true`
- `stale_window_pass=true`
- `data_quality_pass=true`
- `drift_pass=true`
- `validation_pass=false`
- `model_review_pass=false`
- `all_passed=false`

Decision ledger rows:

- `decision_ac5ddb4414aca73fd96c44581d633812`: `PROPOSAL_CREATED`, `RECORDED`, reason `REJECT_CHALLENGER`, direct comparison evidence.
- `decision_8ab341bd964102908dbd5db103fd8821`: `CYCLE_CREATED`, `CREATED`, reason `controlled_research_cycle_created`.
- `decision_29603013acf2d45906e909b47715adbc`: `PROPOSAL_CREATED`, `RECORDED`, reason `REJECT_CHALLENGER`, cycle comparison evidence.
- `decision_abbaa0eee561a235822e1c4d9bbc576f`: `CYCLE_COMPLETED`, `BLOCKED`, reason `REJECT_CHALLENGER`.

## Bottom Line

The exact rejection path is:

`validation rejected` -> `model review BLOCK` -> `comparison all_passed=false` -> `proposal REJECTED` -> `research cycle BLOCKED`.

Recommended action remains `REJECT_CHALLENGER`. The current Postgres database must be restored or regenerated before any additional certification work.
