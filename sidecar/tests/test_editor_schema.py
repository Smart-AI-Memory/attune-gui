"""Tests for /api/editor/template-schema (M3 #16)."""

from __future__ import annotations

from attune_gui.app import create_app
from fastapi.testclient import TestClient


def test_template_schema_endpoint() -> None:
    """Returns the JSON schema bundled with attune-rag.

    The enum is pinned in attune-rag's own schema test
    (``test_type_enum_covers_all_corpus_kinds``) — here we just confirm
    the proxy returns it intact and the well-known kinds are present.
    Adding a check on every enum entry would couple this test to
    schema evolution without a corresponding behavioural payoff.
    """
    client = TestClient(create_app())
    res = client.get("/api/editor/template-schema")
    assert res.status_code == 200
    schema = res.json()
    assert schema["title"] == "Attune Template Frontmatter"
    assert "properties" in schema
    assert "type" in schema["properties"]
    enum = set(schema["properties"]["type"]["enum"])
    # Spot-check both the original four and the kinds added when the
    # schema was reconciled with the corpus.
    for kind in {"concept", "task", "reference", "guide", "quickstart", "faq", "warning"}:
        assert kind in enum, f"missing {kind!r} from /api/editor/template-schema"
    assert schema["required"] == ["type", "name"]
