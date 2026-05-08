"""attune-gui — local FastAPI sidecar driving attune-rag, attune-author, attune-help."""

from __future__ import annotations

try:
    from importlib.metadata import PackageNotFoundError, version

    __version__ = version("attune-gui")
except PackageNotFoundError:  # pragma: no cover — running from a non-installed checkout
    __version__ = "dev"
