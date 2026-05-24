"""Home page summary: KPI tiles + recent jobs + workspace snapshot.

Composes data from existing accessors so the home route is a thin
orchestrator. All accessors fail soft (return zero/None on missing
data) so the page renders cleanly on a fresh install or when one
data source is unavailable.

Public API: :func:`build_home_summary` — async function the route awaits.
"""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TemplateKpi:
    """Templates count + stale-vs-fresh ratio for the home tiles."""

    total: int
    manual: int
    generated: int
    fresh: int
    stale: int

    @property
    def fresh_ratio(self) -> float:
        """Fraction of generated templates that are fresh (0.0 to 1.0)."""
        denom = self.fresh + self.stale
        return (self.fresh / denom) if denom else 1.0


@dataclass(frozen=True)
class JobsKpi:
    """Job-activity snapshot."""

    today_count: int
    week_count: int
    last_status: str | None  # "completed" | "errored" | "cancelled" | "running" | None
    last_finished_at: str | None  # ISO 8601 or None


@dataclass(frozen=True)
class DailyJobs:
    """One day's job count for the sparkline."""

    day: str  # YYYY-MM-DD
    count: int


@dataclass(frozen=True)
class FamilyVersion:
    """Installed version of one attune-* package."""

    package: str
    version: str | None
    importable: bool


@dataclass(frozen=True)
class RecentJob:
    """Trimmed Job for the recent-activity panel."""

    id: str
    name: str
    status: str
    duration_seconds: float | None
    started_at: str | None  # ISO 8601 or None


@dataclass(frozen=True)
class HomeSummary:
    """Everything the home page needs in one shape."""

    templates: TemplateKpi
    jobs: JobsKpi
    sparkline: list[DailyJobs] = field(default_factory=list)  # 7 entries, oldest first
    sparkline_points: str = ""  # SVG polyline points string ("" = no data)
    recent_jobs: list[RecentJob] = field(default_factory=list)
    family: list[FamilyVersion] = field(default_factory=list)
    family_interpreter: str | None = None  # sys.executable of dashboard process
    family_python_version: str | None = None  # e.g. "3.11.7"
    workspace_path: str | None = None
    manifest_path: str | None = None
    feature_count: int = 0


def sparkline_points(values: list[int], *, width: int = 240, height: int = 40) -> str:
    """Render a list of values as an SVG ``polyline`` ``points`` string.

    Returns an empty string when there's nothing to plot. The y-axis is
    inverted (SVG origin is top-left) so larger values appear higher.
    """
    if not values or all(v == 0 for v in values):
        return ""
    n = len(values)
    span = max(values) or 1
    points: list[str] = []
    for i, v in enumerate(values):
        x = (i / max(n - 1, 1)) * width
        y = height - (v / span) * height
        points.append(f"{x:.1f},{y:.1f}")
    return " ".join(points)


def _to_day(ts: str | None) -> str | None:
    if not ts:
        return None
    with contextlib.suppress(ValueError):
        cleaned = ts.rstrip("Z")
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.date().isoformat()
    return None


def _duration(started: str | None, finished: str | None) -> float | None:
    if not started or not finished:
        return None
    with contextlib.suppress(ValueError):
        a = datetime.fromisoformat(started.rstrip("Z"))
        b = datetime.fromisoformat(finished.rstrip("Z"))
        return (b - a).total_seconds()
    return None


def _build_template_kpi(items: list[dict[str, Any]]) -> TemplateKpi:
    total = len(items)
    manual = sum(1 for t in items if t.get("manual"))
    generated = total - manual
    fresh = sum(1 for t in items if t.get("staleness") == "fresh")
    stale = sum(1 for t in items if t.get("staleness") == "stale")
    return TemplateKpi(
        total=total,
        manual=manual,
        generated=generated,
        fresh=fresh,
        stale=stale,
    )


