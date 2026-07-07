# Phase 21S Contaminated Archive Report

Status date: 2026-07-04

`PHASE_21S_ARCHIVE_STATUS = ARCHIVED_CONTAMINATED_DB`

## Scope

Phase 21S preserved the contaminated default evidence database before any clean evidence restoration work. This archive is an audit artifact only. It is not certification evidence and must not be used for model approval, export certification, or activation decisions.

## Source Database

| Field | Value |
|---|---|
| Database | `adaptive_market_decoder` |
| Host | `localhost` |
| Port | `15432` |
| Role | `evidence` |
| Alembic revision | `0012_phase16_fmp_freshness` |
| Audit status | `CONTAMINATED` |
| Total rows | `2609` |
| Fixture-like rows | `29` |
| Missing tables | `none` |

Key row counts at archive time:

| Table | Rows |
|---|---:|
| `bars` | 480 |
| `features` | 576 |
| `candidate_signals` | 1256 |
| `labels` | 224 |
| `replay_runs` | 1 |
| `model_runs` | 3 |
| `validation_reports` | 7 |
| `exports` | 1 |

Fixture-like samples included known regression IDs such as `parity-proposal`, `parity-review`, and `parity-model-accepted`. Mixed real and fixture-like rows make this database unusable for certification.

## Archive Artifact

| Field | Value |
|---|---|
| Archive path | `data/raw/phase21s/adaptive_market_decoder_contaminated_phase21s_2026-07-04.pgdump` |
| Format | PostgreSQL custom dump via container-side `pg_dump -Fc` |
| Size | `413076 bytes` |
| SHA-256 | `6a8cb438e766f2ab59a398f8bcd9790ecebe1c1fa656465d163524d180b1b7ec` |

The initial host-side Homebrew `pg_dump` attempt was rejected because the client was older than the server. The successful archive used the running Postgres container's matching `pg_dump`. The dump emitted a Timescale continuous aggregate circular foreign-key warning; the dump completed successfully.

## Certification Impact

The contaminated database was archived, not cleaned in place. No contaminated row is approved as Phase 21S evidence. The clean restoration path must use a separate clean database, a clean backup, or bounded live regeneration from runtime-only credentials.
