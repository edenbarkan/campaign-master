#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

DB_URL="${DATABASE_URL:-sqlite:///campaign_master.db}"

echo "DATABASE_URL: ${DB_URL}"

if [[ "${DB_URL}" != sqlite:* ]]; then
  echo "Non-SQLite database detected; table listing skipped."
  exit 0
fi

export BACKEND_ROOT_PATH="${BACKEND_ROOT}"
export DB_URL_FOR_PY="${DB_URL}"

python3 <<'PY'
import os
import sqlite3
from urllib.parse import urlparse

db_url = os.environ['DB_URL_FOR_PY']
base = os.environ['BACKEND_ROOT_PATH']
parsed = urlparse(db_url)
path = parsed.path

if path.startswith('//'):
    sqlite_path = path[1:]
else:
    sqlite_path = os.path.join(base, path.lstrip('/'))

sqlite_path = os.path.abspath(sqlite_path)
print(f"SQLite file: {sqlite_path}")

if not os.path.exists(sqlite_path):
    print("File does not exist yet.")
    raise SystemExit(0)

conn = sqlite3.connect(sqlite_path)
tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
print("Tables:", tables if tables else "none")

try:
    version_rows = list(conn.execute("SELECT version_num FROM alembic_version"))
    if version_rows:
        print("alembic_version:", version_rows[0][0])
    else:
        print("alembic_version table empty")
except sqlite3.OperationalError:
    print("alembic_version table missing")
PY
