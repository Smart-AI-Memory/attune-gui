"""Tests for ``attune_gui.services.staleness_cache``.

The cache is exercised end-to-end against the real
``attune_author.staleness.check_staleness`` (via the
``build_workspace`` fixture) and also with mocked behavior to
cover the graceful-degrade paths.
"""

from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import patch

import pytest
from attune_gui.services import staleness_cache

from ._fixtures.staleness import build_workspace


@pytest.fixture(autouse=True)
def _reset_cache() -> None:
    staleness_cache._reset_for_tests()
    yield
    staleness_cache._reset_for_tests()


def _hash_for(workspace: Path, feature: str) -> str:
    """Compute the current source_hash for ``feature`` in ``workspace``."""
    from attune_author.manifest import load_manifest
    from attune_author.staleness import compute_source_hash

    manifest = load_manifest(workspace / ".help")
    feat = manifest.features[feature]
    digest, _ = compute_source_hash(feat, workspace)
    return digest


def _template_with_hash(source_hash: str) -> str:
    return f"---\nname: x\nsource_hash: {source_hash}\n---\nbody\n"


def _stale_template() -> str:
    return "---\nname: x\nsource_hash: 0000\n---\nbody\n"


def test_fresh_template_returns_fresh(tmp_path: Path) -> None:
    workspace = build_workspace(
        tmp_path,
        features={"auth": ["src/auth/**"]},
        sources={"src/auth/login.py": "x = 1\n"},
    )
    fresh_hash = _hash_for(workspace, "auth")
    template = Path(".help/templates/auth/concept.md")
    build_workspace(
        tmp_path,
        features={"auth": ["src/auth/**"]},
        sources={"src/auth/login.py": "x = 1\n"},
        templates={str(template): _template_with_hash(fresh_hash)},
    )

    status = staleness_cache.get_template_staleness(workspace, workspace / template)
    assert status == "fresh"


def test_stale_template_returns_stale(tmp_path: Path) -> None:
    workspace = build_workspace(
        tmp_path,
        features={"auth": ["src/auth/**"]},
        sources={"src/auth/login.py": "x = 1\n"},
        templates={".help/templates/auth/concept.md": _stale_template()},
    )

    status = staleness_cache.get_template_staleness(
        workspace, workspace / ".help/templates/auth/concept.md"
    )
    assert status == "stale"


def test_template_outside_any_feature_dir_is_manual(tmp_path: Path) -> None:
    workspace = build_workspace(
        tmp_path,
        features={"auth": ["src/auth/**"]},
        sources={"src/auth/login.py": "x = 1\n"},
        templates={".help/templates/glossary.md": "no frontmatter\n"},
    )

    status = staleness_cache.get_template_staleness(
        workspace, workspace / ".help/templates/glossary.md"
    )
    assert status == "manual"


def test_template_outside_workspace_is_manual(tmp_path: Path) -> None:
    workspace = build_workspace(
        tmp_path,
        features={"auth": ["src/auth/**"]},
        sources={"src/auth/login.py": "x = 1\n"},
    )
    outside = tmp_path.parent / "elsewhere.md"
    status = staleness_cache.get_template_staleness(workspace, outside)
    assert status == "manual"


def test_cache_populates_once_per_workspace(tmp_path: Path) -> None:
    workspace = build_workspace(
        tmp_path,
        features={"auth": ["src/auth/**"]},
        sources={"src/auth/login.py": "x = 1\n"},
        templates={".help/templates/auth/concept.md": _stale_template()},
    )

    call_count = {"n": 0}
    real_check = __import__("attune_author.staleness", fromlist=["check_staleness"]).check_staleness

    def counting(*args, **kwargs):
        call_count["n"] += 1
        return real_check(*args, **kwargs)

    with patch("attune_author.staleness.check_staleness", side_effect=counting):
        staleness_cache.get_template_staleness(
            workspace, workspace / ".help/templates/auth/concept.md"
        )
        staleness_cache.get_template_staleness(
            workspace, workspace / ".help/templates/auth/concept.md"
        )
    assert call_count["n"] == 1


