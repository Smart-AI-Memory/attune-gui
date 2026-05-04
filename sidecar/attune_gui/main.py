"""Entry point: `attune-gui` runs uvicorn bound to 127.0.0.1 on a chosen/free port.

Prints `SIDECAR_URL=http://127.0.0.1:<port>` on stdout as the first line after
startup so a supervising process (Tauri later, or a shell script now) can
discover the URL reliably.
"""

from __future__ import annotations

import argparse
import logging
import os
import socket
import sys
import webbrowser
from pathlib import Path

import uvicorn

logger = logging.getLogger(__name__)


def _pick_free_port() -> int:
    """Ask the kernel for an unused port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _load_dotenv() -> None:
    """Load ``KEY=value`` lines from a local ``.env`` so jobs that need
    ``ANTHROPIC_API_KEY`` (etc.) work without exporting them in the shell.

    Search order, first hit wins (lower-precedence files do not overwrite):
      1. ``./.env`` in the current working directory
      2. ``<repo-root>/.env`` (two parents above this file)
      3. ``~/.attune-gui/.env``
      4. ``~/.attune/.env``

    Existing environment variables are never overwritten.
    """
    repo_root = Path(__file__).resolve().parents[2]
    candidates = [
        Path.cwd() / ".env",
        repo_root / ".env",
        Path.home() / ".attune-gui" / ".env",
        Path.home() / ".attune" / ".env",
    ]
    seen: set[Path] = set()
    for path in candidates:
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if resolved in seen or not resolved.is_file():
            continue
        seen.add(resolved)
        try:
            for raw_line in resolved.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                if line.startswith("export "):
                    line = line[len("export ") :].lstrip()
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
        except OSError:
            continue


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run the attune-gui sidecar on 127.0.0.1.")
    p.add_argument("--port", type=int, default=None, help="Port (default: auto-pick a free one).")
    p.add_argument(
        "--open", action="store_true", help="Open the UI in the default browser after startup."
    )
    p.add_argument("--reload", action="store_true", help="Enable uvicorn auto-reload (dev only).")
    p.add_argument(
        "--log-level", default="info", choices=["critical", "error", "warning", "info", "debug"]
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    _load_dotenv()

    port = args.port or _pick_free_port()
    url = f"http://127.0.0.1:{port}"

    # Announce the URL as the very first stdout line. Consumers (Tauri,
    # scripts/dev.sh) read from here to know where to point browsers.
    print(f"SIDECAR_URL={url}", flush=True)

    if args.open:
        webbrowser.open(url)

    uvicorn.run(
        "attune_gui.app:create_app",
        factory=True,
        host="127.0.0.1",
        port=port,
        reload=args.reload,
        log_level=args.log_level,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
