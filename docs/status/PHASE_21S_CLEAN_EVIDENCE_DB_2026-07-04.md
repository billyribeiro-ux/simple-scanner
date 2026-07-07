# Phase 21S Clean Evidence DB Report

Status date: 2026-07-04

`PHASE_21S_CLEAN_DB_STATUS = CLEAN_REGENERATED`

## Database Identity

| Field | Value |
|---|---|
| Database | `adaptive_market_decoder_evidence` |
| Host | `localhost` |
| Port | `15432` |
| Role | `evidence` |
| Alembic revision | `0012_phase16_fmp_freshness` |
| Tables | `44` |
| Extensions | `plpgsql,timescaledb` |
| Timescale hypertables | `bars` |
| Missing schema objects | `none` |

## Final Audit

`make evidence-db-audit` against the clean evidence DB reported:

| Field | Value |
|---|---:|
| Total rows | 27377 |
| Fixture-like rows | 0 |
| Bars | 3960 |
| Quote snapshots | 4 |
| Features | 3960 |
| Candidate signals | 4846 |
| Labels | 578 |
| Replay runs | 12 |
| Simulated trades | 9060 |
| Sensitivity runs / scenarios | 6 / 450 |
| Model runs | 1 |
| Evidence cells | 421 |
| Score audits | 3723 |
| Validation reports | 1 |
| Model review reports | 1 |
| Model proposals | 2 |
| Decision ledger rows | 6 |
| Export ledger rows | 94 |
| Active models | 0 |

## Certification Impact

The clean evidence DB is structurally current, fixture-clean, populated from bounded live FMP regeneration, and remains separated from the isolated test database. It is acceptable Phase 21S evidence.
