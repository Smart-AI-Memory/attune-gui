"""Hatchling build hook — bundles the Vite UI into the wheel.

When ``python -m build`` (or any tool that drives hatchling) runs, this hook
ensures the React UI is built and copied into the package's ``static/``
directory so the installed sidecar serves a real UI, not the placeholder.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class BundleUIHook(BuildHookInterface):
    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict) -> None:
        if self.target_name not in {"wheel", "sdist"}:
            return

        repo_root = Path(self.root)
        ui_dir = repo_root / "ui"
        dist_dir = ui_dir / "dist"
        static_dir = repo_root / "sidecar" / "attune_gui" / "static"

        if not ui_dir.is_dir():
            raise RuntimeError(f"Expected UI sources at {ui_dir}; cannot build attune-gui wheel.")

        if not (ui_dir / "node_modules").is_dir():
            subprocess.run(["npm", "install"], cwd=ui_dir, check=True)
        subprocess.run(["npm", "run", "build"], cwd=ui_dir, check=True)

        index_html = dist_dir / "index.html"
        if not index_html.is_file():
            raise RuntimeError(f"UI build did not produce {index_html}; aborting wheel build.")

        if static_dir.exists():
            shutil.rmtree(static_dir)
        shutil.copytree(dist_dir, static_dir)

        force_include = build_data.setdefault("force_include", {})
        for path in static_dir.rglob("*"):
            if path.is_file():
                rel = path.relative_to(repo_root)
                force_include[str(path)] = str(rel.relative_to("sidecar"))
