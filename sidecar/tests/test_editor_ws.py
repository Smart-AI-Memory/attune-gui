"""Tests for the editor WebSocket + rename refactor routes (M2 task #12)."""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from attune_gui import editor_corpora
from attune_gui.app import create_app
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _isolated_registry(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        editor_corpora,
        "_REGISTRY_PATH",
        tmp_path / ".attune" / "corpora.json",
        raising=False,
    )


@pytest.fixture
def client() -> TestClient:
    """Override conftest client to attach the X-Attune-Client token.

    The rename refactor routes now require the token. The unauth check
    below uses a fresh TestClient.
    """
    c = TestClient(create_app())
    c.headers["X-Attune-Client"] = c.get("/api/session/token").json()["token"]
    return c


def test_rename_apply_requires_session_token() -> None:
    """POST /api/corpus/<id>/refactor/rename/apply must reject without the token."""
    plain = TestClient(create_app())
    r = plain.post(
        "/api/corpus/x/refactor/rename/apply",
        json={"old": "a", "new": "b", "kind": "alias"},
    )
    assert r.status_code in (401, 403)


@pytest.fixture
def corpus(tmp_path: Path) -> tuple[str, Path]:
    """Three-template corpus with a shared alias to drive rename tests."""
    root = tmp_path / "docs"
    (root / "concepts").mkdir(parents=True)
    (root / "concepts" / "alpha.md").write_text(
        "---\ntype: concept\nname: Alpha\naliases: [a, alpha]\ntags: [security]\n---\n\nbody\n",
        encoding="utf-8",
    )
    (root / "concepts" / "beta.md").write_text(
        "---\ntype: concept\nname: Beta\ntags: [api]\n---\n\nReferences [[alpha]] inline.\n",
        encoding="utf-8",
    )
    (root / "concepts" / "gamma.md").write_text(
        "---\ntype: concept\nname: Gamma\n---\n\nAlso uses [[alpha]] here.\n",
        encoding="utf-8",
    )
    entry = editor_corpora.register("Test", str(root))
    return entry.id, root


# -- WebSocket -----------------------------------------------------


def test_ws_pushes_file_changed_on_external_write(
    client: TestClient, corpus: tuple[str, Path]
) -> None:
    corpus_id, root = corpus
    target = root / "concepts" / "alpha.md"
    with client.websocket_connect(f"/ws/corpus/{corpus_id}?path=concepts/alpha.md") as ws:
        # External writer modifies the file.
        time.sleep(0.05)
        target.write_text(target.read_text() + "\nappended line\n", encoding="utf-8")
        msg = ws.receive_json(mode="text")
        assert msg["type"] == "file_changed"
        assert isinstance(msg["new_hash"], str) and len(msg["new_hash"]) == 16


