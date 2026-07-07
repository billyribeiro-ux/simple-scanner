# Phase 28 Data Sufficiency

Status date: 2026-07-06

`PHASE_28_DATA_SUFFICIENCY_STATUS = RECORDED`

Source ID: `phase28_tcs_13dcd7f09159fc3c`

Spec hash: `9bcac6111f0c6e079b20c6160386d4ad2f78c4c9755cbbad788992350903162b`

## Scope

This report records pre-OOS data sufficiency for the pre-registered `trend continuation short` diagnostic. Counts use signal-time candidate fields only. They do not use OOS outcomes, future labels, future outcomes, or realized same-bar ambiguity as a live filter.

## Interval Summary

| Interval | Bars | Candidates | Training | Embargo | OOS | OOS days | Training exact cells | Cells 5+ | Cells 10+ | OOS broad-parent reliance proxy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `1min` | 15600 | 218 | 130 | 1 | 87 | 5 | 26 | 5 | 5 | 55/87 = 63.22% |
| `5min` | 3120 | 236 | 141 | 6 | 89 | 5 | 41 | 11 | 2 | 50/89 = 56.18% |
| `15min` | 3432 | 478 | 286 | 3 | 189 | 12 | 43 | 21 | 10 | 42/189 = 22.22% |

## Candidate Coverage By Symbol

| Interval | AAPL | NVDA | QQQ | SPY |
|---|---:|---:|---:|---:|
| `1min` | 70 | 103 | 43 | 2 |
| `5min` | 74 | 89 | 59 | 14 |
| `15min` | 141 | 174 | 105 | 58 |

`APPL` was not used; symbol boundaries normalize to `AAPL`.

## Candidate Coverage By Regime

| Interval | Chop | Mean reversion | Opening drive | Trend long | Trend short |
|---|---:|---:|---:|---:|---:|
| `1min` | 36 | 15 | 75 | 0 | 92 |
| `5min` | 9 | 54 | 7 | 19 | 147 |
| `15min` | 5 | 84 | 0 | 54 | 335 |

## Candidate Coverage By Time Bucket

| Interval | Afternoon continuation | Lunch window | Off hours | Opening drive | Power hour | Ten-AM reversal zone |
|---|---:|---:|---:|---:|---:|---:|
| `1min` | 7 | 8 | 48 | 89 | 36 | 30 |
| `5min` | 26 | 58 | 72 | 9 | 33 | 38 |
| `15min` | 95 | 187 | 111 | 0 | 85 | 0 |

## Days Needed Estimate

| Interval | Target OOS | Estimated total days | Additional days needed |
|---|---:|---:|---:|
| `1min` | 30 | 2 | 0 |
| `1min` | 50 | 3 | 0 |
| `1min` | 100 | 6 | 1 |
| `5min` | 30 | 2 | 0 |
| `5min` | 50 | 3 | 0 |
| `5min` | 100 | 6 | 1 |
| `15min` | 30 | 2 | 0 |
| `15min` | 50 | 4 | 0 |
| `15min` | 100 | 7 | 0 |

## Sufficiency Read

The diagnostic had enough candidates to run the pre-registered replay and sensitivity checks on all three intervals. The `1min` and `5min` OOS samples remained below 100 selected candidates and had high broad-parent reliance proxies. The `15min` sample was larger and less parent-reliant, but still required full validation and sensitivity rather than inference from density alone.

This report does not activate a model, approve a proposal, loosen gates, or make a profitability claim.
