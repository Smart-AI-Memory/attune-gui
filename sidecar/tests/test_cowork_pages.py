"""Smoke tests for the Jinja2-rendered HTML pages.

Each page is hit with seeded data and asserted on:
  - status code
  - presence of the sidebar nav (via "Attune" brand)
  - the active nav slug is highlighted
  - core page content is present in the HTML
"""

from __future__ import annotations

from pathlib import Path

import pytest
from attune_gui.app import create_app
from fastapi.testclient import TestClient

HDR = {"Origin": "http://localhost:5173"}


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


# ---------------------------------------------------------------------------
# Root + nav
# ---------------------------------------------------------------------------


def test_root_redirects_to_dashboard(client: TestClient) -> None:
    r = client.get("/", headers=HDR, follow_redirects=False)
    assert r.status_code in (307, 308)
    assert r.headers["location"] == "/dashboard"


def test_dashboard_renders_sidebar(client: TestClient) -> None:
    r = client.get("/dashboard", headers=HDR)
    assert r.status_code == 200
    assert "Attune" in r.text
    # All seven nav items present
    for label in (
        "Health",
        "Templates",
        "Specs",
        "Summaries",
        "Living Docs",
        "Commands",
        "Jobs",
    ):
        assert label in r.text


def test_dashboard_health_marks_active(client: TestClient) -> None:
    r = client.get("/dashboard", headers=HDR)
    assert 'data-slug="health"' in r.text
    # active class applied to the health nav link
    assert 'class="nav-link active"' in r.text


# ---------------------------------------------------------------------------
# Per-page status checks (no seed required — pages must not 500 when empty)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "/dashboard",
        "/dashboard/templates",
        "/dashboard/specs",
        "/dashboard/summaries",
        "/dashboard/living-docs",
        "/dashboard/commands",
        "/dashboard/jobs",
    ],
)
def test_page_returns_200(client: TestClient, path: str) -> None:
    r = client.get(path, headers=HDR)
    assert r.status_code == 200, f"{path} returned {r.status_code}: {r.text[:200]}"


# ---------------------------------------------------------------------------
# Specs page renders seeded data
# ---------------------------------------------------------------------------