def _build_jobs_kpi_and_sparkline(
    jobs: list[dict[str, Any]],
    *,
    today: date | None = None,
) -> tuple[JobsKpi, list[DailyJobs]]:
    today = today or date.today()
    today_iso = today.isoformat()

    by_day: dict[str, int] = {}
    today_count = 0
    week_count = 0
    last_status: str | None = None
    last_finished_at: str | None = None

    week_start = date.fromordinal(today.toordinal() - 6)

    for j in jobs:
        finished = j.get("finished_at") or j.get("started_at")
        day = _to_day(finished)
        if day:
            by_day[day] = by_day.get(day, 0) + 1
            if day == today_iso:
                today_count += 1
            if day >= week_start.isoformat():
                week_count += 1
        if last_finished_at is None and j.get("finished_at"):
            last_finished_at = j["finished_at"]
            last_status = j.get("status")

    spark: list[DailyJobs] = []
    for offset in range(6, -1, -1):
        d = date.fromordinal(today.toordinal() - offset).isoformat()
        spark.append(DailyJobs(day=d, count=by_day.get(d, 0)))

    return (
        JobsKpi(
            today_count=today_count,
            week_count=week_count,
            last_status=last_status,
            last_finished_at=last_finished_at,
        ),
        spark,
    )


def _build_recent_jobs(jobs: list[dict[str, Any]], *, limit: int = 5) -> list[RecentJob]:
    out: list[RecentJob] = []
    for j in jobs[:limit]:
        out.append(
            RecentJob(
                id=str(j.get("id", "")),
                name=str(j.get("name", "")),
                status=str(j.get("status", "")),
                duration_seconds=_duration(j.get("started_at"), j.get("finished_at")),
                started_at=j.get("started_at"),
            )
        )
    return out


def _build_family_versions(layers: dict[str, dict[str, Any]]) -> list[FamilyVersion]:
    out: list[FamilyVersion] = []
    for slug, info in sorted(layers.items()):
        out.append(
            FamilyVersion(
                package=f"attune-{slug}",
                version=info.get("version"),
                importable=bool(info.get("importable")),
            )
        )
    return out


async def build_home_summary() -> HomeSummary:
    """Build the home-page summary by composing existing accessors.

    Each accessor is wrapped so any one failure doesn't take down the page.
    """
    from attune_gui.jobs import get_registry  # noqa: PLC0415
    from attune_gui.routes import cowork_health, cowork_templates  # noqa: PLC0415
    from attune_gui.workspace import get_workspace  # noqa: PLC0415

    template_items: list[dict[str, Any]] = []
    feature_count = 0
    manifest_path: str | None = None
    try:
        data = await cowork_templates.list_templates()
        template_items = list(data.get("templates", []))
    except Exception:  # noqa: BLE001
        logger.debug("home: cowork_templates.list_templates failed; using empty list")

    layers: dict[str, dict[str, Any]] = {}
    interpreter: str | None = None
    python_version: str | None = None
    try:
        layer_data = await cowork_health.layer_health()
        layers = layer_data.get("layers", {})
        interpreter = layer_data.get("interpreter")
        python_version = layer_data.get("python_version")
    except Exception:  # noqa: BLE001
        logger.debug("home: cowork_health.layer_health failed; using empty list")

    try:
        corpus = await cowork_health.corpus_health()
        manifest_path = corpus.get("manifest_path")
        feature_count = int(corpus.get("feature_count") or 0)
    except Exception:  # noqa: BLE001
        logger.debug("home: cowork_health.corpus_health failed; treating as missing")

    job_dicts: list[dict[str, Any]] = []
    try:
        registry = get_registry()
        job_dicts = [j.to_dict() for j in registry.list_jobs()]
    except Exception:  # noqa: BLE001
        logger.debug("home: jobs.get_registry().list_jobs failed; using empty list")

    workspace_path: str | None = None
    try:
        ws = get_workspace()
        if ws is not None:
            workspace_path = str(ws)
    except Exception:  # noqa: BLE001
        logger.debug("home: workspace.get_workspace failed; treating as unset")

    template_kpi = _build_template_kpi(template_items)
    jobs_kpi, spark = _build_jobs_kpi_and_sparkline(job_dicts)
    recent = _build_recent_jobs(job_dicts)
    family = _build_family_versions(layers)
    points = sparkline_points([d.count for d in spark])

    return HomeSummary(
        templates=template_kpi,
        jobs=jobs_kpi,
        sparkline=spark,
        sparkline_points=points,
        recent_jobs=recent,
        family=family,
        family_interpreter=interpreter,
        family_python_version=python_version,
        workspace_path=workspace_path,
        manifest_path=manifest_path,
        feature_count=feature_count,
    )
