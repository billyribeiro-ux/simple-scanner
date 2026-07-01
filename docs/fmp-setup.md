# FMP Setup

1. Copy `.env.example` to `.env.local` or export variables in your shell.
2. Set `FMP_API_KEY` to your FMP key.
3. Do not put the key in frontend files, command output, screenshots, commits, or documentation.
4. Run `make db-up`.
5. Run `make ingest` with your desired date range or call `POST /data/ingest`.

Provider health is available at:

- `GET /provider/health`
- `GET /provider/capabilities`

WebSocket support is optional and depends on FMP entitlement. REST polling remains the V1 default.
