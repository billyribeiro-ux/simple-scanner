# Phase 21 Completion - 2026-07-04

`PHASE_21_STATUS = DIAGNOSTICS_COMPLETE_CURRENT_DB_BLOCKED`

Phase 21 completed the challenger rejection diagnostics, gate attribution, sample/concentration analysis, and evidence-improvement plan. The correct recommendation remains `REJECT_CHALLENGER` / `BLOCK`.

## Critical Certification Boundary

The Phase 21 diagnostic snapshot was collected before a regression incident. After collection, `make api-smoke-postgres` and `make repository-parity-test` wrote test fixtures into the default Postgres database because the tests hardcode `adaptive_market_decoder` and ignored the attempted isolated `DATABASE_URL`.

Current Postgres diagnostic after the incident:

- `bars.rows=480`
- `features.rows=576`
- `candidate_signals.rows=1256`
- `labels.rows=224`
- `replay_runs.rows=1`
- `model_runs.rows=3`
- `validation_reports.rows=7`
- `research_cycles.rows=1`
- `model_proposals.rows=1`
- `exports.rows=1`
- `dirty_windows=replay:4`
- Current rows include `parity-replay`, `parity-model-accepted`, `parity-review`, `parity-research-cycle`, `parity-proposal`, and `parity-decision`.

Therefore Phase 21 is not an artifact-readiness certification of the current default database. The current evidence store must be restored or regenerated before any future acceptance claim.

## Exact Rejection Gates

Primary rejection:

- Validation report `report_0091f7e03f0bd9d674ff6fdb75219b0e` rejected the challenger.
- Rejection reasons: `minimum_selected_candidate_sample_not_met`, `single_setup_profit_concentration_too_high`, `single_symbol_profit_concentration_too_high`.

Secondary persisted blocks:

- Model review `model_review_ae563bded0b1a0ab4eedbb35e99e4d66` assigned `BLOCK` because `validation_rejected`.
- Champion/challenger comparison recorded `validation_pass=false`, `model_review_pass=false`, and `all_passed=false`.
- Proposals `proposal_e800968cc4ba52a648f6bc00430d306b` and `proposal_ca9d2a25a6eda708ea88e1706e4313ab` persisted `REJECTED` with `REJECT_CHALLENGER`.
- Research cycle `research_cycle_ece57ebd9e3f0efa4d4fa48c0518b821` ended `BLOCKED`.

Non-rejection gates:

- Calibration passed and had no rejection reasons.
- Data freshness and stale-window gates passed in the pre-regression research scope.
- Data-quality warnings did not cause comparison rejection.
- Drift gate passed by absence of a drift report.

## Artifact IDs

| Artifact | ID |
|---|---|
| Research cycle | `research_cycle_ece57ebd9e3f0efa4d4fa48c0518b821` |
| Challenger model | `amd-replay-aware-20260702-195615` |
| Validation report | `report_0091f7e03f0bd9d674ff6fdb75219b0e` |
| Calibration audit | `calibration_a22adf288c34de793f37e474515b377a` |
| Model review | `model_review_ae563bded0b1a0ab4eedbb35e99e4d66` |
| Comparisons | `champion_challenger_d7ff387488ea651b063c1a4c809c342e`, `champion_challenger_55114da3840f82134efb1b39eb6b1f25` |
| Proposals | `proposal_e800968cc4ba52a648f6bc00430d306b`, `proposal_ca9d2a25a6eda708ea88e1706e4313ab` |
| Portfolio replay | `replay_20260704195543_48a6b35debfd62244361ea09` |
| Counterfactual replay | `replay_20260704195544_df74191456eb8e03eaec364e` |
| Counterfactual vs portfolio comparison | `comparison_4ff8bc0505bf9f940764b051b150b9dd` |

Decision ledger IDs:

- `decision_ac5ddb4414aca73fd96c44581d633812`
- `decision_8ab341bd964102908dbd5db103fd8821`
- `decision_29603013acf2d45906e909b47715adbc`
- `decision_abbaa0eee561a235822e1c4d9bbc576f`

## Validation Diagnostics

