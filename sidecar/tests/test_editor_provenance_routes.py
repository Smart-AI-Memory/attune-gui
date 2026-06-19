"""Tests for /api/corpus/<id>/template/{provenance,regenerate}.

The regenerate route's generator call is mocked at the import boundary
(per testing-conventions.md) so no LLM/network call happens.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from attune_gui import editor_corpora, provenance
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
    provenance._MANIFEST_CACHE.clear()


@pytest.fixture
def client() -> TestClient:
    c = TestClient(create_app())
    c.headers["X-Attune-Client"] = c.get("/api/session/token").json()["token"]
    return c


def _write(p: Path, text: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


@pytest.fixture
def corpus(tmp_path: Path) -> tuple[str, str, Path]:
    """A project corpus with a stale `auth` template. Returns (corpus_id, rel_path, help_dir)."""
    root = tmp_path / "proj"
    help_dir = root / ".help"
    _write(
        help_dir / "features.yaml",
        'version: 1\nfeatures:\n  auth:\n    description: Auth\n    files: ["src/auth/**"]\n',
    )
    _write(root / "src" / "auth" / "login.py", "def login():\n    return True\n")
    tmpl = _write(
        help_dir / "templates" / "auth" / "concept.md",
        "---\ntype: concept\nname: Auth\nfeature: auth\n"
        "source_hash: stale000\ndepth: concept\n---\n\nbody\n",
    )
    cid = editor_corpora.register("Test", str(root)).id
    return cid, str(tmpl.relative_to(root)), help_dir


# -- GET provenance -------------------------------------------------


def test_provenance_reports_stale(client: TestClient, corpus) -> None:
    cid, rel, _ = corpus
    r = client.get(f"/api/corpus/{cid}/template/provenance", params={"path": rel})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "stale"
    assert body["feature"] == "auth"
    assert body["can_regenerate"] is True
    assert body["source_files"]


def test_provenance_unknown_corpus_404(client: TestClient) -> None:
    r = client.get("/api/corpus/nope/template/provenance", params={"path": "x.md"})
    assert r.status_code == 404


def test_provenance_missing_template_404(client: TestClient, corpus) -> None:
    cid, _rel, _ = corpus
    r = client.get(
        f"/api/corpus/{cid}/template/provenance", params={"path": ".help/templates/auth/ghost.md"}
    )
    assert r.status_code == 404


# -- POST regenerate ------------------------------------------------


def test_regenerate_requires_token(corpus) -> None:
    cid, rel, _ = corpus
    plain = TestClient(create_app())
    r = plain.post(f"/api/corpus/{cid}/template/regenerate", json={"path": rel})
    assert r.status_code in (401, 403)


@pytest.fixture(autouse=True)
def _mock_generator(monkeypatch: pytest.MonkeyPatch) -> None:
    """No background regen job can ever reach the real LLM (testing-conventions)."""

    def _fake_generate(*_args, **_kwargs):
        return None

    monkeypatch.setattr("attune_author.generator.generate_feature_templates", _fake_generate)


def test_regenerate_starts_job(client: TestClient, corpus) -> None:
    """POST creates a template.regenerate job carrying the resolved feature/depth."""
    cid, rel, _ = corpus
    r = client.post(f"/api/corpus/{cid}/template/regenerate", json={"path": rel})
    assert r.status_code == 200
    job = r.json()
    assert job["name"] == "template.regenerate"
    assert job["args"]["feature"] == "auth"
    assert job["args"]["depth"] == "concept"


@pytest.mark.asyncio
async def test_regenerate_executor_calls_generator(corpus, monkeypatch: pytest.MonkeyPatch) -> None:
    """The executor loads the manifest and calls the generator with [depth]+overwrite."""
    from attune_gui.jobs import Job, JobContext
    from attune_gui.routes import editor_provenance

    _cid, _rel, help_dir = corpus
    calls: list[tuple] = []

    def _fake_generate(
        feature, help_dir_, project_root, depths=None, overwrite=False, use_rag=True
    ):
        calls.append((feature.name, depths, overwrite))
        return None

    monkeypatch.setattr("attune_author.generator.generate_feature_templates", _fake_generate)

    ctx = JobContext(Job(id="t", name="template.regenerate", args={}))
    result = await editor_provenance._regenerate_template_executor(
        {
            "help_dir": str(help_dir),
            "project_root": str(help_dir.parent),
            "feature": "auth",
            "depth": "concept",
        },
        ctx,
    )
    assert result == {"feature": "auth", "depth": "concept"}
    assert calls == [("auth", ["concept"], True)]


def test_regenerate_unbound_409(client: TestClient, tmp_path: Path) -> None:
    root = tmp_path / "p2"
    _write(
        root / ".help" / "features.yaml",
        'version: 1\nfeatures:\n  auth:\n    description: Auth\n    files: ["src/auth/**"]\n',
    )
    # Template with no `feature` binding.
    tmpl = _write(
        root / ".help" / "templates" / "x" / "concept.md",
        "---\ntype: concept\nname: X\n---\n\nbody\n",
    )
    cid = editor_corpora.register("P2", str(root)).id
    r = client.post(
        f"/api/corpus/{cid}/template/regenerate",
        json={"path": str(tmpl.relative_to(root))},
    )
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "not_regenerable"
