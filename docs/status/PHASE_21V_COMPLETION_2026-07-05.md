# Phase 21V Report Pack - 2026-07-05

`PHASE_21V_STATUS = ACCEPTED_PARTIAL_SENSITIVITY_DISCLOSED`

Phase 21V is accepted only for bounded sensitivity scaling, explicit partial/full-grid disclosure, and conservative governance re-run. Full default sensitivity was not claimed complete. No model was activated, no challenger was approved, no broker/order/options/WebSocket production path was used, and no profitability claim is made.

## Security And Runtime Boundaries

- `FMP_API_KEY` was loaded only from runtime environment / ignored `.env.local`.
- Secret scan: `PASS`, secret value file hits `0`, secret assignment hits `0`, `.env.local` ignored `true`.
- FMP key value was not printed, exported, persisted, or committed.
- Evidence database: `adaptive_market_decoder_evidence` with `AMD_DB_ROLE=evidence`.
- Final evidence audit: `CLEAN`, fixture rows `0`, active models `0`.

## Code Changes

- Added sensitivity coverage metadata: `coverage_mode`, planned/completed/remaining scenarios, configured-grid completion, full-default-grid completion, partial disclosure, coverage warnings, and runtime.
- Added deterministic `TIERED_ESSENTIAL` sensitivity mode with a four-scenario essential grid.
- Required-sensitivity validation and model review now block bounded/partial/non-full-grid sensitivity when full sensitivity is required.
- Model review exports now include sensitivity summaries.
- Replay runtime improved by maintaining active portfolio exit timestamps instead of scanning all prior trades per candidate.

## Final Evidence Counts

| Artifact | Rows |
| --- | --- |
| bars | 19800 |
| features | 19800 |
| candidate_signals | 23882 |
| labels | 3032 |
| replay_runs | 26 |
| simulated_trades | 67204 |
| replay_sensitivity_runs | 18 |
| replay_sensitivity_scenarios | 498 |
| model_review_reports | 5 |
| champion_challenger_comparisons | 6 |
| model_proposals | 6 |
| research_cycles | 7 |
| research_cycle_artifacts | 7 |
| exports | 195 |
| active_models | 0 |

Dirty pipeline windows for `SPY/QQQ/AAPL/NVDA` over `1min/5min/15min`: `0`.

## Bounded Sensitivity Results

All six required interval/purpose runs were rebuilt from current persisted real bars and completed bounded essential sensitivity. All six are explicitly marked as partial/full-grid-disclosed because `full_default_grid_complete=false`.

| Interval | Purpose | Replay ID | Candidates | Trades | Sensitivity ID | Completion | Scenarios | Full Grid | Partial Disclosure | Pass/Fail |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `1min` | `portfolio` | `replay_20260705222826_33726551f81599994d55da1b` | 7297 | 1938 | `sensitivity_239b24c5e3afe7c294eaa80b15ef87ef` | BOUNDED_COMPLETE | 4/4 | False | True | fail |
| `1min` | `counterfactual` | `replay_20260705222903_30a05915b7d9ab1dc2a0566c` | 7297 | 7295 | `sensitivity_4ce60ea81a6c37b403d56332719f4755` | BOUNDED_COMPLETE | 4/4 | False | True | fail |
| `5min` | `portfolio` | `replay_20260705223001_2a3bedc9d2abaa0a750aefc2` | 2326 | 605 | `sensitivity_165ad84e6d7587397e82e5d187a6f1fa` | BOUNDED_COMPLETE | 4/4 | False | True | fail |
| `5min` | `counterfactual` | `replay_20260705223005_7e38150cc8ad1259cd668e04` | 2326 | 2324 | `sensitivity_69e106e2c30ddefeba4d69e627656fff` | BOUNDED_COMPLETE | 4/4 | False | True | fail |
| `15min` | `portfolio` | `replay_20260705223012_afc4202e318c155d012444f6` | 947 | 295 | `sensitivity_ba9280db5c4b31f2032dfc5b631d8f6a` | BOUNDED_COMPLETE | 4/4 | False | True | fail |
| `15min` | `counterfactual` | `replay_20260705223013_39d7d508606d7e8782962ead` | 947 | 942 | `sensitivity_d70696e374a5878e6310b3aeabefb928` | BOUNDED_COMPLETE | 4/4 | False | True | fail |

Coverage warnings on all six sensitivity runs: `bounded_sensitivity_not_full_default_grid`, `tiered_essential_sensitivity_scope`.

## Governance Re-Run

- Model version: `amd-replay-aware-20260702-164145`
- Validation report: `report_65d036bc0fb422f6de0697fbd4c5111d`
- Calibration audit: `calibration_70021b4dc0bb829a2fbb92e9d1d386a9`
- Drift report: `calibration_drift_2245a2352dfa80965c2b9d6632c35034`
- Sensitivity evidence count: `6`

