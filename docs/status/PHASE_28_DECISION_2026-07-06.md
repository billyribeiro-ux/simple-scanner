# Phase 28 Decision

Status date: 2026-07-06

`PHASE_28_STATUS = ACCEPTED_REJECTED_BY_SENSITIVITY`

Final decision: `REJECTED_BY_SENSITIVITY`

Source ID: `phase28_tcs_13dcd7f09159fc3c`

Spec hash: `9bcac6111f0c6e079b20c6160386d4ad2f78c4c9755cbbad788992350903162b`

## Decision

The pre-registered `trend continuation short` diagnostic is rejected by sensitivity. Every interval failed portfolio or counterfactual full-grid sensitivity.

| Interval | Interval decision | Primary reason |
|---|---|---|
| `1min` | `REJECTED_BY_SENSITIVITY` | Portfolio and counterfactual full-grid sensitivity both failed with robustness `0.00`. |
| `5min` | `REJECTED_BY_SENSITIVITY` | Portfolio robustness was only `0.44`; counterfactual robustness was `0.00`. |
| `15min` | `REJECTED_BY_SENSITIVITY` | Baseline portfolio and counterfactual expectancy were negative, and both full-grid sensitivity runs failed. |

## Activation And Governance Status

| Item | Status |
|---|---|
| Model activation | No |
| Proposal approval | No |
| Active models changed | No |
| Validation gate loosened | No |
| Calibration gate loosened | No |
| Sensitivity gate loosened | No |
| OOS-derived filter selected | No |
| Future labels or outcomes used for filters | No |
| Realized same-bar ambiguity used as live filter | No |
| Broker/order execution path added | No |
| Production WebSocket ingestion added | No |
| Profitability claim made | No |

## Export Manifest

| Export type | Export ID | Format | Rows | File SHA-256 |
|---|---|---|---:|---|
| `phase28_filter_spec` | `export_f00b2408e06695c97dcbff7ba0bc366d` | json | 1 | `fb3c1e52f03c2e6123f6ec4a6e71fd36ea74456e7c824de56568e60b9b4ebc55` |
| `phase28_data_sufficiency` | `export_9dd83209406e88bc97e9d4df1aa339f9` | json | 3 | `c4c7b8433d66beb280b9a9d2b931614a9ed0821259152fb19d00853f98b455e7` |
| `phase28_split_leakage` | `export_867286944863d5e13a282bb0a7544275` | json | 3 | `263c906c7e31254c304508f41cdd6dc2d840714306f784858f4652319c5963b9` |
| `phase28_primary_results` | `export_6b761552056a1173e890e10a5ab74ebe` | json | 3 | `6b600885f3d9923c749cfac690aedf3fa646812e1533bb97a26b47c357e7b3e4` |
| `phase28_exploratory_results` | `export_3d55ecc7ca0e1b813cf6347a28cb6b86` | json | 12 | `070a24208b991fa1d3934384624ee722d0f6fde36b7339ed8dab86301c0611fc` |
| `phase28_comparison` | `export_5ff966cce536fdec7af9f26bec515508` | json | 3 | `03122e1610f9de1db8ffee7efd9f75de479ec82e78e251fcc0fa8dcc41ce706c` |
| `phase28_decision` | `export_8a5679bc9bf94442d090179abb7e7ad6` | json | 3 | `7a8f93963d8fe544db84c22e670591b539396768eb33af9478d91fb2ae90d785` |
| `phase28_sensitivity_scenarios` | `export_f98c0a35f5bce38b2869a2b80ff686ce` | csv | 450 | `21921a7e1197354ea322da748a7ac95bf0fe2165f31df85f05f301c308aeec13` |
| `phase28_export_manifest` | `export_35de7fe0f9b479e5df2ef64eb25c3bb3` | json | 8 | `95c8708b7e4646a6a0a344e333bbe14d72ecb1ad76d001a0199653992eead8fa` |

Workbook sheets: `[]` for Phase 28 JSON/CSV exports.

## Final Read

Phase 28 accepts the diagnostic as completed and rejects the `trend continuation short` candidate family under the current pre-registered formulation. The result is research evidence only.

Exact next work should not activate this cohort. It should either select another pre-registered signal family or design a new trend-continuation-short hypothesis without using Phase 28 OOS outcomes as live filters.