| Field | Value |
|---|---|
| Mode | `replay_aware_walk_forward` |
| Train | 2026-07-01 13:30:00 UTC to 2026-07-01 19:59:00 UTC |
| Validation | 2026-07-02 13:30:00 UTC to 2026-07-02 19:59:00 UTC |
| Test | none |
| Training replay | `replay_20260704195544_df74191456eb8e03eaec364e` |
| Validation replay | `replay_20260704195543_48a6b35debfd62244361ea09` |
| Scored candidates | 953 |
| Selected candidates | 1 |
| Suppressed candidates | 952 |
| Selected average / median R | 1.5000 / 1.5000 |
| Selected PF | 99.0 from one selected trade |
| Selected max drawdown | 0.0 |
| Same-bar ambiguity | 0/1 selected |

The positive selected trade is not sufficient evidence because the sample is 1 and fully concentrated.

## Calibration Diagnostics

Calibration audit `calibration_a22adf288c34de793f37e474515b377a`:

- Rejection reasons: none.
- Warning: `score_concentrated_in_one_bucket`.
- Monotonicity: pass.
- Rank correlation: 0.2824.
- TAKE average R: 0.9748 from 89 outcomes.
- WATCH average R: 0.6038 from 106 outcomes.
- SUPPRESS average R: -0.2863 from 1,413 outcomes.
- A-grade sample: 13, average R 1.1154, PF 8.25.
- No probability-calibration claim is made; provenance is score-audit to replay-outcome join.

## Sample And Concentration Findings

The rejection was driven by validation sample scarcity and concentration:

- Selected validation sample was 1 versus activation criterion 30.
- Selected evidence was 1/1 QQQ.
- Selected evidence was 1/1 `VWAP loss short`.
- Selected evidence was 1/1 on 2026-07-02.
- Selected evidence was 1/1 `power_hour`.
- Selected evidence was 1/1 `chop`.
- Only one replay-aware validation window existed.

Minimum additional evidence: 29 more selected validation trades are required just to reach the 30-trade threshold. At the observed rate of one selected validation trade per day, the mathematical lower bound is 29 additional trading days. The evidence plan recommends at least 30 additional RTH trading days and 8 to 10 non-overlapping validation windows without weakening gates.

## Counterfactual Vs Portfolio

Persisted comparison `comparison_4ff8bc0505bf9f940764b051b150b9dd`:

| Metric | Value |
|---|---:|
| Independent candidate count | 1608 |
| Portfolio executed count | 405 |
| Portfolio skipped count | 1205 |
| Counterfactual expectancy | -0.1578 |
| Portfolio expectancy | -0.1327 |
| Overlap cost estimate | 597.4307 |
| Missed edge due to portfolio constraints | 1203 |
| Constraint drag | -0.0251 |

Both counterfactual and portfolio replay expectancy were negative. Counterfactual replay is candidate-quality evidence only, not executable P/L. The comparison does not rescue the challenger.

## Export Verification

Pre-regression export ledger IDs captured before the database incident:

