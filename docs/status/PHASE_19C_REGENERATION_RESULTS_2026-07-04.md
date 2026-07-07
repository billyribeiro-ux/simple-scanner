# Phase 19C Regeneration Results - 2026-07-04

Status: BLOCKED_NO_DATA

## Evidence Preservation

Pre-repair evidence checks found no recoverable Phase 19 runtime artifacts:

- `data/local_repo.sqlite3` existed but held no Phase 19 bars, features, candidates, labels, replay rows, freshness rows, research cycles, or exports.
- `exports/` contained only `.gitkeep`.
- `model_artifacts/` contained `.gitkeep` and the existing `active_model.json`.
- Postgres public app tables were initially absent and `alembic_version` was absent.
- No ignored Phase 19 export files were found.

## Runtime State After Repair

Postgres migration, schema inspection, diagnostics, API smoke, and repository parity are repaired and passing. Synthetic rows created by verification tests were cleaned after the test pass because preflight proved no recoverable runtime evidence and the rows were generated during Phase 19C verification.

Final Postgres evidence after cleanup and no-key checks:

| Table | Rows |
|---|---:|
| `bars` | 0 |
| `quote_snapshots` | 0 |
| `features` | 0 |
| `candidate_signals` | 0 |
| `labels` | 0 |
| `replay_runs` | 0 |
| `simulated_trades` | 0 |
| `pipeline_build_windows` | 0 |
| `data_freshness_reports` | 2 |
| `research_cycles` | 1 |
| `provider_capability_checks` | 8 |
| `ingestion_runs` | 0 |
| `exports` | 0 |

## FMP Source Availability

`FMP_API_KEY` is not present in the shell and no `.env` or `.env.local` file exists in the repo. Live FMP ingestion was not attempted.

`DATABASE_URL=postgresql+psycopg://... make fmp-smoke` safely recorded eight `SKIPPED_NO_KEY` capability rows:

- `quote`
- `quote_short`
- `batch_quote`
- `batch_quote_short`
- `historical_eod_full`
- `intraday_1min`
- `intraday_5min`
- `intraday_15min`

## Freshness And Dry Run

- Freshness report `freshness_8512eb780b5c859136c2060ccb6b5033`: `BLOCKED`, 20 missing items, 0 stale items.
- Dry-run freshness report `freshness_4493d045c05f30f4b107d8a1471843ba`: `BLOCKED`, 20 missing items, 0 stale items.
- Research cycle `research_cycle_95fbdba8b52c6b95437f08908e7aa807`: created for strict dry-run with `allow_stale=false`.
- Strict dry-run result: `blocked=true`, `block_reason=data_freshness_blocked`.

## Regeneration Decision

No Phase 19 features, candidates, labels, replay, model review, research artifacts, or exports were regenerated because there are no real bars and no approved FMP key/source. No synthetic bars were used.
