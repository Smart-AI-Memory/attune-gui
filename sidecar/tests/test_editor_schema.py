"""Tests for /api/editor/template-schema (M3 #16)."""

from __future__ import annotations

from attune_gui.app import create_app
from fastapi.testclient import TestClient


def test_template_schema_endpoint() -> None:
    """Returns the JSON schema bundled with attune-rag."""
    client = TestClient(create_app())
    res = client.get("/api/editor/template-schema")
    assert res.status_code == 200
    schema = res.json()
    assert schema["title"] == "Attune Template Frontmatter"
    assert "properties" in schema
    assert "type" in schema["properties"]
    assert schema["properties"]["type"]["enum"] == ["concept", "task", "reference", "guide"]
    assert schema["required"] == ["type", "name"]
