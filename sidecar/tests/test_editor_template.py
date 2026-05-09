"""Tests for sidecar/attune_gui/routes/editor_template.py helpers.

Targets the pure helpers that aren't exercised by integration tests:
``_split_frontmatter``, ``_hash_text``, ``_parse_hunk_header``, and
``_apply_accepted_hunks``. Route-level tests live in
``test_editor_template_routes.py`` (if present) or get exercised through
the editor pages tests.
"""

from __future__ import annotations

import pytest
from attune_gui.routes.editor_template import (
    _hash_text,
    _parse_hunk_header,
    _split_frontmatter,
)

# ---------------------------------------------------------------------------
# _hash_text
# ---------------------------------------------------------------------------


def test_hash_text_is_deterministic() -> None:
    assert _hash_text("hello") == _hash_text("hello")


def test_hash_text_differs_on_change() -> None:
    assert _hash_text("hello") != _hash_text("hello!")


def test_hash_text_is_16_hex_chars() -> None:
    h = _hash_text("any text")
    assert len(h) == 16
    int(h, 16)  # raises if not hex


def test_hash_text_handles_empty() -> None:
    assert _hash_text("") == _hash_text("")
    assert len(_hash_text("")) == 16


# ---------------------------------------------------------------------------
# _split_frontmatter
# ---------------------------------------------------------------------------


def test_split_returns_empty_fm_when_no_block() -> None:
    fm, body = _split_frontmatter("# Just a heading\n\nbody text\n")
    assert fm == ""
    assert body == "# Just a heading\n\nbody text\n"


def test_split_extracts_frontmatter_and_body() -> None:
    text = '---\ntitle: "Foo"\ntags: [a, b]\n---\n\n# Heading\n\nBody.\n'
    fm, body = _split_frontmatter(text)
    assert "title:" in fm
    assert "tags:" in fm
    # Parser strips the immediate \n after the closing fence, leaving the
    # next blank line intact in the body.
    assert body.lstrip("\n") == "# Heading\n\nBody.\n"
    assert body.startswith("\n")


def test_split_returns_original_when_no_closing_fence() -> None:
    """Unclosed `---` block: nothing is parsed; whole thing is body."""
    text = "---\ntitle: incomplete\n\nstill the same block.\n"
    fm, body = _split_frontmatter(text)
    assert fm == ""
    assert body == text


def test_split_handles_immediately_closed_fence() -> None:
    """``---\n---`` with no content between fences: parser requires a real
    ``\n---`` separator after some content, so this degenerate form is
    treated as no-frontmatter; body == original text."""
    text = "---\n---\nrest\n"
    fm, body = _split_frontmatter(text)
    assert fm == ""
    assert body == text


def test_split_handles_three_dashes_no_newline() -> None:
    """`---` without a following newline returns empty fm."""
    fm, body = _split_frontmatter("---")
    assert fm == ""
    assert body == "---"


# ---------------------------------------------------------------------------
# _parse_hunk_header
# ---------------------------------------------------------------------------


def test_parse_hunk_header_typical_form() -> None:
    """``@@ -10,3 +10,4 @@`` — 0-indexed start = 9, count = 3."""
    start, count = _parse_hunk_header("@@ -10,3 +10,4 @@")
    assert start == 9
    assert count == 3


def test_parse_hunk_header_pure_insertion_count_zero() -> None:
    """``@@ -0,0 +1,3 @@`` — count zero keeps start as-is."""
    start, count = _parse_hunk_header("@@ -0,0 +1,3 @@")
    assert start == 0
    assert count == 0


def test_parse_hunk_header_no_count_means_one() -> None:
    """``@@ -5 +5 @@`` — when count omitted, defaults to 1."""
    start, count = _parse_hunk_header("@@ -5 +5 @@")
    assert start == 4  # 5 - 1
    assert count == 1


def test_parse_hunk_header_garbage_returns_zero_zero() -> None:
    assert _parse_hunk_header("not a hunk header") == (0, 0)
    assert _parse_hunk_header("") == (0, 0)


@pytest.mark.parametrize(
    "header,expected",
    [
        ("@@ -1,0 +2,3 @@", (1, 0)),
        ("@@ -100,5 +200,5 @@", (99, 5)),
        ("@@ -42 +42 @@", (41, 1)),
    ],
)
def test_parse_hunk_header_parametrized(header: str, expected: tuple[int, int]) -> None:
    assert _parse_hunk_header(header) == expected
