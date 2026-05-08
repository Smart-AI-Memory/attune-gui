"""Phase D4: ``attune_gui.services.rag_pipeline.pipeline_for`` is the
canonical owner of the workspace-keyed RagPipeline cache.

These tests pin two contracts:

1. ``pipeline_for(workspace)`` returns the same instance for the same
   workspace (the cache works) and a different instance after
   ``invalidate(workspace)`` (the cache is bustable).
2. ``routes.rag``, ``routes.search``, and ``routes.living_docs`` all
   route through this single helper rather than crossing into each
   other's modules.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from attune_gui.services import rag_pipeline as svc


@pytest.fixture(autouse=True)
def _clean_cache() -> None:
    """Reset the cache around every test so neighbours can't leak state."""
    saved = dict(svc._PIPELINES)
    svc._PIPELINES.clear()
    yield
    svc._PIPELINES.clear()
    svc._PIPELINES.update(saved)


class _FakePipeline:
    """Stand-in for ``attune_rag.RagPipeline`` — same constructor shape."""

    def __init__(self, *, corpus, expander) -> None:
        self.corpus = corpus
        self.expander = expander


class _FakeCorpus:
    def __init__(self, root: Path) -> None:
        self.root = root


def _patch_attune_rag():
    """Patch the lazy-imported ``attune_rag`` symbols inside ``pipeline_for``."""
    return patch.dict(
        "sys.modules",
        {
            "attune_rag": _FakeAttuneRagModule(),
        },
    )


class _FakeAttuneRagModule:
    """Fake ``attune_rag`` module exposing just the three names ``pipeline_for`` imports."""

    DirectoryCorpus = _FakeCorpus
    QueryExpander = type("QueryExpander", (), {"__init__": lambda self: None})
    RagPipeline = _FakePipeline


# ---------------------------------------------------------------------------
# pipeline_for + invalidate
# ---------------------------------------------------------------------------


def test_pipeline_for_caches_per_workspace(tmp_path: Path) -> None:
    with _patch_attune_rag():
        first = svc.pipeline_for(tmp_path)
        second = svc.pipeline_for(tmp_path)
    assert first is second


def test_pipeline_for_default_when_no_workspace() -> None:
    with _patch_attune_rag():
        a = svc.pipeline_for(None)
        b = svc.pipeline_for(None)
    assert a is b


def test_invalidate_drops_cached_entry(tmp_path: Path) -> None:
    with _patch_attune_rag():
        first = svc.pipeline_for(tmp_path)
        svc.invalidate(tmp_path)
        second = svc.pipeline_for(tmp_path)
    assert first is not second


def test_invalidate_unknown_workspace_is_noop(tmp_path: Path) -> None:
    """Bare invalidate on an absent key must not raise."""
    svc.invalidate(tmp_path)  # cache is empty
    svc.invalidate(None)  # default key also empty


def test_pipeline_for_uses_directory_corpus_when_templates_dir_exists(
    tmp_path: Path,
) -> None:
    (tmp_path / ".help" / "templates").mkdir(parents=True)
    with _patch_attune_rag():
        pipeline = svc.pipeline_for(tmp_path)
    assert isinstance(pipeline.corpus, _FakeCorpus)
    assert pipeline.corpus.root == tmp_path / ".help" / "templates"


def test_pipeline_for_uses_bundled_corpus_when_no_templates_dir(tmp_path: Path) -> None:
    with _patch_attune_rag():
        pipeline = svc.pipeline_for(tmp_path)
    assert pipeline.corpus is None  # attune_rag fills in the default


# ---------------------------------------------------------------------------
# Cross-module wiring (closes finding #5)
# ---------------------------------------------------------------------------


def test_routes_rag_re_exports_pipeline_for() -> None:
    """``routes.rag`` keeps ``_get_pipeline`` as a backwards-compat alias."""
    from attune_gui.routes import rag as routes_rag

    assert routes_rag.pipeline_for is svc.pipeline_for
    assert routes_rag.invalidate is svc.invalidate
    assert routes_rag._get_pipeline is svc.pipeline_for


def test_routes_search_uses_canonical_pipeline_for() -> None:
    """``routes.search`` no longer crosses into ``routes.rag`` for the cache."""
    import inspect

    from attune_gui.routes import search

    src = inspect.getsource(search._rag_search)
    assert "attune_gui.services.rag_pipeline" in src
    assert "attune_gui.routes.rag" not in src


def test_commands_invalidate_uses_canonical_module() -> None:
    """The author-proxy invalidate path imports from the services module."""
    import inspect

    from attune_gui import commands

    src = inspect.getsource(commands._author_proxy)
    assert "attune_gui.services.rag_pipeline" in src
    assert "from attune_gui.routes import rag" not in src
