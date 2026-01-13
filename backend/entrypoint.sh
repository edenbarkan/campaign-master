#!/usr/bin/env sh
set -e

if [ -n "$DATABASE_URL" ]; then
  echo "Waiting for database..."
  python - <<'PY'
import os
import time
import psycopg2

url = os.environ.get("DATABASE_URL")

for _ in range(30):
    try:
        conn = psycopg2.connect(url)
        conn.close()
        print("Database is ready")
        break
    except Exception:
        time.sleep(1)
else:
    print("Database connection failed after retries")
    raise SystemExit(1)
PY
fi

flask db upgrade
exec flask run --host=0.0.0.0 --port=5000
