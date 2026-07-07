# Phase 21W Completion

Date: 2026-07-05
Status: ACCEPTED_FULL_GRID_REJECTION

## Summary

Phase 21W completed full default-grid replay sensitivity through chunked resumable execution and hardened activation-grade sensitivity policy. All six required `1min`, `5min`, and `15min` portfolio/counterfactual replay runs completed the 75-scenario full default grid from persisted real bars. No model was activated, no challenger was approved, and no stale gate was bypassed.

The final governance result remains rejection: every full-grid sensitivity run is complete but failed robustness gates.

## Evidence Counts After Phase 21W

Final evidence audit:

- database: `adaptive_market_decoder_evidence`
- status: `CLEAN`
- fixture rows: `0`
- active models: `0`
- dirty windows: `0`
- bars: `19800`
- features: `19800`
- candidates: `23882`
- labels: `3032`
- replay runs: `26`
- sensitivity runs: `24`
- sensitivity scenarios: `948`
- exports: `220`

## Key Artifacts

- Full-grid spec: `docs/status/PHASE_21W_FULL_GRID_SPEC_2026-07-05.md`
- Sensitivity execution: `docs/status/PHASE_21W_SENSITIVITY_EXECUTION_2026-07-05.md`
- Governance policy: `docs/status/PHASE_21W_GOVERNANCE_POLICY_2026-07-05.md`
- Governance review: `docs/status/PHASE_21W_GOVERNANCE_REVIEW_2026-07-05.md`
- Comparison: `docs/status/PHASE_21W_COMPARISON_2026-07-05.md`

## Verification

Passed:

- `make backend-test`: 132 passed
- `make backend-lint`
- `make backend-typecheck`
- `make frontend-doctor` with a known secret-shaped identifier warning
- `corepack pnpm --filter @amd/web test:e2e`: 11 passed
- `make test-db-smoke`
- `make evidence-guard-test`: 2 passed
- concrete FMP key value scan: passed
- final `make evidence-db-audit` against `adaptive_market_decoder_evidence`: `CLEAN`, fixture rows `0`
- `git diff --check`

## Final Decision

`PHASE_21W_STATUS = ACCEPTED_FULL_GRID_REJECTION`

Full-grid sensitivity completion is accepted. Model promotion is rejected because full-grid sensitivity robustness failed and validation/calibration governance remained blocking. No profitability claim is made.

