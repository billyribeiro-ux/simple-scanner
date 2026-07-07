# Phase 25 Completion

`PHASE_25_STATUS = ACCEPTED_EVIDENCE_TOO_SPARSE`

Phase 25 completed scorer coverage diagnostics and OOS selection-failure analysis. No model was activated, no proposal was approved, no threshold was changed, no stale gate was bypassed, no broker or order path was used, and no profitability claim is made.

## Executive Summary

- OOS scored candidates: `145`.
- Actions: `{'SUPPRESS': 143, 'TAKE': 2}`.
- `WATCH` count is `0` because every below-TAKE OOS candidate carried at least one suppression reason; the scorer has no separate WATCH lower threshold.
- Suppressed candidates: `143`.
- Dominant suppression reason: `negative_expectancy_after_shrinkage` on `143` candidates.
- Exact evidence-cell match count: `128`; broad-parent-reliant count: `113`.
- OOS base counterfactual avg R: `-0.057926` across `145` trades.
- Selected TAKE counterfactual avg R: `-1.000000` across `2` trades.
- Next decision: `EVIDENCE_TOO_SPARSE`.

## Score Distribution Audit

| metric | count | min | p25 | median | mean | p75 | p90 | max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| score | 145 | 26.559700 | 35.000000 | 35.000000 | 35.077769 | 35.000000 | 35.000000 | 76.777100 |
| pre_ceiling_score_estimate | 145 | 49.342960 | 49.675300 | 49.953744 | 53.551155 | 52.136248 | 67.027372 | 74.710584 |
| evidence_quality_score | 145 | 0.000000 | 0.000000 | 0.000000 | 9.818572 | 3.687200 | 49.581400 | 66.041400 |
| risk_quality_score | 145 | 100.000000 | 100.000000 | 100.000000 | 100.000000 | 100.000000 | 100.000000 | 100.000000 |
| robustness_score | 145 | 100.000000 | 100.000000 | 100.000000 | 100.000000 | 100.000000 | 100.000000 | 100.000000 |
| ticker_personality_score | 145 | 21.074000 | 29.382500 | 32.379500 | 37.775216 | 45.668200 | 54.350600 | 76.583900 |
| regime_alignment_score | 145 | 75.000000 | 75.000000 | 75.000000 | 75.000000 | 75.000000 | 75.000000 | 75.000000 |
| time_bucket_score | 145 | 0.000000 | 0.000000 | 3.964100 | 9.955073 | 18.046200 | 26.972500 | 53.856100 |
| sample_confidence_score | 145 | 100.000000 | 100.000000 | 100.000000 | 100.000000 | 100.000000 | 100.000000 | 100.000000 |
| ambiguity_penalty | 145 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| stale_data_penalty | 145 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| label_vs_replay_divergence_penalty | 145 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| fragility_penalty | 145 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |
| concentration_penalty | 145 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 | 0.000000 |

Action distribution:

| action | count |
| --- | --- |
| SUPPRESS | 143 |
| TAKE | 2 |

## Suppression Reason Audit

| key | count |
| --- | --- |
| negative_expectancy_after_shrinkage | 143 |
| profit_factor_below_threshold | 112 |
| same_bar_ambiguity_dependency_too_high | 10 |

Top suppression pathways:

