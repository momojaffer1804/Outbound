"""
outbound/backend/retrieval/hybrid_retriever.py

Phase 3 retrieval module (the piece reranker.py was built early in
anticipation of, per the original ingestion handoff -- "Not yet wired to
anything real"). This file is what wires it up.

What this does:
- Pulls together every RawRequirement record across all registered
  universities' scrapers (the same UNIVERSITIES-style list used in
  api/main.py -- see NOTE below on why this list is duplicated here rather
  than imported from api/, which is deliberate).
- Builds TWO indexes over that combined set:
    1. BM25 (keyword/lexical match) -- via rank_bm25, pure Python, no model
       download needed.
    2. Embeddings (semantic match) -- via sentence-transformers
       ('all-MiniLM-L6-v2', a small, fast, commonly-used model), so a query
       like "German language requirement" can still find RWTH's
       "german_test" record even if the word "German" isn't repeated
       verbatim in a way BM25 would score highly.
- Combines both scores via Reciprocal Rank Fusion (RRF) -- simpler and more
  robust than tuning a weighted-sum blend between two very differently-
  scaled scores (BM25 raw scores and cosine similarities aren't on the same
  scale, so a naive weighted sum would need constant re-tuning; RRF sidesteps
  that by only using each method's RANK, not its raw score).
- Returns the top-k RawRequirement candidates, ready to be handed to
  reranker.py's cross-encoder for final re-scoring against the query.

NOTE on why UNIVERSITIES is duplicated here instead of imported from
api/main.py: api/ is documented (there, and in base_scraper.py) as "the
ONLY module allowed to wire ingestion -> eligibility together" -- retrieval
importing FROM api/ would invert that dependency direction and violate the
project's own modularity rule. Instead, api/main.py should import
hybrid_retriever.py's `retrieve()` function when a retrieval-backed endpoint
is added, not the other way around.

WHAT THIS IS FOR: this is NOT what eligibility-checking uses (that's
direct dictionary lookup by requirement_type in the checkers -- reliable
and correct for a small, KNOWN set of requirement types per university).
Retrieval is for a DIFFERENT feature: free-text search/Q&A over the corpus
of requirements. The eligibility CHECKER logic itself should keep using
direct lookup, not this retriever -- don't replace one with the other.
"""

from __future__ import annotations

import sys
from pathlib import Path
from dataclasses import dataclass

from rank_bm25 import BM25Okapi

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(BACKEND_ROOT / "ingestion"))

from scraper_tum_informatics import TUMInformaticsScraper  # noqa: E402
from scraper_rwth_computer_science import RWTHComputerScienceScraper  # noqa: E402
from scraper_kaist_ai import KAISTAIScraper  # noqa: E402
from scraper_kaist_cs import KAISTCSScraper  # noqa: E402

SCRAPERS = [
    TUMInformaticsScraper,
    RWTHComputerScienceScraper,
    KAISTAIScraper,
    KAISTCSScraper,
]

# Lazily imported -- sentence-transformers pulls a real model from the
# network on first use. Deferred so BM25-only usage still works without it.
_embedder = None


def _get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


@dataclass
class RetrievedRequirement:
    requirement: object  # the original RawRequirement
    bm25_rank: int | None
    embedding_rank: int | None
    fused_score: float


def _record_text(req) -> str:
    """What gets indexed/searched for a given RawRequirement -- combine the
    fields a user's question is likely to match against. Keeping this in one
    place means both BM25 and embeddings search the exact same text."""
    parts = [req.university, req.program, req.requirement_type, req.value]
    if req.notes:
        parts.append(req.notes)
    return " | ".join(parts)


def _load_all_requirements() -> list:
    all_reqs = []
    for scraper_cls in SCRAPERS:
        all_reqs.extend(scraper_cls().run())
    return all_reqs


def _reciprocal_rank_fusion(rank_lists: list[list[int]], k: int = 60) -> dict[int, float]:
    """rank_lists: each is a list of indices (into the shared requirement
    list) in best-to-worst order from one retrieval method. Returns a dict
    of index -> fused score, higher is better. k=60 is RRF's standard
    constant -- dampens the impact of any one method's rank without needing
    dataset-specific tuning."""
    scores: dict[int, float] = {}
    for ranks in rank_lists:
        for position, idx in enumerate(ranks):
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + position + 1)
    return scores


def retrieve(query: str, top_k: int = 5, requirements: list | None = None,
             use_embeddings: bool = True) -> list[RetrievedRequirement]:
    """Main entry point. `requirements` can be pre-fetched and passed in to
    avoid re-scraping on every call (recommended for a real API endpoint --
    scrape once, retrieve many times against the same snapshot); if omitted,
    this fetches fresh from all 4 scrapers (slow, hits live network).
    """
    all_reqs = requirements if requirements is not None else _load_all_requirements()
    texts = [_record_text(r) for r in all_reqs]

    # --- BM25 ranking ---
    tokenized_corpus = [t.lower().split() for t in texts]
    bm25 = BM25Okapi(tokenized_corpus)
    bm25_scores = bm25.get_scores(query.lower().split())
    bm25_ranking = sorted(range(len(all_reqs)), key=lambda i: bm25_scores[i], reverse=True)

    rank_lists = [bm25_ranking]
    bm25_rank_of = {idx: pos for pos, idx in enumerate(bm25_ranking)}
    embedding_rank_of: dict[int, int] = {}

    # --- Embedding ranking (optional -- skipped if model unavailable/disabled) ---
    if use_embeddings:
        try:
            import numpy as np
            model = _get_embedder()
            doc_embeddings = model.encode(texts)
            query_embedding = model.encode([query])[0]
            norms = np.linalg.norm(doc_embeddings, axis=1) * np.linalg.norm(query_embedding)
            norms[norms == 0] = 1e-8
            sims = (doc_embeddings @ query_embedding) / norms
            embedding_ranking = sorted(range(len(all_reqs)), key=lambda i: sims[i], reverse=True)
            rank_lists.append(embedding_ranking)
            embedding_rank_of = {idx: pos for pos, idx in enumerate(embedding_ranking)}
        except Exception as exc:
            print(f"[hybrid_retriever] Embedding ranking skipped: {exc}")

    fused = _reciprocal_rank_fusion(rank_lists)
    ranked_indices = sorted(fused.keys(), key=lambda i: fused[i], reverse=True)[:top_k]

    return [
        RetrievedRequirement(
            requirement=all_reqs[idx],
            bm25_rank=bm25_rank_of.get(idx),
            embedding_rank=embedding_rank_of.get(idx),
            fused_score=fused[idx],
        )
        for idx in ranked_indices
    ]


if __name__ == "__main__":
    results = retrieve("do I need German for this program?", top_k=3)
    for r in results:
        print(f"[fused={r.fused_score:.4f} bm25_rank={r.bm25_rank} emb_rank={r.embedding_rank}] "
              f"{r.requirement.university} — {r.requirement.requirement_type}: {r.requirement.value[:80]}")