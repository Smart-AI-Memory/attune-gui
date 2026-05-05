"""WebSocket + refactor routes for the template editor (M2 task #12).

Exposes:

- ``WS  /ws/corpus/<id>?path=<rel>`` — pushes ``file_changed`` events
  from the on-disk file watcher; sends ``duplicate_session`` to a
  second tab opening the same ``(corpus, path)`` key.
- ``POST /api/corpus/<id>/refactor/rename/preview`` — return a
  multi-file :class:`RenamePlan` (no disk writes).
- ``POST /api/corpus/<id>/refactor/rename/apply`` — apply a freshly
  computed plan; rolls back on partial failure.

WebSocket presence is tracked in :data:`_subscribers`. The first
connection on a given ``(corpus, path)`` owns an :class:`EditorSession`
that watches the file. Subsequent connections on the same key get a
``duplicate_session`` notice — they may stay connected (the route does
not force-close them) so the UI can render a read-only banner.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field
from starlette.websockets import WebSocketState

from attune_gui import editor_corpora
from attune_gui.editor_session import EditorSession

logger = logging.getLogger(__name__)

router = APIRouter(tags=["editor-ws"])


# -- WS subscriber registry ----------------------------------------


class _Subscriber:
    """One open WebSocket on a particular ``(corpus_id, rel_path)``."""

    __slots__ = ("websocket", "is_primary", "session", "_pump_task")

    def __init__(self, websocket: WebSocket, *, is_primary: bool) -> None:
        self.websocket = websocket
        self.is_primary = is_primary
        self.session: EditorSession | None = None
        self._pump_task: asyncio.Task | None = None


# Keyed by (corpus_id, rel_path). Lifetime = open WebSockets only.
_subscribers: dict[tuple[str, str], list[_Subscriber]] = {}


def _key(corpus_id: str, rel_path: str) -> tuple[str, str]:
    return (corpus_id, rel_path)


def _broadcast_to_others(
    key: tuple[str, str], origin: _Subscriber, message: dict[str, Any]
) -> list[asyncio.Task]:
    """Send ``message`` to all subscribers on ``key`` except ``origin``.

    Returns the spawned send tasks so callers can await them.
    """
    tasks: list[asyncio.Task] = []
    for sub in list(_subscribers.get(key, ())):
        if sub is origin:
            continue
        if sub.websocket.application_state != WebSocketState.CONNECTED:
            continue
        tasks.append(asyncio.create_task(sub.websocket.send_json(message)))
    return tasks


# -- WS route ------------------------------------------------------


@router.websocket("/ws/corpus/{corpus_id}")
async def corpus_ws(websocket: WebSocket, corpus_id: str, path: str) -> None:
    """File-watch + presence channel for one ``(corpus, path)`` editor tab."""
    entry = editor_corpora.get_corpus(corpus_id)
    if entry is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="unknown corpus")
        return

    root = Path(entry.path).resolve()
    candidate = (root / path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="path escapes root")
        return
    if not candidate.is_file():
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="template not found")
        return

    await websocket.accept()
    key = _key(corpus_id, path)
    bucket = _subscribers.setdefault(key, [])
    is_primary = not bucket
    sub = _Subscriber(websocket, is_primary=is_primary)
    bucket.append(sub)

    try:
        if not is_primary:
            await websocket.send_json({"type": "duplicate_session"})
            # Stay connected so the UI can show a read-only banner. The
            # tab will be closed by the user or the receive loop below.
            await _drain_until_close(websocket)
            return

        sub.session = EditorSession.load(candidate)
        sub.session.start()

        # Pump session events into the websocket.
        async def _pump() -> None:
            assert sub.session is not None
            try:
                while True:
                    event = await sub.session.next_event()
                    if websocket.application_state != WebSocketState.CONNECTED:
                        return
                    await websocket.send_json(event)
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 — pump must not crash the route
                logger.exception("editor_ws pump failed for %s", key)

        sub._pump_task = asyncio.create_task(_pump())

        await _drain_until_close(websocket)
    finally:
        await _teardown(key, sub)


async def _drain_until_close(websocket: WebSocket) -> None:
    """Block until the client closes the connection.

    The editor protocol is push-only from server → client, so we just
    wait for any incoming frame (which only ever signals close).
    """
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        return


async def _teardown(key: tuple[str, str], sub: _Subscriber) -> None:
    bucket = _subscribers.get(key)
    if bucket and sub in bucket:
        bucket.remove(sub)
    if bucket is not None and not bucket:
        _subscribers.pop(key, None)

    if sub._pump_task is not None:
        sub._pump_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await sub._pump_task

    if sub.session is not None:
        await sub.session.stop()


# -- rename refactor routes ----------------------------------------


class RenameRequest(BaseModel):
    old: str = Field(..., min_length=1)
    new: str = Field(..., min_length=1)
    kind: Literal["alias", "tag", "template_path"] = "alias"


@router.post("/api/corpus/{corpus_id}/refactor/rename/preview")
async def rename_preview(corpus_id: str, req: RenameRequest) -> dict[str, Any]:
    from attune_rag.editor import RenameCollisionError, plan_rename  # noqa: PLC0415

    try:
        corpus = editor_corpora.load_corpus(corpus_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    try:
        plan = plan_rename(corpus, req.old, req.new, req.kind)
    except RenameCollisionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "name_collision",
                "message": str(exc),
                "owning_path": exc.owning_path,
            },
        ) from exc
    except NotImplementedError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return plan.to_dict()


@router.post("/api/corpus/{corpus_id}/refactor/rename/apply")
async def rename_apply(corpus_id: str, req: RenameRequest) -> dict[str, Any]:
    from attune_rag.editor import (  # noqa: PLC0415
        RenameCollisionError,
        RenameError,
        apply_rename,
        plan_rename,
    )

    try:
        corpus = editor_corpora.load_corpus(corpus_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    try:
        plan = plan_rename(corpus, req.old, req.new, req.kind)
    except RenameCollisionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "name_collision",
                "message": str(exc),
                "owning_path": exc.owning_path,
            },
        ) from exc
    except NotImplementedError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    try:
        affected = apply_rename(corpus, plan)
    except RenameError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except OSError as exc:
        # Atomic-write failure mid-stream. _rename.apply_rename rolls
        # the earlier writes back from in-memory snapshots; we just
        # surface the failure so the client can retry.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "rename_io_error", "message": str(exc)},
        ) from exc

    # Notify any open editors on changed files.
    for rel_path in affected:
        key = _key(corpus_id, rel_path)
        for sub in list(_subscribers.get(key, ())):
            if sub.session is not None:
                new_hash = sub.session.current_disk_hash()
                if new_hash is None:
                    continue
                if sub.websocket.application_state != WebSocketState.CONNECTED:
                    continue
                with contextlib.suppress(Exception):
                    await sub.websocket.send_json({"type": "file_changed", "new_hash": new_hash})

    return {"affected_files": affected, "plan": plan.to_dict()}


__all__ = ["router"]
