# Phase 27 Ten-AM Discard Record

Status date: 2026-07-06

`PHASE_27_TEN_AM_DISCARD_RECORD_STATUS = FORMAL_DISCARD`

## Hypothesis

Current specialist hypothesis:

`15min ten_am_reversal_zone specialist based on the Phase 23-26 Ten-AM research chain`

## Formal Decision

`TEN_AM_DISCARD_DECISION = DISCARD_CURRENT_15MIN_TEN_AM_HYPOTHESIS`

The current 15min Ten-AM hypothesis must not continue as a specialist challenger.

## Source Phases

| Phase | Role in discard |
|---|---|
| Phase 22 | Identified Ten-AM as a positive but non-robust research pocket. |
| Phase 23 | Showed filtered Ten-AM variants failed sensitivity, except a tiny TAKE/WATCH artifact. |
| Phase 24 | Expanded and pre-registered the TAKE/WATCH specialist; selected only 2 OOS candidates, both losses. |
| Phase 25 | Diagnosed scorer sparsity and confirmed all-OOS Ten-AM weakness. |
| Phase 26 | Solved selected-count sparsity with 145 all-actionable OOS candidates and still rejected the cohort. |

## Spec Hashes And Source IDs

| Artifact | Identifier |
|---|---|
| Phase 23 filter spec hash | `be9de3e9bbe516f882174df8eeebee19f0f66f970e7177f2e1ea287b3289a106` |
| Phase 24 filter spec hash | `220cbea95476458b0cfd7c78ec4f297dd6bd404f5c101cbafdcda3661d741d5d` |
| Phase 25 source ID | `phase25_81b88a7a49d13e87` |
| Phase 26 spec version | `phase26_broader_15min_ten_am_evidence_density.v1` |
| Phase 26 spec hash | `ff4df70e7d98246d4f4bde977e3aedd632db3dcc6a5a2fdce038fab3c93d4cf4` |
| Phase 26 source ID | `phase26_537f582b33387bf5` |
| Phase 26 report pack | `export_2ccdec26381eabeec675c9eb3070a20f` |
| Phase 26 report pack SHA-256 | `a0c3ba33376a81edb0607d434b23376b6cd8bf6b8aedd4943419617352291c9c` |

## Reason For Discard

The hypothesis is discarded because:

- Phase 26 Policy A selected 145 OOS actionable candidates, so the sparse selected-sample objection was answered.
- Policy A portfolio avg R was `-0.053513`; counterfactual avg R was `-0.057926`.
- Policy A portfolio total R was `-3.050261`; counterfactual total R was `-8.399252`.
- Policy A PF was below 1.0 for both portfolio and counterfactual.
- Policy A full-grid robustness was `0.00` for both portfolio and counterfactual.
- All Phase 26 policies A-H had full-grid robustness `0.00`.
- Phase 24 selected only two TAKE candidates, both losses, and calibration rejected the high-grade slice.
- Phase 25 showed exact specialist evidence remained sparse: 79 exact cells, 7 with 5+ outcomes, 0 with 10+ outcomes, 113 broad-parent-reliant OOS candidates.

## Future Restrictions

- Do not continue current 15min Ten-AM as a specialist challenger.
- Do not rename the same hypothesis and rerun it as a new promotion path.
- Do not rescue it with thresholds selected from OOS outcomes.
- Do not use realized same-bar ambiguity as a live filter.
- Do not use future labels or future outcomes in filters.
- Revisit Ten-AM only with a materially redesigned, pre-registered hypothesis and a new spec hash.
- Any future Ten-AM redesign must pass chronological OOS validation, calibration, model review, proposal lifecycle, and full-grid sensitivity from scratch.

## Activation And Proposal Status

| Item | Status |
|---|---|
| Proposal approved | No |
| Model activated | No |
| Active model changed | No |
| Broker/order path | Not used |
| Production WebSocket ingestion | Not used |
| Profitability claim | None |

## Final Record

This discard record is explicit and intended to prevent accidental continuation of the failed current Ten-AM specialist under a new label.