| Export ID | Type | Source ID | Rows | SHA-256 |
|---|---|---|---:|---|
| `export_7eb4f3e26ad2a411cdf2874275ed5530` | `replay_aware_validation` xlsx | `amd-replay-aware-20260702-195615` | 1 | `6e1d1758d1862d5778bbbbc93454b9e81d06c13bb81a6a6b98db46bab342ee67` |
| `export_2a55d7e20621dcd83a77c48e5fc652cc` | `calibration_audit` xlsx | `calibration_a22adf288c34de793f37e474515b377a` | 13 | `f81a606489b137b3bc87830b8d3250812d1fa197b9075e46ca9ccb795c673080` |
| `export_2b2609390e5a4f91b62ef976394f2679` | `calibration_bins` csv | `calibration_a22adf288c34de793f37e474515b377a` | 13 | `728f7b126136406041e195db326b389b4e5dffbcb528f00f6d5e7eb59583b28e` |
| `export_553ca3b86f2de4fcf98861992a368e79` | `calibration_bins` xlsx | `calibration_a22adf288c34de793f37e474515b377a` | 13 | `dc48e76c70ab078cf2cf3c5f4c8f144d5ca7fcb9d754a6e451c4b7744a081863` |
| `export_55626862e66a03144d3a623fba1efd3a` | `calibration_metrics` json | `calibration_a22adf288c34de793f37e474515b377a` | 1 | `785252088a8bda91034ab053446a0accae0933b4dc29be035d6498005971559f` |
| `export_422099b6dbd4ff3824533059c8379264` | `model_review` xlsx | `model_review_ae563bded0b1a0ab4eedbb35e99e4d66` | 1 | `3833cdfafe4162d94275795998e5f72f084bde0b65c137b296e0448d46a2ca06` |
| `export_ec2caefa74984183f3f0116e279db18d` | `model_review` json | `model_review_ae563bded0b1a0ab4eedbb35e99e4d66` | 1 | `591f82caea5898d10d3137638c172fed1433924b98016ebe2f62273f7d85650a` |
| `export_10eb8821004df4be0237688ae4791050` | `champion_challenger_comparison` xlsx | `champion_challenger_d7ff387488ea651b063c1a4c809c342e` | 1 | `ad0ae11017d00d2c2baf48f911aa1a0de2ef7c559af8c8ad9d3d7767675ee934` |
| `export_fc366a2f1ab04ee47182e45e11a59816` | `model_proposal` xlsx | `proposal_e800968cc4ba52a648f6bc00430d306b` | 1 | `e77835d3d2b1639caaac863fb44659bb658ddea75414de7073c429fe60a3e56b` |
| `export_d975bbf0fd4bd6d5919e26ef3bd08bed` | `model_proposal` json | `proposal_e800968cc4ba52a648f6bc00430d306b` | 1 | `22a5222ef701743aebcb02bb5916753a69887aae0e475c06732492a799a0ddce` |
| `export_47d6c5df9bb58790ebfdbe146cde2184` | `research_cycle` xlsx | `research_cycle_ece57ebd9e3f0efa4d4fa48c0518b821` | 3 | `079959ec4d6c701b35e7658ffa6463b073a96d584a6dd9d368669668cad2c364` |
| `export_035099fb6a6013169496a0dae7fa3ebd` | `research_cycle` json | `research_cycle_ece57ebd9e3f0efa4d4fa48c0518b821` | 3 | `46d60b56a849adb3476ad3e6540c62745ed55df3d79bd6e4212c1b3a139b8708` |

The validation workbook sheets were `Summary`, `Walk Forward Windows`, `Selected Trades`, `Suppressed Candidates`, `Per Symbol`, `Per Setup`, `Per Regime`, `Per Time Bucket`, `Sensitivity`, `Drawdown`, `Rejection Reasons`, and `Config`.

On-disk export hashes verified after the database incident:

| File | SHA-256 |
|---|---|
| `exports/replay_aware_validation_report_0091f7e03f0bd9d674ff6fdb75219b0e.xlsx` | `6e1d1758d1862d5778bbbbc93454b9e81d06c13bb81a6a6b98db46bab342ee67` |
| `exports/research_cycle_research_cycle_ece57ebd9e3f0efa4d4fa48c0518b821.json` | `46d60b56a849adb3476ad3e6540c62745ed55df3d79bd6e4212c1b3a139b8708` |
| `exports/research_cycle_research_cycle_ece57ebd9e3f0efa4d4fa48c0518b821.xlsx` | `079959ec4d6c701b35e7658ffa6463b073a96d584a6dd9d368669668cad2c364` |
| `exports/model_proposal_proposal_e800968cc4ba52a648f6bc00430d306b.json` | `22a5222ef701743aebcb02bb5916753a69887aae0e475c06732492a799a0ddce` |
| `exports/model_proposal_proposal_e800968cc4ba52a648f6bc00430d306b.xlsx` | `e77835d3d2b1639caaac863fb44659bb658ddea75414de7073c429fe60a3e56b` |
| `exports/champion_challenger_comparison_champion_challenger_d7ff387488ea651b063c1a4c809c342e.xlsx` | `ad0ae11017d00d2c2baf48f911aa1a0de2ef7c559af8c8ad9d3d7767675ee934` |
| `exports/model_review_model_review_ae563bded0b1a0ab4eedbb35e99e4d66.json` | `591f82caea5898d10d3137638c172fed1433924b98016ebe2f62273f7d85650a` |
| `exports/model_review_model_review_ae563bded0b1a0ab4eedbb35e99e4d66.xlsx` | `3833cdfafe4162d94275795998e5f72f084bde0b65c137b296e0448d46a2ca06` |
| `exports/calibration_metrics_calibration_a22adf288c34de793f37e474515b377a.json` | `785252088a8bda91034ab053446a0accae0933b4dc29be035d6498005971559f` |
| `exports/calibration_bins_calibration_a22adf288c34de793f37e474515b377a.csv` | `728f7b126136406041e195db326b389b4e5dffbcb528f00f6d5e7eb59583b28e` |
| `exports/calibration_bins_calibration_a22adf288c34de793f37e474515b377a.xlsx` | `dc48e76c70ab078cf2cf3c5f4c8f144d5ca7fcb9d754a6e451c4b7744a081863` |
| `exports/calibration_audit_calibration_a22adf288c34de793f37e474515b377a.xlsx` | `f81a606489b137b3bc87830b8d3250812d1fa197b9075e46ca9ccb795c673080` |

