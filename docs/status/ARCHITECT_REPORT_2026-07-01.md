# Adaptive Market Decoder Architect Report — 2026-07-01

## 1. Executive Summary

Adaptive Market Decoder currently exists as a credible first-pass monorepo scaffold. It has a SvelteKit/Svelte 5 frontend, a FastAPI backend source tree, FMP REST provider code, quant modules for features/labels/rules/regimes/models/signals, export services, migrations, and documentation. It is not yet a complete scanner, research, backtest, or model platform.

Direct answers:

- Is the repo runnable? PARTIAL. Frontend checks run; full backend/database/FMP workflow does not run in this environment.
- Is the frontend runnable? YES, with Node engine warnings because local Node is `25.3.0` and the repo targets `24.18.0`.
- Is the backend runnable? NOT VERIFIED. Backend source compiles, but target Python `3.14.6` is not installed and the backend venv does not exist.
- Is FMP ingestion runnable? NOT VERIFIED. Routes and provider code exist, but no live request was made because `FMP_API_KEY` is not present in the shell and the supplied key was not written to files.
- Is training runnable? PARTIAL/NOT VERIFIED. `/models/train` exists and writes statistical artifacts from in-memory labels, but no real ML classifier training was verified.
- Is live scanning runnable? PARTIAL/NOT VERIFIED. Start/stop routes and scanner loop exist, but scanner lacks historical context and was not run against FMP.
- Are CSV/XLSX exports runnable? PARTIAL/NOT VERIFIED. Export service exists for live signals and daily review scaffolds; backend runtime was not available to verify.
- Are tests passing? PARTIAL. Frontend checks, build, lint, and Playwright smoke tests pass. Backend pytest fails under Python 3.9.6; ruff/mypy are unavailable.
- What is the biggest blocker? The backend target environment is missing: no Python `3.14.6` venv, no Docker daemon, and no verified migrations. The biggest product blocker after that is that core workflow state is still in memory instead of persisted.

Verdict: safe to continue development from, not safe to present as a completed market scanner or validated model platform.

## 2. Files Created or Modified

- `docs/HANDOFF.md`: updated operator handoff with honest current status, exact runtime pins, run commands, FMP key handling, blockers, and next prompt focus.
- `docs/status/ARCHITECT_REPORT_2026-07-01.md`: created this full chief-architect review report.
- `apps/web`: existing SvelteKit application for dashboard, research, backtest, scanner, exports, and settings.
- `packages/shared`: existing shared TypeScript types/constants.
- `services/quant-engine`: existing FastAPI backend, FMP provider, quant engines, exports, scanner, tests, and migrations.
- `docs/research`: existing FMP and Svelte research notes.
- `docs/architecture.md`: target architecture documentation; more aspirational than current implementation.
- `docs/data-model.md`: target data model documentation; not fully wired to runtime.
- `docs/signal-methodology.md`: signal design notes; implementation is partial.
- `docs/validation-methodology.md`: intended validation standard; walk-forward validation is not implemented.
- `docs/roadmap.md`: roadmap; should continue separating target state from current state.

## 3. Architecture Actually Implemented

Monorepo structure: COMPLETE. The repo has root package metadata, pnpm workspace configuration, frontend app, shared package, backend service, docs, and Docker Compose.

SvelteKit frontend: PARTIAL. A real SvelteKit app exists and passes checks/build/smoke tests. It is mostly a dashboard/workflow shell with limited backend integration.

FastAPI backend: PARTIAL. Routes exist for the required groups, but workflow state is in module-level memory and not persisted.

FMP provider: PARTIAL. REST quote, batch quote, and intraday bar provider paths exist with redaction, retry, backoff, and parsing. Several documented endpoints are not implemented.

Database layer: PLACEHOLDER/PARTIAL. Alembic and SQLAlchemy schema files exist, but the active API path does not use repositories. Migrations were not run.