def test_invalidate_workspace_drops_all_entries(tmp_path: Path) -> None:
    workspace = build_workspace(
        tmp_path,
        features={"auth": ["src/auth/**"]},
        sources={"src/auth/login.py": "x = 1\n"},
        templates={".help/templates/auth/concept.md": _stale_template()},
    )
    template = workspace / ".help/templates/auth/concept.md"

    staleness_cache.get_template_staleness(workspace, template)
    assert workspace.resolve() in staleness_cache._CACHE

    staleness_cache.invalidate_workspace(workspace)
    assert workspace.resolve() not in staleness_cache._CACHE


def test_invalidate_path_drops_workspace(tmp_path: Path) -> None:
    workspace = build_workspace(
        tmp_path,
        features={"auth": ["src/auth/**"]},
        sources={"src/auth/login.py": "x = 1\n"},
        templates={".help/templates/auth/concept.md": _stale_template()},
    )
    template = workspace / ".help/templates/auth/concept.md"

    staleness_cache.get_template_staleness(workspace, template)
    staleness_cache.invalidate_path(workspace, template)
    assert workspace.resolve() not in staleness_cache._CACHE


def test_invalidate_path_for_unknown_file_noop(tmp_path: Path) -> None:
    workspace = build_workspace(
        tmp_path,
        features={"auth": ["src/auth/**"]},
        sources={"src/auth/login.py": "x = 1\n"},
        templates={".help/templates/auth/concept.md": _stale_template()},
    )
    template = workspace / ".help/templates/auth/concept.md"
    staleness_cache.get_template_staleness(workspace, template)

    staleness_cache.invalidate_path(workspace, workspace / "nope.md")
    # Cache still present for the known path.
    assert workspace.resolve() in staleness_cache._CACHE


def test_missing_features_yaml_returns_unknown(tmp_path: Path) -> None:
    workspace = tmp_path
    (workspace / ".help").mkdir()
    template = workspace / ".help/templates/auth/concept.md"
    template.parent.mkdir(parents=True)
    template.write_text("body", encoding="utf-8")

    status = staleness_cache.get_template_staleness(workspace, template)
    assert status == "unknown"


def test_missing_attune_author_returns_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace = build_workspace(
        tmp_path,
        features={"auth": ["src/auth/**"]},
        sources={"src/auth/login.py": "x = 1\n"},
        templates={".help/templates/auth/concept.md": _stale_template()},
    )
    template = workspace / ".help/templates/auth/concept.md"

    import builtins

    real_import = builtins.__import__

    def deny_attune_author(name, *args, **kwargs):
        if name == "attune_author.staleness":
            raise ImportError(f"blocked {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", deny_attune_author)
    status = staleness_cache.get_template_staleness(workspace, template)
    assert status == "unknown"


def test_check_staleness_exception_returns_unknown(tmp_path: Path) -> None:
    workspace = build_workspace(
        tmp_path,
        features={"auth": ["src/auth/**"]},
        sources={"src/auth/login.py": "x = 1\n"},
        templates={".help/templates/auth/concept.md": _stale_template()},
    )
    template = workspace / ".help/templates/auth/concept.md"

    with patch(
        "attune_author.staleness.check_staleness",
        side_effect=RuntimeError("boom"),
    ):
        status = staleness_cache.get_template_staleness(workspace, template)
    assert status == "unknown"


def test_degrade_logged_once_per_workspace(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    workspace = tmp_path
    (workspace / ".help").mkdir()
    template = workspace / ".help/templates/auth/concept.md"
    template.parent.mkdir(parents=True)
    template.write_text("body", encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="attune_gui.services.staleness_cache"):
        staleness_cache.get_template_staleness(workspace, template)
        staleness_cache.get_template_staleness(workspace, template)
        staleness_cache.get_template_staleness(workspace, template)

    degrade_logs = [r for r in caplog.records if "staleness check unavailable" in r.getMessage()]
    assert len(degrade_logs) == 1


def test_relative_template_path_resolves(tmp_path: Path) -> None:
    workspace = build_workspace(
        tmp_path,
        features={"auth": ["src/auth/**"]},
        sources={"src/auth/login.py": "x = 1\n"},
        templates={".help/templates/auth/concept.md": _stale_template()},
    )
    rel = Path(".help/templates/auth/concept.md")
    status = staleness_cache.get_template_staleness(workspace, rel)
    assert status == "stale"
