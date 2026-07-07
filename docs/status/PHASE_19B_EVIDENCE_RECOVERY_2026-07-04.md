# Phase 19B Evidence Recovery - 2026-07-04

## Result

`RECOVERY_STATUS = NOT_RECOVERED`

The original July 3 Phase 19 runtime DB/export artifacts were not recovered.

## Search Scope

Phase 19B searched safely for:

- expected Phase 19 export filenames;
- Phase 19 replay run IDs;
- Phase 19 research cycle ID;
- SQLite/database files;
- local `data/`, `exports/`, and `model_artifacts/` locations;
- likely Codex attachment/output locations;
- Docker containers and volumes.

No secrets were printed.

## Expected Phase 19 Exports

None of these files were found as runtime files:

- `phase19_dirty_window_audit_20260703T132337_ca95334fb939.json`
- `phase19_dirty_window_audit_20260703T132707_ab43f50a2625.json`
- `phase19_feature_rebuild_report_20260703T132340_9a603451ed54.json`
- `phase19_candidate_rebuild_report_20260703T132535_b53a870c1991.json`
- `phase19_label_rebuild_report_20260703T132536_fb4fa48ac8b0.json`
- `phase19_replay_report_20260703T132544_d8beb5f13450.json`
- `phase19_replay_report_20260703T132706_24c375e58c47.json`
- `phase19_freshness_report_20260703T132707_7628fa1fd58c.json`
- `phase19_research_cycle_dry_run_report_20260703T132707_b35201ab340d.json`

`mdfind` returned no exact filename hits. Targeted `find` of the repo, current Codex workspace, and attachment area found no Phase 19 JSON exports.

## Expected IDs

Searches for these IDs found committed docs only, not runtime rows or export payloads:

- `replay_20260703132342_48a6b35debfd62244361ea09`
- `replay_20260703132343_df74191456eb8e03eaec364e`
- `replay_20260703132536_549bebf359fa0e6d9261108a`
- `replay_20260703132540_d77a7add68d69518dc6b1c4a`
- `research_cycle_b3e371c34dccba95c8eb29ff3e657bca`

## Local Runtime Files

Found:

- `data/local_repo.sqlite3`
- `exports/.gitkeep`
- `model_artifacts/.gitkeep`
- `model_artifacts/active_model.json`

Not found:

- July 3 Phase 19 exports.
- Any recovered SQLite DB containing July 3 Phase 19 rows.
- Any recovered model artifact tied to the listed replay/research IDs.

Current SQLite row counts:

| Table | Rows |
| --- | ---: |
| `bars` | 0 |
| `quote_snapshots` | 0 |
| `provider_capability_checks` | 8 |
| `pipeline_build_windows` | 0 |
| `features` | 0 |
| `candidate_signals` | 0 |
| `labels` | 0 |
| `replay_runs` | 0 |
| `simulated_trades` | 0 |
| `data_freshness_reports` | 0 |
| `research_cycles` | 0 |
| `exports` | 0 |

The eight provider capability rows were created by the Phase 19B no-key `make fmp-smoke` check and are `SKIPPED_NO_KEY`; they are not July 3 recovery evidence.

## Docker Evidence

Docker volume inventory includes `simple-scanner_postgres_data`, created on 2026-07-04 during this audit path. No older project-specific Phase 19 volume was identified.

Read-only Postgres inspection showed:

- Database: `adaptive_market_decoder`
- User: `amd`
- Public app tables: 0
- `public.alembic_version`: absent

## Recovery Conclusion

The July 3 runtime evidence remains missing. Phase 19 cannot be marked recovered.
