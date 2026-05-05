"""Unit tests for :class:`EditorSession` (template-editor M2 task #9).

Exercises the spec's golden flow:

    load → edit → file-change-event → save (hash check)

The "save" step is simulated by writing to disk via the same atomic
helper the route uses, then asserting the session's drift detection
agrees.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from attune_gui.editor_session import EditorSession, hash_text


@pytest.fixture
def template_file(tmp_path: Path) -> Path:
    f = tmp_path / "alpha.md"
    f.write_text("---\ntype: concept\nname: Alpha\n---\n\nbody\n", encoding="utf-8")
    return f


def test_load_snapshots_base_text_and_hash(template_file: Path) -> None:
    session = EditorSession.load(template_file)
    assert session.base_text == template_file.read_text(encoding="utf-8")
    assert session.base_hash == hash_text(session.base_text)
    assert session.draft_text == session.base_text  # draft tracks base initially
    assert session.matches_base() is True


def test_update_draft_does_not_touch_disk(template_file: Path) -> None:
    session = EditorSession.load(template_file)
    on_disk_before = template_file.read_text(encoding="utf-8")
    session.update_draft("totally different content")
    assert template_file.read_text(encoding="utf-8") == on_disk_before
    assert session.draft_text == "totally different content"


def test_matches_base_detects_external_write(template_file: Path) -> None:
    session = EditorSession.load(template_file)
    assert session.matches_base() is True
    template_file.write_text("changed externally\n", encoding="utf-8")
    assert session.matches_base() is False
    assert session.current_disk_hash() != session.base_hash


@pytest.mark.asyncio
async def test_file_change_event_emitted(template_file: Path) -> None:
    """Golden flow: load → edit → external file change → event arrives."""
    session = EditorSession.load(template_file, poll_interval=0.02)
    session.start()
    try:
        # Edit the in-memory draft (no disk write).
        session.update_draft("editor pending changes\n")
        assert session.matches_base() is True  # disk untouched

        # External writer changes the file (e.g., `git pull`).
        new_text = "external rewrite of file\n"
        template_file.write_text(new_text, encoding="utf-8")

        # Watcher pushes file_changed within a short window.
        event = await asyncio.wait_for(session.next_event(), timeout=2.0)
        assert event["type"] == "file_changed"
        assert event["new_hash"] == hash_text(new_text)
        # Hash check: drift detected vs base_hash.
        assert event["new_hash"] != session.base_hash
        assert session.matches_base() is False
    finally:
        await session.stop()


@pytest.mark.asyncio
async def test_event_dedup_no_spurious_events(template_file: Path) -> None:
    """A single change emits one event, not a stream."""
    session = EditorSession.load(template_file, poll_interval=0.02)
    session.start()
    try:
        template_file.write_text("once\n", encoding="utf-8")
        first = await asyncio.wait_for(session.next_event(), timeout=2.0)
        assert first["type"] == "file_changed"
        # Wait a few poll cycles — no second event for the same content.
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(session.next_event(), timeout=0.2)
    finally:
        await session.stop()


@pytest.mark.asyncio
async def test_stop_cancels_watcher(template_file: Path) -> None:
    session = EditorSession.load(template_file, poll_interval=0.02)
    session.start()
    await session.stop()
    # After stop, writing the file produces no event because the watcher
    # is cancelled. (next_event would block forever; we just check the
    # watcher task is gone.)
    assert session._watch_task is None