Feature engine: PARTIAL. Basic features exist, but grouping/session isolation and several planned market-structure features are missing.

Label engine: PARTIAL. Forward labels use future bars for outcome measurement and next-bar entry, but no complete train/test or walk-forward split exists.

Backtest engine: PLACEHOLDER/PARTIAL. It summarizes labels; it does not simulate strategy execution chronologically.

Model engine: PLACEHOLDER/PARTIAL. It writes statistical JSON artifacts; no real scikit-learn classifier is active.

Validation engine: MISSING. Validation methodology is documented, but walk-forward/out-of-sample validation is not implemented as a real engine.

Live scanner: PARTIAL. Scanner loop exists, but it builds one synthetic quote bar and lacks recent historical context.

Export engine: PARTIAL. CSV/XLSX exports exist for live signals and daily review scaffolds; backtest/model/ticker reports are incomplete.

Self-learning review scaffold: PLACEHOLDER. Daily review export scaffold exists; controlled retraining and activation from reviews do not.

## 4. FMP Integration Status

Official FMP docs referenced in project planning:

- Quote endpoint: `https://site.financialmodelingprep.com/developer/docs/stable/quote`
- Batch quote endpoint: `https://site.financialmodelingprep.com/developer/docs/stable/batch-quote`
- Intraday charts: `https://site.financialmodelingprep.com/developer/docs/stable/intraday-1-min`
- EOD charts: `https://site.financialmodelingprep.com/developer/docs/stable/historical-price-eod-full`
- WebSocket dataset: `https://site.financialmodelingprep.com/datasets/websocket`

Status:

- Quote endpoint status: PARTIAL. Provider method exists and parses one quote.
- Batch quote endpoint status: PARTIAL. Provider method exists and parses batch quotes.
- Quote-short status: MISSING. Documented but not implemented.
- Historical intraday bars status: PARTIAL. Provider method exists for intraday historical bars.
- Daily bars status: MISSING. EOD full/light endpoints are documented but not implemented.
- WebSocket status: MISSING. Documented as entitlement-gated; no client implemented.
- Technical indicators status: MISSING. Documented as secondary/future inputs; no adapter implemented.
- Index/ETF data status: PARTIAL. Symbols like SPY/QQQ can be requested as normal symbols; no dedicated index-history adapter.
- Options data status: MISSING. FMP gaps documented; no OPRA/options adapter.
- Market internals status: MISSING. No breadth/TICK/TRIN/advance-decline provider.
- Gamma/Greek/IV limitations: MISSING. Not available from current implementation; future provider adapter required.
- Rate limit / entitlement concerns: PARTIAL. Retry/backoff exists; true throttling and entitlement registry do not.
- REST polling fallback status: PARTIAL. `stream_quotes` polls REST; scanner uses batch quotes.
- Request retry/backoff/throttle status: PARTIAL. Retry/backoff exists; throttle is not a robust token bucket.
- Response validation status: PARTIAL. Basic parsing exists; no strong Pydantic validation boundary for raw provider responses.
- Timestamp normalization status: PARTIAL. Intraday strings are treated as America/New_York and converted to UTC; needs tests across DST/session boundaries.

FMP integration is a usable starting point, not a production-grade provider layer.

## 5. Quant / Math / Market Logic Implemented

