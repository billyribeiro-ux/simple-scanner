# FMP Live Entitlement Matrix

Date: 2026-07-01

This matrix is based on the current official Financial Modeling Prep documentation pages reviewed before Phase 15 implementation. It documents what Adaptive Market Decoder V1 may probe safely. Runtime entitlement remains detectable only by executing redacted checks with `FMP_API_KEY` present in the runtime environment.

## Official Sources

- FMP developer docs: https://site.financialmodelingprep.com/developer/docs
- Quote: https://site.financialmodelingprep.com/developer/docs/stable/quote
- Quote short: https://site.financialmodelingprep.com/developer/docs/stable/quote-short
- Batch quote: https://site.financialmodelingprep.com/developer/docs/stable/batch-quote
- Batch quote short: https://site.financialmodelingprep.com/developer/docs/stable/batch-quote-short
- Intraday 1 minute: https://site.financialmodelingprep.com/developer/docs/stable/intraday-1-min
- Intraday 5 minute: https://site.financialmodelingprep.com/developer/docs/stable/intraday-5-min
- Intraday 15 minute: https://site.financialmodelingprep.com/developer/docs/stable/intraday-15-min
- Historical EOD full: https://site.financialmodelingprep.com/developer/docs/stable/historical-price-eod-full
- WebSocket dataset: https://site.financialmodelingprep.com/datasets/websocket

## Auth Decision

The official docs allow authorization by request header or URL query parameter. Phase 15 uses header auth only:

`apikey: <runtime FMP_API_KEY>`

The client must never append `apikey` to request URLs, metadata, exceptions, exports, frontend bundles, logs, scheduler payloads, or persisted provider records. FMP key status is represented only as present or missing.

## REST Endpoint Matrix

| Endpoint key | Category | Stable path | Probe symbols | V1 use | Runtime entitlement status |
| --- | --- | --- | --- | --- | --- |
| `quote` | real-time quote | `/quote?symbol=SPY` | SPY | single-symbol live quote and smoke | Detectable only by live check |
| `quote_short` | real-time quote | `/quote-short?symbol=SPY` | SPY | lightweight quote smoke | Detectable only by live check |
| `batch_quote` | real-time quote | `/batch-quote?symbols=SPY,QQQ,AAPL,NVDA` | SPY, QQQ, AAPL, NVDA | default quote snapshot | Detectable only by live check |
| `batch_quote_short` | real-time quote | `/batch-quote-short?symbols=SPY,QQQ,AAPL,NVDA` | SPY, QQQ, AAPL, NVDA | lightweight batch smoke | Detectable only by live check |
| `historical_eod_full` | historical bars | `/historical-price-eod/full?symbol=SPY&from=YYYY-MM-DD&to=YYYY-MM-DD` | SPY | daily bars ingestion | Detectable only by live check |
| `intraday_1min` | intraday bars | `/historical-chart/1min?symbol=SPY&from=YYYY-MM-DD&to=YYYY-MM-DD` | SPY | 1 minute historical/incremental ingestion | Detectable only by live check |
| `intraday_5min` | intraday bars | `/historical-chart/5min?symbol=SPY&from=YYYY-MM-DD&to=YYYY-MM-DD` | SPY | 5 minute historical/incremental ingestion | Detectable only by live check |
| `intraday_15min` | intraday bars | `/historical-chart/15min?symbol=SPY&from=YYYY-MM-DD&to=YYYY-MM-DD` | SPY | 15 minute historical/incremental ingestion | Detectable only by live check |
| `intraday_30min` | optional intraday bars | `/historical-chart/30min?symbol=SPY` | SPY | optional future adapter | Unknown until explicitly added |
| `intraday_1hour` | optional intraday bars | `/historical-chart/1hour?symbol=SPY` | SPY | optional future adapter | Unknown until explicitly added |
| `intraday_4hour` | optional intraday bars | `/historical-chart/4hour?symbol=SPY` | SPY | optional future adapter | Unknown until explicitly added |

## WebSocket Scope

The official WebSocket dataset page lists `wss://financialmodelingprep.com/ws/us-stocks` for U.S. stocks and describes persistent streaming use cases. Phase 15 does not build production WebSocket ingestion. It only permits a bounded entitlement/auth probe when both are true:

- `FMP_API_KEY` is present in runtime environment.
- `AMD_ENABLE_FMP_WS_PROBE=true`.

REST polling remains the default scanner and ingestion path.

## Status Taxonomy

Persisted capability checks use these statuses:

- `ACCESSIBLE`: HTTP success and non-empty parseable response.
- `DENIED`: HTTP 401/403 or an entitlement/auth response shape.
- `RATE_LIMITED`: HTTP 429 or documented/observed rate-limit response.
- `EMPTY`: HTTP success with no usable rows.
- `ERROR`: transport, parse, timeout, or unexpected response error.
- `SKIPPED_NO_KEY`: runtime key is missing.
- `SKIPPED_MARKET_CLOSED`: reserved for bounded checks that intentionally avoid market-quiet probes.
- `UNKNOWN`: no live check has been run.

## V1 Security Boundary

This phase only verifies and ingests data. It does not add broker execution, order routing, options, gamma, Greeks, implied volatility, Level 2, dark-pool data, order books, automatic model activation, automatic deployment, self-learning claims, or profitability claims.
