# Phase 27 Research Rules

Status date: 2026-07-06

`PHASE_27_RESEARCH_RULES_STATUS = COMPLETE`

These rules encode lessons from the Ten-AM discard and preserve the existing governance gates. They do not claim profitability and do not approve activation.

## Rules

1. No specialist proposal may advance from a low-sample artifact. Minimum OOS selected counts and minimum OOS trade counts must be met before a specialist can be considered for governance.

2. No specialist proposal may advance with full-grid robustness `0.00` in either portfolio or counterfactual replay.

3. No specialist proposal may advance if the broader all-actionable OOS cohort is negative and the only positive evidence is a smaller post-hoc slice.

4. No filter or threshold may be selected using OOS outcomes. Thresholds must be pre-registered and computed from training-only evidence before OOS replay.

5. No future filter may use future labels, future outcomes, or realized same-bar ambiguity as a live-time rule.

6. Specialist evidence claims must report exact-cell density, including exact cells, cells with 5+ outcomes, cells with 10+ outcomes, parent/backoff use, and broad-parent reliance.

7. Broad-parent evidence may support diagnostics, but it cannot carry a specialist claim by itself.

8. Model review cannot PASS when required full-grid sensitivity is missing, partial, bounded-only, or failing.

9. Calibration must show enough high-grade samples and avoid high-score concentration in one symbol, setup, day, or tiny slice.

10. Score TAKE/WATCH cohorts may be studied only through pre-registered replay, calibration, review, and full-grid sensitivity. Positive observed replay is not enough.

11. Same-bar ambiguity risk may be addressed only through signal-time proxies and training-fold evidence. Realized same-bar ambiguity cannot be used as a forward-looking live filter.

12. Candidate-family redesign must specify the family, interval, symbols, sides, time buckets, regime handling, sample-size target, and full-grid sensitivity requirement before running OOS.

13. Weak setup families identified in Phase 22 must be blocked, downweighted, or explicitly redesigned before inclusion in a specialist proposal.

14. No proposal approval or model activation can occur unless validation, calibration, model review, proposal lifecycle, and champion/challenger governance all agree.

15. Every report must state whether active models changed. Research phases should keep active models at `0` unless explicit manual approval is separately requested and all gates pass.

16. Evidence DB cleanliness is a hard prerequisite. Fixture rows in the evidence DB trigger contamination handling, not research acceptance.

17. A failed hypothesis cannot be continued under a new name unless the future work is materially redesigned and pre-registered with a new spec hash.

## Phase 27 Application

Applying these rules to the current Ten-AM path:

- Phase 23 D is rejected as a low-sample artifact.
- Phase 24 is rejected by low selected count, negative selected outcomes, calibration rejection, and robustness `0.00`.
- Phase 25 is rejected as evidence sparse and not rescued by score-threshold diagnostics.
- Phase 26 is rejected because the all-actionable OOS cohort is negative and full-grid robustness is `0.00`.
- Current 15min Ten-AM is discarded.
