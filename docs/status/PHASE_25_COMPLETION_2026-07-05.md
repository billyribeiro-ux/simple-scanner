# Phase 25 Completion

`PHASE_25_STATUS = ACCEPTED_EVIDENCE_TOO_SPARSE`

Phase 25 completed specialist scorer coverage diagnostics and OOS selection-failure analysis for the Phase 24 15min Ten-AM slice. It did not activate a model, approve a proposal, loosen gates, change thresholds, bypass stale checks, use broker/order execution, use production WebSocket ingestion, expose secrets, or claim profitability.

## Final Finding

The sparse Phase 24 selection is primarily explained by sparse exact specialist evidence plus broad parent/backoff reliance, with persisted suppression reasons showing negative shrunk expectancy on every suppressed OOS candidate. The whole OOS base cohort is also weak, so this is not an activation lead.

| Item | Result |
|---|---:|
| OOS scored candidates | 145 |
| TAKE | 2 |
| WATCH | 0 |
| SUPPRESS | 143 |
| Score median | 35.000000 |
| Score max | 76.777100 |
| Pre-ceiling score median | 49.953744 |
| Exact evidence-cell matches | 128 |
| Broad parent reliant candidates | 113 |
| Specialist exact cells | 79 |
| Specialist exact cells with 5+ observed outcomes | 7 |

## Suppression Summary

| Suppression reason | Count |
|---|---:|
| `negative_expectancy_after_shrinkage` | 143 |
| `profit_factor_below_threshold` | 112 |
| `same_bar_ambiguity_dependency_too_high` | 10 |

`WATCH` is zero because this scorer only emits `WATCH` when a candidate has no suppression reasons and scores below the `TAKE` threshold. Every below-TAKE OOS candidate had at least one suppression reason, so the middle tier disappeared through suppression, not through a separate WATCH cutoff.

## Base Vs Selected

| Group | Candidates | Portfolio avg R | Portfolio robustness | Counterfactual avg R | Counterfactual robustness |
|---|---:|---:|---:|---:|---:|
| All OOS | 145 | -0.053513 | 0.00 | -0.057926 | 0.00 |
| Selected TAKE | 2 | -1.000000 | 0.00 | -1.000000 | 0.00 |
| Selected WATCH | 0 | n/a | n/a | n/a | n/a |
| Suppressed | 143 | -0.053513 | 0.00 | -0.044750 | 0.00 |
| Top score quartile | 37 | -0.843750 | 0.00 | -0.864865 | 0.00 |
| Top score decile | 15 | -1.000000 | 0.00 | -1.000000 | 0.00 |

The scorer did not improve OOS selection relative to the base cohort in this expanded run. The top-score buckets were materially worse than the full OOS base cohort.

## Threshold Diagnostic

Current config uses `take_score_threshold=70.0`, `suppressed_score_ceiling=35.0`, and no explicit WATCH threshold. Training-score q75/q90 both collapsed to `35.0` because suppressed scores are ceiling-capped. Training pre-ceiling q75 was `53.729132`; training pre-ceiling q90 was `69.735132`. Under each diagnostic threshold, only 2 OOS candidates were unsuppressed. No threshold change is recommended without a future pre-registered test.

## Phase 23 Vs Phase 24

Phase 23's `P23_FILTER_D_TAKE_WATCH_SLICE` had 9 total TAKE/WATCH candidates and 6 validation trades, and passed full-grid sensitivity only in that tiny diagnostic slice. Phase 24 expanded to 330 base candidates and 145 OOS scored candidates, but the stricter discovery-trained scorer selected only 2 TAKE and 0 WATCH; both lost and both full-grid sensitivities had robustness `0.00`. The Phase 23 result is therefore best treated as a low-sample artifact.

## Exports

| Export | ID | Rows | SHA-256 |
|---|---|---:|---|
| Score distribution audit CSV | `export_b6387a697c1ea9856bab4da818aedcd9` | 145 | `2d52b39f8e37d654868778da3b9ac48dbbd79c4ece6fa4a3432814bcee68717e` |
| Suppression reason audit CSV | `export_4a9d8e480b7545a1c220551c0d17c646` | 143 | `f007c232d2298608a9e1f89e0e4cc2a01c8f82f22c4bb9a124e16877a01c5f44` |
| Evidence sparsity CSV | `export_ddba66a8a260c7385e8b3c6497ff586a` | 145 | `64508ff7e552597b70709205777bb7b0de39e724e7fa5f16b06667751e540474` |
| Base vs selected comparison CSV | `export_002be22732ef08238ec02b250623936c` | 7 | `61aed376d679d36a62bb6fec06a7d2d402e40180d971783dd1aa501360a4351e` |
| Threshold diagnostic CSV | `export_0ecc96f9c56406e03eeb22ad2e0bd616` | 6 | `1722e3abc9654e9455a56796688ee13e55695a4116b9b82a0f0123f06edbf36c` |
| Phase 23 vs Phase 24 comparison CSV | `export_0bcfdafc8f487825832b3f67357a117c` | 10 | `6477d338aa658a254eadb44a8a7cfe157b45eace5a216ede6f13cf26a17b0644` |
| Next experiment decision JSON | `export_c4216f1619435fea21a1d27eee274321` | 1 | `fd2003ba8a55cef78a20b41493db01a2b0eb82a2c1d986ad72568c502b30f6dc` |
| Phase 25 workbook | `export_80c537f96b4d166e550c47cab63e156f` | 457 | `780d34d73b01362d8b34effab96a5e14b4c5be184a385faddbee95fdbcafa728` |

Workbook sheets: `Score Distribution`, `Suppression`, `Evidence Sparsity`, `Comparison`, `Threshold`, `Phase23vs24`, `Decision`.

## Evidence DB

Final audit remained `CLEAN`: total rows `208163`, fixture rows `0`, active models `0`, dirty windows `none`, exports `321`, replay runs `48`, replay sensitivity runs `44`, replay sensitivity scenarios `2448`.

## Tests And Scans

- `make doctor` passed with expected non-secret warning that shell-level `FMP_API_KEY` was not exported.
- `make db-migrate`, `make db-inspect`, `make db-query-diagnostics` passed.
- `make evidence-db-audit`, `make test-db-smoke`, `make evidence-guard-test` passed.
- `make backend-test`: 132 passed.
- `make backend-lint`, `make backend-typecheck` passed.
- `make replay-sensitivity-test`, `make model-review-test`, `make research-cycle-test`, `make export-test`, `make scheduler-test` passed.
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm check`, `build`, `test`, `lint`, and `--filter @amd/web test:e2e` passed; e2e was 11 passed.
- `python3 -m compileall services/quant-engine/app services/quant-engine/tests` plus the Phase 25 diagnostic script passed.
- `git diff --check` passed.
- Secret scan passed: exact runtime key hits `0`, real query-string key hits `0`, suspicious secret assignments `0`; six known fake placeholder query-string fixtures were ignored.

## Next Phase

Exact next recommended phase: `PHASE 26 - Pre-register a broader 15min Ten-AM evidence-density experiment or wait for more 15min days before retesting`.

The next phase must remain research-only: no activation, no proposal approval, no OOS-threshold selection, no gate lowering, no realized ambiguity live filter, no broker execution, and no profitability claim.
