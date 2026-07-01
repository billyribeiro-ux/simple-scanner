PYTHON ?= python3
PYTHON314 ?= python3.14
SERVICE_DIR := services/quant-engine
LOCAL_POSTGRES_USER ?= amd
LOCAL_POSTGRES_PASSWORD ?= amd
LOCAL_POSTGRES_HOST ?= localhost
LOCAL_POSTGRES_PORT ?= 15432
LOCAL_POSTGRES_DB ?= adaptive_market_decoder

.PHONY: help doctor setup setup-backend require-backend-venv quant-test backend-test backend-lint backend-typecheck api-smoke api-smoke-sqlite api-smoke-postgres repository-parity-test replay-test replay-sensitivity-test export-test fmp-smoke dev api-dev web-dev db-up db-down db-migrate db-inspect db-diagnostics db-reset-dev ingest features labels train validate backtest scanner export test lint typecheck

help:
	@printf "Adaptive Market Decoder commands\n\n"
	@printf "Runtime:\n"
	@printf "  make doctor              Check Node 24.18.0, Python 3.14.6, venv, Docker, env, and backend tools\n"
	@printf "  make setup               Install frontend workspace and backend venv\n"
	@printf "  make setup-backend       Create services/quant-engine/.venv with python3.14 and install [dev,ml]\n"
	@printf "  make api-dev             Start FastAPI backend on :8000\n"
	@printf "  make web-dev             Start SvelteKit dev server\n"
	@printf "  make dev                 Start db services plus API and web dev servers\n\n"
	@printf "Database:\n"
	@printf "  make db-up               Start local Postgres/Timescale and Redis\n"
	@printf "  make db-down             Stop local database services\n"
	@printf "  make db-migrate          Run Alembic migrations\n"
	@printf "  make db-inspect          Inspect migrated Postgres/Timescale schema\n"
	@printf "  make db-diagnostics      Print read-only Postgres replay/sensitivity diagnostics\n"
	@printf "  make db-reset-dev        DEV ONLY: delete local database volumes, restart, and migrate\n\n"
	@printf "Quality:\n"
	@printf "  make quant-test          Run pure quant tests, with python3 fallback when venv is absent\n"
	@printf "  make backend-test        Run full backend pytest in the target venv\n"
	@printf "  make backend-lint        Run backend ruff checks\n"
	@printf "  make backend-typecheck   Run backend mypy checks\n"
	@printf "  make api-smoke           Run default SQLite persisted FastAPI smoke test\n"
	@printf "  make api-smoke-sqlite    Run explicit SQLite persisted FastAPI smoke test\n"
	@printf "  make api-smoke-postgres  Run Postgres persisted FastAPI smoke test against local compose DB\n"
	@printf "  make repository-parity-test Run SQLite/Postgres repository parity tests\n"
	@printf "  make replay-test        Run candidate-to-trade replay simulator tests\n"
	@printf "  make replay-sensitivity-test Run replay audit and sensitivity tests\n"
	@printf "  make export-test        Run export workbook/CSV tests\n"
	@printf "  make fmp-smoke           Run optional live FMP REST smoke if FMP_API_KEY is configured\n"
	@printf "  make test lint typecheck Run backend and frontend quality gates\n"

setup:
	corepack enable
	corepack pnpm install
	$(MAKE) setup-backend

doctor:
	@./scripts/doctor.sh

setup-backend:
	@if ! command -v $(PYTHON314) >/dev/null 2>&1; then \
		echo "Python 3.14.6 is required for the backend target runtime, but $(PYTHON314) was not found."; \
		echo "Install it with pyenv, asdf, uv python install, or a manual python.org build, then rerun make setup-backend."; \
		echo "See README.md and docs/HANDOFF.md for the no-Docker pure quant test path."; \
		exit 1; \
	fi
	$(PYTHON314) -m venv $(SERVICE_DIR)/.venv
	$(SERVICE_DIR)/.venv/bin/python -m pip install --upgrade pip
	$(SERVICE_DIR)/.venv/bin/python -m pip install -e "$(SERVICE_DIR)[dev,ml]"

require-backend-venv:
	@if [ ! -x "$(SERVICE_DIR)/.venv/bin/python" ]; then \
		echo "Backend venv missing at $(SERVICE_DIR)/.venv."; \
		echo "Install Python 3.14.6, then run make setup-backend."; \
		exit 1; \
	fi

quant-test:
	@if [ -x "$(SERVICE_DIR)/.venv/bin/python" ]; then \
		cd $(SERVICE_DIR) && PYTHONPATH=. .venv/bin/python -m pytest tests/quant; \
	else \
		echo "Backend venv missing; running pure quant tests with python3 as a compatibility fallback."; \
		cd $(SERVICE_DIR) && PYTHONPATH=. python3 -m pytest tests/quant; \
	fi

backend-test: require-backend-venv
	cd $(SERVICE_DIR) && PYTHONPATH=. .venv/bin/python -m pytest

backend-lint: require-backend-venv
	cd $(SERVICE_DIR) && .venv/bin/ruff check app tests

backend-typecheck: require-backend-venv
	cd $(SERVICE_DIR) && .venv/bin/mypy app