Phase 21-specific export routes for gate attribution, sample concentration, counterfactual-vs-portfolio packet, evidence-improvement plan, and proposal rejection packet were not available. Markdown reports were created instead. The current DB export ledger is no longer reliable after contamination.

## Commands And Tests

Passed:

- `make doctor` with expected warnings that `DATABASE_URL` and `FMP_API_KEY` were not configured in that shell.
- `make db-migrate`
- `make db-inspect`
- `make db-query-diagnostics` before collection and after contamination; the after-state confirms the blocker.
- `make backend-lint`
- `make backend-typecheck`
- `python3 -m compileall services/quant-engine/app services/quant-engine/tests`
- `make backend-test` after Postgres was unavailable to PG-specific tests: `123 passed, 2 skipped`.
- `make model-review-test`: `5 passed`.
- `make research-cycle-test`: `4 passed, 2 deselected`.
- `make export-test`: `5 passed`.
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm check`
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm build`
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm test`
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm lint`
- `COREPACK_ENABLE_DOWNLOAD_PROMPT=0 corepack pnpm --filter @amd/web test:e2e`: `11 passed`.
- `git diff --check`
- Secret scan over source, docs, exports, frontend output, provider metadata, scheduler/model artifact surfaces: pass with two allowlisted fake redaction-test placeholders.

Failed and contaminating:

- `make api-smoke-postgres` failed after hardcoding the default DB and produced `KeyError: 'report_id'`.
- `make repository-parity-test` failed after hardcoding the default DB and reopening against the wrong state; it expected 96 bars and got 0 in the reopened repository.

These failures are blockers because they mutated the default evidence store.

## Code And Docs Changed

Code:

- `services/quant-engine/app/services/workflows.py` retains the Phase 20 fix for deterministic replay-aware validation window IDs instead of a hardcoded ID.

Docs/reports:

- `docs/status/PHASE_21_PLAN_2026-07-04.md`
- `docs/status/PHASE_21_GATE_ATTRIBUTION_2026-07-04.md`
- `docs/status/PHASE_21_SAMPLE_CONCENTRATION_2026-07-04.md`
- `docs/status/PHASE_21_EVIDENCE_IMPROVEMENT_PLAN_2026-07-04.md`
- `docs/status/PHASE_21_COMPLETION_2026-07-04.md`
- `docs/live-data-research-cycle-results.md`
- `docs/HANDOFF.md`

Work artifact:

- `/Users/billyribeiro/Documents/Codex/2026-07-04/ch/work/phase21_summary.json`

## Activation And Proposal Status

The Phase 20 challenger `amd-replay-aware-20260702-195615` remained inactive in the captured evidence and its proposal remained rejected. No Phase 21 action activated it.

Current Postgres contains parity activation/proposal fixtures from tests; those are not live-data approvals and must not be treated as model activation evidence.

## Remaining Risks

- Current default Postgres is contaminated.
- Export files remain on disk, but export ledger rows in current Postgres were lost.
- Provider-request status semantics can create false `provider_request_errors_detected` warnings for reviewed HTTP 200 `ACCESSIBLE` rows.
- Calibration score distribution is concentrated in one low score bucket.
- Sensitivity evidence is missing for the challenger.
- Validation evidence spans only one out-of-sample day/window.

## Exact Next Phase

Proceed to `PHASE_21R - Runtime Evidence Store Restoration And Isolated Regression Repair`.

Phase 21R should fix Postgres test isolation, restore/regenerate a clean evidence database from runtime-only FMP credentials, rerun the artifact rebuild and governance diagnostics, regenerate exports with hashes/source IDs, rerun tests/scans, and keep the challenger rejected unless the strict gates pass without bypass.
