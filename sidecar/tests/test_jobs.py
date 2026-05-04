"""Tests for attune_gui.jobs — Job, JobContext, JobRegistry."""

from __future__ import annotations

import asyncio

import pytest
from attune_gui.jobs import (
    Job,
    JobContext,
    JobRegistry,
    get_registry,
)

# ---------------------------------------------------------------------------
# Job.to_dict
# ---------------------------------------------------------------------------


def test_job_to_dict_serializes_all_fields() -> None:
    job = Job(id="abc", name="rag.query", args={"q": "x"})
    job.output_lines.append("hello")
    job.result = {"hits": 3}

    d = job.to_dict()

    assert d["id"] == "abc"
    assert d["name"] == "rag.query"
    assert d["args"] == {"q": "x"}
    assert d["status"] == "pending"
    assert d["created_at"]  # ISO string
    assert d["started_at"] is None
    assert d["finished_at"] is None
    assert d["output_lines"] == ["hello"]
    assert d["result"] == {"hits": 3}
    assert d["error"] is None


# ---------------------------------------------------------------------------
# JobContext
# ---------------------------------------------------------------------------


def test_job_context_log_appends_to_job_output() -> None:
    job = Job(id="x", name="t", args={})
    ctx = JobContext(job)
    ctx.log("first")
    ctx.log("second")
    assert job.output_lines == ["first", "second"]
    assert ctx.job_id == "x"


# ---------------------------------------------------------------------------
# JobRegistry — list / get / start / cancel
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_registry_start_runs_executor_and_records_result() -> None:
    reg = JobRegistry()

    async def executor(args, ctx):
        ctx.log("running")
        return {"ok": True, "n": args["n"]}

    job = await reg.start("test", {"n": 7}, executor)
    # Drain the asyncio task
    await asyncio.sleep(0.01)

    finished = reg.get(job.id)
    assert finished is not None
    assert finished.status == "completed"
    assert finished.result == {"ok": True, "n": 7}
    assert "running" in finished.output_lines


@pytest.mark.asyncio
async def test_registry_records_error_on_failure() -> None:
    reg = JobRegistry()

    async def executor(args, ctx):
        raise RuntimeError("boom")

    job = await reg.start("fail", {}, executor)
    await asyncio.sleep(0.01)

    finished = reg.get(job.id)
    assert finished.status == "errored"
    assert "RuntimeError" in finished.error
    assert "boom" in finished.error


@pytest.mark.asyncio
async def test_registry_cancel_running_job() -> None:
    reg = JobRegistry()
    started = asyncio.Event()

    async def slow(args, ctx):
        started.set()
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            ctx.log("cancelled cleanup")
            raise

    job = await reg.start("slow", {}, slow)
    await started.wait()

    assert reg.cancel(job.id) is True
    await asyncio.sleep(0.05)

    finished = reg.get(job.id)
    assert finished.status == "cancelled"


@pytest.mark.asyncio
async def test_registry_cancel_unknown_job_returns_false() -> None:
    reg = JobRegistry()
    assert reg.cancel("does-not-exist") is False


@pytest.mark.asyncio
async def test_registry_cancel_finished_job_returns_false() -> None:
    reg = JobRegistry()

    async def quick(args, ctx):
        return "done"

    job = await reg.start("quick", {}, quick)
    await asyncio.sleep(0.01)
    # Job has finished; task is done
    assert reg.cancel(job.id) is False


def test_registry_get_unknown_returns_none() -> None:
    reg = JobRegistry()
    assert reg.get("nope") is None


@pytest.mark.asyncio
async def test_registry_list_jobs_orders_newest_first() -> None:
    reg = JobRegistry()

    async def noop(args, ctx):
        return None

    j1 = await reg.start("first", {}, noop)
    await asyncio.sleep(0.01)
    j2 = await reg.start("second", {}, noop)
    await asyncio.sleep(0.01)

    jobs = reg.list_jobs()
    assert [j.id for j in jobs] == [j2.id, j1.id]


@pytest.mark.asyncio
async def test_registry_trim_drops_oldest_finished_when_over_max() -> None:
    """JobRegistry holds at most max_jobs; oldest finished are dropped first."""
    reg = JobRegistry(max_jobs=3)

    async def noop(args, ctx):
        return None

    ids = []
    for i in range(5):
        j = await reg.start(f"j{i}", {}, noop)
        ids.append(j.id)
        await asyncio.sleep(0.01)

    # Allow trim to run
    remaining = {j.id for j in reg.list_jobs()}
    # We expect the 3 most-recent jobs are still around
    assert ids[-1] in remaining
    assert ids[-2] in remaining
    # And at least one of the oldest got trimmed
    assert ids[0] not in remaining or ids[1] not in remaining


# ---------------------------------------------------------------------------
# get_registry singleton
# ---------------------------------------------------------------------------


def test_get_registry_returns_same_instance(monkeypatch: pytest.MonkeyPatch) -> None:
    # Reset the module-global so this test is independent of order
    from attune_gui import jobs

    monkeypatch.setattr(jobs, "_REGISTRY", None)
    a = get_registry()
    b = get_registry()
    assert a is b
