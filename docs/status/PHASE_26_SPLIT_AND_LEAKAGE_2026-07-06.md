# Phase 26 Split And Leakage

Status date: 2026-07-06

`PHASE_26_SPLIT_LEAKAGE_STATUS = PASS`

Source ID: `phase26_537f582b33387bf5`

## Chronological Split

| Field | Value |
|---|---|
| Split method | chronological |
| Training end | `2026-06-11T14:00:00+00:00` |
| Embargo end | `2026-06-11T15:00:00+00:00` |
| Embargo length | 60 minutes |
| Max training timestamp | `2026-06-11T14:00:00+00:00` |
| Min OOS timestamp | `2026-06-12T14:00:00+00:00` |

| Split | Candidate count |
|---|---:|
| Training/discovery | 178 |
| Embargo | 7 |
| OOS/validation | 145 |

## Leakage Checks

| Check | Result |
|---|---|
| Thresholds computed from training only | PASS |
| OOS outcomes used for thresholds | NO |
| Future labels used for filters | NO |
| Future outcomes used for filters | NO |
| Realized same-bar ambiguity used as filter | NO |
| OOS results labeled by frozen policy | PASS |

The seven embargo candidates were excluded from threshold fitting and OOS validation. OOS replay outcomes were used only after policies A-H were frozen.
