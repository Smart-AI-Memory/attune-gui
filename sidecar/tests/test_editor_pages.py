"""Tests for /editor HTML shell + Vite manifest reader."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from attune_gui.routes import editor_pages


def test_read_bundle_assets_returns_sentinel_when_manifest_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """No manifest = developer hasn't run `make build-editor`. Return sentinels
    so the editor page still renders; the broken URL surfaces in the browser."""
    monkeypatch.setattr(editor_pages, "_MANIFEST_PATH", tmp_path / "missing.json")
    js, css = editor_pages._read_bundle_assets()
    assert js == "dev.js"
    assert css == "dev.css"


def test_read_bundle_assets_returns_hashed_filenames_from_manifest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """With a valid manifest, return the hashed JS + CSS filenames."""
    manifest = tmp_path / ".vite" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "src/main.ts": {"file": "editor-AbCdEf.js", "css": ["style-XyZ.css"]},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(editor_pages, "_MANIFEST_PATH", manifest)
    js, css = editor_pages._read_bundle_assets()
    assert js == "editor-AbCdEf.js"
    assert css == "style-XyZ.css"


def test_read_bundle_assets_prefers_explicit_style_entry(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """If the manifest has a separate style.css entry, prefer it over main.ts.css."""
    manifest = tmp_path / ".vite" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps(
            {
                "src/main.ts": {"file": "editor-Hash.js", "css": ["fallback.css"]},
                "style.css": {"file": "preferred.css"},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(editor_pages, "_MANIFEST_PATH", manifest)
    _, css = editor_pages._read_bundle_assets()
    assert css == "preferred.css"


def test_read_bundle_assets_falls_back_on_corrupt_manifest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog
) -> None:
    """A corrupt manifest logs a warning and returns sentinels."""
    manifest = tmp_path / "manifest.json"
    manifest.write_text("not json {", encoding="utf-8")
    monkeypatch.setattr(editor_pages, "_MANIFEST_PATH", manifest)
    with caplog.at_level("WARNING"):
        js, css = editor_pages._read_bundle_assets()
    assert (js, css) == ("dev.js", "dev.css")
    assert any("Failed to read editor manifest" in r.message for r in caplog.records)
