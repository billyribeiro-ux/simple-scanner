# Phase 11 Research Cycle Status

Status date: 2026-07-01

Research cycle persistence and APIs are implemented with SQLite/Postgres parity. Cycles store status transitions, symbols, intervals, range/session, active/challenger model versions, replay/source IDs, data-quality report ID, stale-window state, summary, warnings, `config_hash`, `input_fingerprint`, `git_commit`, `database_revision`, and `persistence_backend`.

Implemented routes:

- `POST /research/cycles`
- `GET /research/cycles`
- `GET /research/cycles/{research_cycle_id}`
- `POST /research/cycles/{research_cycle_id}/run`
- `POST /research/cycles/{research_cycle_id}/dry-run`
- `GET /research/cycles/{research_cycle_id}/artifacts`
- `POST /research/cycles/{research_cycle_id}/export`

Guardrails verified:

- dry-run does not activate;
- stale windows block by default;
- `allow_stale=true` records the warning and permits controlled tests;
- `refresh_data=true` blocks without `FMP_API_KEY`;
- cycle run records `model_activation_unchanged=true`;
- cycle artifacts persist and survive repository reinitialization.

Remaining limits: V1 uses explicit artifact IDs and simple service orchestration. It does not yet schedule daily jobs, queue long runs, or automatically reuse matching expensive artifacts by config hash.
