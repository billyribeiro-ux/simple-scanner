# Multi-Window Replay Orchestration

Status date: 2026-07-01

Phase 10 adds persisted replay window sets for controlled research runs. A window set defines symbols, intervals, replay configuration, optional model version, and generated windows. It is diagnostic only; it does not route orders or activate models.

## Modes

- `daily`: one replay window per UTC calendar day between `start` and `end`.
- `rolling`: repeated fixed-size replay windows with configurable `window_size_days`, `step_days`, optional train/validation spans, and embargo minutes.
- `anchored`: train start remains anchored at the set start while replay windows advance.
- `custom`: callers provide explicit window boundaries.

Each generated window stores replay/test boundaries, optional train/validation boundaries, embargo minutes, a deterministic `window_id`, and warnings such as `short_replay_window` or `insufficient_data_no_bars`.

## API

- `POST /orchestration/replay-window-sets`
- `GET /orchestration/replay-window-sets`
- `GET /orchestration/replay-window-sets/{window_set_id}`
- `GET /orchestration/replay-window-sets/{window_set_id}/results`
- `POST /orchestration/replay-window-sets/{window_set_id}/run`
- `POST /orchestration/replay-window-sets/{window_set_id}/export`

`run_replay=false` is useful for dry-run orchestration tests. Normal runs reuse the existing persisted candidate market replay service and save `replay_window_results` with replay IDs, comparison IDs, model versions, metrics, warnings, and completion status.

## Export

Use:

```bash
curl -s -X POST http://localhost:8000/exports/replay-window-set.xlsx \
  -H 'content-type: application/json' \
  -d '{"kind":"replay-window-set","run_id":"{window_set_id}"}'
```

The workbook includes `Summary`, `Generated Windows`, `Window Results`, `Replay Runs`, `Warnings`, and `Config`. Export records include file SHA-256 and workbook sheet names.
