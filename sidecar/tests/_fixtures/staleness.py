"""Test helpers for building a minimal workspace + manifest + templates.

attune-author's own ``help_dir`` / ``project_root`` fixtures live in
its private conftest and aren't published. This is a sidecar-local
copy scoped to what the staleness-cache tests need: build a workspace
under ``tmp_path`` with a ``features.yaml``, optional source files,
and optional template files under ``.help/templates/<feature>/``.
"""

from __future__ import annotations

from pathlib import Path


def build_workspace(
    tmp_path: Path,
    *,
    features: dict[str, list[str]] | None = None,
    sources: dict[str, str] | None = None,
    templates: dict[str, str] | None = None,
) -> Path:
    """Create a workspace at ``tmp_path`` and return its root.

    Args:
        tmp_path: pytest tmp_path fixture.
        features: ``{feature_name: [glob, ...]}`` for ``features.yaml``.
            Each glob is matched against ``sources``.
        sources: ``{rel_path_under_workspace: text_content}`` files
            written under the workspace (e.g. ``"src/auth/login.py"``).
        templates: ``{rel_path_under_workspace: text_content}`` files
            written under the workspace (typically under
            ``.help/templates/<feature>/...``). Caller is responsible
            for embedding a ``source_hash:`` frontmatter line if the
            test needs the template to read as fresh.
    """
    features = features or {}
    sources = sources or {}
    templates = templates or {}

    workspace = tmp_path
    help_dir = workspace / ".help"
    help_dir.mkdir(parents=True, exist_ok=True)

    yaml_lines = ["version: 1", "", "features:"]
    for name, globs in features.items():
        yaml_lines.append(f"  {name}:")
        yaml_lines.append(f'    description: "{name} feature"')
        yaml_lines.append("    files:")
        for g in globs:
            yaml_lines.append(f"      - {g}")
    (help_dir / "features.yaml").write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")

    for rel, body in sources.items():
        target = workspace / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")

    for rel, body in templates.items():
        target = workspace / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")

    return workspace
