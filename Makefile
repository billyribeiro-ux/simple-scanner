PYTHON ?= python3
PYTHON314 ?= python3.14
SERVICE_DIR := services/quant-engine

.PHONY: doctor setup setup-backend quant-test dev db-up db-migrate ingest features labels train validate backtest scanner export test lint typecheck

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

quant-test:
	@if [ -x "$(SERVICE_DIR)/.venv/bin/python" ]; then \
		cd $(SERVICE_DIR) && PYTHONPATH=. .venv/bin/python -m pytest tests/quant; \
	else \
		echo "Backend venv missing; running pure quant tests with python3 as a compatibility fallback."; \
		cd $(SERVICE_DIR) && PYTHONPATH=. python3 -m pytest tests/quant; \
	fi

dev:
	$(MAKE) db-up
	$(SERVICE_DIR)/.venv/bin/uvicorn app.main:app --reload --app-dir $(SERVICE_DIR) --host 0.0.0.0 --port 8000 & corepack pnpm dev

db-up:
	docker compose up -d postgres redis

db-migrate:
	cd $(SERVICE_DIR) && .venv/bin/alembic upgrade head

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

test:
	cd $(SERVICE_DIR) && .venv/bin/python -m pytest
	corepack pnpm test

lint:
	cd $(SERVICE_DIR) && .venv/bin/ruff check app tests
	corepack pnpm lint

typecheck:
	cd $(SERVICE_DIR) && .venv/bin/mypy app
	corepack pnpm check