| Item | Status | Notes |
| --- | --- | --- |
| VWAP | PARTIAL | Cumulative VWAP exists but needs explicit symbol/session/interval grouping. |
| ATR | PARTIAL | ATR proxy from rolling high-low range exists; not true ATR. |
| Relative volume | PARTIAL | Rolling average volume ratio exists; not same-time-of-day. |
| Same-time-of-day volume | MISSING | Not implemented. |
| Previous day high/low | MISSING | Not implemented. |
| Premarket high/low | PARTIAL | Basic premarket high/low accumulation exists. |
| Opening range | PARTIAL | Basic opening range fields exist. |
| Gap features | MISSING | Not implemented. |
| Trend slope | PARTIAL | Simple recent return/regime heuristics exist. |
| Candle/range/wick features | COMPLETE | Body, range, wick, and return features exist. |
| Volume acceleration | MISSING | Not implemented. |
| Absorption proxy | MISSING | Not implemented. |
| Liquidity sweep proxy | MISSING | Not implemented explicitly. |
| Failed breakout/breakdown logic | PARTIAL | Rule detection exists, but setup validation is shallow. |
| Relative strength vs SPY | MISSING | Not implemented. |
| Relative strength vs QQQ | MISSING | Not implemented. |
| Market regime classifier | PARTIAL | Simple rule-based classifier exists. |
| Ticker personality stats | PLACEHOLDER | Basic statistical summaries exist; no durable personality model. |
| Setup detection | PARTIAL | Rule engine detects several setups. |
| Entry logic | PARTIAL | Labels use next bar open; live signals use current/latest close. |
| Stop logic | PARTIAL | Rule-based stop planning exists; no realistic execution/slippage model. |
| Target logic | PARTIAL | R-multiple targets exist; not validated. |
| Expected R | PARTIAL | Derived from statistical evidence and score; not calibrated. |
| Confidence scoring | PARTIAL | Heuristic score; not calibrated probability. |
| Signal grade | PARTIAL | Grade mapping exists. |
| Meta-scorer | PLACEHOLDER | Signal scorer blends rule/statistics/regime heuristics; no trained meta-model. |

## 6. Labeling and Leakage Review

- Are features computed using only information available at or before the signal timestamp? PARTIAL. Individual rolling computations use current/past bars, but the engine must be called with data grouped by symbol/session/interval. If mixed data is passed, rolling state and VWAP can cross-contaminate.
- Are labels allowed to use future bars only for outcome measurement? YES/PARTIAL. Labeling uses future bars to determine outcomes, which is appropriate for labels, but the broader pipeline lacks split enforcement.
- Is entry based on next bar open, current close, or something else? Labels use next bar open. Live scanner uses latest quote/close style values.
- Are stop/target calculations realistic? PARTIAL. Stops/targets are rule based and conservative in some cases, but no slippage, spread, partial fill, or intrabar path model exists.
- Is there any lookahead leakage? POSSIBLE PIPELINE RISK. Label code itself is mostly forward-outcome based, but feature grouping and validation splits are not enforced.
- Is there any train/test leakage? YES RISK. No train/test split or walk-forward process is implemented in the active training path.
- Is there random shuffling across time? No evidence of random shuffling was found in the active code, but no chronological split exists either.
- Are splits chronological? MISSING. Chronological split is documented but not implemented.
- Does walk-forward validation exist? MISSING.
- Are premarket/RTH boundaries handled correctly? PARTIAL. Time flags and basic premarket/opening-range logic exist; full session boundary tests are missing.
- Are timestamps handled correctly? PARTIAL. Provider normalization exists; DST, exchange holidays, and mixed timezone cases are not verified.
- Are there assumptions that could inflate backtest results? YES. Label-summary backtests, weak split enforcement, no slippage/spread, no execution model, and scanner synthetic bars could all overstate usefulness.

Important files/functions:

- `services/quant-engine/app/features/engine.py`: rolling feature state must be isolated by symbol, interval, and session.
- `services/quant-engine/app/labels/engine.py`: labels use next bar open and future window outcomes; reasonable for labels, but not a full validation pipeline.
- `services/quant-engine/app/backtesting/engine.py`: summarizes labels rather than simulating chronological trades.
- `services/quant-engine/app/models/engine.py`: trains statistical summaries from labels without a proper temporal validation split.

## 7. Validation / Backtest Status

