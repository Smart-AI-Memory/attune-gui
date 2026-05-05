"""Tests for the ``attune_rag.editor`` dependency guard."""

from __future__ import annotations

import pytest
from attune_gui._editor_dep import require_editor_submodule
from fastapi import HTTPException


def test_returns_module_when_present() -> None:
    mod = require_editor_submodule("")
    assert mod.__name__ == "attune_rag.editor"


def test_returns_submodule_when_present() -> None:
    mod = require_editor_submodule("_schema")
    assert mod.__name__ == "attune_rag.editor._schema"


def test_raises_503_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulate the PyPI scenario where attune_rag.editor doesn't ship."""
    from attune_gui import _editor_dep

    def fake_import(name: str):
        raise ModuleNotFoundError(f"No module named {name!r}")

    monkeypatch.setattr(_editor_dep, "import_module", fake_import)

    with pytest.raises(HTTPException) as excinfo:
        require_editor_submodule("_rename")
    assert excinfo.value.status_code == 503
    detail = excinfo.value.detail
    assert isinstance(detail, dict)
    assert detail["code"] == "editor_backend_unavailable"
