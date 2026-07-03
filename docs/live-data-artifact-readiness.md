# Live Data Artifact Readiness

Status date: 2026-07-03

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
