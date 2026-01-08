#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$BACKEND_DIR"

export FLASK_APP=run.py

if [[ -z "${DATABASE_URL:-}" ]]; then
  mkdir -p "$BACKEND_DIR/instance"
  DB_PATH="$BACKEND_DIR/instance/campaign_master.db"
  rm -f "$DB_PATH"
  export DATABASE_URL="sqlite:////${DB_PATH}"
  echo "Resetting default SQLite DB at ${DB_PATH}"
else
  echo "Using provided DATABASE_URL=${DATABASE_URL}"
fi

echo "CWD=$(pwd)"
if [[ -d "$BACKEND_DIR/instance" ]]; then
  ls -la "$BACKEND_DIR/instance"
fi

flask db upgrade
echo "Database ready (${DATABASE_URL})"
