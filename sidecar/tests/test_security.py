"""Direct unit tests for sidecar/attune_gui/security.py.

Covers ``current_session_token``, ``require_client_token``, and the
``origin_guard`` middleware against the Origin allowlist. These checks
are exercised indirectly by route tests, but isolated tests keep the
contract visible and document the malformed-origin / missing-origin /
mismatched-token paths that route tests skip.
"""

from __future__ import annotations

import pytest
from attune_gui.security import (
    current_session_token,
    origin_guard,
    require_client_token,
)
from fastapi import HTTPException
from starlette.datastructures import Headers
from starlette.requests import HTTPConnection

# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------


def test_session_token_is_url_safe_and_stable() -> None:
    token = current_session_token()
    assert isinstance(token, str)
    assert len(token) >= 32
    # Stable for the process lifetime.
    assert current_session_token() == token


def test_require_client_token_accepts_matching_token() -> None:
    token = current_session_token()
    # Should not raise.
    require_client_token(x_attune_client=token)


def test_require_client_token_rejects_missing_header() -> None:
    with pytest.raises(HTTPException) as excinfo:
        require_client_token(x_attune_client=None)
    assert excinfo.value.status_code == 403
    assert excinfo.value.detail["code"] == "invalid_client"


def test_require_client_token_rejects_wrong_token() -> None:
    with pytest.raises(HTTPException) as excinfo:
        require_client_token(x_attune_client="not-the-token")
    assert excinfo.value.status_code == 403
    assert excinfo.value.detail["code"] == "invalid_client"


# ---------------------------------------------------------------------------
# origin_guard
# ---------------------------------------------------------------------------


def _connection(origin: str | None) -> HTTPConnection:
    """Build a minimal HTTPConnection scope with the given Origin header."""
    headers: list[tuple[bytes, bytes]] = []
    if origin is not None:
        headers.append((b"origin", origin.encode()))
    scope = {
        "type": "http",
        "headers": headers,
    }
    conn = HTTPConnection(scope=scope)
    # Force header property access to use the scope we built.
    assert isinstance(conn.headers, Headers)
    return conn


@pytest.mark.asyncio
async def test_origin_guard_allows_missing_origin() -> None:
    """No Origin header (curl, server-to-server) is allowed."""
    await origin_guard(_connection(None))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost:5173",
        "http://127.0.0.1:8000",
        "https://localhost",
    ],
)
async def test_origin_guard_allows_localhost_forms(origin: str) -> None:
    await origin_guard(_connection(origin))


@pytest.mark.asyncio
@pytest.mark.xfail(
    reason="Pre-existing bug: parser strips [::1] brackets; allowlist contains "
    "'[::1]' but parser yields '[' as the host. Tracked separately; fix in pass 3.",
    strict=True,
)
async def test_origin_guard_allows_ipv6_loopback() -> None:
    """Documents the IPv6-loopback regression. Remove xfail once parser is fixed."""
    await origin_guard(_connection("http://[::1]:9090"))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "origin",
    [
        "http://evil.example.com",
        "https://attacker.test:9999",
        "http://192.0.2.1",
    ],
)
async def test_origin_guard_rejects_non_localhost(origin: str) -> None:
    with pytest.raises(HTTPException) as excinfo:
        await origin_guard(_connection(origin))
    assert excinfo.value.status_code == 403
    assert excinfo.value.detail["code"] == "bad_origin"


@pytest.mark.asyncio
async def test_origin_guard_rejects_malformed_origin() -> None:
    """An Origin without ://host parses to a bad_origin error."""
    with pytest.raises(HTTPException) as excinfo:
        await origin_guard(_connection("not-a-url"))
    assert excinfo.value.status_code == 403
    assert excinfo.value.detail["code"] == "bad_origin"
