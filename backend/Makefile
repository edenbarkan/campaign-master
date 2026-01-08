SHELL := /bin/bash
.PHONY: test test-sqlite dev-up dev-migrate dev-run-pg flows-dev

## Run full test suite on Postgres (override PG_PORT=... if needed)
test:
	@echo "[make] Running Postgres-backed tests"
	./scripts/test_pg.sh

## Run pytest with SQLite (no DATABASE_URL override)
test-sqlite:
	@echo "[make] Running pytest with SQLite"
	DATABASE_URL= pytest -q

## Start Postgres dev container
dev-up:
	@echo "[make] docker compose up -d db"
	docker compose up -d db

## Apply migrations using current DATABASE_URL
dev-migrate:
	@echo "[make] flask db upgrade"
	FLASK_APP=run.py flask db upgrade

## Run dev server on Postgres (calls scripts/dev_pg.sh)
dev-run-pg:
	./scripts/dev_pg.sh

## Run manual flows (verify + smoke) against current BASE_URL
flows-dev:
	./scripts/flows_dev_pg.sh
