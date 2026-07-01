PYTHON ?= python3
SERVICE_DIR := services/quant-engine

.PHONY: setup dev db-up db-migrate ingest features labels train validate backtest scanner export test lint typecheck

setup:
	corepack enable
	corepack pnpm install
	$(PYTHON) -m venv $(SERVICE_DIR)/.venv
	$(SERVICE_DIR)/.venv/bin/python -m pip install --upgrade pip
	$(SERVICE_DIR)/.venv/bin/python -m pip install -e "$(SERVICE_DIR)[dev,ml]"

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
