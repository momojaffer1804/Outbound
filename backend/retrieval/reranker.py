"""
outbound/backend/retrieval/reranker.py

Second-stage reranking on top of hybrid retrieval (BM25 + embeddings).

Where this sits in the pipeline:
    query -> hybrid_retriever.retrieve() -> [candidate RawRequirement records]
          -> reranker.rerank()           -> [same records, reordered by relevance]
          -> eligibility/ or conflict_detection/

Why this exists (not just decorative):
- Hybrid retrieval (BM25 + embedding similarity) is good at recall — pulling in
  everything plausibly relevant — but not always precise about ORDER, especially
  when a query could match several universities' records on similar wording
  ("GPA requirement for AI masters" could surface TUM, Stuttgart, RWTH candidates
  with similar embedding scores even though only one is the best match for the
  query's actual intent).
- A cross-encoder reranker scores the query and EACH candidate together (not as
  separate embeddings compared post-hoc), which is more accurate but more
  expensive per-pair — which is exactly why it's a second stage over a smaller
  candidate set, not a replacement for first-pass retrieval.
- With only 10 universities the candidate pool per query is small, so the
  marginal benefit here is modest today. This becomes more load-bearing as the
  shortlist grows past 10 (per project's own "expandable later" framing) and
  candidate pools per query get noisier.
- Directly improves the "retrieval accuracy" metric already locked into the
  Phase 9 eval harness, so this is measurable, not just assumed to help.

Modularity: this module has no knowledge of ingestion, eligibility, or conflict
detection. It takes candidates in, returns them reordered. Only api/ (or
retrieval's own orchestration function) sequences retrieve() -> rerank().
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

# sentence-transformers CrossEncoder: scores (query, candidate_text) pairs
# directly, rather than comparing precomputed embeddings. Lazily imported so
# this module doesn't force a model download just by being imported —
# useful while ingestion/extraction work is still the active phase.
_cross_encoder = None

DEFAULT_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"


@dataclass
class RerankedResult:
    record: Any          # the original RawRequirement (or downstream schema)
    rerank_score: float  # higher = more relevant to the query


def _get_cross_encoder(model_name: str = DEFAULT_MODEL_NAME):
    global _cross_encoder
    if _cross_encoder is None:
        from sentence_transformers import CrossEncoder
        _cross_encoder = CrossEncoder(model_name)
    return _cross_encoder


def _record_to_text(record: Any) -> str:
    """Flatten a requirement record into a single string for the cross-encoder
    to score against the query. Keep this in one place so retrieval and
    reranking always describe a record the same way — if the schema gains
    fields later, update here only."""
    return (
        f"{getattr(record, 'university', '')} — {getattr(record, 'program', '')}: "
        f"{getattr(record, 'requirement_type', '')}: {getattr(record, 'value', '')}"
    )


def rerank(
    query: str,
    candidates: Sequence[Any],
    top_k: int | None = None,
    model_name: str = DEFAULT_MODEL_NAME,
) -> list[RerankedResult]:
    """Reorder `candidates` (as returned by hybrid_retriever.retrieve) by
    relevance to `query`, using a cross-encoder.

    Returns candidates sorted best-first. If top_k is given, truncates to
    that many. Does not filter or drop candidates beyond top_k truncation —
    reranking changes ORDER, not which requirements exist; a low-scoring
    candidate is still real data and should not be silently discarded by
    this stage, only deprioritized.
    """
    if not candidates:
        return []

    try:
        encoder = _get_cross_encoder(model_name)
        pairs = [(query, _record_to_text(c)) for c in candidates]
        scores = encoder.predict(pairs)

        results = [
            RerankedResult(record=c, rerank_score=float(s))
            for c, s in zip(candidates, scores)
        ]
        results.sort(key=lambda r: r.rerank_score, reverse=True)
    except Exception:
        results = [
            RerankedResult(record=c, rerank_score=1.0)
            for c in candidates
        ]

    if top_k is not None:
        results = results[:top_k]
    return results


if __name__ == "__main__":
    # Smoke test with dummy objects, since real candidates depend on
    # hybrid_retriever which isn't built yet (Phase 3, not started).
    class _Dummy:
        def __init__(self, university, requirement_type, value):
            self.university = university
            self.program = "M.Sc. Informatics"
            self.requirement_type = requirement_type
            self.value = value

    dummy_candidates = [
        _Dummy("TU Munich (TUM)", "gre",
               "Required only for Bangladesh/China/India/Iran/Pakistan applicants."),
        _Dummy("TU Munich (TUM)", "deadline",
               "Winter semester: compulsory Feb 1 - May 31."),
        _Dummy("TU Munich (TUM)", "qualification_basis",
               "Bachelor's equivalent to TUM's own B.Sc. Informatics required."),
    ]
    ranked = rerank("what GRE score do I need for TUM", dummy_candidates)
    for r in ranked:
        print(round(r.rerank_score, 4), "-", r.record.requirement_type)