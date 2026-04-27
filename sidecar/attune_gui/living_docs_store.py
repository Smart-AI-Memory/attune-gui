"""In-memory state for the Living Docs dashboard.

Tracks the doc registry (scanned from the workspace), the review queue
(auto-applied changes awaiting human sign-off), and quality scores from
the last smoke eval run. All state resets on sidecar restart — that is
intentional for the prototype; a persistent backend can be added later.
"""

from __future__ import annotations

import asyncio
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Depth → persona mapping
# Depths not in this map are assigned to "author" (internal/oversight docs).
# ---------------------------------------------------------------------------

DEPTH_PERSONA: dict[str, str] = {
    # End user — context-sensitive help
    "concept": "end_user",
    "quickstart": "end_user",
    "note": "end_user",
    "tip": "end_user",
    "faq": "end_user",
    # Developer — technical reference
    "reference": "developer",
    "comparison": "developer",
    # Support agent — operational docs
    "task": "support",
    "troubleshooting": "support",
    "error": "support",
    "warning": "support",
}

# Core depths that must exist for every feature — used to detect missing docs.
_CORE_DEPTHS = ("concept", "reference", "task")


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class DocEntry:
    id: str  # "{feature}/{depth}"
    feature: str
    depth: str
    persona: str  # end_user | developer | support | author
    status: str  # current | stale | missing
    path: str | None  # relative to project root; None when missing
    last_modified: str | None  # ISO 8601

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "feature": self.feature,
            "depth": self.depth,
            "persona": self.persona,
            "status": self.status,
            "path": self.path,
            "last_modified": self.last_modified,
        }


@dataclass
class ReviewItem:
    id: str
    doc_id: str
    feature: str
    depth: str
    persona: str
    trigger: str  # manual | git_hook | scheduled
    auto_applied_at: str  # ISO 8601
    reviewed: bool = False
    diff_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "doc_id": self.doc_id,
            "feature": self.feature,
            "depth": self.depth,
            "persona": self.persona,
            "trigger": self.trigger,
            "auto_applied_at": self.auto_applied_at,
            "reviewed": self.reviewed,
            "diff_summary": self.diff_summary,
        }


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------


