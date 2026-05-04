"""Tests for the corpora registry + /api/corpus routes (M2 task #7)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from attune_gui import editor_corpora
from attune_gui.app import create_app
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _isolated_registry(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Redirect the registry file to a per-test tmp path."""
    registry = tmp_path / ".attune" / "corpora.json"
    monkeypatch.setattr(editor_corpora, "_REGISTRY_PATH", registry, raising=False)
    return registry


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("ATTUNE_GUI_TEST", "1")
    return TestClient(create_app())


def _make_corpus_dir(tmp_path: Path, name: str = "templates") -> Path:
    p = tmp_path / name
    p.mkdir(parents=True, exist_ok=True)
    (p / "a.md").write_text("---\ntype: concept\nname: A\n---\nbody\n", encoding="utf-8")
    return p


# -- registry helpers (unit) ----------------------------------------


def test_load_registry_empty_when_missing() -> None:
    reg = editor_corpora.load_registry()
    assert reg.active is None
    assert reg.corpora == []


def test_register_creates_entry_and_persists(tmp_path: Path) -> None:
    corpus_dir = _make_corpus_dir(tmp_path)
    entry = editor_corpora.register("My Corpus", str(corpus_dir))
    assert entry.id == "my-corpus"
    assert entry.name == "My Corpus"
    assert entry.path == str(corpus_dir.resolve())
    assert entry.kind == "source"

    # Persisted to disk.
    raw = editor_corpora._REGISTRY_PATH.read_text(encoding="utf-8")
    payload = json.loads(raw)
    assert payload["version"] == 1
    assert payload["active"] == "my-corpus"
    assert len(payload["corpora"]) == 1


def test_register_idempotent_on_same_path(tmp_path: Path) -> None:
    corpus_dir = _make_corpus_dir(tmp_path)
    first = editor_corpora.register("My Corpus", str(corpus_dir))
    second = editor_corpora.register("Different Name", str(corpus_dir))
    assert first.id == second.id  # no duplicate


def test_register_unique_id_when_names_collide(tmp_path: Path) -> None:
    a = _make_corpus_dir(tmp_path, "a")
    b = _make_corpus_dir(tmp_path, "b")
    first = editor_corpora.register("Same", str(a))
    second = editor_corpora.register("Same", str(b))
    assert first.id != second.id
    assert second.id.startswith("same")


def test_register_rejects_non_directory(tmp_path: Path) -> None:
    f = tmp_path / "not-a-dir.txt"
    f.write_text("hi", encoding="utf-8")
    with pytest.raises(ValueError, match="Not a directory"):
        editor_corpora.register("X", str(f))


def test_set_active_updates_pointer(tmp_path: Path) -> None:
    a = _make_corpus_dir(tmp_path, "a")
    b = _make_corpus_dir(tmp_path, "b")
    editor_corpora.register("Alpha", str(a))
    e2 = editor_corpora.register("Beta", str(b))
    editor_corpora.set_active(e2.id)
    assert editor_corpora.get_active() == e2

    with pytest.raises(KeyError):
        editor_corpora.set_active("ghost")


def test_resolve_path_finds_owning_corpus(tmp_path: Path) -> None:
    corpus_dir = _make_corpus_dir(tmp_path)
    entry = editor_corpora.register("X", str(corpus_dir))
    found = editor_corpora.resolve_path(str(corpus_dir / "a.md"))
    assert found is not None
    matched, rel = found
    assert matched.id == entry.id
    assert rel == "a.md"


def test_resolve_path_nested_picks_deepest_root(tmp_path: Path) -> None:
    """If a path is inside multiple registered corpora (e.g., a parent
    and a nested subdir), the deepest match wins."""
    outer = _make_corpus_dir(tmp_path, "outer")
    inner = outer / "nested"
    inner.mkdir()
    (inner / "x.md").write_text("hello", encoding="utf-8")

    editor_corpora.register("Outer", str(outer))
    inner_entry = editor_corpora.register("Inner", str(inner))

    found = editor_corpora.resolve_path(str(inner / "x.md"))
    assert found is not None
    matched, rel = found
    assert matched.id == inner_entry.id
    assert rel == "x.md"


def test_resolve_path_returns_none_when_unowned(tmp_path: Path) -> None:
    elsewhere = tmp_path / "elsewhere" / "x.md"
    elsewhere.parent.mkdir()
    elsewhere.write_text("hi", encoding="utf-8")
    assert editor_corpora.resolve_path(str(elsewhere)) is None


# -- HTTP routes ----------------------------------------------------


def test_list_endpoint(client: TestClient, tmp_path: Path) -> None:
    response = client.get("/api/corpus")
    assert response.status_code == 200
    assert response.json() == {"active": None, "corpora": []}

    corpus_dir = _make_corpus_dir(tmp_path)
    editor_corpora.register("Test", str(corpus_dir))

    response = client.get("/api/corpus")
    body = response.json()
    assert body["active"] == "test"
    assert len(body["corpora"]) == 1
    assert body["corpora"][0]["name"] == "Test"


def test_register_endpoint(client: TestClient, tmp_path: Path) -> None:
    corpus_dir = _make_corpus_dir(tmp_path)
    response = client.post(
        "/api/corpus/register",
        json={"name": "From API", "path": str(corpus_dir)},
    )
    assert response.status_code == 200
    assert response.json()["id"] == "from-api"


def test_register_endpoint_rejects_bad_path(client: TestClient, tmp_path: Path) -> None:
    response = client.post(
        "/api/corpus/register",
        json={"name": "X", "path": str(tmp_path / "ghost")},
    )
    assert response.status_code == 400


def test_active_endpoint_404s_unknown_id(client: TestClient) -> None:
    response = client.post("/api/corpus/active", json={"id": "nope"})
    assert response.status_code == 404


def test_resolve_endpoint(client: TestClient, tmp_path: Path) -> None:
    corpus_dir = _make_corpus_dir(tmp_path)
    editor_corpora.register("R", str(corpus_dir))
    response = client.post("/api/corpus/resolve", json={"abs_path": str(corpus_dir / "a.md")})
    assert response.status_code == 200
    body = response.json()
    assert body["corpus_id"] == "r"
    assert body["rel_path"] == "a.md"


def test_resolve_endpoint_404s_unowned(client: TestClient, tmp_path: Path) -> None:
    response = client.post("/api/corpus/resolve", json={"abs_path": str(tmp_path / "ghost.md")})
    assert response.status_code == 404