| Metric / Method | Status | Notes |
| --- | --- | --- |
| Chronological split | MISSING | Documented only. |
| Walk-forward validation | MISSING | Not implemented. |
| Out-of-sample test | MISSING | Not implemented. |
| Per-symbol metrics | PARTIAL | Breakdown support exists. |
| Per-setup metrics | PARTIAL | Breakdown support exists. |
| Per-regime metrics | PARTIAL | Breakdown support exists. |
| Per-time-window metrics | MISSING | Not implemented. |
| Win rate | PARTIAL | Computed from labels/stat summaries. |
| Precision | MISSING | Not implemented. |
| Recall | MISSING | Not implemented. |
| Expectancy | PARTIAL | Average R exists; full expectancy reporting is shallow. |
| Average R | PARTIAL | Computed from labels. |
| Median R | MISSING | Not implemented. |
| Profit factor | PARTIAL | Present in backtest summary logic, but based on labels not full trades. |
| Max drawdown | MISSING | Not implemented. |
| MFE | MISSING | Not implemented. |
| MAE | MISSING | Not implemented. |
| Target hit rate | PARTIAL | Label outcomes can imply this, but reporting is limited. |
| Stop hit rate | PARTIAL | Label outcomes can imply this, but reporting is limited. |
| Calibration/Brier score | PLACEHOLDER | Baseline Brier-like field exists in model metrics, not true calibration. |
| No-trade suppression rate | MISSING | Not implemented. |

## 8. Model Status

- Model types implemented: statistical summary artifact only.
- Baseline model exists: PARTIAL. Baseline win-rate/average-R statistics exist.
- ML classifier exists: MISSING. No active scikit-learn classifier training path.
- Gradient boosting exists: MISSING.
- Calibration exists: MISSING.
- Regime model exists: PARTIAL. Rule-based regime classifier exists, not a trained model.
- Meta-scorer exists: PLACEHOLDER. Signal scoring blends heuristic evidence; no trained meta-scorer.
- Model versioning exists: PARTIAL. JSON artifacts include versions.
- Model activation safety exists: PARTIAL. Activation guard checks minimum trades and positive average R; this is too weak for live use.
- Model artifacts are stored: `services/quant-engine/model_artifacts`, ignored by git.
- Previous models are archived: PARTIAL. Separate JSON artifacts can remain, but there is no robust registry/archival policy.

Do not call this self-learning yet. Daily review, controlled retraining, validation, and activation rules are not implemented as a complete loop.

## 9. Live Scanner Status

| Capability | Status | Notes |
| --- | --- | --- |
| Start | PARTIAL | Route and scanner task exist; not verified live. |
| Stop | PARTIAL | Route exists; not verified live. |
| Fetch live quotes | PARTIAL | Uses FMP batch quotes; not verified with key. |
| Fetch historical context | MISSING | Scanner does not hydrate recent intraday context. |
| Compute live features | PARTIAL | Computes features from synthetic quote bars; too shallow. |
| Classify regime | PARTIAL | Calls simple classifier, but context is weak. |
| Generate LONG | PARTIAL | Signal engine can emit LONG, but live context likely suppresses most signals. |
| Generate SHORT | PARTIAL | Signal engine can emit SHORT, but live context likely suppresses most signals. |
| Generate NO_TRADE | COMPLETE | Rule engine/scorer can suppress to NO_TRADE. |
| Generate ticker, entry, stop, targets | PARTIAL | Signal structure exists. |
| Generate reasons/warnings | PARTIAL | Reasons/warnings exist. |
| Stream signals to frontend | PARTIAL | SSE route exists; not verified end-to-end. |
| Save signals to database | MISSING | No persistence. |
| Export signals | PARTIAL | Export service exists for latest signal list. |

## 10. Frontend Status