api-smoke: api-smoke-sqlite

api-smoke-sqlite: require-backend-venv
	cd $(SERVICE_DIR) && PYTHONPATH=. .venv/bin/python -m pytest tests/test_persisted_api_smoke.py::test_persisted_api_vertical_slice_sqlite

api-smoke-postgres: require-backend-venv
	@DEFAULT_DATABASE_SCHEME="postgresql+psycopg"; \
		DEFAULT_DATABASE_AUTH="$(LOCAL_POSTGRES_USER):$(LOCAL_POSTGRES_PASSWORD)"; \
		DEFAULT_DATABASE_HOST="$(LOCAL_POSTGRES_HOST):$(LOCAL_POSTGRES_PORT)"; \
		DEFAULT_DATABASE_URL="$${DEFAULT_DATABASE_SCHEME}://$${DEFAULT_DATABASE_AUTH}@$${DEFAULT_DATABASE_HOST}/$(LOCAL_POSTGRES_DB)"; \
		DATABASE_URL="$${DATABASE_URL:-$${DEFAULT_DATABASE_URL}}" \
		PYTHONPATH=$(SERVICE_DIR) \
		$(SERVICE_DIR)/.venv/bin/python -m pytest $(SERVICE_DIR)/tests/test_persisted_api_smoke.py::test_persisted_api_vertical_slice_postgres

repository-parity-test: require-backend-venv
	@DEFAULT_DATABASE_SCHEME="postgresql+psycopg"; \
		DEFAULT_DATABASE_AUTH="$(LOCAL_POSTGRES_USER):$(LOCAL_POSTGRES_PASSWORD)"; \
		DEFAULT_DATABASE_HOST="$(LOCAL_POSTGRES_HOST):$(LOCAL_POSTGRES_PORT)"; \
		DEFAULT_DATABASE_URL="$${DEFAULT_DATABASE_SCHEME}://$${DEFAULT_DATABASE_AUTH}@$${DEFAULT_DATABASE_HOST}/$(LOCAL_POSTGRES_DB)"; \
		DATABASE_URL="$${DATABASE_URL:-$${DEFAULT_DATABASE_URL}}" \
		PYTHONPATH=$(SERVICE_DIR) \
		$(SERVICE_DIR)/.venv/bin/python -m pytest $(SERVICE_DIR)/tests/test_repository_parity.py

replay-test: require-backend-venv
	cd $(SERVICE_DIR) && PYTHONPATH=. .venv/bin/python -m pytest tests/quant/test_replay_engine.py

replay-sensitivity-test: require-backend-venv
	cd $(SERVICE_DIR) && PYTHONPATH=. .venv/bin/python -m pytest tests/quant/test_replay_sensitivity.py

export-test: require-backend-venv
	cd $(SERVICE_DIR) && PYTHONPATH=. .venv/bin/python -m pytest tests/test_exports.py

fmp-smoke: require-backend-venv
	PYTHONPATH=$(SERVICE_DIR) $(SERVICE_DIR)/.venv/bin/python scripts/fmp_smoke.py

dev:
	$(MAKE) db-up
	$(MAKE) -j2 api-dev web-dev

api-dev: require-backend-venv
	$(SERVICE_DIR)/.venv/bin/uvicorn app.main:app --reload --app-dir $(SERVICE_DIR) --host 0.0.0.0 --port 8000

web-dev:
	corepack pnpm dev

db-up:
	docker compose up -d postgres redis

db-down:
	docker compose down

db-migrate: require-backend-venv
	cd $(SERVICE_DIR) && .venv/bin/alembic upgrade head

db-inspect: require-backend-venv
	PYTHONPATH=$(SERVICE_DIR) $(SERVICE_DIR)/.venv/bin/python scripts/inspect_db_schema.py

db-diagnostics: require-backend-venv
	PYTHONPATH=$(SERVICE_DIR) $(SERVICE_DIR)/.venv/bin/python scripts/db_query_diagnostics.py

db-reset-dev:
	@printf "\nDEV ONLY: this deletes local Postgres/Redis containers and named volumes for this compose project.\n"
	@printf "Press Ctrl-C within 5 seconds to abort.\n\n"
	@sleep 5
	docker compose down -v
	$(MAKE) db-up
	$(MAKE) db-migrate

ingest:
	cd $(SERVICE_DIR) && .venv/bin/python -m app.cli ingest

features:
	cd $(SERVICE_DIR) && .venv/bin/python -m app.cli features

labels:
	cd $(SERVICE_DIR) && .venv/bin/python -m app.cli labels

train:
	cd $(SERVICE_DIR) && .venv/bin/python -m app.cli train

validate:
	cd $(SERVICE_DIR) && .venv/bin/python -m app.cli validate

backtest:
	cd $(SERVICE_DIR) && .venv/bin/python -m app.cli backtest

scanner:
	cd $(SERVICE_DIR) && .venv/bin/python -m app.cli scanner

export:
	cd $(SERVICE_DIR) && .venv/bin/python -m app.cli export

test: backend-test
	corepack pnpm test

lint: backend-lint
	corepack pnpm lint

typecheck: backend-typecheck
	corepack pnpm check
