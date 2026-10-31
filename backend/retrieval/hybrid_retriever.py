"""
outbound/backend/retrieval/hybrid_retriever.py

Phase 3 retrieval module wiring lexical and semantic vector search across all 10 universities.
"""

from __future__ import annotations

import sys
from pathlib import Path
from dataclasses import dataclass

from rank_bm25 import BM25Okapi

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(BACKEND_ROOT / "ingestion"))

from scraper_tum_informatics import TUMInformaticsScraper
from scraper_rwth_computer_science import RWTHComputerScienceScraper
from scraper_kaist_ai import KAISTAIScraper
from scraper_kaist_cs import KAISTCSScraper
from scraper_tu_berlin_cs import TUBerlinCSScraper
from scraper_stuttgart_cs import StuttgartCSScraper
from scraper_tu_darmstadt_cs import TUDarmstadtCSScraper
from scraper_tu_delft_cs import TUDelftCSScraper
from scraper_eth_zurich_cs import ETHZurichCSScraper
from scraper_nus_computing import NUSComputingScraper

SCRAPERS = [
    TUMInformaticsScraper,
    RWTHComputerScienceScraper,
    KAISTAIScraper,
    KAISTCSScraper,
    TUBerlinCSScraper,
    StuttgartCSScraper,
    TUDarmstadtCSScraper,
    TUDelftCSScraper,
    ETHZurichCSScraper,
    NUSComputingScraper,
]

_embedder = None
_cached_texts = None
_cached_doc_embeddings = None


def _get_embedder():
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


@dataclass
class RetrievedRequirement:
    requirement: object
    bm25_rank: int | None
    embedding_rank: int | None
    fused_score: float


def _record_text(req) -> str:
    parts = [req.university, req.program, req.requirement_type, req.value]
    if getattr(req, "notes", None):
        parts.append(req.notes)
    return " | ".join(parts)


def _load_all_requirements() -> list:
    all_reqs = []
    for scraper_cls in SCRAPERS:
        all_reqs.extend(scraper_cls().run())
    return all_reqs


def _reciprocal_rank_fusion(rank_lists: list[list[int]], k: int = 60) -> dict[int, float]:
    scores: dict[int, float] = {}
    for ranks in rank_lists:
        for position, idx in enumerate(ranks):
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + position + 1)
    return scores


def retrieve(query: str, top_k: int = 5, requirements: list | None = None,
             use_embeddings: bool = True) -> list[RetrievedRequirement]:
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

    # --- Embedding ranking ---
    if use_embeddings:
        try:
            import numpy as np
            model = _get_embedder()
            global _cached_texts, _cached_doc_embeddings
            if _cached_texts == texts and _cached_doc_embeddings is not None:
                doc_embeddings = _cached_doc_embeddings
            else:
                doc_embeddings = model.encode(texts)
                _cached_texts = list(texts)
                _cached_doc_embeddings = doc_embeddings
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
