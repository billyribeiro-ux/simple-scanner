# Phase 10 Calibration Drift

Status date: 2026-07-01

The drift engine lives at `services/quant-engine/app/models/calibration_drift.py` and compares persisted calibration audits plus optional replay window results.

## Drift Flags

- `rank_correlation_deteriorating`
- `monotonicity_failed_in_recent_window`
- `high_grade_expectancy_turns_negative`
- `take_underperforms_watch_recently`
- `calibration_warning_spike`
- `stale_window_contamination`
- `stale_replay_source_contamination`
- `too_few_recent_samples`
- `insufficient_history_for_drift`

Severity is conservative and advisory. `BLOCKING` is a review gate, not an automatic model-state mutation.
