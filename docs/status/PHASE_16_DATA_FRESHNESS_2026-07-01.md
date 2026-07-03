# Phase 16 Data Freshness Status

Date: 2026-07-01

## Status

Phase 16 adds persisted quote snapshots and persisted data freshness reports. Freshness reports are local and redacted; they read bars, quote snapshots, dirty pipeline windows, and capability review state.

## Implemented

- `quote_snapshots` table and repository.
- `data_freshness_reports` table and repository.
- Quote snapshot persistence from FMP batch quote ingestion.
- `POST /data/freshness/check`.
- `GET /data/freshness/latest`.
- `data_freshness_check` scheduler job.
- Research-cycle plan integration that blocks on `BLOCKED` or `STALE` freshness unless `allow_stale=true`.
- `/operations/data` quote snapshot and freshness display.
- `/operations` freshness summary card.

## Default Thresholds

- `1min`: 30 minutes
- `5min`: 90 minutes
- `15min`: 180 minutes
- `1day`: 2880 minutes
- quote snapshots: 900 seconds

## Current Runtime Result

Because `FMP_API_KEY` is missing, no live quote snapshots or live bars were ingested in this shell. Mocked tests verify `READY`, `STALE`, and `BLOCKED` freshness states.
