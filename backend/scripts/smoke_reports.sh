#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:5001}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="${BACKEND_DIR}/tmp/last_users.env"
[[ -f "$ENV_FILE" ]] || { echo "[smoke_reports][error] missing $ENV_FILE. Run verify_flow.sh first." >&2; exit 1; }
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

fetch_totals() {
  local path=$1
  local cookie=$2
  curl -sS -b "$cookie" -c "$cookie" "$BASE_URL$path"
}

login "$ADV_EMAIL" "$PASSWORD" "$ADV_COOKIE"
login "$PUB_EMAIL" "$PASSWORD" "$PUB_COOKIE"

adv_json=$(fetch_totals /api/reports/advertiser "$ADV_COOKIE")
pub_json=$(fetch_totals /api/reports/publisher "$PUB_COOKIE")

echo "[smoke_reports] Advertiser report: $adv_json"
echo "[smoke_reports] Publisher report: $pub_json"

python3 - "$adv_json" "$pub_json" <<'PY'
import json, sys
adv = json.loads(sys.argv[1])
pub = json.loads(sys.argv[2])

def check_non_negative(label, data):
    totals = data['totals']
    for key, value in totals.items():
        if value < 0:
            raise SystemExit(f"{label} total {key} is negative: {value}")

check_non_negative('advertiser', adv)
check_non_negative('publisher', pub)

adv_spend = adv['totals'].get('spend_micro', 0)
pub_earn = pub['totals'].get('earn_micro', 0)
if pub_earn > 0 and adv_spend == 0:
    raise SystemExit("Publisher earned funds while advertiser spend is zero.")
if adv_spend != pub_earn:
    raise SystemExit(f"Spend/Earn mismatch: advertiser spend={adv_spend}, publisher earn={pub_earn}")
PY

echo "[smoke_reports] Totals look good and conserved"
