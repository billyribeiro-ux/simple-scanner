# Phase 24 Specialist Decision

`PHASE_24_STATUS = ACCEPTED_NEEDS_MORE_DATA`

Phase 24 expanded the evidence base and ran the pre-registered 15min TAKE/WATCH validation. The strict signal-time scorer selected only 2 out-of-sample TAKE candidates, both of which lost in portfolio and counterfactual replay. Full-grid sensitivity failed, calibration rejected the tiny high-grade slice, and concentration remained high.

## Classification

`NEEDS_MORE_DATA`

The formal classification is sample-size blocked first because the selected pre-registered cohort is only 2 candidates versus the 30-candidate and 30-OOS-trade minimums. It also carries explicit rejection evidence:

- Portfolio avg R: `-1.000000`
- Counterfactual avg R: `-1.000000`
- Portfolio robustness: `0.00`
- Counterfactual robustness: `0.00`
- Calibration rejection: `minimum_high_grade_samples_not_met`

## Decision

No specialist candidate was found. The current global challenger remains rejected. No model was activated, no proposal was approved, no broker/order path was used, no WebSocket production ingestion was used, no stale gate was bypassed, and no profitability claim is made.
