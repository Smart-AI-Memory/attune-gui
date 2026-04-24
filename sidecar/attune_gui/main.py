"""Entry point: `attune-gui` runs uvicorn bound to 127.0.0.1 on a chosen/free port.

Prints `SIDECAR_URL=http://127.0.0.1:<port>` on stdout as the first line after
startup so a supervising process (Tauri later, or a shell script now) can
discover the URL reliably.
"""

from __future__ import annotations

import argparse
import logging
import socket
import sys
import webbrowser

import uvicorn

logger = logging.getLogger(__name__)


def _pick_free_port() -> int:
    """Ask the kernel for an unused port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


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
