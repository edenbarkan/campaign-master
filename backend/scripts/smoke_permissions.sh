#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:5001}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="${BACKEND_DIR}/tmp/last_users.env"
[[ -f "$ENV_FILE" ]] || { echo "[smoke_permissions][error] missing $ENV_FILE. Run verify_flow.sh first." >&2; exit 1; }
# shellcheck disable=SC1090
source "$ENV_FILE"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
ADV_COOKIE="$TMP_DIR/adv.cookies"
PUB_COOKIE="$TMP_DIR/pub.cookies"

login() {
  local email=$1
  local password=$2
  local cookie=$3
  curl -sS -b "$cookie" -c "$cookie" -H 'Content-Type: application/json' -X POST \
    -d "{\"email\":\"$email\",\"password\":\"$password\"}" \
    "$BASE_URL/api/auth/login" >/dev/null
}

status_for() {
  local path=$1
  local cookie=$2
  curl -sS -o /dev/null -w '%{http_code}' -b "$cookie" -c "$cookie" "$BASE_URL$path"
}

login "$ADV_EMAIL" "$PASSWORD" "$ADV_COOKIE"
login "$PUB_EMAIL" "$PASSWORD" "$PUB_COOKIE"

adv_status=$(status_for /api/reports/publisher "$ADV_COOKIE")
pub_status=$(status_for /api/reports/advertiser "$PUB_COOKIE")

echo "[smoke_permissions] advertiser hitting publisher report -> $adv_status"
echo "[smoke_permissions] publisher hitting advertiser report -> $pub_status"

[[ $adv_status == 403 ]] || { echo "Expected advertiser to receive 403, got $adv_status" >&2; exit 1; }
[[ $pub_status == 403 ]] || { echo "Expected publisher to receive 403, got $pub_status" >&2; exit 1; }

echo "[smoke_permissions] checks passed"
