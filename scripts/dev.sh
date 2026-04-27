#!/usr/bin/env bash
# Dev runner — starts the sidecar on a fixed port and the Vite dev server.
# The Vite server proxies /api/* to the sidecar and opens the browser itself.
#
# Usage:
#   ./scripts/dev.sh              # default dev port 8765
#   SIDECAR_PORT=9000 ./scripts/dev.sh

set -euo pipefail
cd "$(dirname "$0")/.."

SIDECAR_PORT=${SIDECAR_PORT:-8765}

if [ ! -d ".venv" ]; then
  echo "No .venv found. Run: uv venv && uv pip install -e '.[dev]'" >&2
  exit 1
fi

if [ ! -d "ui/node_modules" ]; then
  echo "No ui/node_modules. Run: cd ui && npm install" >&2
  exit 1
fi

echo "Starting sidecar on port $SIDECAR_PORT ..."
.venv/bin/python -m attune_gui.main --reload --port "$SIDECAR_PORT" &
SIDECAR_PID=$!
trap "kill $SIDECAR_PID 2>/dev/null; exit" INT TERM EXIT

# Give uvicorn a moment to bind the port
sleep 1

echo "Starting Vite dev server (proxying /api -> 127.0.0.1:$SIDECAR_PORT) ..."
SIDECAR_PORT=$SIDECAR_PORT npm --prefix ui run dev

wait $SIDECAR_PID
