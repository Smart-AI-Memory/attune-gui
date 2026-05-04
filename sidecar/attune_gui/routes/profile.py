"""Profile API — GET/PUT the active UI profile (developer | author)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["profile"])

_CONFIG_PATH = Path.home() / ".attune-gui" / "config.json"
_VALID_PROFILES = {"developer", "author", "support"}
_DEFAULT_PROFILE = "developer"


def _read_profile() -> str:
    try:
        data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        profile = data.get("profile", _DEFAULT_PROFILE)
        return profile if profile in _VALID_PROFILES else _DEFAULT_PROFILE
    except (OSError, json.JSONDecodeError):
        return _DEFAULT_PROFILE


def _write_profile(profile: str) -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(json.dumps({"profile": profile}), encoding="utf-8")


class ProfileUpdate(BaseModel):
    profile: str


@router.get("/profile")
async def get_profile() -> dict[str, str]:
    """Return the active UI profile (developer | author | support)."""
    return {"profile": _read_profile()}


@router.put("/profile")
async def set_profile(body: ProfileUpdate) -> dict[str, str]:
    """Persist a new UI profile. 400 if the value isn't in the allowed set."""
    if body.profile not in _VALID_PROFILES:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "invalid_profile",
                "message": f"Unknown profile {body.profile!r}. Valid: {sorted(_VALID_PROFILES)}",
            },
        )
    _write_profile(body.profile)
    logger.info("Profile set to %r", body.profile)
    return {"profile": body.profile}
