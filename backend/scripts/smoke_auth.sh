#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:5001}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

COOKIE_FILE="$TMP_DIR/auth.cookies"
EMAIL="smoke_$RANDOM$RANDOM@example.com"
PASSWORD="SmokePass123!"

log() {
  echo "[smoke_auth] $*"
}

call() {
  local method=$1
  local path=$2
  local body=${3-}
  local output
  if [[ -n $body ]]; then
    output=$(curl -sS -w "\n%{http_code}" -b "$COOKIE_FILE" -c "$COOKIE_FILE" -H 'Content-Type: application/json' -X "$method" -d "$body" "$BASE_URL$path")
  else
    output=$(curl -sS -w "\n%{http_code}" -b "$COOKIE_FILE" -c "$COOKIE_FILE" -X "$method" "$BASE_URL$path")
  fi
  local status=${output##*$'\n'}
  local body_json=${output%$'\n'*}
  echo "$body_json"
  echo "HTTP $status"
  return 0
}

log "Registering $EMAIL"
call POST /api/auth/register "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"is_advertiser\":true}"

log "Logging in"
call POST /api/auth/login "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}"

log "Fetching /me"
call GET /api/auth/me

log "Logging out"
call POST /api/auth/logout

log "Verifying session cleared"
call GET /api/auth/me || true
