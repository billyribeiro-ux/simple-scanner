# Phase 19B Runtime Repair - 2026-07-04

## Result

`RUNTIME_REPAIR_STATUS = BLOCKED_INFRA`

Runtime repair was not completed. Redis is running in-container, but Postgres migrations remain blocked and Python target drift remains unresolved.

## Python

Observed:

- `python3.14 --version`: `Python 3.14.4`
- `services/quant-engine/.venv/bin/python --version`: `Python 3.14.4`
- Project target: `3.14.6`

No Python `3.14.6` executable was found in the checked paths. The existing venv can run tests as a non-acceptance fallback, but it does not satisfy the documented target runtime.

## Redis

Phase 19A found host port `6379` occupied by another Docker container. Phase 19B confirmed:

- `rtp-redis` publishes host port `6379`.
- `revolution-redis` publishes host port `6380`.
- `adaptive-market-decoder-redis` started and became healthy, but Docker showed only container port `6379/tcp`, not a host-published `0.0.0.0:6379`.

No other container was killed or modified.

## Postgres

Postgres container:

- `adaptive-market-decoder-postgres`: running and healthy.
- Host port: `15432 -> 5432`.

Read-only inspection:

- `search_path`: `"$user", public`
- Public app tables: 0
- `public.alembic_version`: absent

Migration command:

- `make db-migrate`: failed at `0008_phase11_research_governance.py`
- Error: `DuplicateTable: relation "research_cycles" already exists`

Inspection commands:

- `make db-inspect`: failed because `alembic_version` does not exist.
- `make db-query-diagnostics`: failed because `alembic_version` does not exist.

Root cause observed in migration code:

- `0001_initial.py` calls `metadata.create_all(bind=op.get_bind())`.
- That metadata is current application metadata, so a fresh migration attempts to create later-phase tables during `0001`.
- Later migrations then try to create those same tables, causing duplicate-table failures.

No destructive reset was performed.

## Runtime Repair Conclusion

The runtime is not healthy enough for certifiable Postgres-backed regeneration. SQLite remains usable for mocked/local tests, but the runtime does not have real bars or quote snapshots. Phase 19B is blocked on infrastructure and data availability.
