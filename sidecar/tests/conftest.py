"""Shared pytest fixtures for the sidecar test suite.

The vast majority of route tests want a fresh ``TestClient`` and a
session token. Defining them here removes ~15 duplicated copies
across the test files. Test-file-local fixtures (e.g. ``reset_store``,
``workspace``, ``_patch_*_root``) stay in their original files since
their scope is genuinely test-suite-specific.
"""

from __future__ import annotations

import pytest
from attune_gui import editor_corpora, living_docs_store
from attune_gui.app import create_app
from fastapi.testclient import TestClient


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
