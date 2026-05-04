"""Sidecar portfile + freshness validation (template-editor M2 task #8).

The portfile lives at ``~/.attune/sidecar.port`` and contains
``{pid, port, token}`` describing the currently-running attune-gui
sidecar. The CLI in attune-author reads it to find a sidecar to talk
to, then validates with a ``/healthz?token=...`` request before
trusting the file. Stale portfiles (PID dead or wrong token) cause the
CLI to spawn a fresh sidecar and overwrite the file.

Public API:

- :func:`write_portfile`, :func:`read_portfile`, :func:`delete_portfile`
- :func:`is_pid_alive`, :func:`is_portfile_stale`
- :func:`portfile_context` — wrap a sidecar run

The ``/healthz`` route lives in :mod:`attune_gui.routes.editor_health`.
"""

from __future__ import annotations

import contextlib
import json
import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

_PORTFILE_PATH = Path.home() / ".attune" / "sidecar.port"


@dataclass(frozen=True)
class PortfileData:
    pid: int
    port: int
    token: str


# -- IO -------------------------------------------------------------


def write_portfile(pid: int, port: int, token: str) -> None:
    """Write ``{pid, port, token}`` to the portfile (overwriting)."""
    _PORTFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"pid": pid, "port": port, "token": token}
    _PORTFILE_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def read_portfile() -> PortfileData | None:
    """Return the parsed portfile or ``None`` if missing/corrupt."""
    try:
        raw = _PORTFILE_PATH.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    try:
        return PortfileData(
            pid=int(data["pid"]),
            port=int(data["port"]),
            token=str(data["token"]),
        )
    except (KeyError, TypeError, ValueError):
        return None


def delete_portfile() -> None:
    """Remove the portfile if it exists. No-op when absent."""
    try:
        _PORTFILE_PATH.unlink()
    except FileNotFoundError:
        pass


# -- freshness ------------------------------------------------------


def is_pid_alive(pid: int) -> bool:
    """Return True if a process with ``pid`` is currently running.

    Uses ``os.kill(pid, 0)`` which doesn't actually signal — it just
    raises if the process is dead. Cross-platform on POSIX; on Windows
    ``os.kill`` raises a :class:`PermissionError` for live processes
    we don't own, which we treat as alive.
    """
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def is_portfile_stale() -> bool:
    """Return True if no fresh sidecar is reachable via the portfile.

    Stale conditions: file missing, file corrupt, recorded PID dead.
    Token mismatch is *not* checked here — that requires a
    ``/healthz`` round-trip the CLI does separately.
    """
    data = read_portfile()
    if data is None:
        return True
    if not is_pid_alive(data.pid):
        return True
    return False


# -- lifecycle helper ----------------------------------------------


@contextlib.contextmanager
def portfile_context(port: int, token: str) -> Iterator[PortfileData]:
    """Write the portfile on enter, remove on exit. Always cleans up."""
    pid = os.getpid()
    write_portfile(pid=pid, port=port, token=token)
    try:
        yield PortfileData(pid=pid, port=port, token=token)
    finally:
        delete_portfile()
