"""Shared pytest fixtures for the sidecar test suite.

The vast majority of route tests want a fresh ``TestClient`` and a
session token. Defining them here removes ~15 duplicated copies
across the test files. Test-file-local fixtures (e.g. ``reset_store``,
``workspace``, ``_patch_*_root``) stay in their original files since
their scope is genuinely test-suite-specific.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from attune_gui import editor_corpora, living_docs_store
from attune_gui.app import create_app
from fastapi.testclient import TestClient

# Real home-dir state this layer's tests must never touch (they isolate to a
# tmp dir instead). The guard below is a regression alarm — see
# specs/test-isolation-guard/ and the workspace testing-conventions.md.
_GUARDED_PATHS = [
    Path.home() / ".attune" / "corpora.json",
    Path.home() / ".attune-gui",
]


def _home_snapshot(p: Path):
    """Comparable snapshot: dir → child names; file → mtime; absent → None."""
    if p.is_dir():
        return frozenset(c.name for c in p.iterdir())
    if p.exists():
        return ("file", p.stat().st_mtime)
    return None


@pytest.fixture(scope="session", autouse=True)
def _guard_real_home_state():
    """Fail the run if any test wrote to real home-dir state (missing isolation)."""
    before = {p: _home_snapshot(p) for p in _GUARDED_PATHS}
    yield
    leaked = []
    for p in _GUARDED_PATHS:
        b, a = before[p], _home_snapshot(p)
        if isinstance(b, frozenset) or isinstance(a, frozenset):
            new = (a or frozenset()) - (b or frozenset())
            if new:
                leaked.append(f"{p}: new entries {sorted(new)[:5]}")
        elif b != a:
            leaked.append(f"{p}: created or modified")
    assert not leaked, (
        "Tests wrote to real home-dir state (missing isolation):\n  "
        + "\n  ".join(leaked)
        + "\nIsolate via the tmp-dir fixture — see testing-conventions.md."
    )


@pytest.fixture(autouse=True)
def _isolated_living_docs_state(tmp_path, monkeypatch):
    """Redirect the living-docs persistence file to a tmp path.

    Without this, any test that constructs ``LivingDocsStore()`` with no
    arguments would read from / write to the developer's real
    ``~/.attune-gui/living_docs.json``.
    """
    monkeypatch.setattr(
        living_docs_store,
        "_DEFAULT_STATE_PATH",
        tmp_path / "living_docs.json",
    )


@pytest.fixture(autouse=True)
def _isolated_corpora_registry(tmp_path, monkeypatch):
    """Redirect the editor corpora registry to a tmp file.

    Without this, any test that calls ``editor_corpora.register()`` writes
    to the developer's real ``~/.attune/corpora.json``. The per-file
    ``monkeypatch.setattr(editor_corpora, "_REGISTRY_PATH", ...)`` used
    before was a silent no-op — that attribute does not exist; the path is
    resolved by ``editor_corpora._registry_path()``. Patch the resolver.
    """
    registry = tmp_path / "corpora.json"
    monkeypatch.setattr(editor_corpora, "_registry_path", lambda: registry)


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def session_token(client: TestClient) -> str:
    """Mint a session token for routes guarded by ``X-Attune-Client``."""
    return client.get("/api/session/token").json()["token"]
