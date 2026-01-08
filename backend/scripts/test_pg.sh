#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$BACKEND_DIR"

TEST_DB="campaign_master_test"
HOST_PORT="${PG_PORT:-5432}"
PG_URI="postgresql+psycopg://cm:cm@localhost:${HOST_PORT}/${TEST_DB}"

echo "[test_pg] Starting postgres container on port ${HOST_PORT}"
docker compose up -d db

printf '[test_pg] waiting for postgres'
until docker compose exec -T db pg_isready -U cm -d campaign_master >/dev/null 2>&1; do
  printf '.'
  sleep 1
done
printf '\n'

echo "[test_pg] Recreating database ${TEST_DB}"
docker compose exec -T db psql -U cm -d postgres -c "DROP DATABASE IF EXISTS ${TEST_DB};" >/dev/null
docker compose exec -T db psql -U cm -d postgres -c "CREATE DATABASE ${TEST_DB} OWNER cm;" >/dev/null

export DATABASE_URL="$PG_URI"
export FLASK_APP=run.py

echo "[test_pg] Running migrations against ${DATABASE_URL}"
flask db upgrade

echo "[test_pg] Running pytest"
pytest -q
echo "[test_pg] Tests completed successfully"
