"""Tests for /api/corpus/<id>/template + /lint + /autocomplete (M2 #10, #11)."""

from __future__ import annotations

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

    Template diff/save and lint now require the token; tests in this file
    exercise those routes. The unauth tests below use fresh TestClients.
    """
    c = TestClient(create_app())
    c.headers["X-Attune-Client"] = c.get("/api/session/token").json()["token"]
    return c


def test_template_save_requires_session_token() -> None:
    """POST /api/corpus/<id>/template/save must reject calls without the token."""
    plain = TestClient(create_app())
    r = plain.post(
        "/api/corpus/x/template/save",
        json={"path": "x.md", "draft_text": "x", "base_hash": "0" * 64},
    )
    assert r.status_code in (401, 403)


def test_lint_requires_session_token() -> None:
    """POST /api/corpus/<id>/lint must reject calls without the token."""
    plain = TestClient(create_app())
    r = plain.post("/api/corpus/x/lint", json={"path": "x.md", "text": ""})
    assert r.status_code in (401, 403)


@pytest.fixture
def corpus_id(tmp_path: Path) -> str:
    """Register a tiny 3-template corpus and return its id."""
    root = tmp_path / "docs"
    (root / "concepts").mkdir(parents=True)
    (root / "concepts" / "alpha.md").write_text(
        "---\ntype: concept\nname: Alpha\naliases: [a, alpha]\ntags: [security]\n---\n\nbody\n",
        encoding="utf-8",
    )
    (root / "concepts" / "beta.md").write_text(
        "---\ntype: concept\nname: Beta\ntags: [security, api]\n---\n\nReferences [[alpha]].\n",
        encoding="utf-8",
    )
    entry = editor_corpora.register("Test", str(root))
    return entry.id


# -- GET /template --------------------------------------------------


def test_get_template_returns_split_content(client: TestClient, corpus_id: str) -> None:
    response = client.get(f"/api/corpus/{corpus_id}/template", params={"path": "concepts/alpha.md"})
    assert response.status_code == 200
    body = response.json()
    assert body["rel_path"] == "concepts/alpha.md"
    assert "type: concept" in body["frontmatter_text"]
    assert "body" in body["body"]
    assert len(body["base_hash"]) == 16


def test_get_template_404_when_missing(client: TestClient, corpus_id: str) -> None:
    response = client.get(f"/api/corpus/{corpus_id}/template", params={"path": "nope.md"})
    assert response.status_code == 404


def test_get_template_rejects_path_traversal(client: TestClient, corpus_id: str) -> None:
    response = client.get(f"/api/corpus/{corpus_id}/template", params={"path": "../escape.md"})
    assert response.status_code == 400


def test_get_template_unknown_corpus(client: TestClient) -> None:
    response = client.get("/api/corpus/ghost/template", params={"path": "alpha.md"})
    assert response.status_code == 404


# -- POST /template/diff --------------------------------------------


def test_diff_returns_hunks(client: TestClient, corpus_id: str) -> None:
    initial = client.get(
        f"/api/corpus/{corpus_id}/template", params={"path": "concepts/alpha.md"}
    ).json()
    draft = initial["text"].replace("body", "modified body content")

    response = client.post(
        f"/api/corpus/{corpus_id}/template/diff",
        json={
            "path": "concepts/alpha.md",
            "draft_text": draft,
            "base_hash": initial["base_hash"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["hunks"]
    assert all("hunk_id" in h for h in body["hunks"])


def test_diff_409_on_drift(client: TestClient, corpus_id: str, tmp_path: Path) -> None:
    # Hand the route a base_hash that doesn't match the file's actual hash.
    response = client.post(
        f"/api/corpus/{corpus_id}/template/diff",
        json={
            "path": "concepts/alpha.md",
            "draft_text": "anything",
            "base_hash": "0000000000000000",
        },
    )
    assert response.status_code == 409


# -- POST /template/save --------------------------------------------


def test_save_full_draft_round_trip(client: TestClient, corpus_id: str, tmp_path: Path) -> None:
    initial = client.get(
        f"/api/corpus/{corpus_id}/template", params={"path": "concepts/alpha.md"}
    ).json()
    draft = initial["text"].replace("body", "fresh body text")

    response = client.post(
        f"/api/corpus/{corpus_id}/template/save",
        json={
            "path": "concepts/alpha.md",
            "draft_text": draft,
            "base_hash": initial["base_hash"],
        },
    )
    assert response.status_code == 200

    # File on disk now reflects the new draft.
    on_disk = (tmp_path / "docs" / "concepts" / "alpha.md").read_text(encoding="utf-8")
    assert "fresh body text" in on_disk


def test_save_409_on_drift(client: TestClient, corpus_id: str) -> None:
    response = client.post(
        f"/api/corpus/{corpus_id}/template/save",
        json={
            "path": "concepts/alpha.md",
            "draft_text": "x",
            "base_hash": "0000000000000000",
        },
    )
    assert response.status_code == 409


def test_save_path_traversal_blocked(client: TestClient, corpus_id: str) -> None:
    response = client.post(
        f"/api/corpus/{corpus_id}/template/save",
        json={
            "path": "../escape.md",
            "draft_text": "x",
            "base_hash": "0000000000000000",
        },
    )
    assert response.status_code == 400


def test_save_no_op_with_empty_accepted_hunks(
    client: TestClient, corpus_id: str, tmp_path: Path
) -> None:
    initial = client.get(
        f"/api/corpus/{corpus_id}/template", params={"path": "concepts/alpha.md"}
    ).json()
    draft = initial["text"].replace("body", "doomed change")

    response = client.post(
        f"/api/corpus/{corpus_id}/template/save",
        json={
            "path": "concepts/alpha.md",
            "draft_text": draft,
            "base_hash": initial["base_hash"],
            "accepted_hunks": [],  # explicitly accept nothing
        },
    )
    assert response.status_code == 200
    on_disk = (tmp_path / "docs" / "concepts" / "alpha.md").read_text(encoding="utf-8")
    assert "doomed change" not in on_disk


def test_save_invalidates_staleness_cache(client: TestClient, monkeypatch, tmp_path: Path) -> None:
    """A successful save drops the cache entry for the workspace it belongs to."""
    from attune_gui import editor_corpora
    from attune_gui.routes import editor_template
    from attune_gui.services import staleness_cache

    # Build a workspace with .help/features.yaml so _workspace_for_path resolves.
    workspace = tmp_path / "ws"
    (workspace / ".help").mkdir(parents=True)
    (workspace / ".help" / "features.yaml").write_text(
        "version: 1\nfeatures:\n  auth:\n    description: x\n    files: [src/**]\n",
        encoding="utf-8",
    )
    templates_root = workspace / ".help" / "templates" / "auth"
    templates_root.mkdir(parents=True)
    target = templates_root / "concept.md"
    target.write_text("---\nname: x\n---\nbody\n", encoding="utf-8")

    entry = editor_corpora.register("ws-test", str(workspace / ".help" / "templates"))

    invalidated: list[tuple[Path, Path]] = []
    monkeypatch.setattr(
        staleness_cache,
        "invalidate_path",
        lambda ws, p: invalidated.append((ws, p)),
    )

    initial = client.get(
        f"/api/corpus/{entry.id}/template", params={"path": "auth/concept.md"}
    ).json()
    response = client.post(
        f"/api/corpus/{entry.id}/template/save",
        json={
            "path": "auth/concept.md",
            "draft_text": initial["text"].replace("body", "edited"),
            "base_hash": initial["base_hash"],
        },
    )
    assert response.status_code == 200
    assert invalidated == [(workspace, target)]
    # Sanity: helper located the right workspace.
    assert editor_template._workspace_for_path(target) == workspace


# -- /lint ----------------------------------------------------------


def test_lint_finds_broken_alias(client: TestClient, corpus_id: str) -> None:
    text = "---\ntype: concept\nname: X\n---\n\nLink to [[ghost-alias]].\n"
    response = client.post(
        f"/api/corpus/{corpus_id}/lint",
        json={"path": "x.md", "text": text},
    )
    assert response.status_code == 200
    diags = response.json()
    codes = {d["code"] for d in diags}
    assert "broken-alias" in codes


def test_lint_404_unknown_corpus(client: TestClient) -> None:
    response = client.post("/api/corpus/ghost/lint", json={"path": "x.md", "text": ""})
    assert response.status_code == 404


# -- /autocomplete --------------------------------------------------


def test_autocomplete_tags(client: TestClient, corpus_id: str) -> None:
    response = client.get(
        f"/api/corpus/{corpus_id}/autocomplete",
        params={"kind": "tag", "prefix": "se"},
    )
    assert response.status_code == 200
    assert response.json() == ["security"]


def test_autocomplete_aliases_returns_full_info(client: TestClient, corpus_id: str) -> None:
    response = client.get(
        f"/api/corpus/{corpus_id}/autocomplete",
        params={"kind": "alias", "prefix": "alpha"},
    )
    assert response.status_code == 200
    body = response.json()
    assert any(item["alias"] == "alpha" for item in body)
    assert all({"alias", "template_path", "template_name"} == set(item) for item in body)


def test_autocomplete_404_unknown_corpus(client: TestClient) -> None:
    response = client.get("/api/corpus/ghost/autocomplete", params={"kind": "tag", "prefix": ""})
    assert response.status_code == 404
