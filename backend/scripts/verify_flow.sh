#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:5000}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TMP_DIR="$(mktemp -d)"
TMP_DIR_ROOT="${BACKEND_DIR}/tmp"
mkdir -p "$TMP_DIR_ROOT"
ENV_FILE="${TMP_DIR_ROOT}/last_users.env"
trap 'rm -rf "$TMP_DIR"' EXIT

ADV_COOKIE="$TMP_DIR/adv.cookies"
PUB_COOKIE="$TMP_DIR/pub.cookies"

log() {
  echo "[verify] $*"
}

fail() {
  echo "[verify][error] $*" >&2
  exit 1
}

api_call() {
  local method=$1
  local url=$2
  local data=${3-}
  local cookie=${4-}
  local body_file
  body_file=$(mktemp "$TMP_DIR/body.XXXX")
  local args=(-sS -w '%{http_code}' -o "$body_file" -X "$method")
  if [[ -n ${cookie:-} ]]; then
    args+=(-b "$cookie" -c "$cookie")
  fi
  if [[ -n ${data:-} ]]; then
    args+=(-H 'Content-Type: application/json' -d "$data")
  fi
  args+=("$url")
  API_STATUS=$(curl "${args[@]}" || true)
  API_BODY_FILE="$body_file"
  API_BODY="$(cat "$body_file")"
}

write_env_file() {
  local mode=${1:-intermediate}
  local temp_env="${ENV_FILE}.tmp"
  {
    printf "BASE_URL='%s'\n" "$BASE_URL"
    printf "ADV_EMAIL='%s'\n" "$adv_email"
    printf "PUB_EMAIL='%s'\n" "$pub_email"
    printf "PASSWORD='%s'\n" "$password"
    printf "DB_URL='%s'\n" "${DATABASE_URL:-}"
  } > "$temp_env"
  mv "$temp_env" "$ENV_FILE"
  if [[ $mode == "final" ]]; then
    echo "Credentials written to $ENV_FILE"
  else
    log "Credentials saved to $ENV_FILE"
  fi
}

json_extract_file() {
  local file=$1
  local path=$2
  python3 - "$file" "$path" <<'PY'
import json, sys
filename, path = sys.argv[1], sys.argv[2].split('.')
with open(filename) as f:
    data = json.load(f)
for key in path:
    data = data[key]
print(data)
PY
}

timestamp="$(date +%s)"
password="Pass1234!"
adv_email="adv_${timestamp}@example.com"
pub_email="pub_${timestamp}@example.com"
floor_cpm=900000
floor_cpc=600000
bid_cpm=$floor_cpm
bid_cpc=$floor_cpc
impression_cost_est=$((floor_cpm / 1000))
if (( impression_cost_est < 1 )); then
  impression_cost_est=1
fi
required_micro_est=$((impression_cost_est + floor_cpc))
topup_amount=$((required_micro_est + 2000000))

log "Registering advertiser $adv_email"
api_call POST "$BASE_URL/api/auth/register" "{\"email\":\"$adv_email\",\"password\":\"$password\",\"is_advertiser\":true,\"is_publisher\":false}"
[[ $API_STATUS == 201 ]] || fail "Advertiser registration failed ($API_STATUS): $API_BODY"

log "Registering publisher $pub_email"
api_call POST "$BASE_URL/api/auth/register" "{\"email\":\"$pub_email\",\"password\":\"$password\",\"is_advertiser\":false,\"is_publisher\":true}"
[[ $API_STATUS == 201 ]] || fail "Publisher registration failed ($API_STATUS): $API_BODY"
write_env_file intermediate

log "Logging in advertiser"
api_call POST "$BASE_URL/api/auth/login" "{\"email\":\"$adv_email\",\"password\":\"$password\"}" "$ADV_COOKIE"
[[ $API_STATUS == 200 ]] || fail "Advertiser login failed ($API_STATUS): $API_BODY"

topup_amount=2000000
log "Topping up advertiser wallet by ${topup_amount}"
api_call POST "$BASE_URL/api/wallet/topup" "{\"amount_micro\":$topup_amount}" "$ADV_COOKIE"
[[ $API_STATUS == 200 ]] || fail "Wallet topup failed ($API_STATUS): $API_BODY"