| pathway | count | symbols | setups | sides | median_expected_r | median_sample_count |
| --- | --- | --- | --- | --- | --- | --- |
| negative_expectancy_after_shrinkage+profit_factor_below_threshold \| NVDA \| failed breakdown long \| LONG \| trend_short | 8 | {'NVDA': 8} | {'failed breakdown long': 8} | {'LONG': 8} | -0.639869 | 804.000000 |
| negative_expectancy_after_shrinkage+profit_factor_below_threshold \| NVDA \| liquidity sweep reversal long \| LONG \| trend_short | 8 | {'NVDA': 8} | {'liquidity sweep reversal long': 8} | {'LONG': 8} | -0.639869 | 804.000000 |
| negative_expectancy_after_shrinkage+profit_factor_below_threshold \| NVDA \| failed breakout short \| SHORT \| trend_long | 6 | {'NVDA': 6} | {'failed breakout short': 6} | {'SHORT': 6} | -0.668335 | 920.000000 |
| negative_expectancy_after_shrinkage+profit_factor_below_threshold \| NVDA \| liquidity sweep reversal short \| SHORT \| trend_long | 6 | {'NVDA': 6} | {'liquidity sweep reversal short': 6} | {'SHORT': 6} | -0.668335 | 920.000000 |
| negative_expectancy_after_shrinkage+profit_factor_below_threshold \| AAPL \| failed breakout short \| SHORT \| trend_long | 5 | {'AAPL': 5} | {'failed breakout short': 5} | {'SHORT': 5} | -0.633017 | 920 |
| negative_expectancy_after_shrinkage+profit_factor_below_threshold \| AAPL \| liquidity sweep reversal short \| SHORT \| trend_long | 5 | {'AAPL': 5} | {'liquidity sweep reversal short': 5} | {'SHORT': 5} | -0.633017 | 920 |
| negative_expectancy_after_shrinkage+profit_factor_below_threshold \| AAPL \| VWAP reclaim long \| LONG \| trend_long | 5 | {'AAPL': 5} | {'VWAP reclaim long': 5} | {'LONG': 5} | -0.376305 | 804 |
| negative_expectancy_after_shrinkage \| SPY \| failed breakout short \| SHORT \| trend_long | 4 | {'SPY': 4} | {'failed breakout short': 4} | {'SHORT': 4} | -0.241241 | 920.000000 |
| negative_expectancy_after_shrinkage \| SPY \| liquidity sweep reversal short \| SHORT \| trend_long | 4 | {'SPY': 4} | {'liquidity sweep reversal short': 4} | {'SHORT': 4} | -0.241241 | 920.000000 |
| negative_expectancy_after_shrinkage+profit_factor_below_threshold \| QQQ \| failed breakout short \| SHORT \| mean_reversion | 4 | {'QQQ': 4} | {'failed breakout short': 4} | {'SHORT': 4} | -0.698054 | 920.000000 |

## Evidence Sparsity Finding

| metric | value |
| --- | --- |
| exact_match_count | 128 |
| missing_cell_count | 0 |
| parent_backoff_used_count | 145 |
| broad_parent_reliant_count | 113 |
| unique_evidence_keys_used | 187 |
| specialist_exact_cells | 79 |
| specialist_exact_cells_with_5plus_observed | 7 |

Evidence quality grades used by OOS scores:

| grade | count |
| --- | --- |
| LOW_SAMPLE | 55 |
| NEGATIVE | 741 |
| B | 47 |
| A | 7 |
| NO_EVIDENCE | 3 |

## Base Cohort Vs Selected

| group_id | candidate_count | portfolio_trades | portfolio_average_r | portfolio_robustness | counterfactual_trades | counterfactual_average_r | counterfactual_robustness |
| --- | --- | --- | --- | --- | --- | --- | --- |
| all_oos | 145 | 57 | -0.053513 | 0.000000 | 145 | -0.057926 | 0.000000 |
| selected_take | 2 | 2 | -1.000000 | 0.000000 | 2 | -1.000000 | 0.000000 |
| selected_watch | 0 | None | None | None | None | None | None |
| suppressed | 143 | 57 | -0.053513 | 0.000000 | 143 | -0.044750 | 0.000000 |
| top_score_quartile | 37 | 16 | -0.843750 | 0.000000 | 37 | -0.864865 | 0.000000 |
| top_score_decile | 15 | 7 | -1.000000 | 0.000000 | 15 | -1.000000 | 0.000000 |
| phase23_like_current_take_watch | 2 | 2 | -1.000000 | 0.000000 | 2 | -1.000000 | 0.000000 |

## Threshold Diagnostic

| threshold_source | threshold | oos_score_count_at_or_above | oos_unsuppressed_count_at_or_above |
| --- | --- | --- | --- |
| current_take_threshold | 70.000000 | 2 | 2 |
| training_score_q75 | 35.000000 | 135 | 2 |
| training_score_q90 | 35.000000 | 135 | 2 |
| training_pre_ceiling_q75 | 53.729132 | 2 | 2 |
| training_pre_ceiling_q90 | 69.735132 | 2 | 2 |

Current config: TAKE threshold `70.0`, suppressed score ceiling `35.0`, explicit WATCH threshold `None`.

## Phase 23 Vs Phase 24