def test_specs_page_lists_seeded_features(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from attune_gui.routes import cowork_specs

    specs_root = tmp_path / "specs"
    feat = specs_root / "alpha"
    feat.mkdir(parents=True)
    (feat / "requirements.md").write_text("# spec\n\n**Status**: approved\n")

    monkeypatch.setattr(cowork_specs, "_specs_root", lambda: specs_root)

    r = client.get("/dashboard/specs", headers=HDR)
    assert r.status_code == 200
    assert "alpha" in r.text
    assert "approved" in r.text


# ---------------------------------------------------------------------------
# Templates page renders seeded data + manual flag
# ---------------------------------------------------------------------------


def test_templates_page_lists_seeded_with_manual_flag(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from attune_gui.routes import cowork_templates

    root = tmp_path / "templates-root"
    root.mkdir()
    (root / "alpha.md").write_text("---\nmanual: true\n---\nbody")
    (root / "beta.md").write_text("---\n---\nbody")

    monkeypatch.setattr(cowork_templates, "_templates_root", lambda: root)

    r = client.get("/dashboard/templates", headers=HDR)
    assert r.status_code == 200
    assert "alpha.md" in r.text
    assert "beta.md" in r.text
    # Pin checkbox present for both
    assert r.text.count("data-pin-path=") == 2
    # Filter chips
    assert "AI-generated" in r.text
    assert "Manual" in r.text


def test_templates_page_filter_chip(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from attune_gui.routes import cowork_templates

    root = tmp_path / "templates-root"
    root.mkdir()
    (root / "alpha.md").write_text("---\nmanual: true\n---\nbody")
    (root / "beta.md").write_text("---\n---\nbody")

    monkeypatch.setattr(cowork_templates, "_templates_root", lambda: root)

    r = client.get("/dashboard/templates?filter=manual", headers=HDR)
    assert r.status_code == 200
    assert "alpha.md" in r.text
    assert "beta.md" not in r.text


# ---------------------------------------------------------------------------
# Preview page renders rendered HTML
# ---------------------------------------------------------------------------


def test_preview_page_renders_markdown(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from attune_gui.routes import cowork_specs

    root = tmp_path / "specs"
    feat = root / "feature-a"
    feat.mkdir(parents=True)
    (feat / "requirements.md").write_text("# Heading\n\nBody text here.")

    monkeypatch.setattr(cowork_specs, "_specs_root", lambda: root)

    r = client.get("/dashboard/preview?root=specs&path=feature-a/requirements.md", headers=HDR)
    assert r.status_code == 200
    assert "Heading" in r.text
    assert "Body text here" in r.text
    # Editor textarea present with raw content
    assert "<textarea" in r.text


def test_preview_page_no_path_shows_message(client: TestClient) -> None:
    r = client.get("/dashboard/preview", headers=HDR)
    assert r.status_code == 200
    assert "No file path" in r.text


# ---------------------------------------------------------------------------
# Commands page — regression coverage for the args-schema embed
# ---------------------------------------------------------------------------


def test_commands_page_embeds_args_schema_per_command(client: TestClient) -> None:
    """Each command card must carry a parseable JSON schema script tag.

    Regression: an earlier version embedded the schema as a `data-schema`
    attribute via Jinja's ``{{ x | tojson | e }}``. ``tojson`` returns
    Markup-safe content that bypasses ``|e``, so raw ``"`` ended up
    inside the attribute value and broke at the first quote — the JS
    only saw ``{`` and `author.generate` always 400'd with
    "Missing required args: feature" because the modal couldn't
    render its form. The fix moves the schema into a sibling
    ``<script type="application/json">`` tag.
    """
    import json
    import re

    r = client.get("/dashboard/commands?profile=author", headers=HDR)
    assert r.status_code == 200, r.text[:200]
    assert 'data-name="author.generate"' in r.text
    # Pull every cmd-schema script and verify each parses + has the
    # expected shape.
    script_re = re.compile(
        r'<script type="application/json" class="cmd-schema" data-name="([^"]+)">'
        r"(.*?)</script>",
        re.DOTALL,
    )
    matches = script_re.findall(r.text)
    assert matches, "no cmd-schema scripts rendered on the commands page"

    by_name = {name: json.loads(payload) for name, payload in matches}
    assert "author.generate" in by_name
    schema = by_name["author.generate"]
    assert schema["type"] == "object"
    assert schema["required"] == ["feature"]
    # Spot-check a known property.
    assert "feature" in schema["properties"]
    # Old bug check: the schema MUST NOT also be present as a raw
    # data-schema attribute (would suggest a regression to the
    # broken embed).
    assert 'data-schema="' not in r.text


def test_commands_page_renders_browse_buttons_for_path_widgets(client: TestClient) -> None:
    """Path-typed args should get a `Browse…` button + picker wiring.

    Regression: an earlier version rendered every string as a bare
    text input. Users had to type absolute paths blind, and the
    relative defaults (`.help`, `.`) silently resolved against the
    sidecar's CWD instead of the project root — hard to tell from
    a typo, easy to misconfigure.
    """
    r = client.get("/dashboard/commands?profile=author", headers=HDR)
    assert r.status_code == 200
    # The HTML carries the JS that renders the button at runtime,
    # not the button itself (the form is built client-side from the
    # schema). What we *can* assert at render time is that the JS
    # block defines `openPathPicker` and that the schemas mark the
    # right fields with `ui:widget: "path"`.
    assert "openPathPicker" in r.text
    assert "cmd-path-browse" in r.text  # CSS class referenced by the JS
    # Schemas must declare the path-widget hint for the targeted fields.
    api = client.get("/api/commands?profile=author", headers=HDR).json()
    by = {c["name"]: c for c in api["commands"]}
    gen_props = by["author.generate"]["args_schema"]["properties"]
    assert gen_props["help_dir"].get("ui:widget") == "path"
    assert gen_props["project_root"].get("ui:widget") == "path"
