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
                # Treat empty/whitespace-only values in os.environ as "unset"
                # so a stray `export FOO=` in the shell doesn't shadow .env.
                if key and not os.environ.get(key, "").strip():
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

    sub = p.add_subparsers(dest="command")

    config_p = sub.add_parser(
        "config",
        help="Show or modify ~/.attune-gui/config.json (workspace, corpora_registry, specs_root).",
    )
    config_sub = config_p.add_subparsers(dest="config_action", required=True)
    config_sub.add_parser("list", help="Print all keys with their resolved value and source.")
    get_p = config_sub.add_parser("get", help="Print the resolved value for a single key.")
    get_p.add_argument("key")
    set_p = config_sub.add_parser("set", help="Persist a value to the config file.")
    set_p.add_argument("key")
    set_p.add_argument("value")
    unset_p = config_sub.add_parser("unset", help="Remove a key from the config file.")
    unset_p.add_argument("key")

    return p


def _config_command(args: argparse.Namespace) -> int:
    """Handle ``attune-gui config <action>``. Returns process exit code."""
    from attune_gui import config  # noqa: PLC0415

    action = args.config_action
    if action == "list":
        for key in config.known_keys():
            value = config.get(key)
            source = config.get_source(key)
            display = value if value is not None else "<unset>"
            print(f"{key} = {display}  ({source}; env={config.env_var_for(key)})")
        return 0

    if action == "get":
        if not config.is_valid_key(args.key):
            print(
                f"unknown key: {args.key!r}. valid: {', '.join(config.known_keys())}",
                file=sys.stderr,
            )
            return 2
        value = config.get(args.key)
        if value is None:
            return 1
        print(value)
        return 0

    if action == "set":
        if not config.is_valid_key(args.key):
            print(
                f"unknown key: {args.key!r}. valid: {', '.join(config.known_keys())}",
                file=sys.stderr,
            )
            return 2
        if args.key == "workspace":
            # workspace carries directory-existence validation; route through it
            from attune_gui.workspace import set_workspace  # noqa: PLC0415

            try:
                resolved = set_workspace(args.value)
            except ValueError as exc:
                print(str(exc), file=sys.stderr)
                return 1
            print(f"workspace = {resolved}")
            return 0
        config.set_value(args.key, args.value)
        print(f"{args.key} = {args.value}")
        return 0

    if action == "unset":
        if not config.is_valid_key(args.key):
            print(
                f"unknown key: {args.key!r}. valid: {', '.join(config.known_keys())}",
                file=sys.stderr,
            )
            return 2
        removed = config.unset_value(args.key)
        print(f"removed {args.key}" if removed else f"{args.key} was not set")
        return 0

    return 2


def main(argv: list[str] | None = None) -> int:
    """CLI entry point: parse args, pick a port, print SIDECAR_URL, run uvicorn."""
    args = _build_parser().parse_args(argv)

    if args.command == "config":
        return _config_command(args)

    _load_dotenv()

    port = args.port or _pick_free_port()
    url = f"http://127.0.0.1:{port}"

    # Announce the URL as the very first stdout line. Consumers (Tauri,
    # scripts/dev.sh) read from here to know where to point browsers.
    print(f"SIDECAR_URL={url}", flush=True)

    if args.open:
        webbrowser.open(url)

    # Write the portfile so attune-author's `edit` CLI can find this
    # sidecar via ~/.attune/sidecar.port. Cleaned up on shutdown.
    from attune_gui.editor_sidecar import portfile_context  # noqa: PLC0415
    from attune_gui.security import current_session_token  # noqa: PLC0415

    with portfile_context(port=port, token=current_session_token()):
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
