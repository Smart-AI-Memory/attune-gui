"""Template provenance + regenerate routes for the editor.

Implements ``specs/hash-regenerate-button/``:

- ``GET  /api/corpus/<id>/template/provenance?path=<rel>`` — staleness +
  provenance for one template. No auth, no LLM (pure read path).
- ``POST /api/corpus/<id>/template/regenerate`` — start a job that
  re-renders the template's bound feature from source. Token-guarded;
  mirrors ``living-docs.regenerate``. The actual file rewrite propagates
  to the open editor through the existing ``file_changed`` WS event.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from attune_gui import provenance as provenance_mod
from attune_gui.jobs import JobContext, get_registry
from attune_gui.security import require_client_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/corpus", tags=["editor-provenance"])


def _resolve_or_http(corpus_id: str, rel_path: str) -> provenance_mod.ProvenanceResult:
    """Run resolve_provenance, mapping resolution errors to HTTP codes."""
    try:
        return provenance_mod.resolve_provenance(corpus_id, rel_path)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{corpus_id}/template/provenance")
async def get_provenance(
    corpus_id: str,
    path: str = Query(..., min_length=1),
) -> dict[str, Any]:
    """Return staleness + provenance for the template at ``path``."""
    result = await asyncio.to_thread(_resolve_blocking, corpus_id, path)
    return result


def _resolve_blocking(corpus_id: str, rel_path: str) -> dict[str, Any]:
    return _resolve_or_http(corpus_id, rel_path).to_dict()


# ---------------------------------------------------------------------------
# Regenerate
# ---------------------------------------------------------------------------


class RegenerateRequest(BaseModel):
    path: str = Field(..., min_length=1)


async def _regenerate_template_executor(args: dict[str, Any], ctx: JobContext) -> dict[str, Any]:
    """Job executor: re-render one feature's templates from source."""
    help_dir = Path(args["help_dir"])
    project_root = Path(args["project_root"])
    feature_name = str(args["feature"])
    depth = args.get("depth")

    ctx.log(f"regenerating feature={feature_name} depth={depth or '(all)'}")
    ctx.log(f"help_dir     = {help_dir}")
    ctx.log(f"project_root = {project_root}")

    from attune_author.generator import generate_feature_templates  # noqa: PLC0415
    from attune_author.manifest import load_manifest  # noqa: PLC0415

    ctx.log("loading manifest…")
    manifest = await asyncio.to_thread(load_manifest, help_dir)
    feat = manifest.features.get(feature_name)
    if feat is None:
        available = ", ".join(sorted(manifest.features.keys())) or "(none)"
        raise ValueError(f"Feature {feature_name!r} not in manifest. Available: {available}")

    depths = [depth] if depth else None
    ctx.log(f"running attune-author generate (depths={depths or 'all'})…")
    await asyncio.to_thread(
        generate_feature_templates,
        feat,
        help_dir,
        project_root,
        depths,
        True,  # overwrite=True
    )
    provenance_mod.invalidate(help_dir)
    ctx.log("generate complete; template rewritten on disk")
    return {"feature": feature_name, "depth": depth}


@router.post(
    "/{corpus_id}/template/regenerate",
    dependencies=[Depends(require_client_token)],
)
async def regenerate_template(corpus_id: str, req: RegenerateRequest) -> dict[str, Any]:
    """Start a regen job for the template's bound feature; returns the job dict.

    409 if the template isn't regenerable (unbound / sources missing).
    """
    try:
        inputs = await asyncio.to_thread(provenance_mod.regen_inputs, corpus_id, req.path)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "not_regenerable", "message": str(exc)},
        ) from exc

    job = await get_registry().start(
        name="template.regenerate",
        args={
            "corpus_id": corpus_id,
            "path": req.path,
            "help_dir": str(inputs.help_dir),
            "project_root": str(inputs.project_root),
            "feature": inputs.feature,
            "depth": inputs.depth,
        },
        executor=_regenerate_template_executor,
    )
    return job.to_dict()
