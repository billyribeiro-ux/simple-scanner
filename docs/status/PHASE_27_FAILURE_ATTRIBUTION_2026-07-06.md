# Phase 27 Failure Attribution

Status date: 2026-07-06

`PHASE_27_FAILURE_ATTRIBUTION_STATUS = COMPLETE`

This report attributes the current 15min `ten_am_reversal_zone` failure to concrete Phase 22-26 evidence. It does not approve a model, activate a model, loosen gates, or claim profitability.

## Summary Attribution

Ten-AM failed for all three material reasons:

| Failure class | Result | Evidence |
|---|---|---|
| Evidence sparsity | Yes, secondary but real. | Phase 26 exact specialist cells `79`; cells with 5+ outcomes `7`; cells with 10+ outcomes `0`; 113 of 145 OOS candidates broad-parent-reliant. |
| Negative cohort expectancy | Yes, primary. | Phase 26 Policy A selected 145 OOS candidates and remained negative: portfolio avg `-0.053513`; counterfactual avg `-0.057926`. |
| Sensitivity failure | Yes, primary. | Phase 26 all policies A-H had portfolio and counterfactual robustness `0.00` on the full 75-scenario default grid. |

## Data And Evidence Density

| Metric | Value | Interpretation |
|---|---:|---|
| 15min RTH days | 33 | Enough to run the broader diagnostic. |
| 15min Ten-AM actionable candidates | 330 | Enough for all-actionable sample testing. |
| Training / embargo / OOS candidates | 178 / 7 / 145 | Chronological split with embargo preserved. |
| OOS RTH days | 13 | Enough for a broad diagnostic, not enough to save exact specialist cells. |
| Specialist exact cells | 79 | Many sparse dimensions. |
| Exact cells with 5+ outcomes | 7 | Too few dense exact cells for specialist confidence. |
| Exact cells with 10+ outcomes | 0 | No deep exact specialist cell. |
| OOS broad-parent-reliant candidates | 113 | `77.93%` broad-parent reliance. |
| Phase 24 high-grade selected count | 2 | Calibration rejected for too few high-grade samples. |

Conclusion: evidence sparsity is still a blocker for specialist scoring, but it is no longer the only explanation. The broad all-actionable OOS cohort was large enough to test the general premise and was still negative.

## Replay Outcome

Phase 26 Policy A is the decisive broad test because it selected all 145 OOS actionable Ten-AM candidates.

| Purpose | Replay ID | Trades | Avg R | Total R | PF | Win rate | Max DD R | Median R |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Portfolio | `r26_a_p_e3ee2360f204` | 57 | `-0.053513` | `-3.050261` | `0.912748` | `38.60%` | `-16.050261` | `-1.000000` |
| Counterfactual | `r26_a_c_a29ac04aa924` | 145 | `-0.057926` | `-8.399252` | `0.904474` | `38.62%` | `-42.100523` | `-1.000000` |

Training-only threshold variants did not rescue the cohort:

| Policy | OOS selected | Portfolio avg R | Counterfactual avg R | Counterfactual PF | Decision reasons |
|---|---:|---:|---:|---:|---|
| A all actionable | 145 | `-0.053513` | `-0.057926` | `0.904474` | negative portfolio, negative counterfactual, full-grid failed |
| B score q75 | 135 | `-0.123590` | `-0.136291` | `0.785872` | worse than A |
| C score q90 | 135 | `-0.123590` | `-0.136291` | `0.785872` | same collapse as B |
| D pre-ceiling q75 | 35 | `-0.054547` | `-0.205196` | `0.687745` | smaller and worse counterfactual |
| E pre-ceiling q90 | 6 | `-0.500000` | `-0.583333` | `0.300000` | too few and negative |
| F evidence quality q75 | 35 | `-0.054547` | `-0.205196` | `0.687745` | smaller and worse counterfactual |
| G time bucket q75 | 35 | `-0.054547` | `-0.205196` | `0.687745` | smaller and worse counterfactual |
| H current TAKE/WATCH | 2 | `-1.000000` | `-1.000000` | `0.000000` | low sample, negative, reference-only |

## Sensitivity

| Policy | Portfolio sensitivity | Counterfactual sensitivity | Worst case |
|---|---|---|---|
| A | full-grid complete, robustness `0.00`, fail | full-grid complete, robustness `0.00`, fail | worst avg R `-0.604927` portfolio, `-0.571137` counterfactual |
| B / C | full-grid complete, robustness `0.00`, fail | full-grid complete, robustness `0.00`, fail | threshold score slices were more negative than A |
| D / F / G | full-grid complete, robustness `0.00`, fail | full-grid complete, robustness `0.00`, fail | 35 OOS candidates, counterfactual avg `-0.205196` |
| E | full-grid complete, robustness `0.00`, fail | full-grid complete, robustness `0.00`, fail | only 6 OOS candidates, worst avg `-1.000000` |
| H | full-grid complete, robustness `0.00`, fail | full-grid complete, robustness `0.00`, fail | current selected slice lost both trades |

Sensitivity is a hard rejection. No Phase 26 policy is activation-grade.

## Validation

Validation rejected the current Ten-AM path at multiple points:

- Phase 23: base and filtered Ten-AM cohorts failed sensitivity; the only full-grid pass had only 9 candidates and 6 validation trades.
- Phase 24: expanded pre-registered scorer selected only 2 TAKE candidates; both lost; validation was sample-size blocked and negative.
- Phase 25: all-OOS diagnostic showed selected-scoring sparsity and negative all-OOS replay.
- Phase 26: all-actionable OOS solved selected-count sparsity and still rejected on negative expectancy and full-grid sensitivity.

## Calibration

Calibration failure is clearest in Phase 24:

- audit: `calibration_e2e0661d5b36ca23f485cd70b7fea585`;
- scored outcomes: `2`;
- rank correlation: `0.0`;
- rejection reason: `minimum_high_grade_samples_not_met`;
- warnings: `high_score_depends_on_one_setup`, `high_score_depends_on_one_symbol`, `high_score_negative_expectancy`, `too_few_high_grade_samples`.

Phase 25 explained the score distribution mechanics: `SUPPRESS=143`, `TAKE=2`, `WATCH=0`. WATCH disappeared because all below-TAKE OOS candidates had suppression reasons. The score ceiling collapsed training q75/q90 thresholds to `35.000000`.

## Governance

Governance did what it was supposed to do:

- model review remained `BLOCK` on rejected challengers;
- champion/challenger decisions rejected rather than promoted;
- proposals remained rejected with `REJECT_CHALLENGER`;
- active models remained `0`;
- no proposal was approved;
- no model was activated;
- no broker/order path was used.

## Final Attribution

The current 15min Ten-AM hypothesis is discarded because it failed the broad OOS test after the sparse selected-sample problem was removed. The final blocker is not a single gate. It is the combination of negative broad cohort expectancy, `0.00` full-grid robustness, weak exact-cell evidence, failed high-grade calibration, and governance rejection.
