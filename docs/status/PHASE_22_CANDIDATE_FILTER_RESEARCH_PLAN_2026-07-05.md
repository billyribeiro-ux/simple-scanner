# Phase 22 Candidate Filter Research Plan

Date: 2026-07-05
Status: PROPOSED_RESEARCH_ONLY

## Purpose

Phase 22 did not find a full-grid robust subset. The next work should be a controlled filter experiment, not model activation.

Recommended next phase:

`PHASE 23 - Diagnostic Candidate Filter Experiment for 15min Ten-AM Reversal and Ambiguity Suppression`

## Non-Negotiable Boundaries

- Do not activate models.
- Do not approve the rejected Phase 21W challenger.
- Do not loosen validation, calibration, model-review, or sensitivity gates.
- Do not bypass stale/freshness gates.
- Do not use broker execution or order routing.
- Do not add options, Greeks, order-book, dark-pool, or production WebSocket ingestion.
- Do not use realized same-bar ambiguity as a live forward-looking filter.
- Do not claim profitability.
- Do not expose `FMP_API_KEY`.

## Experiment Hypothesis

The current full-universe challenger fails broadly, but a specialist diagnostic filter may reduce the dominant failure families:

- concentrate on the only non-robust positive pocket: `15min` `ten_am_reversal_zone`;
- suppress signal-time ambiguity risk rather than realized ambiguity labels;
- downweight or block the worst time buckets, symbols, and setup families;
- evaluate score action/grade cohorts as diagnostic slices, not activation decisions.

## Candidate Filter Candidates

| Filter | Proposed treatment | Evidence basis | Leakage note |
|---|---|---|---|
| `15min` + `ten_am_reversal_zone` | isolate as specialist cohort | 64-68% scenario research pass rate, positive mean scenario avg R | safe if derived from signal timestamp/time bucket |
| `power_hour` | block in experiment A, downweight in experiment B | worst time bucket, `-719.188186` source total R | safe if signal-time bucket |
| `afternoon_continuation` | downweight or block | second worst time bucket by source total R | safe if signal-time bucket |
| `SPY` | isolate/downweight | 0/450 subset scenario pass, worst symbol avg R | safe if symbol-level training fold only |
| `NVDA` | isolate/downweight | worst source total R | safe if symbol-level training fold only |
| `opening range breakdown short` | block/downweight | worst setup source total R and weak full-grid profile | safe if setup known at signal time |
| `liquidity sweep reversal long` | block/downweight | high negative average R and high ambiguity exposure | safe if setup known at signal time |
| `failed breakdown long` / `failed breakout short` | block unless ambiguity proxy passes | high same-bar rates, negative source outcomes | use only pre-entry proxy, not future realized ambiguity |
| score `TAKE` / `WATCH` cohorts | isolate diagnostic slice | positive observed replay outcomes | must be revalidated; current calibration rejected |

## Signal-Time Ambiguity Proxy

Do not filter on realized `same_bar_ambiguous` in live/research selection. That is outcome information.

Allowed future proxy features must be computable at signal time, for example:

- current signal-bar range relative to planned stop-to-target corridor;
- stop distance too tight relative to recent true range;
- target-2 distance too tight relative to current/prior bar range;
- high recent wick/range instability in the candidate setup;
- training-fold historical ambiguity rate by setup/symbol/time bucket, applied only out-of-sample.

The experiment must explicitly audit leakage by proving every filter input exists at or before `signal_timestamp_utc`.

## Required Experiment Arms

| Arm | Description | Purpose |
|---|---|---|
| A | `15min` `ten_am_reversal_zone` only | test the strongest Phase 22 pocket |
| B | Arm A plus signal-time ambiguity proxy | test whether ambiguity risk explains fragility |
| C | Arm B plus score `TAKE`/`WATCH` diagnostic slice | test whether deterministic scorer ranking survives out-of-sample |
| D | Arm B plus symbol/setup downweights | test whether concentration filters improve robustness |
| Control | Phase 21W current challenger scope | prevent false improvement from changed evaluation only |

## Required Rebuild And Governance Sequence

For each arm:

1. derive candidate filters from training-fold evidence only;
2. rebuild candidate signals or filtered candidate views from persisted bars/features;
3. rerun `candidate_market_replay`;
4. rerun `model_training_counterfactual`;
5. rerun replay-aware validation;
6. rerun calibration audit;
7. rerun calibration drift/report review;
8. rerun model review with sensitivity required;
9. rerun full default-grid replay sensitivity, all 75 scenarios;
10. rerun strict research-cycle dry-run with `allow_stale=false`;
11. export sensitivity, validation, calibration, review, comparison, proposal, and cycle artifacts with source IDs and file hashes;
12. run evidence/test isolation checks, backend/frontend tests, and secret scans.

## Acceptance Criteria For Future Research

A future specialist candidate may be recommended for further review only if:

- evidence DB remains clean, fixture rows `0`;
- active models remain `0`;
- strict dry-run records `allow_stale=false`;
- validation accepts the filtered challenger;
- calibration does not reject;
- drift/review do not block;
- full-grid sensitivity completes 75/75 scenarios;
- full-grid sensitivity pass rate is at least the configured activation threshold, with no undisclosed partial grid;
- no subset claim is made without source IDs and hashes.

## Expected Decision Outcomes

- If Arm A/B remains non-robust: reject the specialist direction and investigate feature/label design.
- If Arm C improves observed outcomes but calibration still rejects: focus on calibration/sample depth, not activation.
- If any arm passes validation but fails full-grid sensitivity: record `VALIDATION_PASS_SENSITIVITY_FAIL` and keep rejected.
- If any arm passes full-grid sensitivity but fails validation/calibration: record `SENSITIVITY_PASS_GOVERNANCE_FAIL` and keep rejected.
- If an arm passes all gates: create a future proposal for human review only; activation still requires separate explicit manual confirmation and is out of scope for Phase 23.

