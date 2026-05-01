"""Merge logic for unified help + RAG search.

Combines ``HelpEngine.search`` (keyword/fuzzy) results with
``RagPipeline.run`` (keyword-retrieval) results into a single
ranked list.

Weighting:
  RAG   — 0.6  (more corpus-aware scoring)
  Help  — 0.4  (fuzzy slug matching)
  Both  — ×1.2 cross-source boost, capped at 1.0
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

_RAG_WEIGHT = 0.6
_HELP_WEIGHT = 0.4
_BOTH_BOOST = 1.2

# Depth-indicator stems used by attune-author's <feature>/<depth>.md layout.
# When a RAG path ends with one of these, the feature name is in the parent.
_DEPTH_STEMS = frozenset({"concept", "task", "reference", "quickstart", "how-to", "guide"})


def _rag_topic(path: str) -> str:
    """Derive a stable topic key from a RAG corpus entry path.

    For bundled-help layout  (``concepts/tool-planning.md``)  → ``"tool-planning"``
    For author layout        (``auth/concept.md``)             → ``"auth"``
    """
    p = Path(path)
    return p.parent.name if p.stem in _DEPTH_STEMS else p.stem


def merge(
    help_hits: list[tuple[str, float]],
    rag_hits: list[Any],  # list[RetrievalHit] at runtime
    limit: int,
) -> list[dict[str, Any]]:
    """Merge and rank help + RAG hits into a unified result list.

    Args:
        help_hits: ``[(slug, score), ...]`` from ``HelpEngine.search``.
            Scores are SequenceMatcher ratios in ``[0, 1]``.
        rag_hits: ``[RetrievalHit, ...]`` from ``RagResult.citation.hits``.
            Raw scores are normalized against the top hit.
        limit: Maximum results to return.

    Returns:
        List of result dicts sorted by descending score, capped at ``limit``.
    """
    # Normalize RAG scores to [0, 1] relative to the top hit.
    max_rag = max((h.score for h in rag_hits), default=1.0) or 1.0

    # Accumulate per-topic: {topic_key: {rag_score, help_score, path, excerpt}}
    acc: dict[str, dict[str, Any]] = {}

    for hit in rag_hits:
        # citation.hits contains CitedSource objects: .template_path, .score, .excerpt
        topic = _rag_topic(hit.template_path)
        acc[topic] = {
            "topic": topic,
            "path": hit.template_path,
            "excerpt": (hit.excerpt or "")[:200].strip(),
            "rag_score": hit.score / max_rag,
            "help_score": None,
        }

    for slug, help_score in help_hits:
        if slug in acc:
            acc[slug]["help_score"] = help_score
        else:
            acc[slug] = {
                "topic": slug,
                "path": slug,
                "excerpt": "",
                "rag_score": None,
                "help_score": help_score,
            }

    results: list[dict[str, Any]] = []
    for item in acc.values():
        r = item["rag_score"]
        h = item["help_score"]
        if r is not None and h is not None:
            score = min((r * _RAG_WEIGHT + h * _HELP_WEIGHT) * _BOTH_BOOST, 1.0)
            source = "both"
        elif r is not None:
            score = r * _RAG_WEIGHT
            source = "rag"
        else:
            score = (h or 0.0) * _HELP_WEIGHT
            source = "help"

        results.append(
            {
                "topic": item["topic"],
                "path": item["path"],
                "score": round(score, 4),
                "source": source,
                "excerpt": item["excerpt"],
            }
        )

    results.sort(key=lambda x: -x["score"])
    return results[:limit]
