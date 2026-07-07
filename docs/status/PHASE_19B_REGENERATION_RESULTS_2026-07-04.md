# Phase 19B Regeneration Results - 2026-07-04

## Result

`REGENERATION_STATUS = NOT_RUN`

Phase 19 was not regenerated because runtime evidence recovery failed, Postgres migration remains blocked, and no real persisted bars/quote snapshots are available in SQLite. `FMP_API_KEY` is absent, so a bounded live refresh could not run.

## Data Availability

Current SQLite data rows:

| Table | Rows |
| --- | ---: |
| `bars` | 0 |
| `quote_snapshots` | 0 |
| `features` | 0 |
| `candidate_signals` | 0 |
| `labels` | 0 |
| `replay_runs` | 0 |
| `simulated_trades` | 0 |
| `data_freshness_reports` | 0 |
| `research_cycles` | 0 |
| `exports` | 0 |

`make fmp-smoke` ran without a key and skipped all required FMP endpoints as `SKIPPED_NO_KEY`. It did not ingest bars or quotes.

## Rebuild Sequence

The Phase 19 dependency sequence was not run:

1. Dirty-window audit: not run against real data because no bars/quotes exist.
2. Feature rebuild: blocked by no persisted bars.
3. Candidate rebuild: blocked by no rebuilt features.
4. Label rebuild: blocked by no candidates/bars/features.
5. Replay rebuild: blocked by no candidates/bars/features.
6. Freshness recheck: not meaningful without real data.
7. Strict research-cycle dry run: not meaningful without rebuilt artifacts.
8. Diagnostic `allow_stale=true`: not run.
9. Exports: not generated.

## Freshness Before/After

Phase 18 baseline remains the only real-data baseline in committed docs:

- Default universe: `STALE`, 0 missing groups, 40 stale groups, 400 dirty windows.
- Research-cycle scope: `STALE`, 0 missing groups, 12 stale groups, 160 dirty windows.

Phase 19B after-state:

- No regenerated freshness after-state exists.
- No strict dry-run after-state exists.

## Regeneration Conclusion

Phase 19B cannot regenerate Phase 19 in the current runtime. The primary status is `BLOCKED_INFRA`; the secondary data status is `BLOCKED_NO_DATA` because real bars are absent and live FMP refresh cannot run without `FMP_API_KEY`.