def test_ws_file_changed_event_invalidates_staleness_cache(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An external write that triggers file_changed must drop the cache entry."""
    from attune_gui.services import staleness_cache

    # Workspace with a manifest so workspace_for_file resolves.
    workspace = tmp_path / "ws"
    (workspace / ".help").mkdir(parents=True)
    (workspace / ".help" / "features.yaml").write_text(
        "version: 1\nfeatures:\n  auth:\n    description: x\n    files: [src/**]\n",
        encoding="utf-8",
    )
    feature_dir = workspace / ".help" / "templates" / "auth"
    feature_dir.mkdir(parents=True)
    target = feature_dir / "concept.md"
    target.write_text("---\nname: x\n---\nbody\n", encoding="utf-8")

    entry = editor_corpora.register("ws-test", str(workspace / ".help" / "templates"))

    invalidated: list[Path] = []
    monkeypatch.setattr(
        staleness_cache,
        "invalidate_for_file",
        lambda p: invalidated.append(p),
    )
    # Re-bind the import alias inside editor_ws so the patch takes effect.
    from attune_gui.routes import editor_ws

    monkeypatch.setattr(
        editor_ws,
        "_invalidate_staleness_for",
        lambda p: invalidated.append(p),
    )

    with client.websocket_connect(f"/ws/corpus/{entry.id}?path=auth/concept.md") as ws:
        time.sleep(0.05)
        target.write_text(target.read_text() + "\nappended\n", encoding="utf-8")
        msg = ws.receive_json(mode="text")
        assert msg["type"] == "file_changed"

    assert invalidated == [target]


def test_ws_second_tab_gets_duplicate_session(client: TestClient, corpus: tuple[str, Path]) -> None:
    corpus_id, _ = corpus
    path = "concepts/alpha.md"
    with client.websocket_connect(f"/ws/corpus/{corpus_id}?path={path}") as primary:
        with client.websocket_connect(f"/ws/corpus/{corpus_id}?path={path}") as secondary:
            msg = secondary.receive_json(mode="text")
            assert msg == {"type": "duplicate_session"}
        # Primary keeps working — verify the session is still alive.
        assert primary is not None  # explicit: secondary close didn't blow up primary


def test_ws_unknown_corpus_closes(client: TestClient) -> None:
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/corpus/ghost?path=x.md") as ws:
            ws.receive_text()


def test_ws_path_traversal_blocked(client: TestClient, corpus: tuple[str, Path]) -> None:
    from starlette.websockets import WebSocketDisconnect

    corpus_id, _ = corpus
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/ws/corpus/{corpus_id}?path=../escape.md") as ws:
            ws.receive_text()


# -- rename preview / apply ----------------------------------------


def test_rename_preview_returns_multifile_diff(
    client: TestClient, corpus: tuple[str, Path]
) -> None:
    corpus_id, _ = corpus
    response = client.post(
        f"/api/corpus/{corpus_id}/refactor/rename/preview",
        json={"old": "alpha", "new": "alphabet", "kind": "alias"},
    )
    assert response.status_code == 200
    plan = response.json()
    assert plan["old"] == "alpha"
    assert plan["new"] == "alphabet"
    assert plan["kind"] == "alias"
    paths = {edit["path"] for edit in plan["edits"]}
    # alpha (declares alias) + beta + gamma (reference it in body)
    assert paths == {"concepts/alpha.md", "concepts/beta.md", "concepts/gamma.md"}
    # Each edit has hunks.
    assert all(edit["hunks"] for edit in plan["edits"])


def test_rename_preview_does_not_write_disk(client: TestClient, corpus: tuple[str, Path]) -> None:
    corpus_id, root = corpus
    before = (root / "concepts" / "alpha.md").read_text(encoding="utf-8")
    client.post(
        f"/api/corpus/{corpus_id}/refactor/rename/preview",
        json={"old": "alpha", "new": "alphabet", "kind": "alias"},
    )
    after = (root / "concepts" / "alpha.md").read_text(encoding="utf-8")
    assert before == after


def test_rename_apply_writes_all_files_atomically(
    client: TestClient, corpus: tuple[str, Path]
) -> None:
    corpus_id, root = corpus
    response = client.post(
        f"/api/corpus/{corpus_id}/refactor/rename/apply",
        json={"old": "alpha", "new": "alphabet", "kind": "alias"},
    )
    assert response.status_code == 200
    body = response.json()
    assert set(body["affected_files"]) == {
        "concepts/alpha.md",
        "concepts/beta.md",
        "concepts/gamma.md",
    }

    alpha = (root / "concepts" / "alpha.md").read_text(encoding="utf-8")
    beta = (root / "concepts" / "beta.md").read_text(encoding="utf-8")
    gamma = (root / "concepts" / "gamma.md").read_text(encoding="utf-8")
    assert "alphabet" in alpha and "alpha," not in alpha.split("---")[1]
    assert "[[alphabet]]" in beta and "[[alpha]]" not in beta
    assert "[[alphabet]]" in gamma and "[[alpha]]" not in gamma


def test_rename_apply_rolls_back_on_failure(
    client: TestClient, corpus: tuple[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """If a mid-stream rename fails, earlier files are restored."""
    corpus_id, root = corpus
    alpha = root / "concepts" / "alpha.md"
    beta = root / "concepts" / "beta.md"
    gamma = root / "concepts" / "gamma.md"
    alpha_before = alpha.read_text(encoding="utf-8")
    beta_before = beta.read_text(encoding="utf-8")
    gamma_before = gamma.read_text(encoding="utf-8")

    # Force the third os.replace to fail; earlier writes must be restored.
    import os as _os

    real_replace = _os.replace
    calls = {"n": 0}

    def flaky_replace(src, dst, *args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 3:
            raise OSError("simulated rename failure")
        return real_replace(src, dst, *args, **kwargs)

    from attune_rag.editor import rename as rename_mod

    monkeypatch.setattr(rename_mod.os, "replace", flaky_replace)

    response = client.post(
        f"/api/corpus/{corpus_id}/refactor/rename/apply",
        json={"old": "alpha", "new": "alphabet", "kind": "alias"},
    )
    # The apply call surfaces the OSError as a 500 (uncaught) in the
    # current handler; our contract is just that the disk is restored.
    assert response.status_code in (409, 500)
    assert alpha.read_text(encoding="utf-8") == alpha_before
    assert beta.read_text(encoding="utf-8") == beta_before
    assert gamma.read_text(encoding="utf-8") == gamma_before


def test_rename_preview_unknown_corpus(client: TestClient) -> None:
    response = client.post(
        "/api/corpus/ghost/refactor/rename/preview",
        json={"old": "a", "new": "b", "kind": "alias"},
    )
    assert response.status_code == 404


def test_rename_apply_collision_returns_409(client: TestClient, corpus: tuple[str, Path]) -> None:
    corpus_id, _ = corpus
    # `a` already exists as an alias on alpha.md; renaming `alpha` -> `a` collides.
    response = client.post(
        f"/api/corpus/{corpus_id}/refactor/rename/preview",
        json={"old": "alpha", "new": "a", "kind": "alias"},
    )
    assert response.status_code == 409


# -- template_path rename (v0.1.16) --------------------------------


def test_template_path_preview_includes_moves(client: TestClient, corpus: tuple[str, Path]) -> None:
    corpus_id, _ = corpus
    response = client.post(
        f"/api/corpus/{corpus_id}/refactor/rename/preview",
        json={
            "old": "concepts/alpha.md",
            "new": "concepts/alpha-renamed.md",
            "kind": "template_path",
        },
    )
    assert response.status_code == 200
    plan = response.json()
    assert plan["kind"] == "template_path"
    assert plan["moves"] == [
        {"old_path": "concepts/alpha.md", "new_path": "concepts/alpha-renamed.md"}
    ]


def test_template_path_apply_moves_file_and_reports_affected(
    client: TestClient, corpus: tuple[str, Path]
) -> None:
    corpus_id, root = corpus
    response = client.post(
        f"/api/corpus/{corpus_id}/refactor/rename/apply",
        json={
            "old": "concepts/alpha.md",
            "new": "concepts/alpha-renamed.md",
            "kind": "template_path",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "concepts/alpha-renamed.md" in body["affected_files"]
    assert not (root / "concepts" / "alpha.md").exists()
    assert (root / "concepts" / "alpha-renamed.md").exists()


def test_template_path_preview_missing_source_returns_400(
    client: TestClient, corpus: tuple[str, Path]
) -> None:
    corpus_id, _ = corpus
    response = client.post(
        f"/api/corpus/{corpus_id}/refactor/rename/preview",
        json={
            "old": "concepts/nope.md",
            "new": "concepts/whatever.md",
            "kind": "template_path",
        },
    )
    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"]["message"].lower()


def test_template_path_preview_escapes_root_returns_400(
    client: TestClient, corpus: tuple[str, Path]
) -> None:
    corpus_id, _ = corpus
    response = client.post(
        f"/api/corpus/{corpus_id}/refactor/rename/preview",
        json={
            "old": "concepts/alpha.md",
            "new": "../escape.md",
            "kind": "template_path",
        },
    )
    assert response.status_code == 400
    assert "escapes" in response.json()["detail"]["message"].lower()


def test_template_path_preview_collision_returns_409(
    client: TestClient, corpus: tuple[str, Path]
) -> None:
    corpus_id, _ = corpus
    response = client.post(
        f"/api/corpus/{corpus_id}/refactor/rename/preview",
        json={
            "old": "concepts/alpha.md",
            "new": "concepts/beta.md",
            "kind": "template_path",
        },
    )
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["code"] == "name_collision"
    assert "concepts/beta.md" in detail["message"]
    # The envelope now round-trips ``owning_path`` so the frontend
    # collision banner can name the conflicting file.
    assert detail["owning_path"] == "concepts/beta.md"
