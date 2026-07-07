# Phase 21S Regeneration Results

Status date: 2026-07-04

`PHASE_21S_REGENERATION_STATUS = ACCEPTED_LIVE_FMP_REGENERATION`

## Source Path

Live FMP regeneration was used because no clean backup/dump or populated clean SQLite source existed. The key was loaded from ignored `.env.local` only. It was not committed, exported, logged, or placed in query strings.

## FMP Seed Scope

| Field | Value |
|---|---|
| Symbols | `SPY`, `QQQ`, `AAPL`, `NVDA` |
| Intervals | `1day`, `1min`, `5min`, `15min` |
| Window | `2026-07-01T13:30:00+00:00` through `2026-07-02T19:59:00+00:00` |
| Required REST endpoints | 8 reviewed accessible |
| Seed dry-run | `dry_run`, `would_block=false` |
| Live seed | `ingestion_6e7c635f3b0ae005dc563a6c8ab4ca58`, `COMPLETED`, 3964 fetched, 3964 inserted |
| Seed rerun | `ingestion_02065e33fb9f04c4b584900623d9367a`, `COMPLETED`, 3964 fetched, 0 inserted, 3964 updated |
| Incremental refreshes | `ingestion_0e625ee90f01efd6934f162962c974c1`, `ingestion_1b1e942d3c91455ad65f2a4f241f1f3e`; each 1976 fetched, 0 inserted, 1976 updated |

## Artifact Rebuild

| Artifact | Final count / status |
|---|---:|
| Bars | 3960 |
| Bars by interval | `1day=8`, `1min=3120`, `5min=624`, `15min=208` |
| Quote snapshots | 4 |
| Features | 3960 |
| Candidate signals | 4846 |
| Labels | 578 |
| Replay runs | 12 |
| Simulated trades | 9060 |
| Dirty windows | 0 |

Latest required 1-minute replays:

- `candidate_market_replay`: `replay_20260705133505_48a6b35debfd62244361ea09`, 405 trades.
- `model_training_counterfactual`: `replay_20260705133507_df74191456eb8e03eaec364e`, 1608 trades.

## Freshness And Dry Run

- Default wall-clock freshness remained `STALE`, expected because the bounded seed window is historical relative to the July 5 runtime.
- Research-window freshness was `READY`: `freshness_373facfeb5ff59a7fba1989a19a25987`.
- Strict dry-run was recorded with `allow_stale=false`, `refresh_data=false`, and `blocked=false`: `research_cycle_800e1858ac7792b72e92c1281ba296eb`.

No stale gate was bypassed, no model was activated, no broker execution path was used, and no profitability claim is made.