log "Creating active campaign"
campaign_payload=$(cat <<JSON
{"name":"Sprint6 Campaign $timestamp","status":"active","bid_cpm_micro":$bid_cpm,"bid_cpc_micro":$bid_cpc}
JSON
)
api_call POST "$BASE_URL/api/advertiser/campaigns" "$campaign_payload" "$ADV_COOKIE"
[[ $API_STATUS == 201 ]] || fail "Campaign creation failed ($API_STATUS): $API_BODY"
campaign_id=$(json_extract_file "$API_BODY_FILE" 'campaign.id')

log "Creating active ad"
ad_payload=$(cat <<JSON
{"title":"Banner $timestamp","image_url":"https://via.placeholder.com/300x250.png","landing_url":"https://example.com/landing","status":"active"}
JSON
)
api_call POST "$BASE_URL/api/advertiser/campaigns/$campaign_id/ads" "$ad_payload" "$ADV_COOKIE"
[[ $API_STATUS == 201 ]] || fail "Ad creation failed ($API_STATUS): $API_BODY"
ad_id=$(json_extract_file "$API_BODY_FILE" 'ad.id')

log "Logging in publisher"
api_call POST "$BASE_URL/api/auth/login" "{\"email\":\"$pub_email\",\"password\":\"$password\"}" "$PUB_COOKIE"
[[ $API_STATUS == 200 ]] || fail "Publisher login failed ($API_STATUS): $API_BODY"

log "Creating publisher site"
site_payload=$(cat <<JSON
{"name":"Site $timestamp","domain":"site$timestamp.example.com"}
JSON
)
api_call POST "$BASE_URL/api/publisher/sites" "$site_payload" "$PUB_COOKIE"
[[ $API_STATUS == 201 ]] || fail "Site creation failed ($API_STATUS): $API_BODY"
site_id=$(json_extract_file "$API_BODY_FILE" 'site.id')

log "Creating slot with CPM $floor_cpm and CPC $floor_cpc"
slot_payload=$(cat <<JSON
{"name":"Slot $timestamp","width":300,"height":250,"floor_cpm_micro":$floor_cpm,"floor_cpc_micro":$floor_cpc,"status":"active"}
JSON
)
api_call POST "$BASE_URL/api/publisher/sites/$site_id/slots" "$slot_payload" "$PUB_COOKIE"
[[ $API_STATUS == 201 ]] || fail "Slot creation failed ($API_STATUS): $API_BODY"
slot_id=$(json_extract_file "$API_BODY_FILE" 'slot.id')

log "Requesting adserve for slot $slot_id"
api_call GET "$BASE_URL/api/adserve?slot_id=$slot_id"
if [[ $API_STATUS == 204 ]]; then
  echo "------ Adserve Debug ------" >&2
  echo "Slot ID: $slot_id" >&2
  echo "Slot floors: CPM=$floor_cpm, CPC=$floor_cpc" >&2
  echo "Campaign ID: $campaign_id, Bid CPM=$bid_cpm, Bid CPC=$bid_cpc" >&2
  echo "Ad ID: ${ad_id:-unknown}" >&2
  echo "Adserve response body: $(cat "$API_BODY_FILE")" >&2
  fail "Adserve returned 204 (no eligible ads)"
fi
[[ $API_STATUS == 200 ]] || fail "Adserve did not return creative (HTTP $API_STATUS)"
request_id=$(printf '%s' "$API_BODY" | grep -Eo 'request_id=[0-9a-f-]+' | head -n1 | cut -d= -f2)
[[ -n $request_id ]] || fail "Could not parse request_id from adserve response"
log "Received request_id=$request_id"

log "Capturing wallet state before tracking"
api_call GET "$BASE_URL/api/wallet" "" "$ADV_COOKIE"
[[ $API_STATUS == 200 ]] || fail "Failed to fetch advertiser wallet ($API_STATUS)"
adv_balance_before=$(json_extract_file "$API_BODY_FILE" 'wallet.balance_micro')
adv_reserved_before=$(json_extract_file "$API_BODY_FILE" 'wallet.reserved_micro')

