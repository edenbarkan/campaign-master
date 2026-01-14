#!/usr/bin/env bash
set -euo pipefail

DEMO_SKIP_TESTS=${DEMO_SKIP_TESTS:-0}
DEMO_NO_OPEN=${DEMO_NO_OPEN:-0}
DEMO_OPEN_ALL=${DEMO_OPEN_ALL:-1}
: "${DEMO_PRINT_TOKENS:=1}"

BASE_URL="http://localhost:8081"
BUYER_URL="$BASE_URL/buyer/campaigns"
PARTNER_URL="$BASE_URL/partner/get-ad"
ADMIN_URL="$BASE_URL/admin/dashboard"

wait_for_db() {
  local start
  start=$(date +%s)

  while true; do
    if docker compose exec -T db pg_isready -U postgres -d campaign_master >/dev/null 2>&1; then
      echo "Database is ready."
      return
    fi
    if [ $(( $(date +%s) - start )) -ge 90 ]; then
      echo "Database readiness timed out." >&2
      return 1
    fi
    sleep 2
  done
}

wait_for_api() {
  local start
  start=$(date +%s)

  while true; do
    if curl -fsS "$BASE_URL/api/health" >/dev/null 2>&1; then
      echo "API is ready."
      return
    fi
    if [ $(( $(date +%s) - start )) -ge 90 ]; then
      echo "API readiness timed out." >&2
      return 1
    fi
    sleep 2
  done
}

open_url() {
  local url=$1
  if [ "$DEMO_NO_OPEN" = "1" ]; then
    return
  fi

  if command -v open >/dev/null 2>&1; then
    open "$url" >/dev/null 2>&1 &
  elif command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$url" >/dev/null 2>&1 &
  elif command -v powershell.exe >/dev/null 2>&1; then
    powershell.exe Start-Process "$url" >/dev/null 2>&1 &
  fi
}

auth_token() {
  local email=$1
  local password=$2

  local response
  response=$(curl -fsS -X POST "$BASE_URL/api/auth/login" \
    -H 'Content-Type: application/json' \
    -d "{\"email\":\"$email\",\"password\":\"$password\"}")

  if command -v jq >/dev/null 2>&1; then
    echo "$response" | jq -r '.access_token'
  else
    echo "$response" | python3 - <<'PY'
import json
import sys
payload = json.load(sys.stdin)
print(payload.get("access_token", ""))
PY
  fi
}

print_tokens() {
  if [ "$DEMO_PRINT_TOKENS" = "1" ]; then
    local buyer_token
    local partner_token
    local admin_token

    buyer_token=$(auth_token "buyer@demo.com" "buyerpass")
    partner_token=$(auth_token "partner@demo.com" "partnerpass")
    admin_token=$(auth_token "admin@demo.com" "adminpass")

    echo "BUYER_TOKEN=$buyer_token"
    echo "PARTNER_TOKEN=$partner_token"
    echo "ADMIN_TOKEN=$admin_token"
  fi
}

main() {
  echo "Resetting volumes..."
  docker compose down -v

  echo "Building and starting services..."
  docker compose up -d --build

  wait_for_db
  wait_for_api

  echo "Seeding demo data..."
  docker compose exec -T backend python -m app.seed

  if [ "$DEMO_SKIP_TESTS" != "1" ]; then
    echo "Running backend tests..."
    docker compose exec -T backend pytest -q
  else
    echo "Skipping tests (DEMO_SKIP_TESTS=1)."
  fi

  echo ""
  echo "Demo URLs:"
  echo "Base URL:   $BASE_URL"
  echo "Buyer:      $BUYER_URL"
  echo "Partner:    $PARTNER_URL"
  echo "Admin:      $ADMIN_URL"
  echo ""
  echo "Demo credentials:"
  echo "buyer@demo.com / buyerpass"
  echo "partner@demo.com / partnerpass"
  echo "admin@demo.com / adminpass"
  echo ""

  print_tokens

  if [ "$DEMO_NO_OPEN" != "1" ]; then
    if [ "$DEMO_OPEN_ALL" = "0" ]; then
      open_url "$BASE_URL"
    else
      open_url "$BUYER_URL"
      open_url "$PARTNER_URL"
      open_url "$ADMIN_URL"
    fi
  fi
}

main "$@"
