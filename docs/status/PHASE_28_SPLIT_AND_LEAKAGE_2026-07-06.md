# Phase 28 Split And Leakage

Status date: 2026-07-06

`PHASE_28_SPLIT_LEAKAGE_STATUS = PASS`

Source ID: `phase28_tcs_13dcd7f09159fc3c`

Spec hash: `9bcac6111f0c6e079b20c6160386d4ad2f78c4c9755cbbad788992350903162b`

## Split Method

Each interval used the pre-registered per-interval chronological candidate split:

1. Query `trend continuation short` candidates using signal-time fields only.
2. Sort by candidate timestamp.
3. Use the first 60% as training/discovery.
4. Set a 60-minute embargo after the training end timestamp.
5. Evaluate only candidates after the embargo as OOS.

## Split Results

| Interval | Candidates | Candidate start | Candidate end | Training | Training end | Embargo end | Embargo candidates | OOS | OOS start | OOS end |
|---|---:|---|---|---:|---|---|---:|---:|---|---|
| `1min` | 218 | `2026-06-18T13:35:00+00:00` | `2026-07-02T15:29:00+00:00` | 130 | `2026-06-26T15:53:00+00:00` | `2026-06-26T16:53:00+00:00` | 1 | 87 | `2026-06-26T19:22:00+00:00` | `2026-07-02T15:29:00+00:00` |
| `5min` | 236 | `2026-06-18T15:05:00+00:00` | `2026-07-02T19:20:00+00:00` | 141 | `2026-06-25T19:15:00+00:00` | `2026-06-25T20:15:00+00:00` | 6 | 89 | `2026-06-26T13:55:00+00:00` | `2026-07-02T19:20:00+00:00` |
| `15min` | 478 | `2026-05-15T18:15:00+00:00` | `2026-07-02T17:45:00+00:00` | 286 | `2026-06-16T15:00:00+00:00` | `2026-06-16T16:00:00+00:00` | 3 | 189 | `2026-06-16T19:45:00+00:00` | `2026-07-02T17:45:00+00:00` |

## Leakage Checks

| Check | `1min` | `5min` | `15min` |
|---|---|---|---|
| Filters use signal-time fields only | PASS | PASS | PASS |
| OOS outcomes used for filters | PASS - false | PASS - false | PASS - false |
| Future labels used for filters | PASS - false | PASS - false | PASS - false |
| Future outcomes used for filters | PASS - false | PASS - false | PASS - false |
| Realized same-bar ambiguity used as live filter | PASS - false | PASS - false | PASS - false |

## Conclusion

`LEAKAGE_STATUS = PASS`

The Phase 28 split preserved chronology and applied a 60-minute embargo for every interval. No OOS outcome, future label, future outcome, or realized same-bar replay condition was used to choose the primary cohort.

This report is research evidence only. It does not activate a model, approve a proposal, add broker execution, or claim profitability.
