#!/usr/bin/env bash
set -euo pipefail

BASE_URL=${BASE_URL:-http://localhost:8081}
VERIFY_SKIP_DEMO=${VERIFY_SKIP_DEMO:-0}

if [ "$VERIFY_SKIP_DEMO" != "1" ]; then
  MATCHING_DEBUG=1 FREQ_CAP_SECONDS=0 make demo
fi

has_jq() {
  command -v jq >/dev/null 2>&1
}

PYTHON_BIN=python
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN=python3
fi

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

unique_suffix=$(date +%s)

buyer_email="verify-buyer-$unique_suffix@example.com"
partner_email="verify-partner-$unique_suffix@example.com"
password="verifypass"

register() {
  local email=$1
  local role=$2
  curl -fsS -X POST "$BASE_URL/api/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$email\",\"password\":\"$password\",\"role\":\"$role\"}"
}

login() {
  local email=$1
  curl -fsS -X POST "$BASE_URL/api/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$email\",\"password\":\"$password\"}"
}

register "$buyer_email" "buyer" >/dev/null
register "$partner_email" "partner" >/dev/null

buyer_token=$(login "$buyer_email" | json_get '.access_token')
partner_token=$(login "$partner_email" | json_get '.access_token')

create_campaign() {
  local name=$1
  curl -fsS -X POST "$BASE_URL/api/buyer/campaigns" \
    -H "Authorization: Bearer $buyer_token" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"$name\",\"status\":\"active\",\"budget_total\":100,\"max_cpc\":2}"
}

create_ad() {
  local campaign_id=$1
  local title=$2
  curl -fsS -X POST "$BASE_URL/api/buyer/campaigns/$campaign_id/ads" \
    -H "Authorization: Bearer $buyer_token" \
    -H "Content-Type: application/json" \
    -d "{\"title\":\"$title\",\"body\":\"Body\",\"image_url\":\"https://example.com/ad.png\",\"destination_url\":\"https://example.com/landing\",\"active\":true}"
}

campaign_one=$(create_campaign "Verify Campaign 1")
campaign_one_id=$(echo "$campaign_one" | json_get '.campaign.id')
create_ad "$campaign_one_id" "Verify Ad 1" >/dev/null

campaign_two=$(create_campaign "Verify Campaign 2")
campaign_two_id=$(echo "$campaign_two" | json_get '.campaign.id')
create_ad "$campaign_two_id" "Verify Ad 2" >/dev/null

ad_response=$(curl -fsS "$BASE_URL/api/partner/ad" -H "Authorization: Bearer $partner_token")
filled=$(echo "$ad_response" | json_get '.filled')

if [ "$filled" != "true" ]; then
  echo "FAIL: Expected filled ad response." >&2
  echo "$ad_response" >&2
  exit 1
fi

candidates_count=$(echo "$ad_response" | json_get '.debug_candidates[0].ad_id')
if [ -z "$candidates_count" ]; then
  echo "FAIL: debug_candidates missing. Ensure MATCHING_DEBUG=1." >&2
  exit 1
fi

penalty_one=$(echo "$ad_response" | json_get '.debug_candidates[0].score_breakdown.partner_reject_penalty')
penalty_two=$(echo "$ad_response" | json_get '.debug_candidates[1].score_breakdown.partner_reject_penalty')
rate_initial=$(echo "$ad_response" | json_get '.score_breakdown.partner_reject_rate')
penalty_initial=$(echo "$ad_response" | json_get '.score_breakdown.partner_reject_penalty')
weight=$(echo "$ad_response" | json_get '.score_breakdown.partner_reject_penalty_weight')
tracking_path=$(echo "$ad_response" | json_get '.tracking_url')
tracking_url="$BASE_URL$tracking_path"

if [ "$penalty_one" != "$penalty_two" ]; then
  echo "FAIL: Penalty differs across candidates ($penalty_one vs $penalty_two)." >&2
  exit 1
fi

echo "Initial partner_reject_rate=$rate_initial"
echo "Initial partner_reject_penalty=$penalty_initial (weight=$weight)"

headers=("-H" "User-Agent: verify-agent" "-H" "X-Forwarded-For: 198.51.100.2")

curl -fsS -o /dev/null "$tracking_url" "${headers[@]}" >/dev/null
curl -fsS -o /dev/null "$tracking_url" "${headers[@]}" >/dev/null

ad_after=$(curl -fsS "$BASE_URL/api/partner/ad" -H "Authorization: Bearer $partner_token")
rate_after=$(echo "$ad_after" | json_get '.score_breakdown.partner_reject_rate')
penalty_after=$(echo "$ad_after" | json_get '.score_breakdown.partner_reject_penalty')

expected_rate="0.5"
expected_penalty=$(
  "$PYTHON_BIN" - <<PY
rate=float("$expected_rate")
weight=float("$weight")
print(rate*weight)
PY
)

echo "After rejection partner_reject_rate=$rate_after"
echo "After rejection partner_reject_penalty=$penalty_after"

echo "Expected rate=$expected_rate"
echo "Expected penalty=$expected_penalty"

"$PYTHON_BIN" - <<PY
import math
rate_after=float("$rate_after")
penalty_after=float("$penalty_after")
expected_rate=float("$expected_rate")
expected_penalty=float("$expected_penalty")

if not math.isclose(rate_after, expected_rate, rel_tol=0, abs_tol=1e-4):
    raise SystemExit("FAIL: partner_reject_rate did not update as expected.")
if not math.isclose(penalty_after, expected_penalty, rel_tol=0, abs_tol=1e-4):
    raise SystemExit("FAIL: partner_reject_penalty did not match expected.")
PY

echo "PASS: Reject penalty verification succeeded."
