# Phase 21R Restoration Results - 2026-07-04

`PHASE_21R_RESTORATION_STATUS = BLOCKED_NO_CLEAN_SOURCE`

Phase 21R did not restore or regenerate the runtime evidence database because no safe clean source was available in the current runtime.

## Sources Checked

- Runtime `FMP_API_KEY`: not present in the verification environment.
- Ignored local key files: `.env.local` not present; `.env` not present.
- Local SQLite evidence source: `data/local_repo.sqlite3` exists but contains 0 bars, 0 features, 0 candidates, 0 labels, 0 model runs, 0 validation reports, 0 research cycles, and 0 exports.
- Clean DB backups/dumps: no clean usable backup, dump, or snapshot was found in the repo search scope.
- Current default Postgres DB: present and migrated, but contaminated with fixture-like rows.

## Action Taken

- The contaminated evidence database was preserved for audit.
- No destructive reset, drop, delete, or silent cleanup was performed.
- No provided API key was written to files, command lines, docs, logs, exports, or tracked metadata.
- No live FMP regeneration was attempted because the current runtime environment did not provide `FMP_API_KEY`.
- No model activation, proposal approval, broker path, order routing, WebSocket production ingestion, stale-gate bypass, or profitability assertion was performed.

## Current Evidence State

The default Postgres database still contains some real persisted rows, including bars, features, candidate signals, labels, validation reports, provider request records, and an export record. It also contains fixture rows in governance, replay, scheduler, scanner, validation, and model-selection tables. Mixed provenance means it cannot be certified as clean evidence.

The current database therefore cannot satisfy Phase 21R acceptance requirements for a clean restored evidence store, rebuilt downstream artifacts from clean real bars, clean export/source-ID certification, or clean strict research-cycle evidence.

## Required Unblock

One of these sources is required before evidence restoration can be accepted:

- a clean Postgres backup/dump from before the parity/API smoke contamination incident;
- a runtime-only `FMP_API_KEY` supplied through the environment or ignored `.env.local`, followed by a bounded regeneration flow;
- another operator-approved clean persisted evidence source with verifiable provenance.

After one source is available, rerun the clean regeneration sequence under `AMD_DB_ROLE=evidence`: seed real bars, rebuild features, candidate signals, labels, candidate-market replay, model-training counterfactual replay, freshness reports, strict research-cycle dry-run with `allow_stale=false`, exports with hashes/source IDs, tests, and secret scans.

## Conclusion

Restoration is blocked by missing clean input data, not by the repaired regression isolation. The correct final phase posture is partial: isolation fixed, evidence restoration blocked.