| Artifact | ID | Status | Decision / Reasons |
| --- | --- | --- | --- |
| Model review | `model_review_1ef927a48eb24e11886fc3c31f8076e6` | BLOCK | calibration_drift_watch, sensitivity_gate_failed, sensitivity_scope_not_full_grid, too_many_calibration_warnings, validation_rejected |
| Champion/challenger | `champion_challenger_33c0e399b4679cd3fe0a64149a13553e` | BLOCK | REJECT_CHALLENGER |
| Model proposal | `proposal_3e379a7289fc35875eced05436c4bd35` | REJECTED | REJECT_CHALLENGER / BLOCK |

Comparison gates: validation `false`, calibration `false`, model review `false`, stale window `true`, data quality `true`, all passed `false`.

## Strict Research-Cycle Dry-Run

- Research cycle: `research_cycle_750dd3d4bbee9b0a2ae83c2f7c08ae9d`
- Dry-run status: `dry_run`
- `allow_stale=false`, `refresh_data=false`
- Blocked: `False`
- Block reason: `None`
- Freshness: `READY`
- Dirty windows: `0`
- Model activation unchanged: `true`

## Export Manifest

| Export ID | Type | Format | Source ID | Rows | SHA-256 |
| --- | --- | --- | --- | --- | --- |
| `export_27cc394587ac87f6fd0f2d59994ece51` | replay_sensitivity_summary | xlsx | `replay_20260705222826_33726551f81599994d55da1b` | 4 | `48de1281f3bc2323671198fb82d5c1ff766107dc024d360ec489e7c8b28fc073` |
| `export_d603ef76bb27c3ffed5289284c7f4549` | replay_sensitivity_scenarios | csv | `replay_20260705222826_33726551f81599994d55da1b` | 4 | `d775c714dae0d1326b06749f4ef704d2e8ef04e92a417a7696965574698a3898` |
| `export_34af1777b9acb02e5c06282e4a656f48` | replay_sensitivity_metrics | json | `replay_20260705222826_33726551f81599994d55da1b` | 4 | `37b28c7eb12dabf4ecabe2757b54df85baa09756c4b4c07261ff693feb5e756e` |
| `export_abea0d472ef33b6b695fb3a8012afa1f` | replay_sensitivity_summary | xlsx | `replay_20260705222903_30a05915b7d9ab1dc2a0566c` | 4 | `61a3431b7b6c74e75f951646d1038b21a52fb28af75d10ee23f7c60787a49618` |
| `export_cbff7bb1f0d8106ff4dd8b1dad2cec5c` | replay_sensitivity_scenarios | csv | `replay_20260705222903_30a05915b7d9ab1dc2a0566c` | 4 | `4bcc34725f11b69a9f220df3f187f7cf9c6aa6d8492b7b13c804ad1cf9be0929` |
| `export_f19f66fcd8d4a44b565d482e85f05c21` | replay_sensitivity_metrics | json | `replay_20260705222903_30a05915b7d9ab1dc2a0566c` | 4 | `142b64523e0f2f311ecd7b70d7676a1728616b182c5d20b85f9dc99075c91bad` |
| `export_20ce295ebe697073638852c2ae9e6701` | replay_sensitivity_summary | xlsx | `replay_20260705223001_2a3bedc9d2abaa0a750aefc2` | 4 | `a604ac6609ff47504a4a58312816881bda3ff44186c7b7609972cdaac7bc4a73` |
| `export_6d5d0d19a31932d585da2a4c5c3b7501` | replay_sensitivity_scenarios | csv | `replay_20260705223001_2a3bedc9d2abaa0a750aefc2` | 4 | `fe34dfd9f3b094adbd8b4c01635550ffaff658e5470bb8a31aac133754d4cd59` |
| `export_191c6aab3b235db01f4ca9cc4414c7f1` | replay_sensitivity_metrics | json | `replay_20260705223001_2a3bedc9d2abaa0a750aefc2` | 4 | `f72e94a409f62332261f90f21ec1bccd5f3047c9bfc8f085c63bbd593ac367d4` |
| `export_e9d52c78be9ded4277a25007451c0938` | replay_sensitivity_summary | xlsx | `replay_20260705223005_7e38150cc8ad1259cd668e04` | 4 | `288f7478e42f5874c23d183ce1787b9ddedb887780b2f399cd3c2d6a79c17d3f` |
| `export_4e2f2604ecc978db2a5c811137129713` | replay_sensitivity_scenarios | csv | `replay_20260705223005_7e38150cc8ad1259cd668e04` | 4 | `79e7f35cd886bb9e15267657dd767572ed811b4f2ee9fbfa188e51456654e4da` |
| `export_4e5fc4d46e422ffd6af31b6cadb10fc5` | replay_sensitivity_metrics | json | `replay_20260705223005_7e38150cc8ad1259cd668e04` | 4 | `171f0c5c5f17efc407501c9fbdaab4f006425757af66c10117b5492fac583075` |
| `export_9c4c96736f638529f10325666876cee6` | replay_sensitivity_summary | xlsx | `replay_20260705223012_afc4202e318c155d012444f6` | 4 | `6761d6c4291e887964d7fe200a466303fcbd29570c26ed30db9b50e6ba18142e` |
| `export_b9569f83724de6cfe7b485148f97c38d` | replay_sensitivity_scenarios | csv | `replay_20260705223012_afc4202e318c155d012444f6` | 4 | `3f36eb62ee96085a86c8fa0719e8d2a30947f34e9173030da184154158184d6c` |
| `export_64e1975175f7a477b4e5572a95268a9b` | replay_sensitivity_metrics | json | `replay_20260705223012_afc4202e318c155d012444f6` | 4 | `e85f34f3a498240516b257698c5ecfb24d473387d993c85fd56b3a211b942a66` |
| `export_9e7a0c47771764bea2e8b7d4cadd04e1` | replay_sensitivity_summary | xlsx | `replay_20260705223013_39d7d508606d7e8782962ead` | 4 | `5c5840e911aa1d6d7a7e795c792b661ad590c35025ba19944ed3992a04e7323d` |
| `export_d934c36906d0bf58ec5b3bc6c236938c` | replay_sensitivity_scenarios | csv | `replay_20260705223013_39d7d508606d7e8782962ead` | 4 | `695cdb3df323398657e4ccd8e6c9c0febd2b63003f0aa8db3ea63d0f6723adef` |
| `export_bc9abbd07a9dbf94b8c110729ca15904` | replay_sensitivity_metrics | json | `replay_20260705223013_39d7d508606d7e8782962ead` | 4 | `88453bc063360e8d724ad6c9a1fed778dabe8b0d2748c6e51e99b9f86a933556` |
| `export_a22753baf3d19f1d782d9ed4cc3efc93` | model_review | xlsx | `model_review_1ef927a48eb24e11886fc3c31f8076e6` | 1 | `31a90f2bc602916e32981cffef7b3474a58b6af3ce7eb1863609db7bb71bc5d1` |
| `export_095d840b6505b7fff6a0dcd656726292` | model_review | json | `model_review_1ef927a48eb24e11886fc3c31f8076e6` | 1 | `74bd85852e43285b1e8af33e46cd1cbaf94d14eda1c21d0c38e802cc63e9bd5f` |
| `export_7614184c9a8476bd1993cc29dc07505d` | champion_challenger_comparison | xlsx | `champion_challenger_33c0e399b4679cd3fe0a64149a13553e` | 1 | `e993a5c1f86c22272ac72568c7e9b61f9690a4ea1207d15c7ecc274fc547e5c7` |
| `export_fbdcb800e82f3837a1cb3325c1654191` | model_proposal | xlsx | `proposal_3e379a7289fc35875eced05436c4bd35` | 1 | `5065481cabd7250e7fa5d2288a25d9637ae47a7f9c977d657ec13adfc82c2b03` |
| `export_5781b01d82d14b01c8ce503b99e77528` | model_proposal | json | `proposal_3e379a7289fc35875eced05436c4bd35` | 1 | `21d11b9fe52b33b660c7195e878c7721692aec2310f475787733b39e1c7060f2` |
| `export_8fae416abf3b40506e0ea125b422f637` | research_cycle | xlsx | `research_cycle_750dd3d4bbee9b0a2ae83c2f7c08ae9d` | 1 | `85aa16fc7e71f008b855201f325305bea46810f636c036526ed5142827b70282` |
| `export_86ef7a3f15d75def1db00e30346d902d` | research_cycle | json | `research_cycle_750dd3d4bbee9b0a2ae83c2f7c08ae9d` | 1 | `a4cd291b73a06022eef6e221e14f6b9f88cd2c09cde8cccf8e8710ecc6f7ac3e` |

## Verification

- `make evidence-db-audit`: passed, fixture rows `0`, active models `0`.
- `make test-db-smoke`: passed.
- `make evidence-guard-test`: passed.
- `make replay-sensitivity-test`: passed, `4 passed`.
- `make model-review-test`: passed, `6 passed`.
- `make research-cycle-test`: passed, `4 passed`.
- `make export-test`: passed, `5 passed`.
- `make backend-lint`: passed.
- `make backend-typecheck`: passed.
- `python -m compileall app`: passed.
- Isolated `make backend-test`: passed, `131 passed`, `1 warning`.
- `git diff --check`: passed.
- Secret scan: passed.

## Certification

Phase 21V is certified as `ACCEPTED_PARTIAL_SENSITIVITY_DISCLOSED`: bounded sensitivity ran on real persisted artifacts and governance consumed it conservatively. Full-grid sensitivity remains explicitly not complete, sensitivity gates fail under full-grid requirements, review remains `BLOCK`, comparison remains `REJECT_CHALLENGER`, proposal remains `REJECTED`, and active model count remains `0`.