- Svelte version: `5.56.4`.
- SvelteKit version: `2.68.0`.
- TypeScript strict status: PASS. `corepack pnpm check` passed.
- Node version compatibility: PARTIAL. Repo targets Node `24.18.0`; local Node is `25.3.0`, producing warnings.
- pnpm workspace status: PARTIAL. `corepack pnpm` works; bare `pnpm --version` hung. Nested scripts emitted a secondary pnpm engine warning.
- Svelte 5 runes: USED.
- Latest event syntax such as `onclick`: USED.
- Phosphor icons status: `phosphor-svelte@3.1.0` is used because `@phosphor-icons/svelte` was unavailable during planning.
- Route list: `/`, `/research`, `/backtest`, `/scanner`, `/exports`, `/settings`.
- Dashboard page status: PARTIAL/DEMO. Loads and passes smoke check.
- Training/research page status: PARTIAL. UI exists; backend workflow is light.
- Backtest page status: PARTIAL. UI exists; not wired to full validation.
- Live scanner page status: PARTIAL. Start/stop controls visible; backend not fully verified.
- Exports page status: PARTIAL. UI exists; some paths reuse signal export flow.
- Settings page status: PARTIAL. Config display and local controls exist.
- API integration status: PARTIAL. API client exists; not all pages execute real backend workflows.
- Broken UI issues: none observed in smoke tests; no full visual QA across all breakpoints was run in this audit.
- Accessibility concerns: basic semantic UI appears reasonable, but no dedicated accessibility audit was run.
- Responsive layout status: likely reasonable from CSS structure, but not fully verified across devices in this audit.

## 11. Export Status

| Export | Status | Notes |
| --- | --- | --- |
| Live signals CSV | PARTIAL | Service exists; backend runtime not verified. |
| Live signals XLSX | PARTIAL | Service exists; backend runtime not verified. |
| Signal history | MISSING | No durable signal history because signals are not persisted. |
| Backtests | PLACEHOLDER | Backtest XLSX route currently uses signal workbook scaffold behavior. |
| Daily reviews | PARTIAL/PLACEHOLDER | JSON/CSV/XLSX daily review scaffold exists. |
| Model performance summary | MISSING | Not implemented as a true export. |
| Ticker personality report | MISSING | Not implemented. |

Export files are intended to be written under `services/quant-engine/exports`. The exports directory is ignored by git except for `.gitkeep` based on the repository ignore patterns and file list reviewed.

## 12. Database Status

- Database technology used: PostgreSQL/TimescaleDB via Docker Compose.
- TimescaleDB status: CONFIGURED, NOT RUNNING/NOT VERIFIED.
- Redis status: CONFIGURED, NOT RUNNING/NOT VERIFIED.
- Migrations status: PRESENT, NOT APPLIED.
- Tables/models implemented: PARTIAL. Migration and SQLAlchemy metadata exist.
- Bars table status: PRESENT IN SCHEMA/MIGRATION, NOT USED BY API.
- Features table status: PRESENT BUT DIVERGENT. Migration and `db/schema.py` disagree on structure.
- Labels table status: PRESENT BUT DIVERGENT. Migration and `db/schema.py` disagree on structure.
- Signals table status: PRESENT IN SCHEMA/MIGRATION, NOT USED BY API.
- Model runs table status: PRESENT IN SCHEMA/MIGRATION, NOT USED BY API.
- Exports table status: PRESENT IN SCHEMA/MIGRATION, NOT USED BY API.
- Provider requests table status: PRESENT IN SCHEMA/MIGRATION, NOT USED BY API.
- Data quality flags status: PARTIAL. Some fields exist conceptually; no complete data-quality pipeline.
- Whether migrations run cleanly: NOT VERIFIED. Docker daemon and backend venv are unavailable.

## 13. API Status

