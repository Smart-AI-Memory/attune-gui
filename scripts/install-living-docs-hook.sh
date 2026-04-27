#!/usr/bin/env bash
# Install a git post-commit hook that triggers a Living Docs scan.
#
# The hook POSTs to the attune-gui sidecar's webhook endpoint whenever
# a commit lands. The sidecar queues an async scan and returns immediately
# so the hook never blocks the commit.
#
# Usage (run from the repo you want to watch, not the attune-gui repo):
#   bash /path/to/attune-gui/scripts/install-living-docs-hook.sh
#   bash /path/to/attune-gui/scripts/install-living-docs-hook.sh --port 8742
#
# The sidecar port is written to .git/attune-gui-port on startup (see dev.sh).
# If that file isn't present, the hook falls back to the default port (8899)
# or uses the --port argument.

set -euo pipefail

PORT=8899
while [[ $# -gt 0 ]]; do
  case "$1" in
    --port) PORT="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

HOOK_DIR="$(git rev-parse --git-dir)/hooks"
HOOK_FILE="$HOOK_DIR/post-commit"

mkdir -p "$HOOK_DIR"

cat > "$HOOK_FILE" <<HOOK
#!/usr/bin/env bash
# attune-gui Living Docs — post-commit hook (auto-generated)
# Triggers a workspace scan after every commit.

SIDECAR_PORT="${PORT}"
PORT_FILE="\$(git rev-parse --git-dir)/attune-gui-port"
if [[ -f "\$PORT_FILE" ]]; then
  SIDECAR_PORT="\$(cat "\$PORT_FILE")"
fi

curl -s -o /dev/null -w "" \\
  -X POST \\
  "http://127.0.0.1:\${SIDECAR_PORT}/api/living-docs/webhook/git" \\
  --max-time 2 || true
HOOK

chmod +x "$HOOK_FILE"
echo "✓ Living Docs post-commit hook installed at $HOOK_FILE"
echo "  Sidecar port: $PORT (override with --port or via .git/attune-gui-port)"
