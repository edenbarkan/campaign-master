#!/usr/bin/env bash
set -euo pipefail

BASE_URL=${BASE_URL:-http://localhost:8081}
SMOKE_SKIP_DEMO=${SMOKE_SKIP_DEMO:-0}

if [ "$SMOKE_SKIP_DEMO" != "1" ]; then
  make demo
fi

PYTHON_BIN=python
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN=python3
fi

has_jq() {
  command -v jq >/dev/null 2>&1
}

json_get() {
  local expr=$1
  if has_jq; then
    jq -r "$expr"
  else
    "$PYTHON_BIN" - "$expr" <<'PY'
import json
import sys

expr = sys.argv[1]
expr = expr.lstrip(".")
parts = expr.split(".") if expr else []

data = json.load(sys.stdin)
current = data
for part in parts:
    if part.endswith("]"):
        name, rest = part.split("[", 1)
        if name:
            current = current.get(name)
        idx = int(rest[:-1])
        current = current[idx]
    else:
        current = current.get(part)
print("" if current is None else current)
PY
  fi
}

cleanup_files=()
cleanup() {
  for file in "${cleanup_files[@]}"; do
    rm -f "$file"
  done
}
trap cleanup EXIT

buyer_login=$(curl -fsS -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"buyer@demo.com","password":"buyerpass"}')
buyer_token=$(echo "$buyer_login" | json_get '.access_token')

partner_login=$(curl -fsS -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"partner@demo.com","password":"partnerpass"}')
partner_token=$(echo "$partner_login" | json_get '.access_token')

admin_login=$(curl -fsS -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@demo.com","password":"adminpass"}')
admin_token=$(echo "$admin_login" | json_get '.access_token')

campaigns_json=$(curl -fsS "$BASE_URL/api/buyer/campaigns?limit=1" \
  -H "Authorization: Bearer $buyer_token")
max_cpc=$(echo "$campaigns_json" | json_get '.campaigns[0].max_cpc')
partner_payout=$(echo "$campaigns_json" | json_get '.campaigns[0].partner_payout')

if [ -z "$max_cpc" ] || [ -z "$partner_payout" ]; then
  echo "Missing campaign pricing values." >&2
  exit 1
fi

buyer_before=$(mktemp)
partner_before=$(mktemp)
buyer_after=$(mktemp)
partner_after=$(mktemp)
risk_summary=$(mktemp)
cleanup_files+=("$buyer_before" "$partner_before" "$buyer_after" "$partner_after" "$risk_summary")

curl -fsS "$BASE_URL/api/buyer/analytics/summary" \
  -H "Authorization: Bearer $buyer_token" > "$buyer_before"

curl -fsS "$BASE_URL/api/partner/analytics/summary" \
  -H "Authorization: Bearer $partner_token" > "$partner_before"

ad_json=$(curl -fsS "$BASE_URL/api/partner/ad" -H "Authorization: Bearer $partner_token")
assignment_code=$(echo "$ad_json" | json_get '.assignment_code')
tracking_path=$(echo "$ad_json" | json_get '.tracking_url')
tracking_url="$BASE_URL$tracking_path"

if [ -z "$assignment_code" ] || [ -z "$tracking_path" ]; then
  echo "Missing assignment data from partner ad request." >&2
  exit 1
fi

headers=("-H" "User-Agent: smoke-agent" "-H" "X-Forwarded-For: 203.0.113.10")

curl -fsS -X POST "$BASE_URL/api/track/impression?code=$assignment_code" "${headers[@]}" >/dev/null

curl -fsS -o /dev/null "$tracking_url" "${headers[@]}" >/dev/null
curl -fsS -o /dev/null "$tracking_url" "${headers[@]}" >/dev/null

curl -fsS "$BASE_URL/api/buyer/analytics/summary" \
  -H "Authorization: Bearer $buyer_token" > "$buyer_after"

curl -fsS "$BASE_URL/api/partner/analytics/summary" \
  -H "Authorization: Bearer $partner_token" > "$partner_after"

curl -fsS "$BASE_URL/api/admin/risk/summary" \
  -H "Authorization: Bearer $admin_token" > "$risk_summary"

export MAX_CPC="$max_cpc"
export PARTNER_PAYOUT="$partner_payout"
export BUYER_BEFORE_FILE="$buyer_before"
export BUYER_AFTER_FILE="$buyer_after"
export PARTNER_BEFORE_FILE="$partner_before"
export PARTNER_AFTER_FILE="$partner_after"
export RISK_FILE="$risk_summary"

"$PYTHON_BIN" - <<'PY'
import json
import math
import os
import sys

max_cpc = float(os.environ["MAX_CPC"])
partner_payout = float(os.environ["PARTNER_PAYOUT"])

with open(os.environ["BUYER_BEFORE_FILE"], "r", encoding="utf-8") as handle:
    buyer_before = json.load(handle)
with open(os.environ["BUYER_AFTER_FILE"], "r", encoding="utf-8") as handle:
    buyer_after = json.load(handle)
with open(os.environ["PARTNER_BEFORE_FILE"], "r", encoding="utf-8") as handle:
    partner_before = json.load(handle)
with open(os.environ["PARTNER_AFTER_FILE"], "r", encoding="utf-8") as handle:
    partner_after = json.load(handle)
with open(os.environ["RISK_FILE"], "r", encoding="utf-8") as handle:
    risk = json.load(handle)

spend_before = float(buyer_before["totals"]["spend"])
spend_after = float(buyer_after["totals"]["spend"])
spend_delta = spend_after - spend_before

earn_before = float(partner_before["totals"]["earnings"])
earn_after = float(partner_after["totals"]["earnings"])
earn_delta = earn_after - earn_before

if not math.isclose(spend_delta, max_cpc, abs_tol=0.01):
    print(f"FAIL spend delta {spend_delta} != {max_cpc}")
    sys.exit(1)

if not math.isclose(earn_delta, partner_payout, abs_tol=0.01):
    print(f"FAIL earnings delta {earn_delta} != {partner_payout}")
    sys.exit(1)

rejected = risk.get("totals", {}).get("rejected", 0)
if rejected < 1:
    print("FAIL: no rejected clicks recorded in risk summary")
    sys.exit(1)

reasons = {item.get("reason") for item in risk.get("top_reasons", [])}
if "DUPLICATE_CLICK" not in reasons:
    print("FAIL: DUPLICATE_CLICK not found in top reasons")
    sys.exit(1)

print("PASSED: smoke demo validations")
PY