| Route group | Status | Notes |
| --- | --- | --- |
| Health | PARTIAL | Route exists; not verified via running backend in target env. |
| Config | PARTIAL | Route exists and avoids exposing key value. |
| Symbols | PARTIAL | Route exists; defaults and normalization exist. |
| Provider | PARTIAL | Health/capability style routes exist; entitlement not fully implemented. |
| Data | PARTIAL | Ingest and quote routes exist; depend on FMP key and memory state. |
| Features | PARTIAL | Build route exists; memory state only. |
| Labels | PARTIAL | Build route exists; memory state only. |
| Models | PARTIAL/PLACEHOLDER | Train/validate/activate routes exist around statistical artifacts. |
| Backtest | PLACEHOLDER/PARTIAL | Route exists; summarizes labels. |
| Scanner | PARTIAL | Start/stop/status routes exist; not fully verified. |
| Signals | PARTIAL | Latest/SSE routes exist; no durable storage. |
| Exports | PARTIAL | Signal/daily routes exist; backtest/model exports incomplete. |
| Daily review | PLACEHOLDER/PARTIAL | Scaffold exists; not self-learning. |

## 14. Commands Run and Results

| Command | Result | Notes | Blocking? |
| --- | --- | --- | --- |
| `git status --short` | PASS | Clean before report edits; now docs are modified/new. | No |
| `git log --oneline -10` | PASS | Recent commits include `Update Python target to 3.14.6` and `Build adaptive market decoder v1`. | No |
| `git diff --stat` | PASS | Empty before report edits. | No |
| `git ls-files \| grep -E "env\|key\|secret\|token"` | PASS | Only safe files such as `.env.example`, secret utility/tests, and Alembic env. | No |
| Project tree summary | PASS | Inspected excluding dependency/build/cache/output directories. | No |
| `node --version` | PASS | Returned `v25.3.0`; repo target is `24.18.0`. | No, but causes warnings |
| `pnpm --version` | FAIL/HUNG | Bare shim tried recursive bootstrap and was interrupted. | Yes for bare-pnpm workflow |
| `corepack pnpm --version` | PASS | Returned `11.5.2`. | No |
| `python --version` | FAIL | `python` command not found. | No |
| `python3 --version` | PASS | Returned `Python 3.9.6`; backend target is `3.14.6`. | Yes for backend |
| `python3.14 --version` | FAIL | Command not found. | Yes for backend |
| `uv --version` | FAIL | Command not found. | No; project uses venv/pip path |
| `corepack pnpm install` | PASS | Up to date; engine warning due Node `25.3.0`. | No |
| `corepack pnpm check` | PASS | TypeScript and Svelte checks passed. | No |
| `corepack pnpm build` | PASS | SvelteKit build passed; adapter-auto warned no supported production environment detected. | No |
| `corepack pnpm test` | WEAK PASS | Vitest found no test files in shared/web packages. | No, but coverage gap |
| `corepack pnpm lint` | PASS | Prettier passed; engine warnings remain. | No |
| `corepack pnpm --filter @amd/web exec playwright test` | PASS | Two smoke tests passed. | No |
| `python3 -m compileall services/quant-engine/app services/quant-engine/tests` | PASS | Syntax compile only under Python 3.9.6. | No |
| `cd services/quant-engine && python3 -m pytest` | FAIL | `ImportError: cannot import name 'UTC' from 'datetime'`. | Yes for backend tests |
| `cd services/quant-engine && python3 -m ruff check .` | FAIL | `No module named ruff`. | Yes for quality gate |
| `cd services/quant-engine && python3 -m mypy app` | FAIL | `No module named mypy`. | Yes for quality gate |
| `docker compose config` | PASS | Compose config valid. | No |
| `docker compose up -d postgres redis` | FAIL | `failed to connect to the docker API ... no such file or directory`. | Yes for database |
| `make help` | FAIL | `No rule to make target 'help'. Stop.` | No |
| `make test` | FAIL | `.venv/bin/python: No such file or directory`. | Yes |
| `make db-migrate` | FAIL | `.venv/bin/alembic: No such file or directory`. | Yes |
| `make -n dev` | PASS | Dry-run shows DB up plus uvicorn and pnpm dev commands; assumes `.venv` exists. | No |
| Secret scan | PASS | No occurrence of the supplied FMP key substring found. | No |
| `git diff --check` | PASS | No whitespace errors in report edits. | No |

