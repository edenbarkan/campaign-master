#!/usr/bin/env bash
set -euo pipefail
trap 'echo "[flows_dev_pg] error on line $LINENO" >&2' ERR

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$BACKEND_DIR"

BASE_URL="${BASE_URL:-http://localhost:5001}"
export BASE_URL

echo "[flows_dev_pg] Checking server at ${BASE_URL}"
if ! curl -fsS "${BASE_URL}/openapi.yaml" >/dev/null; then
  echo "[flows_dev_pg][error] ${BASE_URL} not reachable. Start the dev server with PG_PORT=... ./scripts/dev_pg.sh" >&2
  exit 1
fi

echo "[flows_dev_pg] Using DATABASE_URL=${DATABASE_URL:-<not set>}"

VERIFY_SCRIPT="$BACKEND_DIR/scripts/verify_flow.sh"
PERMISSIONS_SCRIPT="$BACKEND_DIR/scripts/smoke_permissions.sh"
REPORTS_SCRIPT="$BACKEND_DIR/scripts/smoke_reports.sh"

run_step() {
  local label=$1
  shift
  echo "[flows_dev_pg] Running ${label}"
  "$@"
}

run_step verify_flow "$VERIFY_SCRIPT"
run_step smoke_permissions "$PERMISSIONS_SCRIPT"
run_step smoke_reports "$REPORTS_SCRIPT"

echo "[flows_dev_pg] All flows completed successfully against ${BASE_URL}"
