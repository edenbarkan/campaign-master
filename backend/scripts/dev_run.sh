#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$BACKEND_DIR"

mkdir -p "$BACKEND_DIR/instance"
DB_PATH="$BACKEND_DIR/instance/campaign_master.db"
export FLASK_APP=run.py
export DATABASE_URL="sqlite:////${DB_PATH}"

echo "CWD=$(pwd)"
echo "DB_PATH=${DB_PATH}"
echo "DATABASE_URL=${DATABASE_URL}"
ls -la "$BACKEND_DIR/instance"

flask db upgrade
flask run --port 5001
