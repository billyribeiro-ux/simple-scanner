# Live Data Artifact Readiness

Status date: 2026-07-04

This guide describes the local-only artifact-readiness path added in Phase 19. It repairs derived artifacts from persisted bars, features, and candidates. It does not call FMP, route orders, activate models, or make profitability claims.

## Audit

```bash
curl -s 'http://localhost:8000/pipeline/dirty-windows?symbols=AMZN,AAPL,TSLA,SPY,QQQ,IWM,NVDA,GOOGL,BABA,SHOP&intervals=1min,5min,15min,1day&export=true'
```

The audit reports dirty windows by artifact, symbol, interval, session date, timestamp range, version, source, and recommended rebuild action. It also includes summaries for bars, quote snapshots, features, candidate signals, labels, replay runs, data freshness reports, and research cycles.

## Rebuild Order

Run these steps after live ingestion or incremental refresh marks windows dirty:

```bash
curl -s -X POST http://localhost:8000/pipeline/rebuild/features \
  -H 'content-type: application/json' \
  -d '{"symbols":["AMZN","AAPL","TSLA","SPY","QQQ","IWM","NVDA","GOOGL","BABA","SHOP"],"intervals":["1min","5min","15min","1day"],"export":true}'

curl -s -X POST http://localhost:8000/pipeline/rebuild/candidates \
  -H 'content-type: application/json' \
  -d '{"symbols":["AMZN","AAPL","TSLA","SPY","QQQ","IWM","NVDA","GOOGL","BABA","SHOP"],"intervals":["1min","5min","15min","1day"],"export":true}'

curl -s -X POST http://localhost:8000/pipeline/rebuild/labels \
  -H 'content-type: application/json' \
  -d '{"symbols":["AMZN","AAPL","TSLA","SPY","QQQ","IWM","NVDA","GOOGL","BABA","SHOP"],"intervals":["1min","5min","15min","1day"],"export":true}'

curl -s -X POST http://localhost:8000/pipeline/rebuild/replay \
  -H 'content-type: application/json' \
  -d '{"symbols":["SPY","QQQ","AAPL","NVDA"],"intervals":["1min"],"export":true}'
```

Optional default-universe intraday replay:

```bash
curl -s -X POST http://localhost:8000/pipeline/rebuild/replay \
  -H 'content-type: application/json' \
  -d '{"symbols":["AMZN","AAPL","TSLA","SPY","QQQ","IWM","NVDA","GOOGL","BABA","SHOP"],"intervals":["1min","5min","15min"],"export":true}'
```

If old `1day` replay dirty windows exist, clear them as not applicable:

```bash
curl -s -X POST http://localhost:8000/pipeline/rebuild/replay \
  -H 'content-type: application/json' \
  -d '{"symbols":["AMZN","AAPL","TSLA","SPY","QQQ","IWM","NVDA","GOOGL","BABA","SHOP"],"intervals":["1day"],"export":true}'
```

V1 candidate market replay is intraday-only. The `1day` cleanup marks those windows with reason `candidate_market_replay_is_intraday_only`; it does not simulate daily execution.

## Scheduler Jobs

The same steps can be queued through the bounded scheduler:

- `rebuild_features`
- `rebuild_candidates`
- `rebuild_labels`
- `run_replay`
- `data_freshness_check`
- `research_cycle_dry_run`

Example:

```bash
curl -s -X POST http://localhost:8000/scheduler/jobs \
  -H 'content-type: application/json' \
  -d '{"job_type":"rebuild_features","payload":{"symbols":["AAPL"],"intervals":["1min"],"export":true},"created_by":"local-operator"}'
```

Scheduler payloads and results are redacted. These jobs never activate models or make provider calls unless a separate FMP job is explicitly queued.

## Phase 19 Result

- Initial dirty windows: 560.
- Final dirty windows: 0.
- Strict research-cycle dry run: passed with `allow_stale=false`.
- Default freshness: `STALE` from wall-clock age only.
- Research-scope freshness: `READY`.

See `docs/status/PHASE_19_COMPLETION_2026-07-03.md` for exact counts, export paths, hashes, and verification commands.

## Phase 19A Audit Note

On 2026-07-04, Phase 19A verified the committed code/docs but did not find the ignored July 3 runtime DB or export artifacts in the checkout. Current runtime evidence is therefore insufficient to certify Phase 19 without recovering those artifacts or regenerating the real-data readiness sequence. See `docs/status/PHASE_19A_COMPLETION_2026-07-04.md`.

## Phase 19B Audit Note

Phase 19B did not recover the July 3 runtime artifacts and could not regenerate from real data. Before using this guide to certify readiness, repair Postgres migrations, align Python to `3.14.6`, provide a runtime-only `FMP_API_KEY`, seed real bars/quotes, and rerun the full readiness sequence.
## Phase 19C Readiness Update - 2026-07-04

Artifact readiness remains blocked by missing real market data. The repaired Postgres runtime has no bars, quote snapshots, features, candidates, labels, replay rows, or exports after synthetic verification rows were cleaned. FMP capability checks are persisted as `SKIPPED_NO_KEY` because no `FMP_API_KEY` is configured.

The strict `allow_stale=false` research dry-run for SPY, QQQ, AAPL, and NVDA over `1min`, `5min`, `15min`, and `1day` blocked with `data_freshness_blocked`. No readiness or activation decision should be inferred until real bars are ingested or restored and downstream artifacts are rebuilt.

## Phase 19D Accepted Update - 2026-07-04

Phase 19D regenerated real FMP data and rebuilt artifact readiness from the repaired Phase 19C runtime. The bounded seed covered SPY, QQQ, AAPL, and NVDA over `1day`, `1min`, `5min`, and `15min` for `2026-07-01T13:30:00+00:00` through `2026-07-02T19:59:00+00:00`.

Final readiness counts:

- Bars: 3960
- Quote snapshots: 4
- Features: 3960
- Candidate signals: 4909
- Labels: 778
- Replay runs: 6
- Simulated trades: 4530
- Dirty windows: 0
- Export records: 21

Historical-reference freshness is `READY`; wall-clock freshness remains `STALE` because the seed window is historical relative to July 4. The strict research-cycle dry-run `research_cycle_4e00305e7bd852e64b004c56cd4ce7d2` completed as `dry_run` with `blocked=false`, `allow_stale=false`, and `refresh_data=false`.

Phase 19D does not activate models, route orders, use broker execution, use production WebSocket ingestion, or claim profitability. See `docs/status/PHASE_19D_FINAL_CERTIFICATION_2026-07-04.md` for the acceptance record.