## 15. Bugs, Risks, and Technical Debt

### Critical Blockers

- Python `3.14.6` is not installed, so backend target runtime cannot be verified.
- Backend `.venv` does not exist, so `make test` and migrations fail.
- Docker daemon is unavailable, so Postgres/TimescaleDB and Redis cannot start.
- Migrations have not been applied or verified.
- Active backend state is in memory, not database-backed.

### Quant / Model Risks

- No chronological split or walk-forward validation.
- No real ML classifier in active model path.
- Confidence is heuristic, not calibrated.
- Backtests summarize labels instead of simulating trades.
- No slippage, spread, partial-fill, or intrabar path modeling.
- Feature state can leak across symbols/sessions/intervals if inputs are mixed.
- Scanner lacks historical context.

### Data Risks

- FMP live entitlement not verified.
- FMP rate limits and plan permissions not detected durably.
- Quote-short, EOD, technical indicators, WebSocket, news/calendar, and index-specific endpoints are not implemented.
- Timestamp/session/DST handling lacks tests.
- Missing provider adapters for options, gamma/Greeks/IV, and market internals.

### Backend Risks

- API state is not persisted.
- Database schema and migration definitions diverge.
- Provider request accounting is not durable.
- Scanner job is not production hardened.
- Model artifacts are local JSON without registry semantics.
- Route contracts are early-stage and not deeply tested.

### Frontend Risks

- Pages are partly static workflow shells.
- Some actions are not wired to real backend workflows.
- No meaningful frontend unit tests are discovered.
- Local Node mismatch produces engine warnings.
- Package-manager scripts can hit inconsistent pnpm shims.

### Security Risks

- Current secret hygiene is good, but redaction needs regression tests.
- Provider health should never pass through unredacted provider URLs.
- Raw response capture must avoid request URLs/query strings.

### Product Risks

- The UI can make the system feel more complete than the backend really is.
- Live scanner output would not yet be trustworthy for a trader.
- Exported reports could be mistaken for validated research results.
- Absence of true validation weakens every model/signal claim.

## 16. Complete vs Partial vs Placeholder vs Missing

| Area | Complete | Partial | Placeholder | Missing | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| repo scaffold | 1 | 0 | 0 | 0 | Monorepo shape exists. |
| AGENTS.md | 1 | 0 | 0 | 0 | Project instructions exist. |
| README | 0 | 1 | 0 | 0 | Useful but should stress current blockers. |
| FMP research docs | 0 | 1 | 0 | 0 | Good first pass; live entitlements unknown. |
| FMP provider | 0 | 1 | 0 | 0 | REST basics exist. |
| secret handling | 1 | 0 | 0 | 0 | No key found in repo. |
| database | 0 | 1 | 1 | 0 | Schema exists but runtime not wired. |
| migrations | 0 | 1 | 0 | 0 | Migration exists, not run. |
| ingestion | 0 | 1 | 0 | 0 | Route/provider exist, not verified. |
| features | 0 | 1 | 0 | 0 | Basic features exist. |
| labels | 0 | 1 | 0 | 0 | Label engine exists; split controls missing. |
| leakage controls | 0 | 1 | 0 | 0 | Intent exists; pipeline enforcement missing. |
| backtest | 0 | 1 | 1 | 0 | Label summary, not true simulation. |
| validation | 0 | 0 | 1 | 1 | Mostly documented, not implemented. |
| model training | 0 | 1 | 1 | 0 | Statistical artifact only. |
| model versioning | 0 | 1 | 0 | 0 | JSON versioning exists. |
| model activation safety | 0 | 1 | 0 | 0 | Too weak for production. |
| regime classification | 0 | 1 | 0 | 0 | Simple rules exist. |
| ticker personality | 0 | 0 | 1 | 1 | Not a real model/report. |
| live scanner | 0 | 1 | 0 | 0 | Loop exists; context weak. |
| signal storage | 0 | 0 | 0 | 1 | Not persisted. |
| signal streaming | 0 | 1 | 0 | 0 | SSE exists, not verified end-to-end. |
| frontend dashboard | 0 | 1 | 0 | 0 | Demo works. |
| frontend training page | 0 | 1 | 0 | 0 | Research shell exists. |
| frontend backtest page | 0 | 1 | 0 | 0 | Shell exists. |
| frontend scanner page | 0 | 1 | 0 | 0 | Smoke tested controls. |
| frontend exports page | 0 | 1 | 0 | 0 | Shell exists. |
| exports CSV | 0 | 1 | 0 | 0 | Live/daily paths partial. |
| exports XLSX | 0 | 1 | 0 | 0 | Live/daily paths partial. |
| daily self-learning review | 0 | 0 | 1 | 0 | Review scaffold only. |
| tests | 0 | 1 | 0 | 0 | Frontend smoke passes; backend blocked. |
| lint/type checks | 0 | 1 | 0 | 0 | Frontend passes; backend tools missing. |
| documentation | 0 | 1 | 0 | 0 | Good coverage, target-state needs labeling. |

