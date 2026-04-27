"""Jobs + commands surface.

- GET  /api/commands         — list available commands (UI uses this to build the nav and args form)
- GET  /api/jobs             — list all jobs (most recent first)
- POST /api/jobs             — start a job { name, args } → job dict
- GET  /api/jobs/{id}        — full job state (status, output, result/error)
- DELETE /api/jobs/{id}      — cancel a running job
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from attune_gui.commands import get_command, list_commands
from attune_gui.jobs import get_registry
from attune_gui.security import require_client_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["jobs"])


class StartJobRequest(BaseModel):
    name: str
    args: dict[str, Any] = {}


@router.get("/commands")
async def commands(profile: str | None = None) -> dict[str, Any]:
    return {"commands": list_commands(profile=profile)}


@router.get("/jobs")
async def list_all_jobs() -> dict[str, Any]:
    reg = get_registry()
    return {"jobs": [j.to_dict() for j in reg.list_jobs()]}


@router.post("/jobs", dependencies=[Depends(require_client_token)])
async def start_job(req: StartJobRequest) -> dict[str, Any]:
    spec = get_command(req.name)
    if spec is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "unknown_command", "message": f"No command named {req.name!r}."},
        )

    # Minimal arg validation: check required fields exist. The real
    # schema is documented for the UI; backends should tolerate being
    # called with bad args and raise clearly. We don't run full
    # JSON-Schema validation here because each executor validates its
    # own inputs in practice.
    required = spec.args_schema.get("required", [])
    missing = [k for k in required if k not in req.args]
    if missing:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "missing_args",
                "message": f"Missing required args: {', '.join(missing)}",
            },
        )

    reg = get_registry()
    job = await reg.start(name=req.name, args=req.args, executor=spec.executor)
    return job.to_dict()


@router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> dict[str, Any]:
    reg = get_registry()
    job = reg.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "unknown_job", "message": f"No job {job_id!r}."},
        )
    return job.to_dict()


@router.delete("/jobs/{job_id}", dependencies=[Depends(require_client_token)])
async def cancel_job(job_id: str) -> dict[str, Any]:
    reg = get_registry()
    job = reg.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "unknown_job", "message": f"No job {job_id!r}."},
        )
    if not reg.cancel(job_id):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "not_cancellable",
                "message": f"Job {job_id!r} is not running (status: {job.status}).",
            },
        )
    return {"ok": True, "job_id": job_id}
