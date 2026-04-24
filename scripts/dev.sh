#!/usr/bin/env bash
# Dev runner — start the sidecar, capture the SIDECAR_URL line, open the browser.
# The sidecar picks a free port itself and prints SIDECAR_URL=... on the first
# stdout line. This script reads that line and opens it.

set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -d ".venv" ]; then
  echo "No .venv found. Run: uv venv && uv pip install -e '.[dev,ai]'" >&2
  exit 1
fi

# Start uvicorn with --reload for auto-restart on code edits.
# Pipe stdout through awk so we see the URL line but let the rest of uvicorn's
# output flow through normally.
.venv/bin/python -m attune_gui.main --reload "$@" 2>&1 | \
  awk 'BEGIN{opened=0}
       /^SIDECAR_URL=/ && !opened {
         url=$0; sub("^SIDECAR_URL=", "", url);
         print "Opening " url " ..."; opened=1;
         system("(sleep 0.7 && open \"" url "\") &");
       }
       {print}'
