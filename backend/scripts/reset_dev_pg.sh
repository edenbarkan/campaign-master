#!/usr/bin/env bash
set -euo pipefail
trap 'echo "[reset_dev_pg] error on line $LINENO" >&2' ERR

if [[ "${CONFIRM:-0}" != "1" ]]; then
  echo "[reset_dev_pg] Refusing to reset dev database without CONFIRM=1" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$BACKEND_DIR"

HOST_PORT="${PG_PORT:-5432}"
export PG_PORT="$HOST_PORT"
DEV_DB="campaign_master"

DB_CONTAINER="$(docker compose ps -q db 2>/dev/null || true)"
if [[ -z "$DB_CONTAINER" ]]; then
  if lsof -Pi :"$HOST_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "[reset_dev_pg][error] Port ${HOST_PORT} is already in use. Stop the other service or choose a different PG_PORT." >&2
    exit 1
  fi
fi

echo "[reset_dev_pg] Ensuring Postgres container is running on port ${HOST_PORT}"
docker compose up -d db >/dev/null

printf '[reset_dev_pg] waiting for postgres'
while ! docker compose exec -T db pg_isready -U cm -d postgres >/dev/null 2>&1; do
  printf '.'
  sleep 1
done
printf '\n'

echo "[reset_dev_pg] Dropping database ${DEV_DB}"
docker compose exec -T db psql -U cm -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${DEV_DB}';" >/dev/null
docker compose exec -T db psql -U cm -d postgres -c "DROP DATABASE IF EXISTS ${DEV_DB};" >/dev/null
docker compose exec -T db psql -U cm -d postgres -c "CREATE DATABASE ${DEV_DB};" >/dev/null

export DATABASE_URL="postgresql+psycopg://cm:cm@localhost:${HOST_PORT}/${DEV_DB}"
export FLASK_APP=run.py

echo "[reset_dev_pg] Applying migrations with ${DATABASE_URL}"
flask db upgrade

echo "[reset_dev_pg] Database ${DEV_DB} is ready"
