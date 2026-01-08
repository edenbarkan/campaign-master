#!/usr/bin/env bash
set -euo pipefail
trap 'echo "[dev_pg] error on line $LINENO" >&2' ERR

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$BACKEND_DIR"

HOST_PORT="${PG_PORT:-5432}"
DEV_DB="campaign_master"
DATABASE_URL="postgresql+psycopg://cm:cm@localhost:${HOST_PORT}/${DEV_DB}"
export PG_PORT="$HOST_PORT"

if ! docker compose up -d db >/dev/null; then
  echo "[dev_pg] failed to start postgres container" >&2
  exit 1
fi

printf '[dev_pg] waiting for postgres'
while ! docker compose exec -T db pg_isready -U cm -d "$DEV_DB" >/dev/null 2>&1; do
  printf '.'
  sleep 1
done
printf '\n'

export DATABASE_URL
export FLASK_APP=run.py

echo "[dev_pg] Applying migrations with ${DATABASE_URL}"
flask db upgrade

echo "[dev_pg] Starting dev server"
echo "[dev_pg] Docs: http://localhost:5001/docs"
exec ./scripts/dev_run.sh
