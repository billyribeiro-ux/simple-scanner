# Phase 19D Regeneration Results - 2026-07-04

`PHASE_19_STATUS = ACCEPTED`

This report supersedes the earlier same-day no-key blocker pass. The live runtime pass loaded the provider key from ignored `.env.local` only, used header-authenticated reviewed FMP REST endpoints, and did not print, commit, export, or persist the key value.

## Entitlement

- Required REST endpoints reviewed: `quote`, `quote_short`, `batch_quote`, `batch_quote_short`, `historical_eod_full`, `intraday_1min`, `intraday_5min`, `intraday_15min`.
- `make fmp-smoke`: all 8 required endpoints `ACCESSIBLE`, HTTP 200.
- `make fmp-live-smoke`: all 8 required endpoints `ACCESSIBLE`, HTTP 200.
- Review summary: `READY`, 8 reviewed accessible, 0 blocked, 0 unreviewed.
- Auth mode: header only; query-string API keys are stripped by the FMP client.

## Bounded Seed

Scope:

- Symbols: SPY, QQQ, AAPL, NVDA
- Intervals: `1day`, `1min`, `5min`, `15min`
- Window: `2026-07-01T13:30:00+00:00` through `2026-07-02T19:59:00+00:00`

Seed dry-run returned `dry_run`, `would_block=false`.

Live seed:

- Seed run: `ingestion_10d4f575c1a12c80363350d1d73adbe9`
- Status: `COMPLETED`
- Records fetched/inserted/updated: 3964 / 3964 / 0
- Child quote run: `ingestion_45bd53a41b77459a89d3aae8596eed19`, 4 inserted
- Child EOD run: `ingestion_3a1f2cafc6592934d6554cc8571ca7f8`, 8 inserted
- Child intraday run: `ingestion_24d9e29008b8e5b58e22d571e6460f10`, 3952 inserted
- Provider request count: 17
- Error count: 0

Idempotency rerun:

- Seed rerun: `ingestion_98b1d1b1c9206bc49d1b2fb3ddd909b8`
- Status: `COMPLETED`
- Records fetched/inserted/updated: 3964 / 0 / 3964
- Bar count before/after: 3956 scoped bars / 3956 scoped bars

Incremental refresh:

- Run 1: `ingestion_a0fccadf7e35d55612abfc1ba20272f9`, 1976 fetched, 0 inserted, 1976 updated, 0 errors
- Run 2: `ingestion_898c297f7b30045dff4d5b111661dabb`, 1976 fetched, 0 inserted, 1976 updated, 0 errors

## Final Data Counts

- Bars: 3960 total, with `1day=8`, `1min=3120`, `5min=624`, `15min=208`
- Quote snapshots: 4
- Provider capability checks: 16
- Provider requests: 74
- FMP ingestion runs: 10

## Rebuild Chain

- Feature rebuild, 1-minute first: 3120 bars read, 3120 features written
- Feature rebuild, all intervals: 3960 bars read, 3960 features written
- Session-aligned feature rebuild cleanup: 16 windows, 1980 bars read, 1980 features written
- Candidate/label rebuild, 1-minute first: 3120 bars read, 3120 features read, 3723 candidates generated, 554 labels written
- Candidate/label rebuild, all intervals: 3960 bars read, 3960 features read, 4846 candidates generated, 267 labels written
- Session-aligned candidate/label cleanup: 16 windows, 1980 bars read, 1980 features read, 2465 candidates generated, 408 labels written

Final artifact counts:

- Features: 3960
- Candidate signals: 4909
- Labels: 778
- Dirty windows after replay: 0

## Replay

Mandatory 1-minute replay:

- `candidate_market_replay`: `replay_20260704192729_6beec3610b794d914108bf5d`, 3120 bars, 3120 features, 1610 candidates, 405 trades
- `model_training_counterfactual`: `replay_20260704192730_df74191456eb8e03eaec364e`, 3120 bars, 3120 features, 1610 candidates, 1608 trades

All-intraday replay cleanup also ran for `5min` and `15min` so the seeded interval set has zero dirty replay windows.

## Freshness And Strict Dry Run

- Wall-clock freshness: `freshness_9d151ba8c55c1311eb75d60908446c08`, `STALE`, 0 missing, 20 stale, 0 dirty windows. This is expected because the bounded seed is historical relative to the July 4 runtime clock.
- Historical seed-window freshness: `freshness_dbf1857805007e19d95fe21624656b03`, `READY`, 0 missing, 0 stale, 0 dirty windows.
- Research-cycle dry-run freshness: `freshness_e95214b8566e048c2b337404c72e23e8`, `READY`.
- Strict research-cycle dry-run: `research_cycle_4e00305e7bd852e64b004c56cd4ce7d2`, `blocked=false`, `allow_stale=false`, `refresh_data=false`.
- Dry-run warnings were non-blocking: overnight gap heuristic warnings and provider-status classification warnings. No stale gate was bypassed.

## Export Ledger

21 exports were generated and recorded with file hashes and source IDs. Key certification exports:

| Export | Export ID | Rows | Source ID | SHA-256 |
|---|---|---:|---|---|
| `phase19d_dirty_window_audit` | `export_88cc71838a4137e3d7d2aa7c8ec223d3` | 0 | `pipeline_build_windows` | `b543fad7c057b8fba2d1e18340d6722803061f6df3986a5b69acb8a479e07d7e` |
| `phase19d_artifact_rebuild_report` | `export_d28d5c1189089317d6c241048742091e` | 9647 | `bars_features_candidates_labels` | `e2009fa8e1ced6aecd1ee5c7639ea8e5f0f3e4e4386a1cb6be8e07b0462ab9f8` |
| `phase19d_replay_report` | `export_82e8cf0f5e66e1bde9662382561dcf53` | 6 | `replay_runs` | `5a6d11fdc2bc38cae3839545e55c09f139272d850add7418be1e339873a7fd75` |
| `phase19d_research_cycle_dry_run_report` | `export_59aa0006f438c61299c8993ba46c561b` | 1 | `research_cycle_4e00305e7bd852e64b004c56cd4ce7d2` | `ae4ff2e5eb7ad0f788e9674f65ce8a9c9777209b1dd711a514ef59a3356b6407` |
| `phase19d_provider_and_seed_report` | `export_ecb69cf800c2cd09f19ec59f41955701` | 10 | `fmp` | `6e4abecf99efb9c60d86937025995f747a450b1cbdbd0cdd3e910f2fcaca433e` |
| `fmp_seed_ingestion` | `export_0fcf17b9fb42c39ce42d3366f099e0e1` | 2 | `fmp` | `415366cc2eec83ed777b4d2acde2973946e07bf4cf35604716b681d20f727984` |
| `data_freshness_report` | `export_5ef0f0f5b9fb30f7a326fc3f84f71f1f` | 3 | `fmp` | `867d596e0f78cfe3422ba3d17f185680a0151787157e90a0e9ec440ad8627616` |
| `research_cycle` JSON | `export_d604d9eca85ed906db24afefaec96244` | 1 | `research_cycle_4e00305e7bd852e64b004c56cd4ce7d2` | `b69ff31ece3a0c26feed55e22ff2077daca4402d98593bb0b30b796b6b749e4c` |