api_call GET "$BASE_URL/api/wallet" "" "$PUB_COOKIE"
[[ $API_STATUS == 200 ]] || fail "Failed to fetch publisher wallet ($API_STATUS)"
pub_balance_before=$(json_extract_file "$API_BODY_FILE" 'wallet.balance_micro')

log "Tracking impression (1st call)"
api_call GET "$BASE_URL/api/track/impression?request_id=$request_id"
[[ $API_STATUS == 204 ]] || fail "Impression tracking failed ($API_STATUS): $(cat "$API_BODY_FILE")"

log "Tracking impression again (idempotent)"
api_call GET "$BASE_URL/api/track/impression?request_id=$request_id"
[[ $API_STATUS == 204 ]] || fail "Second impression call unexpected status ($API_STATUS): $(cat "$API_BODY_FILE")"

log "Tracking click (1st call)"
click_headers="$TMP_DIR/click_headers.txt"
http_code=$(curl -sS -D "$click_headers" -o /dev/null -w '%{http_code}' "$BASE_URL/api/track/click?request_id=$request_id")
[[ $http_code == 302 ]] || fail "Click tracking expected 302, got $http_code"
landing_location=$(grep -i '^Location:' "$click_headers" | head -n1 | cut -d' ' -f2- | tr -d '\r')
[[ -n $landing_location ]] || fail "Click tracking response missing Location header"

log "Tracking click again (idempotent)"
http_code=$(curl -sS -D "$click_headers" -o /dev/null -w '%{http_code}' "$BASE_URL/api/track/click?request_id=$request_id")
[[ $http_code == 302 ]] || fail "Second click tracking expected 302, got $http_code"

log "Capturing wallet state after tracking"
api_call GET "$BASE_URL/api/wallet" "" "$ADV_COOKIE"
[[ $API_STATUS == 200 ]] || fail "Failed to fetch final advertiser wallet ($API_STATUS)"
adv_balance_after=$(json_extract_file "$API_BODY_FILE" 'wallet.balance_micro')
adv_reserved_after=$(json_extract_file "$API_BODY_FILE" 'wallet.reserved_micro')

api_call GET "$BASE_URL/api/wallet" "" "$PUB_COOKIE"
[[ $API_STATUS == 200 ]] || fail "Failed to fetch final publisher wallet ($API_STATUS)"
pub_balance_after=$(json_extract_file "$API_BODY_FILE" 'wallet.balance_micro')

adv_balance_delta=$((adv_balance_after - adv_balance_before))
adv_reserved_delta=$((adv_reserved_after - adv_reserved_before))
pub_balance_delta=$((pub_balance_after - pub_balance_before))

echo "------ Wallet impact ------"
echo "Advertiser balance delta: ${adv_balance_delta}"
echo "Advertiser reserved delta: ${adv_reserved_delta}"
echo "Publisher balance delta: ${pub_balance_delta}"
echo "Landing URL: ${landing_location}"
echo "Verification complete."

log "Fetching advertiser totals"
api_call GET "$BASE_URL/api/reports/advertiser" "" "$ADV_COOKIE"
[[ $API_STATUS == 200 ]] || fail "Advertiser report fetch failed ($API_STATUS)"
adv_spend_total=$(json_extract_file "$API_BODY_FILE" 'totals.spend_micro')

log "Fetching publisher totals"
api_call GET "$BASE_URL/api/reports/publisher" "" "$PUB_COOKIE"
[[ $API_STATUS == 200 ]] || fail "Publisher report fetch failed ($API_STATUS)"
pub_earn_total=$(json_extract_file "$API_BODY_FILE" 'totals.earn_micro')

echo "Advertiser spend total: $adv_spend_total"
echo "Publisher earn total: $pub_earn_total"
if [[ $adv_spend_total -ne $pub_earn_total ]]; then
  fail "Spend/Earn mismatch (advertiser=$adv_spend_total, publisher=$pub_earn_total)"
fi

write_env_file final