| metric | phase23 | phase24 |
| --- | --- | --- |
| base actionable candidates | 82 | 330 |
| OOS/validation scored candidates | 34 | 145 |
| TAKE/WATCH selected candidates | 9 | 2 |
| selected TAKE count | 1 | 2 |
| selected WATCH count | 8 | 0 |
| selected portfolio avg R | 1.500000 | -1.000000 |
| selected counterfactual avg R | 1.500000 | -1.000000 |
| selected portfolio robustness | 1.000000 | 0.000000 |
| selected counterfactual robustness | 1.000000 | 0.000000 |
| sample-size classification | low_sample_blocked | needs_more_data_with_rejection_evidence |

## Next Experiment Decision

Classification: `EVIDENCE_TOO_SPARSE`.

Sparse exact specialist evidence and broad parent reliance dominate the failure. Suppression is concrete: the score audits primarily cite negative shrunk expectancy, profit factor below threshold, and a smaller same-bar ambiguity dependency bucket. The zero-WATCH result is explained by suppression gates, not a separate WATCH threshold.

Pre-registerable next phase:

PHASE 26 - Pre-register a broader 15min Ten-AM evidence-density experiment that scores all 15min Ten-AM actionable candidates with training-only thresholds or waits for more 15min days before retesting; do not activate or lower gates.

## Proposal And Activation Status

- Active models remained `0`.
- No model proposal was approved.
- No model was activated.
- No broker execution, order routing, production WebSocket ingestion, or stale-gate bypass occurred.

## Evidence DB Status

- Preflight audit: `CLEAN` with fixture rows `0`.
- Dirty windows before diagnostics: `none`.
- Active models before diagnostics: `0`.

## Exports

| export_type | format | row_count | source_run_id | export_id | file_sha256 |
| --- | --- | --- | --- | --- | --- |
| phase25_score_distribution_audit | csv | 145 | phase25_81b88a7a49d13e87 | export_b6387a697c1ea9856bab4da818aedcd9 | 2d52b39f8e37d654868778da3b9ac48dbbd79c4ece6fa4a3432814bcee68717e |
| phase25_suppression_reason_audit | csv | 143 | phase25_81b88a7a49d13e87 | export_4a9d8e480b7545a1c220551c0d17c646 | f007c232d2298608a9e1f89e0e4cc2a01c8f82f22c4bb9a124e16877a01c5f44 |
| phase25_evidence_sparsity | csv | 145 | phase25_81b88a7a49d13e87 | export_ddba66a8a260c7385e8b3c6497ff586a | 64508ff7e552597b70709205777bb7b0de39e724e7fa5f16b06667751e540474 |
| phase25_base_vs_selected_comparison | csv | 7 | phase25_81b88a7a49d13e87 | export_002be22732ef08238ec02b250623936c | 61aed376d679d36a62bb6fec06a7d2d402e40180d971783dd1aa501360a4351e |
| phase25_threshold_diagnostic | csv | 6 | phase25_81b88a7a49d13e87 | export_0ecc96f9c56406e03eeb22ad2e0bd616 | 1722e3abc9654e9455a56796688ee13e55695a4116b9b82a0f0123f06edbf36c |
| phase25_phase23_phase24_comparison | csv | 10 | phase25_81b88a7a49d13e87 | export_0bcfdafc8f487825832b3f67357a117c | 6477d338aa658a254eadb44a8a7cfe157b45eace5a216ede6f13cf26a17b0644 |
| phase25_next_experiment_decision | json | 1 | phase25_81b88a7a49d13e87 | export_c4216f1619435fea21a1d27eee274321 | fd2003ba8a55cef78a20b41493db01a2b0eb82a2c1d986ad72568c502b30f6dc |
| phase25_report_pack | xlsx | 457 | phase25_81b88a7a49d13e87 | export_80c537f96b4d166e550c47cab63e156f | 780d34d73b01362d8b34effab96a5e14b4c5be184a385faddbee95fdbcafa728 |

## Tests And Scans

See `PHASE_25_COMPLETION_2026-07-05.md` after final verification for the completed command list.

## Critical Blockers

- No contamination blocker was found.
- Phase 21U completion documentation is still missing upstream; Phase 25 records it as a documentation gap, not a data blocker.
- The specialist hypothesis remains unsupported for activation.

## Remaining Risks

- The expanded OOS sample is still small for high-grade action buckets.
- Evidence cells for this exact specialist slice are sparse and shrink heavily toward broad parent cells.
- Phase 23's 9-candidate pass was low-sample and did not survive stricter discovery-trained scoring plus expanded OOS validation.
