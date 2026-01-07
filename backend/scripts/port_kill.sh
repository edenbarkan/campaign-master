#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <port>" >&2
  exit 1
fi

PORT="$1"
PIDS=$(lsof -ti tcp:"${PORT}" || true)

if [[ -z "${PIDS}" ]]; then
  echo "port ${PORT} free"
  exit 0
fi

echo "Killing processes on port ${PORT}: ${PIDS}"
kill ${PIDS}
echo "port ${PORT} cleared"
