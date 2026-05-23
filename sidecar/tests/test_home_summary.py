"""Unit tests for the home page summary builder + helpers."""

from __future__ import annotations

from datetime import date
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from attune_gui.home_summary import (
    HomeSummary,
    _build_family_versions,
    _build_jobs_kpi_and_sparkline,
    _build_recent_jobs,
    _build_template_kpi,
    _duration,
    _to_day,
    build_home_summary,
    sparkline_points,
)

# ---------------------------------------------------------------------------
# sparkline_points
# ---------------------------------------------------------------------------


def test_sparkline_points_empty_for_no_data():
    assert sparkline_points([]) == ""
    assert sparkline_points([0, 0, 0, 0]) == ""


def test_sparkline_points_normalizes_to_box():
    pts = sparkline_points([0, 1, 2, 1, 4, 0, 0])
    coords = [tuple(map(float, p.split(","))) for p in pts.split(" ")]
    assert len(coords) == 7
    assert coords[0][0] == 0.0
    assert coords[-1][0] == pytest.approx(240.0)
    ys = [c[1] for c in coords]
    assert min(ys) == 0.0  # max value at top
    assert max(ys) == 40.0  # zero at bottom


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def test_to_day_returns_iso_date():
    assert _to_day("2026-05-07T13:00:00+00:00") == "2026-05-07"
    assert _to_day("2026-05-07T13:00:00Z") == "2026-05-07"


def test_to_day_returns_none_for_missing_or_garbage():
    assert _to_day(None) is None
    assert _to_day("") is None
    assert _to_day("not a date") is None


def test_duration_seconds_between_iso_timestamps():
    started = "2026-05-07T13:00:00+00:00"
    finished = "2026-05-07T13:00:05+00:00"
    assert _duration(started, finished) == pytest.approx(5.0)


def test_duration_returns_none_when_missing_either_endpoint():
    assert _duration(None, "2026-05-07T13:00:05+00:00") is None
    assert _duration("2026-05-07T13:00:00+00:00", None) is None
    assert _duration(None, None) is None


# ---------------------------------------------------------------------------
# _build_template_kpi
# ---------------------------------------------------------------------------


def test_template_kpi_empty_returns_zeros():
    kpi = _build_template_kpi([])
    assert kpi.total == 0
    assert kpi.fresh_ratio == 1.0  # no generated => 100% by definition (no stale)


def test_template_kpi_counts_manual_vs_generated():
    items: list[dict[str, Any]] = [
        {"manual": True, "staleness": "fresh"},
        {"manual": False, "staleness": "fresh"},
        {"manual": False, "staleness": "stale"},
        {"manual": False, "staleness": "stale"},
    ]
    kpi = _build_template_kpi(items)
    assert kpi.total == 4
    assert kpi.manual == 1
    assert kpi.generated == 3
    assert kpi.fresh == 2
    assert kpi.stale == 2
    # 2 fresh out of 4 with staleness => 50%
    assert kpi.fresh_ratio == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# _build_jobs_kpi_and_sparkline
# ---------------------------------------------------------------------------


def test_jobs_kpi_empty_jobs_today_zero():
    today = date(2026, 5, 7)
    kpi, spark = _build_jobs_kpi_and_sparkline([], today=today)
    assert kpi.today_count == 0
    assert kpi.week_count == 0
    assert kpi.last_status is None
    # 7 entries, oldest first
    assert len(spark) == 7
    assert spark[0].day == "2026-05-01"
    assert spark[-1].day == "2026-05-07"
    assert all(d.count == 0 for d in spark)


def test_jobs_kpi_today_and_week_split():
    today = date(2026, 5, 7)
    jobs: list[dict[str, Any]] = [
        # most recent first (matches registry's newest-first ordering)
        {
            "status": "completed",
            "started_at": "2026-05-07T12:00:00+00:00",
            "finished_at": "2026-05-07T12:00:05+00:00",
        },
        {
            "status": "errored",
            "started_at": "2026-05-05T09:00:00+00:00",
            "finished_at": "2026-05-05T09:00:01+00:00",
        },
        {
            "status": "completed",
            "started_at": "2026-04-20T09:00:00+00:00",  # older than the 7-day window
            "finished_at": "2026-04-20T09:00:01+00:00",
        },
    ]
    kpi, spark = _build_jobs_kpi_and_sparkline(jobs, today=today)
    assert kpi.today_count == 1
    assert kpi.week_count == 2  # today's + 2026-05-05
    assert kpi.last_status == "completed"
    assert kpi.last_finished_at == "2026-05-07T12:00:05+00:00"
    # sparkline entries by day
    counts = {d.day: d.count for d in spark}
    assert counts["2026-05-07"] == 1
    assert counts["2026-05-05"] == 1
    assert counts["2026-05-06"] == 0


