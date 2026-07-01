# FMP Capability Matrix

Research date: 2026-06-30.

Sources checked: FMP developer docs, stable endpoint pages, WebSocket dataset/API pages, and FMP FAQs. Plan availability is marked unknown unless it can be detected at runtime from an authenticated request. The API key must be supplied only through `FMP_API_KEY`.

| Endpoint | Official URL pattern | Parameters | Data returned | Single or batch | Transport | Rate/entitlement notes | Current plan detectable? | V1/V2 | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Stock Quote | `https://financialmodelingprep.com/stable/quote?symbol=AAPL&apikey=...` | `symbol`, `apikey` | price, change, volume, day high/low, year high/low, market cap, timestamp | Single symbol per documented request | REST | Requires API key; delayed/realtime depends on plan | Runtime health check only | V1 | Primary quote endpoint. |
| Quote Short | `https://financialmodelingprep.com/stable/quote-short?symbol=AAPL&apikey=...` | `symbol`, `apikey` | compact price/volume timestamp payload | Single | REST | Same API key and entitlement constraints | Runtime only | V1 | Useful for lightweight polling. |
| Batch Quote | `https://financialmodelingprep.com/stable/batch-quote?symbols=AAPL,MSFT&apikey=...` | `symbols`, `apikey` | quote array for comma-separated symbols | Batch | REST | More efficient for default universe polling | Runtime only | V1 | Preferred REST polling path when allowed. |
| Intraday 1 Minute | `https://financialmodelingprep.com/stable/historical-chart/1min?symbol=AAPL&from=YYYY-MM-DD&to=YYYY-MM-DD&apikey=...` | `symbol`, `from`, `to`, `apikey` | OHLCV intraday bars | Single | REST | Historical depth and realtime delay vary by plan | Runtime only | V1 | Main ingestion feed. |
| Intraday 5 Minute | `https://financialmodelingprep.com/stable/historical-chart/5min?symbol=AAPL&from=YYYY-MM-DD&to=YYYY-MM-DD&apikey=...` | `symbol`, `from`, `to`, `apikey` | OHLCV bars | Single | REST | Same as intraday | Runtime only | V1 | Secondary model interval. |
| Intraday 15 Minute | `https://financialmodelingprep.com/stable/historical-chart/15min?symbol=AAPL&from=YYYY-MM-DD&to=YYYY-MM-DD&apikey=...` | `symbol`, `from`, `to`, `apikey` | OHLCV bars | Single | REST | Same as intraday | Runtime only | V1 | Regime/context interval. |
| EOD Historical Full | `https://financialmodelingprep.com/stable/historical-price-eod/full?symbol=AAPL&from=YYYY-MM-DD&to=YYYY-MM-DD&apikey=...` | `symbol`, `from`, `to`, `apikey` | daily OHLCV and adjusted fields | Single | REST | Historical depth varies by plan | Runtime only | V1 | Previous day levels and gap context. |
| EOD Historical Light | `https://financialmodelingprep.com/stable/historical-price-eod/light?symbol=AAPL&from=YYYY-MM-DD&to=YYYY-MM-DD&apikey=...` | `symbol`, `from`, `to`, `apikey` | compact daily bars | Single | REST | Lower payload alternative | Runtime only | V1 | Fallback for daily context. |
| Index Quote/History | quote/history endpoints with index symbols | `symbol`, dates, `apikey` | index quotes/bars | Single | REST | Symbol support varies | Runtime only | V1 | SPY/QQQ/IWM are ETFs and work through stock endpoints; index proxies can be added when verified. |
| Market Hours | stable exchange-hours and holiday endpoints in FMP docs | exchange/calendar params, `apikey` | market open/close state and holidays | Usually exchange-level | REST | Entitlement may vary | Runtime only | V1 | Used to gate RTH scanner. |
| Technical Indicators | stable technical-indicator endpoints such as SMA/EMA/RSI variants | `symbol`, `period`, `type`, dates, `apikey` | indicator series | Single | REST | Use as optional secondary checks | Runtime only | Later/V2 | Core intelligence computes local features instead. |
| Market News/Calendar | stable news and calendar endpoints in FMP docs | tickers, date range, `apikey` | events, articles, earnings/corporate data | Mixed | REST | Entitlement varies | Runtime only | V2 | Future catalyst adapter. |
| ETF Data | stable ETF-related endpoints where available | ETF symbol, `apikey` | holdings/profile/category data | Single | REST | Entitlement varies | Runtime only | Later | Useful context, not required for first scanner. |
| U.S. Stock WebSocket | `wss://websockets.financialmodelingprep.com` plus login/subscribe messages | API key and symbol subscriptions | streaming quote/trade events | Batch subscription | WebSocket | WebSocket is plan/entitlement dependent | Runtime login response only | V1 optional | REST polling fallback is required. |

## Gaps To Design Around

- True OPRA options feed, per-strike IV/Greeks, gamma exposure, put/call ratio, and full options microstructure were not verified in the official stable docs used for V1.
- L2/order book, market internals, dark-pool/block trade feeds, and broker execution were not verified as first-party FMP capabilities for this V1.
- The provider layer must keep these as future adapters instead of pretending FMP supplies them.

## Runtime Entitlement Detection

The backend exposes `GET /provider/health` and `GET /provider/capabilities`. Those checks call low-risk endpoints using `FMP_API_KEY` from the environment, redact URL/query output, and report `available`, `limited`, `unauthorized`, or `unknown` per capability.