## 17. Recommended Next Five Tasks

1. Objective: Make the backend runtime real.
   Files likely involved: `.python-version`, `Makefile`, `services/quant-engine/pyproject.toml`, `README.md`, `docs/HANDOFF.md`.
   Why it matters: No backend validation can be trusted until Python `3.14.6`, the venv, and dev tools exist.
   Acceptance criteria: `python3.14 --version` works, `.venv` exists, `pytest`, `ruff`, and `mypy` run from the project commands.

2. Objective: Reconcile and apply database migrations.
   Files likely involved: `services/quant-engine/alembic/versions/0001_initial.py`, `services/quant-engine/app/db/schema.py`, `services/quant-engine/app/db/session.py`.
   Why it matters: Persistence work will be brittle while migration and metadata disagree.
   Acceptance criteria: `docker compose up -d postgres redis` succeeds, Alembic upgrade succeeds, schema matches metadata, no divergent feature/label definitions remain.

3. Objective: Replace in-memory API state with repositories.
   Files likely involved: `services/quant-engine/app/api/routes.py`, new repository modules under `services/quant-engine/app/db`, backend tests.
   Why it matters: In-memory state prevents restarts, multiple workers, history, exports, and real review workflows.
   Acceptance criteria: bars/features/labels/model runs/signals/provider requests/exports persist to Postgres and route tests prove restart-safe behavior.

4. Objective: Make scanner feature calculation context-aware.
   Files likely involved: `services/quant-engine/app/jobs/scanner.py`, `services/quant-engine/app/features/engine.py`, `services/quant-engine/app/data/fmp.py`, scanner tests.
   Why it matters: One synthetic quote bar cannot support VWAP, ATR, relative volume, regimes, or setup detection.
   Acceptance criteria: scanner hydrates recent intraday bars per symbol/interval, computes grouped features, emits signals with historical context, and persists scanner snapshots.

5. Objective: Implement real walk-forward validation before expanding ML.
   Files likely involved: `services/quant-engine/app/backtesting/engine.py`, `services/quant-engine/app/models/engine.py`, new validation module/tests, `docs/validation-methodology.md`.
   Why it matters: Without chronological validation, model metrics and confidence scores are not trustworthy.
   Acceptance criteria: chronological train/validation/test windows, walk-forward report, no random time shuffling, per-symbol/setup/regime/time metrics, calibration/Brier score, and model activation gated on out-of-sample results.

## 18. Questions for Chief Architect

No blocking questions. Sensible defaults can be used.