# ---------------------------------------------------------------------------
# _build_recent_jobs
# ---------------------------------------------------------------------------


def test_recent_jobs_caps_at_limit():
    jobs = [{"id": str(i), "name": f"job-{i}", "status": "completed"} for i in range(10)]
    out = _build_recent_jobs(jobs, limit=3)
    assert [j.id for j in out] == ["0", "1", "2"]


def test_recent_jobs_extracts_duration():
    jobs = [
        {
            "id": "a",
            "name": "job-a",
            "status": "completed",
            "started_at": "2026-05-07T12:00:00+00:00",
            "finished_at": "2026-05-07T12:00:03+00:00",
        }
    ]
    out = _build_recent_jobs(jobs, limit=5)
    assert out[0].duration_seconds == pytest.approx(3.0)


# ---------------------------------------------------------------------------
# _build_family_versions
# ---------------------------------------------------------------------------


def test_family_versions_sorts_by_slug_and_marks_importable():
    layers = {
        "ai": {"importable": True, "version": "6.5.5"},
        "rag": {"importable": True, "version": "0.1.12"},
        "gui": {"importable": False, "version": None},
    }
    out = _build_family_versions(layers)
    # sorted by slug => ai, gui, rag
    assert [v.package for v in out] == ["attune-ai", "attune-gui", "attune-rag"]
    by_pkg = {v.package: v for v in out}
    assert by_pkg["attune-ai"].importable is True
    assert by_pkg["attune-gui"].importable is False
    assert by_pkg["attune-gui"].version is None


# ---------------------------------------------------------------------------
# build_home_summary integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_home_summary_composes_all_sources():
    """build_home_summary should call each accessor and assemble a HomeSummary."""

    fake_templates = AsyncMock(
        return_value={
            "templates": [
                {"manual": True, "staleness": "fresh"},
                {"manual": False, "staleness": "stale"},
            ],
            "templates_root": "/fake/help",
        }
    )
    fake_layers = AsyncMock(return_value={"layers": {"ai": {"importable": True, "version": "9"}}})
    fake_corpus = AsyncMock(
        return_value={"manifest_path": "/fake/help/features.yaml", "feature_count": 4}
    )

    fake_job = MagicMock()
    fake_job.to_dict.return_value = {
        "id": "x",
        "name": "demo.run",
        "status": "completed",
        "started_at": "2026-05-07T12:00:00+00:00",
        "finished_at": "2026-05-07T12:00:01+00:00",
    }
    fake_registry = MagicMock()
    fake_registry.list_jobs.return_value = [fake_job]

    with (
        patch("attune_gui.routes.cowork_templates.list_templates", fake_templates),
        patch("attune_gui.routes.cowork_health.layer_health", fake_layers),
        patch("attune_gui.routes.cowork_health.corpus_health", fake_corpus),
        patch("attune_gui.jobs.get_registry", return_value=fake_registry),
        patch("attune_gui.workspace.get_workspace", return_value=None),
    ):
        summary = await build_home_summary()

    assert isinstance(summary, HomeSummary)
    assert summary.templates.total == 2
    assert summary.templates.manual == 1
    assert summary.feature_count == 4
    assert summary.manifest_path == "/fake/help/features.yaml"
    assert len(summary.family) == 1
    assert summary.family[0].package == "attune-ai"
    assert len(summary.recent_jobs) == 1
    assert summary.recent_jobs[0].name == "demo.run"
    assert len(summary.sparkline) == 7


@pytest.mark.asyncio
async def test_build_home_summary_fails_soft_when_accessors_raise():
    """Each accessor failure is contained — page must still render."""

    failing = AsyncMock(side_effect=RuntimeError("boom"))
    fake_registry = MagicMock()
    fake_registry.list_jobs.side_effect = RuntimeError("nope")

    with (
        patch("attune_gui.routes.cowork_templates.list_templates", failing),
        patch("attune_gui.routes.cowork_health.layer_health", failing),
        patch("attune_gui.routes.cowork_health.corpus_health", failing),
        patch("attune_gui.jobs.get_registry", return_value=fake_registry),
        patch("attune_gui.workspace.get_workspace", side_effect=RuntimeError("nope")),
    ):
        summary = await build_home_summary()

    assert summary.templates.total == 0
    assert summary.jobs.today_count == 0
    assert summary.recent_jobs == []
    assert summary.family == []
    assert summary.workspace_path is None
    assert summary.manifest_path is None
    assert summary.feature_count == 0
