# Phase 19 Dirty Window Audit - 2026-07-03

Phase 19 audited persisted `pipeline_build_windows` before rebuilding any derived artifact. No FMP calls were made for the rebuild path and no secrets were written to docs or exports.

## Initial Audit

- Export: `exports/phase19_dirty_window_audit_20260703T132337_ca95334fb939.json`
- SHA-256: `fbd9c831ca6975c98c0ac634ae1dbb0530a5f0d7fe9f32ce0a9e3260935a1d8c`
- Persistence: SQLite at `data/local_repo.sqlite3`
- Dirty windows: 560

| Artifact | Dirty Windows | Recommended Action |
| --- | ---: | --- |
| `features` | 140 | `rebuild_features` |
| `candidates` | 140 | `rebuild_candidates` |
| `labels` | 140 | `rebuild_labels` |
| `replay` | 140 | `run_replay` or not-applicable cleanup for `1day` replay windows |

The audit included persisted summaries for bars, quote snapshots, features, candidate signals, labels, replay runs, data freshness reports, and research cycles.

## Final Audit

- Export: `exports/phase19_dirty_window_audit_20260703T132707_ab43f50a2625.json`
- SHA-256: `47ec177c6bb1498357d2d1b1a4b5cc9aebf1e9221b40e5c0e983e9c6d77db383`
- Dirty windows: 0
- Dirty by artifact: none

## Notes

Daily `1day` bars no longer create replay dirty windows. Candidate market replay is intraday-only for V1; the 40 existing daily replay windows were marked clean with metadata reason `candidate_market_replay_is_intraday_only`, not by pretending a daily replay was executed.

## Phase 19A Audit Addendum - 2026-07-04

Phase 19A could not verify these export files or dirty-window rows from the current runtime. `exports/` contains only `.gitkeep`, and the current SQLite `pipeline_build_windows` table has 0 rows because it was created fresh during the July 4 audit. Treat the Phase 19 dirty-window counts as committed documentation until the original runtime artifacts are recovered or regenerated.

## Phase 19B Audit Addendum - 2026-07-04

Phase 19B also did not recover the July 3 dirty-window exports or runtime rows. No regenerated audit was run because the current runtime has 0 real bars/quotes and Postgres migration remains blocked.
## Phase 19C Dirty Window Result - 2026-07-04

After synthetic verification rows were cleaned, `pipeline_build_windows` contained zero rows and `make db-query-diagnostics` reported `dirty_windows=none`. This is not an artifact-readiness pass because there are also zero real bars, features, candidates, labels, replay rows, and exports.
