"""Tests for DocEntry.reason field plumbing in LivingDocsStore."""

from __future__ import annotations

from attune_gui.living_docs_store import DocEntry


def _entry(**kwargs) -> DocEntry:
    defaults = dict(
        id="feat/concept",
        feature="feat",
        depth="concept",
        persona="end_user",
        status="current",
        path=".help/templates/feat/concept.md",
        last_modified=None,
    )
    return DocEntry(**{**defaults, **kwargs})


# ---------------------------------------------------------------------------
# reason field defaults and serialisation
# ---------------------------------------------------------------------------


def test_reason_defaults_to_none():
    entry = _entry()
    assert entry.reason is None


def test_reason_appears_in_to_dict():
    entry = _entry(reason="signature changed: Foo.bar")
    d = entry.to_dict()
    assert d["reason"] == "signature changed: Foo.bar"


def test_reason_none_serialises_as_null():
    entry = _entry()
    d = entry.to_dict()
    assert "reason" in d
    assert d["reason"] is None


# ---------------------------------------------------------------------------
# Backward-compat: missing stale_reasons attribute on report
# ---------------------------------------------------------------------------


def test_getattr_fallback_on_report_without_stale_reasons():
    """getattr(report, "stale_reasons", {}) must return {} when attribute absent.

    This mirrors the defensive pattern used in _scan_sync so that consumers
    running against an older attune-help (pre-0.10) don't raise AttributeError.
    """

    class _OldReport:
        stale_features: list[str] = []

    report = _OldReport()
    stale_reasons = getattr(report, "stale_reasons", {})
    assert stale_reasons == {}
    assert stale_reasons.get("any_feature") is None


def test_scan_sync_produces_reason_none_when_no_help_dir(tmp_path):
    """_scan_sync completes without error when .help/ is absent."""
    from attune_gui.living_docs_store import LivingDocsStore

    store = LivingDocsStore()
    docs = store._scan_sync(tmp_path)
    assert docs == []
