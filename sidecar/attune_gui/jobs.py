"""In-memory job registry with asyncio-based lifecycle + cancellation.

A "job" is one invocation of a named command. The registry holds jobs in
a dict keyed by uuid, each with status, logs, result, and a backing
asyncio.Task. Cancellation uses Task.cancel() which propagates
CancelledError into the executor; executors that want graceful cleanup
should await a checkpoint (e.g. `await asyncio.sleep(0)`) between chunks
of work.

Sync Python libraries (attune_rag, attune_author) are executed via
asyncio.to_thread(). A cancelled asyncio task won't interrupt in-flight
sync code on the thread, but it does prevent subsequent scheduled
work from running — good enough for loops that cancel between kinds.

Deliberately minimal. If this grows teeth (persistence, multi-process,
log streaming to multiple consumers), swap for something like RQ or
Celery — but for a single-user localhost sidecar, an in-memory dict
is honest.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

logger = logging.getLogger(__name__)

JobStatus = Literal["pending", "running", "completed", "errored", "cancelled"]


@dataclass
class Job:
    id: str
    name: str
    args: dict[str, Any]
    status: JobStatus = "pending"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    finished_at: datetime | None = None
    output_lines: list[str] = field(default_factory=list)
    result: Any | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable snapshot of this job for the API."""
        return {
            "id": self.id,
            "name": self.name,
            "args": self.args,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "output_lines": list(self.output_lines),
            "result": self.result,
            "error": self.error,
        }


class JobContext:
    """Passed into executors so they can emit log lines."""

    def __init__(self, job: Job) -> None:
        self.job = job
        self.job_id = job.id

    def log(self, line: str) -> None:
        """Append a line to the job's output buffer (visible in the UI)."""
        self.job.output_lines.append(line)
        logger.debug("job %s: %s", self.job.id, line)


ExecutorFn = Callable[[dict[str, Any], JobContext], Awaitable[Any]]


class JobRegistry:
    """Process-wide registry. One instance per app (see deps.py)."""

    def __init__(self, max_jobs: int = 200) -> None:
        self._jobs: dict[str, Job] = {}
        self._tasks: dict[str, asyncio.Task[Any]] = {}
        self._max_jobs = max_jobs

    def list_jobs(self) -> list[Job]:
        """All jobs, newest first (sorted by ``created_at`` descending)."""
        return sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)

    def get(self, job_id: str) -> Job | None:
        """Return the job with this id, or None."""
        return self._jobs.get(job_id)

    async def start(self, name: str, args: dict[str, Any], executor: ExecutorFn) -> Job:
        """Register and launch a job; the executor runs in a background asyncio task."""
        job = Job(id=str(uuid.uuid4()), name=name, args=args)
        self._jobs[job.id] = job
        self._trim()

        task = asyncio.create_task(self._run(job, executor))
        self._tasks[job.id] = task
        return job

    def cancel(self, job_id: str) -> bool:
        """Request cancellation of a running job. Returns False if it isn't running."""
        task = self._tasks.get(job_id)
        if task is None or task.done():
            return False
        task.cancel()
        return True

    async def _run(self, job: Job, executor: ExecutorFn) -> None:
        ctx = JobContext(job)
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        ctx.log(f"job started: {job.name}")
        try:
            job.result = await executor(job.args, ctx)
            job.status = "completed"
            ctx.log("job completed")
        except asyncio.CancelledError:
            job.status = "cancelled"
            ctx.log("job cancelled")
            # Swallow the CancelledError — we've recorded the state.
            # Re-raising would bubble to the asyncio task supervisor and
            # spam warnings about unhandled cancellation.
        except Exception as exc:  # noqa: BLE001 — boundary: errors become job state
            job.status = "errored"
            job.error = f"{type(exc).__name__}: {exc}"
            ctx.log(f"job errored: {job.error}")
            logger.exception("executor failed for job %s (%s)", job.id, job.name)
        finally:
            job.finished_at = datetime.now(timezone.utc)
            self._tasks.pop(job.id, None)

    def _trim(self) -> None:
        """Drop oldest finished jobs once we exceed max_jobs."""
        if len(self._jobs) <= self._max_jobs:
            return
        finished = sorted(
            (j for j in self._jobs.values() if j.status in {"completed", "errored", "cancelled"}),
            key=lambda j: j.finished_at or j.created_at,
        )
        overflow = len(self._jobs) - self._max_jobs
        for old in finished[:overflow]:
            self._jobs.pop(old.id, None)


_REGISTRY: JobRegistry | None = None


def get_registry() -> JobRegistry:
    """Return the process-global JobRegistry, creating it on first call."""
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = JobRegistry()
    return _REGISTRY
