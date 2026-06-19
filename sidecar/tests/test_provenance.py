"""Unit tests for the template provenance/staleness service.

Pure Python — exercises compute_source_hash over temp fixtures (no
network, no LLM). Covers: fresh, stale, unbound (no feature / unknown
feature), sources-missing, and the hash-vs-source_hash fallback.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from attune_author.manifest import load_manifest
from attune_author.staleness import compute_source_hash
from attune_gui import editor_corpora, provenance


@pytest.fixture(autouse=True)
def _isolated_registry(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        editor_corpora,
        "_REGISTRY_PATH",
        tmp_path / ".attune" / "corpora.json",
        raising=False,
    )
    provenance._MANIFEST_CACHE.clear()


def _write(p: Path, text: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def _build_project(
    tmp_path: Path,
    *,
    files_glob: str = "src/auth/**",
    create_source: bool = True,
    feature: str = "auth",
) -> tuple[Path, Path]:
    root = tmp_path / "proj"
    help_dir = root / ".help"
    _write(
        help_dir / "features.yaml",
        f"version: 1\nfeatures:\n  {feature}:\n"
        f'    description: Auth\n    files: ["{files_glob}"]\n',
    )
    if create_source:
        _write(root / "src" / "auth" / "login.py", "def login():\n    return True\n")
    return root, help_dir


def _current_hash(help_dir: Path, feature: str = "auth") -> str:
    manifest = load_manifest(help_dir)
    digest, _matched = compute_source_hash(manifest.features[feature], help_dir.parent)
    return digest


def _template_text(
    *, feature: str | None, hash_field: str, hash_value: str, depth: str = "concept"
) -> str:
    lines = ["---", "type: concept", "name: Auth"]
    if feature is not None:
        lines.append(f"feature: {feature}")
    lines += [f"{hash_field}: {hash_value}", f"depth: {depth}", "---", "", "body", ""]
    return "\n".join(lines)


def _make_template(
    help_dir: Path,
    *,
    feature: str | None = "auth",
    hash_field: str = "source_hash",
    hash_value: str = "deadbeef",
    depth: str = "concept",
    feature_dir: str = "auth",
) -> Path:
    tmpl = help_dir / "templates" / feature_dir / f"{depth}.md"
    return _write(
        tmpl,
        _template_text(feature=feature, hash_field=hash_field, hash_value=hash_value, depth=depth),
    )


def _rel(root: Path, tmpl: Path) -> str:
    return str(tmpl.relative_to(root))


def _register(root: Path) -> str:
    return editor_corpora.register("Test", str(root)).id


def test_fresh_when_stored_hash_matches(tmp_path: Path) -> None:
    root, help_dir = _build_project(tmp_path)
    tmpl = _make_template(help_dir, hash_value=_current_hash(help_dir))
    res = provenance.resolve_provenance(_register(root), _rel(root, tmpl))
    assert res.status == "fresh"
    assert res.bound is True
    assert res.can_regenerate is True
    assert res.feature == "auth"
    assert res.source_files  # matched at least one file


def test_stale_when_stored_hash_differs(tmp_path: Path) -> None:
    root, help_dir = _build_project(tmp_path)
    tmpl = _make_template(help_dir, hash_value="0" * 16)
    res = provenance.resolve_provenance(_register(root), _rel(root, tmpl))
    assert res.status == "stale"
    assert res.can_regenerate is True


def test_unbound_when_no_feature_field(tmp_path: Path) -> None:
    root, help_dir = _build_project(tmp_path)
    tmpl = _make_template(help_dir, feature=None)
    res = provenance.resolve_provenance(_register(root), _rel(root, tmpl))
    assert res.status == "unbound"
    assert res.bound is False
    assert res.can_regenerate is False


def test_unbound_when_feature_not_in_manifest(tmp_path: Path) -> None:
    root, help_dir = _build_project(tmp_path)
    tmpl = _make_template(help_dir, feature="ghost", feature_dir="ghost")
    res = provenance.resolve_provenance(_register(root), _rel(root, tmpl))
    assert res.status == "unbound"
    assert res.feature == "ghost"
    assert res.can_regenerate is False
    assert "ghost" in (res.reason or "")


def test_sources_missing_when_globs_match_nothing(tmp_path: Path) -> None:
    root, help_dir = _build_project(tmp_path, files_glob="src/nope/**", create_source=False)
    tmpl = _make_template(help_dir, hash_value="whatever")
    res = provenance.resolve_provenance(_register(root), _rel(root, tmpl))
    assert res.status == "sources_missing"
    assert res.bound is True
    assert res.can_regenerate is False


def test_hash_field_fallback(tmp_path: Path) -> None:
    """A template using the legacy `hash` field is still detected as fresh."""
    root, help_dir = _build_project(tmp_path)
    tmpl = _make_template(help_dir, hash_field="hash", hash_value=_current_hash(help_dir))
    res = provenance.resolve_provenance(_register(root), _rel(root, tmpl))
    assert res.status == "fresh"
    assert res.stored_hash == _current_hash(help_dir)


def test_regen_inputs_raises_for_unbound(tmp_path: Path) -> None:
    root, help_dir = _build_project(tmp_path)
    tmpl = _make_template(help_dir, feature=None)
    with pytest.raises(PermissionError):
        provenance.regen_inputs(_register(root), _rel(root, tmpl))


def test_unknown_corpus_raises_lookup(tmp_path: Path) -> None:
    with pytest.raises(LookupError):
        provenance.resolve_provenance("nope", "x.md")


def test_path_escape_raises_value_error(tmp_path: Path) -> None:
    root, help_dir = _build_project(tmp_path)
    _make_template(help_dir)
    with pytest.raises(ValueError):
        provenance.resolve_provenance(_register(root), "../escape.md")


def test_manifest_cache_is_reused_on_second_call(tmp_path: Path) -> None:
    """Second resolve for the same help_dir hits the cache (mtime unchanged)."""
    root, help_dir = _build_project(tmp_path)
    tmpl = _make_template(help_dir, hash_value=_current_hash(help_dir))
    cid, rel = _register(root), _rel(root, tmpl)
    provenance._MANIFEST_CACHE.clear()
    provenance.resolve_provenance(cid, rel)  # populates the cache
    assert str(help_dir) in provenance._MANIFEST_CACHE
    res = provenance.resolve_provenance(cid, rel)  # cache hit
    assert res.status == "fresh"


def test_help_dir_resolved_via_nested_dot_help(tmp_path: Path) -> None:
    """A template outside .help still binds via an ancestor's .help/features.yaml."""
    root = tmp_path / "proj"
    help_dir = root / ".help"
    _write(
        help_dir / "features.yaml",
        'version: 1\nfeatures:\n  auth:\n    description: Auth\n    files: ["src/auth/**"]\n',
    )
    _write(root / "src" / "auth" / "login.py", "def login():\n    return True\n")
    tmpl = _write(
        root / "docs" / "auth-guide.md",
        _template_text(feature="auth", hash_field="source_hash", hash_value="000"),
    )
    res = provenance.resolve_provenance(_register(root), _rel(root, tmpl))
    assert res.bound is True
    assert res.feature == "auth"
    assert res.status in {"fresh", "stale"}


def test_unbound_when_no_features_yaml_anywhere(tmp_path: Path) -> None:
    root = tmp_path / "loose"
    tmpl = _write(
        root / "notes" / "page.md",
        _template_text(feature="auth", hash_field="source_hash", hash_value="000"),
    )
    res = provenance.resolve_provenance(_register(root), _rel(root, tmpl))
    assert res.status == "unbound"
    assert "features.yaml" in (res.reason or "")


def test_parse_frontmatter_edge_cases() -> None:
    pf = provenance._parse_frontmatter
    assert pf("no frontmatter here") == {}  # no leading ---
    assert pf("---") == {}  # no newline after opener
    assert pf("---\nkey: value\nbody with no close") == {}  # no closing ---
    assert pf("---\n: : bad: yaml: [\n---\n") == {}  # YAMLError
    assert pf("---\n- a\n- b\n---\n") == {}  # parses to a list, not a dict
    assert pf("---\nfeature: auth\n---\nbody") == {"feature": "auth"}