class LivingDocsStore:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._docs: list[DocEntry] = []
        self._queue: list[ReviewItem] = []
        self._quality: dict[str, Any] = {}
        self._last_scan_at: str | None = None
        self._scanning: bool = False

    # -- Scan ----------------------------------------------------------------

    async def scan(self, project_root: Path, trigger: str = "manual") -> dict[str, Any]:
        if self._scanning:
            return {"status": "already_scanning"}
        self._scanning = True
        try:
            docs = await asyncio.to_thread(self._scan_sync, project_root)
            async with self._lock:
                self._docs = docs
                self._last_scan_at = _now()
            return {"status": "ok", "scanned": len(docs)}
        finally:
            self._scanning = False

    def _scan_sync(self, project_root: Path) -> list[DocEntry]:
        help_dir = project_root / ".help"
        templates_dir = help_dir / "templates"
        docs: list[DocEntry] = []
        stale_features: set[str] = set()
        known_features: list[str] = []

        # Load manifest for staleness info — graceful if not present.
        try:
            from attune_author.manifest import load_manifest
            from attune_author.staleness import check_staleness

            manifest = load_manifest(help_dir)
            known_features = [getattr(f, "name", str(f)) for f in manifest.features]
            try:
                report = check_staleness(manifest, help_dir, project_root)
                stale_features = set(report.stale_features)
            except Exception:
                pass
        except Exception:
            pass

        seen_ids: set[str] = set()

        # Walk existing template files.
        if templates_dir.is_dir():
            for md_file in sorted(templates_dir.rglob("*.md")):
                try:
                    parts = md_file.relative_to(templates_dir).parts
                    if len(parts) != 2:
                        continue
                    feature_name, depth_filename = parts
                    depth = depth_filename[:-3]
                    persona = DEPTH_PERSONA.get(depth, "author")
                    doc_id = f"{feature_name}/{depth}"
                    seen_ids.add(doc_id)
                    try:
                        mtime = datetime.fromtimestamp(
                            md_file.stat().st_mtime, tz=timezone.utc
                        ).isoformat()
                    except Exception:
                        mtime = None
                    docs.append(
                        DocEntry(
                            id=doc_id,
                            feature=feature_name,
                            depth=depth,
                            persona=persona,
                            status="stale" if feature_name in stale_features else "current",
                            path=str(md_file.relative_to(project_root)),
                            last_modified=mtime,
                        )
                    )
                except Exception:
                    continue

        # Add missing docs for known features × core depths.
        for feature_name in known_features:
            for depth in _CORE_DEPTHS:
                doc_id = f"{feature_name}/{depth}"
                if doc_id not in seen_ids:
                    docs.append(
                        DocEntry(
                            id=doc_id,
                            feature=feature_name,
                            depth=depth,
                            persona=DEPTH_PERSONA.get(depth, "author"),
                            status="missing",
                            path=None,
                            last_modified=None,
                        )
                    )

        return docs

    # -- Health --------------------------------------------------------------

    async def get_health(self) -> dict[str, Any]:
        async with self._lock:
            docs = list(self._docs)
            quality = dict(self._quality)
            last_scan = self._last_scan_at
            scanning = self._scanning

        by_persona: dict[str, dict[str, int]] = {}
        for doc in docs:
            p = doc.persona
            if p not in by_persona:
                by_persona[p] = {"total": 0, "current": 0, "stale": 0, "missing": 0}
            by_persona[p]["total"] += 1
            by_persona[p][doc.status] = by_persona[p].get(doc.status, 0) + 1

        return {
            "summary": {
                "total": len(docs),
                "current": sum(1 for d in docs if d.status == "current"),
                "stale": sum(1 for d in docs if d.status == "stale"),
                "missing": sum(1 for d in docs if d.status == "missing"),
            },
            "by_persona": by_persona,
            "quality": quality,
            "last_scan_at": last_scan,
            "scanning": scanning,
        }

    # -- Doc registry --------------------------------------------------------

    async def list_docs(self, persona: str | None = None) -> list[dict[str, Any]]:
        async with self._lock:
            docs = list(self._docs)
        if persona and persona != "author":
            docs = [d for d in docs if d.persona == persona]
        return [d.to_dict() for d in docs]

    # -- Review queue --------------------------------------------------------

    async def add_to_queue(self, doc_id: str, trigger: str, project_root: Path) -> ReviewItem:
        parts = doc_id.split("/", 1)
        feature = parts[0]
        depth = parts[1] if len(parts) > 1 else "concept"
        persona = DEPTH_PERSONA.get(depth, "author")
        diff_summary = await asyncio.to_thread(self._git_diff_summary, project_root, feature, depth)
        item = ReviewItem(
            id=str(uuid.uuid4()),
            doc_id=doc_id,
            feature=feature,
            depth=depth,
            persona=persona,
            trigger=trigger,
            auto_applied_at=_now(),
            diff_summary=diff_summary,
        )
        async with self._lock:
            self._queue.append(item)
        return item

    def _git_diff_summary(self, project_root: Path, feature: str, depth: str) -> str:
        path = project_root / ".help" / "templates" / feature / f"{depth}.md"
        if not path.exists():
            return ""
        try:
            result = subprocess.run(
                ["git", "diff", "--stat", "HEAD", "--", str(path)],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip() or "New file (untracked)"
        except Exception:
            return ""

    async def list_queue(
        self,
        persona: str | None = None,
        reviewed: bool | None = None,
    ) -> list[dict[str, Any]]:
        async with self._lock:
            items = list(self._queue)
        if persona and persona != "author":
            items = [i for i in items if i.persona == persona]
        if reviewed is not None:
            items = [i for i in items if i.reviewed == reviewed]
        return [i.to_dict() for i in sorted(items, key=lambda x: x.auto_applied_at, reverse=True)]

    async def approve(self, item_id: str) -> bool:
        async with self._lock:
            for item in self._queue:
                if item.id == item_id:
                    item.reviewed = True
                    return True
        return False

    async def revert(self, item_id: str, project_root: Path) -> dict[str, Any]:
        async with self._lock:
            item = next((i for i in self._queue if i.id == item_id), None)
        if not item:
            return {"ok": False, "error": "Item not found"}
        path = project_root / ".help" / "templates" / item.feature / f"{item.depth}.md"
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["git", "checkout", "HEAD", "--", str(path)],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                async with self._lock:
                    self._queue = [i for i in self._queue if i.id != item_id]
                return {"ok": True}
            return {"ok": False, "error": result.stderr.strip() or "git checkout failed"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # -- Quality -------------------------------------------------------------

    async def set_quality(self, scores: dict[str, Any]) -> None:
        async with self._lock:
            self._quality = scores


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


_store: LivingDocsStore | None = None


def get_store() -> LivingDocsStore:
    global _store
    if _store is None:
        _store = LivingDocsStore()
    return _store
