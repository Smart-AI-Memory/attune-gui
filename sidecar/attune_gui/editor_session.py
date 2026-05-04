"""Per-tab editor session (template-editor M2 task #9).

An :class:`EditorSession` tracks the in-memory state for one browser
tab editing one template file:

- ``base_text`` / ``base_hash`` — the snapshot the client received on
  load. The server uses ``base_hash`` to detect drift on save.
- ``draft_text`` — the latest draft the client sent. Optional; the
  session works as a pure file watcher even if the client never pushes
  drafts.
- An asyncio event queue that emits ``{"type": "file_changed",
  "new_hash": <16-char>}`` when the on-disk file diverges from the
  last hash the session observed.

The session is GC'd when its WebSocket closes (the route is the only
caller; see :mod:`attune_gui.routes.editor_ws`).

Design choices
--------------

We poll ``mtime`` + recompute ``sha256`` on change rather than using
``watchfiles``. Polling at ~100ms keeps the implementation trivially
testable (no inotify/FSEvents semantics to mock) and the cost is
negligible for the one-file-per-tab case.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
from dataclasses import dataclass, field
from pathlib import Path

_HASH_LEN = 16


def hash_text(text: str) -> str:
    """Return the 16-char sha256 prefix used as the session's optimistic
    concurrency token. Matches :func:`routes.editor_template._hash_text`.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:_HASH_LEN]


@dataclass
class EditorSession:
    """In-process state for a single ``(corpus, path)`` editing tab.

    Construct via :meth:`load`. Call :meth:`start` to begin watching
    the file, and :meth:`stop` (typically from a ``finally`` block in
    the WS handler) to cancel the watcher and release resources.
    """

    abs_path: Path
    base_text: str
    base_hash: str
    draft_text: str = field(init=False)
    # Internal: last hash we observed on disk; used to dedupe events.
    _last_disk_hash: str = field(init=False)
    _events: asyncio.Queue = field(default_factory=asyncio.Queue, init=False)
    _watch_task: asyncio.Task | None = field(default=None, init=False)
    _stopped: asyncio.Event = field(default_factory=asyncio.Event, init=False)
    poll_interval: float = 0.1

    def __post_init__(self) -> None:
        self.draft_text = self.base_text
        self._last_disk_hash = self.base_hash

    # ---- construction -------------------------------------------------

    @classmethod
    def load(cls, abs_path: Path, *, poll_interval: float = 0.1) -> EditorSession:
        """Read ``abs_path`` and snapshot it as the base state."""
        text = abs_path.read_text(encoding="utf-8")
        return cls(
            abs_path=abs_path,
            base_text=text,
            base_hash=hash_text(text),
            poll_interval=poll_interval,
        )

    # ---- draft / disk ------------------------------------------------

    def update_draft(self, text: str) -> None:
        """Replace the in-memory draft. The disk is not touched."""
        self.draft_text = text

    def current_disk_hash(self) -> str | None:
        """Hash of the on-disk file *now*. ``None`` if the file is gone."""
        try:
            text = self.abs_path.read_text(encoding="utf-8")
        except (FileNotFoundError, OSError):
            return None
        return hash_text(text)

    def matches_base(self) -> bool:
        """``True`` iff disk still matches the base snapshot."""
        return self.current_disk_hash() == self.base_hash

    def rebase(self) -> None:
        """Adopt the current disk text as the new base. Used after a
        save lands or after the user accepts ``Reload from disk`` in
        conflict mode."""
        text = self.abs_path.read_text(encoding="utf-8")
        self.base_text = text
        self.base_hash = hash_text(text)
        self.draft_text = text
        self._last_disk_hash = self.base_hash

    # ---- watcher -----------------------------------------------------

    def start(self) -> None:
        """Begin polling the file for external changes. Idempotent."""
        if self._watch_task is not None and not self._watch_task.done():
            return
        self._stopped.clear()
        self._watch_task = asyncio.create_task(self._watch())

    async def stop(self) -> None:
        """Cancel the watcher and wait for it to finish."""
        self._stopped.set()
        task = self._watch_task
        if task is None:
            return
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        self._watch_task = None

    async def next_event(self) -> dict:
        """Await the next watcher event (e.g., ``file_changed``)."""
        return await self._events.get()

    async def _watch(self) -> None:
        try:
            while not self._stopped.is_set():
                try:
                    await asyncio.wait_for(self._stopped.wait(), timeout=self.poll_interval)
                    return
                except asyncio.TimeoutError:
                    pass
                disk_hash = self.current_disk_hash()
                if disk_hash is None or disk_hash == self._last_disk_hash:
                    continue
                self._last_disk_hash = disk_hash
                await self._events.put({"type": "file_changed", "new_hash": disk_hash})
        except asyncio.CancelledError:
            raise


__all__ = ["EditorSession", "hash_text"]
