"""Tests for workspace-scoped RagPipeline caching and invalidation."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def clear_pipeline_cache():
    """Reset the module-level pipeline cache between tests."""
    from attune_gui.routes import rag

    rag._PIPELINES.clear()
    yield
    rag._PIPELINES.clear()


def test_none_workspace_uses_default_key():
    """No workspace → pipeline stored under the empty-Path sentinel."""
    from attune_gui.routes.rag import _DEFAULT_KEY, _PIPELINES, _get_pipeline

    p = _get_pipeline(None)
    assert _DEFAULT_KEY in _PIPELINES
    assert _PIPELINES[_DEFAULT_KEY] is p


def test_workspace_without_templates_falls_back_to_default_corpus(tmp_path):
    """Workspace exists but has no .help/templates/ → AttuneHelpCorpus fallback."""
    from attune_gui.routes.rag import _get_pipeline
    from attune_rag import RagPipeline

    pipeline = _get_pipeline(tmp_path)
    assert isinstance(pipeline, RagPipeline)
    # corpus should be the bundled default, not a DirectoryCorpus
    assert "Directory" not in type(pipeline.corpus).__name__


def test_workspace_with_templates_uses_directory_corpus(tmp_path):
    """Workspace with .help/templates/ → DirectoryCorpus scoped to that path."""
    from attune_gui.routes.rag import _get_pipeline
    from attune_rag import DirectoryCorpus

    templates_dir = tmp_path / ".help" / "templates"
    templates_dir.mkdir(parents=True)
    (templates_dir / "sample.md").write_text("# sample\nsome content")

    pipeline = _get_pipeline(tmp_path)
    assert isinstance(pipeline.corpus, DirectoryCorpus)


def test_two_workspaces_get_distinct_pipelines(tmp_path):
    """Different workspace paths → different pipeline instances."""
    from attune_gui.routes.rag import _get_pipeline

    ws_a = tmp_path / "project_a"
    ws_b = tmp_path / "project_b"
    ws_a.mkdir()
    ws_b.mkdir()

    p_a = _get_pipeline(ws_a)
    p_b = _get_pipeline(ws_b)
    assert p_a is not p_b


def test_same_workspace_returns_cached_pipeline(tmp_path):
    """Same workspace path → same pipeline object (cache hit)."""
    from attune_gui.routes.rag import _get_pipeline

    p1 = _get_pipeline(tmp_path)
    p2 = _get_pipeline(tmp_path)
    assert p1 is p2


def test_invalidate_drops_cached_pipeline(tmp_path):
    """invalidate() removes the entry; next call creates a fresh pipeline."""
    from attune_gui.routes.rag import _get_pipeline, invalidate

    p1 = _get_pipeline(tmp_path)
    invalidate(tmp_path)
    p2 = _get_pipeline(tmp_path)
    assert p1 is not p2


def test_invalidate_unknown_workspace_is_noop(tmp_path):
    """invalidate() on an uncached workspace raises no error."""
    from attune_gui.routes.rag import invalidate

    invalidate(tmp_path / "never_cached")  # must not raise


def test_invalidate_does_not_affect_other_workspaces(tmp_path):
    """invalidate(A) leaves pipeline for workspace B intact."""
    from attune_gui.routes.rag import _get_pipeline, invalidate

    ws_a = tmp_path / "a"
    ws_b = tmp_path / "b"
    ws_a.mkdir()
    ws_b.mkdir()

    p_b = _get_pipeline(ws_b)
    invalidate(ws_a)
    assert _get_pipeline(ws_b) is p_b


def test_directory_corpus_reflects_templates(tmp_path):
    """Pipeline built from a workspace returns entries from its templates dir."""
    from attune_gui.routes.rag import _get_pipeline

    templates_dir = tmp_path / ".help" / "templates"
    templates_dir.mkdir(parents=True)
    (templates_dir / "auth.md").write_text("# auth\nHow authentication works.")
    (templates_dir / "billing.md").write_text("# billing\nHow billing works.")

    pipeline = _get_pipeline(tmp_path)
    entries = list(pipeline.corpus.entries())
    paths = {e.path for e in entries}
    assert "auth.md" in paths
    assert "billing.md" in paths


def test_after_invalidate_new_templates_are_picked_up(tmp_path):
    """After invalidate, a newly added template appears in the next pipeline."""
    from attune_gui.routes.rag import _get_pipeline, invalidate

    templates_dir = tmp_path / ".help" / "templates"
    templates_dir.mkdir(parents=True)
    (templates_dir / "original.md").write_text("# original")

    _get_pipeline(tmp_path)  # prime cache

    (templates_dir / "new_feature.md").write_text("# new feature")
    invalidate(tmp_path)

    pipeline = _get_pipeline(tmp_path)
    paths = {e.path for e in pipeline.corpus.entries()}
    assert "new_feature.md" in paths
