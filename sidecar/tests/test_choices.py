"""Coverage for `routes/choices.py` — the Commands page's
`ui:choicesUrl` data source.

Endpoint behavior:

- ``GET /api/author/features?help_dir=<dir>`` lists feature names
  from ``<dir>/features.yaml``.
- ``GET /api/author/features?project_path=<root>`` resolves the
  manifest at ``<root>/.help/features.yaml``.
- 400 on bogus combinations (both / neither query param).
- 404 if the dir or manifest is missing.
- 400 if the manifest is malformed.
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


def _write_manifest(root: Path, features: list[str]) -> Path:
    """Drop a minimal `features.yaml` under ``root/.help/``."""
    help_dir = root / ".help"
    help_dir.mkdir(parents=True, exist_ok=True)
    lines = ["version: 1", "features:"]
    for name in features:
        lines.append(f"  {name}:")
        lines.append(f"    description: {name}")
        lines.append("    files:")
        lines.append(f"      - {name}/**")
    (help_dir / "features.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return help_dir


def test_features_listed_from_help_dir(client: TestClient, tmp_path: Path) -> None:
    help_dir = _write_manifest(tmp_path, ["alpha", "beta", "gamma"])
    r = client.get(
        "/api/author/features",
        params={"help_dir": str(help_dir)},
        headers=HDR,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["choices"] == ["alpha", "beta", "gamma"]
    assert body["help_dir"] == str(help_dir.resolve())


def test_features_listed_from_project_path(client: TestClient, tmp_path: Path) -> None:
    _write_manifest(tmp_path, ["one", "two"])
    r = client.get(
        "/api/author/features",
        params={"project_path": str(tmp_path)},
        headers=HDR,
    )
    assert r.status_code == 200, r.text
    assert r.json()["choices"] == ["one", "two"]


def test_neither_arg_returns_400(client: TestClient) -> None:
    r = client.get("/api/author/features", headers=HDR)
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "missing_arg"


def test_both_args_return_400(client: TestClient, tmp_path: Path) -> None:
    r = client.get(
        "/api/author/features",
        params={"help_dir": str(tmp_path), "project_path": str(tmp_path)},
        headers=HDR,
    )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "ambiguous_args"


def test_help_dir_missing_returns_404(client: TestClient) -> None:
    r = client.get(
        "/api/author/features",
        params={"help_dir": "/no/such/dir"},
        headers=HDR,
    )
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "help_dir_missing"


def test_manifest_missing_returns_404(client: TestClient, tmp_path: Path) -> None:
    # Dir exists but has no features.yaml.
    (tmp_path / ".help").mkdir()
    r = client.get(
        "/api/author/features",
        params={"help_dir": str(tmp_path / ".help")},
        headers=HDR,
    )
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "manifest_missing"


def test_manifest_malformed_returns_400(client: TestClient, tmp_path: Path) -> None:
    help_dir = tmp_path / ".help"
    help_dir.mkdir()
    # Top-level isn't a mapping → ValueError in load_manifest.
    (help_dir / "features.yaml").write_text("- just a list\n", encoding="utf-8")
    r = client.get(
        "/api/author/features",
        params={"help_dir": str(help_dir)},
        headers=HDR,
    )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "manifest_malformed"


def test_choicesurl_present_in_author_generate_schema(client: TestClient) -> None:
    """Regression: the dashboard form relies on this extension to
    populate the `feature` datalist. If it goes missing, the field
    silently degrades to a free-text input again."""
    r = client.get("/api/commands", headers=HDR)
    assert r.status_code == 200
    by_name = {c["name"]: c for c in r.json()["commands"]}
    feature = by_name["author.generate"]["args_schema"]["properties"]["feature"]
    assert feature["ui:choicesUrl"] == "/api/author/features?help_dir={help_dir}"
    feature2 = by_name["author.regen"]["args_schema"]["properties"]["feature"]
    assert feature2["ui:choicesUrl"] == "/api/author/features?project_path={project_path}"
