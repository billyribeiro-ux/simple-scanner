# FMP Provider Security

Status date: 2026-07-01

Phase 15 hardens FMP access around one rule: `FMP_API_KEY` may be used only from the runtime environment or ignored local env files, and must never be committed, logged, exported, persisted, or exposed to frontend code.

## Auth

The REST client uses request header auth only:

```text
apikey: <runtime FMP_API_KEY>
```

The client strips any incoming `apikey` parameter before building requests. Provider request metadata records endpoint keys, latency, sample counts, status, and redacted response shapes, not raw keyed URLs.

## Redaction

Redaction is applied before provider request metadata, scheduler payload/result persistence, capability rows, ingestion runs, and exports. Sensitive key names such as `apikey`, `api_key`, `secret`, `password`, `token`, `database_url`, and `credential` are replaced with `[REDACTED]`.

## Runtime Status

APIs and UI report only:

- key present
- key missing

No route returns the value.

## WebSocket

WebSocket remains disabled by default. A bounded entitlement probe may be attempted only when `AMD_ENABLE_FMP_WS_PROBE=true` and `FMP_API_KEY` is present. There is no production WebSocket ingestion.

## Phase 16 Security Addendum

Operator review stores only review metadata on measured capability rows. Quote snapshots and freshness reports redact raw fields and do not store keys. Seed dry-run performs no provider call. Live seed blocks when `FMP_API_KEY` is absent.
