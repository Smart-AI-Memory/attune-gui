"""Localhost-only guards for the sidecar.

The sidecar is intended to run on 127.0.0.1 and serve a single user
on the same machine. Defense in depth:

1. Bind to 127.0.0.1 in uvicorn config (not here — see main.py).
2. Reject requests whose Origin header isn't in the allowlist (CSRF).
3. Require a per-session X-Attune-Client header on mutating requests.

The token lives in-memory for the sidecar's lifetime. The UI reads it
once at page load from /api/session/token and echoes it on subsequent
requests. This blocks drive-by fetches from random tabs that don't
know the token.

Not a security story for multi-user or network-exposed deployment —
those are explicit non-goals.
"""

from __future__ import annotations

import secrets

from fastapi import Header, HTTPException
from starlette.requests import HTTPConnection

# Generated once per process start. A new sidecar run invalidates old
# tokens, which is fine — the UI reloads and picks up the new one.
_SESSION_TOKEN = secrets.token_urlsafe(32)

# Origins allowed to talk to us. localhost and 127.0.0.1 at any port
# covers dev servers (vite, file://, direct ports) without opening us
# to the public web.
_ALLOWED_ORIGIN_HOSTS = frozenset({"localhost", "127.0.0.1", "[::1]"})


def current_session_token() -> str:
    """Return the in-process session token (exposed via /api/session/token)."""
    return _SESSION_TOKEN


def require_client_token(
    x_attune_client: str | None = Header(default=None),
) -> None:
    """Raise 403 if the X-Attune-Client header doesn't match the session token.

    Used as a FastAPI Depends() on any mutating route.
    """
    if x_attune_client != _SESSION_TOKEN:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "invalid_client",
                "message": "Missing or invalid X-Attune-Client header.",
            },
        )


async def origin_guard(connection: HTTPConnection) -> None:
    """Reject requests whose Origin isn't a localhost form.

    Accepts either an HTTP ``Request`` or a ``WebSocket`` (both are
    ``HTTPConnection`` subclasses), so the same dependency works for
    JSON routes and the editor's WebSocket route.

    Requests with no Origin header (e.g., curl, server-to-server calls
    from uvicorn tooling, uvicorn's own health probes) are allowed —
    the real guard is binding to 127.0.0.1. Origin checking is about
    browser drive-by protection.
    """
    origin = connection.headers.get("origin")
    if origin is None:
        return

    # Origin is like "http://localhost:5173" — parse the host out.
    try:
        host = origin.split("://", 1)[1].split("/", 1)[0].split(":", 1)[0]
    except IndexError:
        raise HTTPException(
            status_code=403,
            detail={"code": "bad_origin", "message": f"Malformed Origin: {origin!r}"},
        ) from None

    if host not in _ALLOWED_ORIGIN_HOSTS:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "bad_origin",
                "message": f"Origin {origin!r} is not on the localhost allowlist.",
            },
        )
