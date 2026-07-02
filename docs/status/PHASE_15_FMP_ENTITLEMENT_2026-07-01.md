# Phase 15 FMP Entitlement

Status date: 2026-07-01

Implemented:

- Header-only FMP REST client auth.
- Persisted `provider_capability_checks`.
- Capability status taxonomy: `ACCESSIBLE`, `DENIED`, `RATE_LIMITED`, `EMPTY`, `ERROR`, `SKIPPED_NO_KEY`, `SKIPPED_MARKET_CLOSED`, `UNKNOWN`.
- Smoke/capability endpoints and make targets.
- Missing-key checks persist `SKIPPED_NO_KEY` without failing regression suites.
- Optional WebSocket probe remains disabled by default.

Live endpoint accessibility is detectable only when `FMP_API_KEY` is already present in the runtime environment. No key value is stored or printed.
