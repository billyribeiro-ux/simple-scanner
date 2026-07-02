# Phase 15 Data Pipeline

Status date: 2026-07-01

Implemented:

- `ingestion_runs` persistence for FMP quote/EOD/intraday/incremental jobs.
- Idempotent bar upsert through the existing `bars` unique key.
- Provider request accounting with HTTP status, latency, sample count, endpoint key, and redacted metadata.
- Data-quality provider/source coverage, latest bars, ingestion summary, and capability warnings.
- Bounded scheduler jobs for FMP capability and ingestion refreshes.
- Thin operator UI pages for provider and data operations.

Quote snapshots are recorded as provider request and ingestion run metadata because V1 does not have a dedicated quotes table.
