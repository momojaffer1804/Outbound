"""
outbound/backend/eval_ablation.py

Evaluation script to perform exact retrieval ablation and metrics computation.
Runs:
1. BM25 only
2. Dense embeddings only (all-MiniLM-L6-v2)
3. Hybrid BM25 + Dense with Reciprocal Rank Fusion (k=60)
4. RRF + Cross-Encoder Reranker (ms-marco-MiniLM-L-6-v2)

Computes Recall@5 and MRR across a curated set of hand-labeled queries across all 4 programs.
Also runs conflict detection and cache benchmark.
"""

import sys
import os
import time
from pathlib import Path
import numpy as np

BACKEND_ROOT = Path(__file__).resolve().parent
sys.path.append(str(BACKEND_ROOT / "ingestion"))
sys.path.append(str(BACKEND_ROOT / "retrieval"))
sys.path.append(str(BACKEND_ROOT / "conflict_detection"))
sys.path.append(str(BACKEND_ROOT / "cache"))

from scraper_tum_informatics import TUMInformaticsScraper
from scraper_rwth_computer_science import RWTHComputerScienceScraper
from scraper_kaist_ai import KAISTAIScraper
from scraper_kaist_cs import KAISTCSScraper
from scraper_tum_english_mygermanuniversity import TUMEnglishMyGermanUniversityScraper
from scraper_tum_english_yocket import TUMEnglishYocketScraper

from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, CrossEncoder
from detect_conflicts import detect_conflicts
from scraper_cache import scraper_cache

# 1. Load corpus from scrapers
scrapers = [
    TUMInformaticsScraper,
    RWTHComputerScienceScraper,
    KAISTAIScraper,
    KAISTCSScraper,
]

corpus_records = []
for s_cls in scrapers:
    try:
        corpus_records.extend(scraper_cache.get_cached_or_fetch(s_cls))
    except Exception:
        corpus_records.extend(s_cls().run())

print(f"Total corpus records indexed: {len(corpus_records)}")

def record_text(req):
    parts = [req.university, req.program, req.requirement_type, req.value]
    if getattr(req, "notes", None):
        parts.append(req.notes)
    return " | ".join(parts)

corpus_texts = [record_text(r) for r in corpus_records]

# Precompute models
print("Initializing dense embedder (all-MiniLM-L6-v2)...")
embedder = SentenceTransformer("all-MiniLM-L6-v2")
doc_embeddings = embedder.encode(corpus_texts)
doc_norms = np.linalg.norm(doc_embeddings, axis=1)
doc_norms[doc_norms == 0] = 1e-8

print("Initializing cross-encoder (cross-encoder/ms-marco-MiniLM-L-6-v2)...")
cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

tokenized_corpus = [t.lower().split() for t in corpus_texts]
bm25 = BM25Okapi(tokenized_corpus)

def rrf(rank_lists, k=60):
    scores = {}
    for ranks in rank_lists:
        for pos, idx in enumerate(ranks):
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + pos + 1)
    return scores

# 2. Hand-labeled query set: 32 realistic student queries covering all 4 programs and requirement types
# Each query maps to (target_university, target_requirement_type) to uniquely identify the ground truth passage(s).
EVAL_QUERIES = [
    # --- TUM M.Sc. Informatics (8 queries) ---
    {"q": "What GRE quantitative score is required for TUM Informatics?", "uni": "TU Munich (TUM)", "type": "gre", "cat": "gre_gate"},
    {"q": "Can Indian students submit GATE instead of GRE for TU Munich?", "uni": "TU Munich (TUM)", "type": "gre", "cat": "gre_gate"},
    {"q": "What is the application deadline for winter semester at TU Munich?", "uni": "TU Munich (TUM)", "type": "deadline", "cat": "deadlines"},
    {"q": "How much tuition fee does TU Munich charge international students per semester?", "uni": "TU Munich (TUM)", "type": "tuition_fees", "cat": "tuition_funding"},
    {"q": "Is APS certificate required for TUM admissions from India?", "uni": "TU Munich (TUM)", "type": "aps_certificate", "cat": "prerequisites"},
    {"q": "What are the required documents for TUM Informatics application?", "uni": "TU Munich (TUM)", "type": "document_checklist", "cat": "prerequisites"},
    {"q": "What bachelor degree is required for TUM Informatics aptitude assessment?", "uni": "TU Munich (TUM)", "type": "qualification_basis", "cat": "gpa_qualification"},
    {"q": "What English language test score is needed for TU Munich?", "uni": "TU Munich (TUM)", "type": "english_test", "cat": "language"},

    # --- RWTH Aachen M.Sc. Computer Science (8 queries) ---
    {"q": "Does RWTH Aachen require German C1 proficiency for Computer Science?", "uni": "RWTH Aachen", "type": "german_test", "cat": "language"},
    {"q": "What GRE percentile cutoff is needed for RWTH Aachen CS?", "uni": "RWTH Aachen", "type": "gre", "cat": "gre_gate"},
    {"q": "Are EU citizens exempt from submitting GRE at RWTH Aachen?", "uni": "RWTH Aachen", "type": "gre", "cat": "gre_gate"},
    {"q": "What is the third country international applicant deadline for RWTH Aachen winter?", "uni": "RWTH Aachen", "type": "deadline", "cat": "deadlines"},
    {"q": "How much tuition fee is charged at RWTH Aachen for international students?", "uni": "RWTH Aachen", "type": "tuition_fees", "cat": "tuition_funding"},
    {"q": "What is the maximum credit point gap allowed in prior coursework for RWTH CS?", "uni": "RWTH Aachen", "type": "qualification_basis", "cat": "credits_prerequisites"},
    {"q": "What English level is required for RWTH Aachen Computer Science?", "uni": "RWTH Aachen", "type": "english_test", "cat": "language"},
    {"q": "What application documents and syllabus catalog are needed for RWTH Aachen?", "uni": "RWTH Aachen", "type": "document_checklist", "cat": "prerequisites"},

    # --- KAIST M.S. Artificial Intelligence (8 queries) ---
    {"q": "What TOEFL score is required for KAIST graduate admissions after Jan 2026?", "uni": "KAIST", "type": "english_test", "cat": "language"},
    {"q": "Are Korean citizens eligible for KAIST international graduate admissions track?", "uni": "KAIST", "type": "citizenship_eligibility", "cat": "prerequisites"},
    {"q": "What is the application submission schedule for KAIST GSAI Fall 2026?", "uni": "KAIST", "type": "deadline", "cat": "deadlines"},
    {"q": "How does the KAIST International Student Scholarship cover tuition and stipend?", "uni": "KAIST", "type": "scholarships_funding", "cat": "tuition_funding"},
    {"q": "What degree qualification standard is accepted for KAIST AI admission?", "uni": "KAIST", "type": "qualification_basis", "cat": "gpa_qualification"},
    {"q": "Can applicants get an English test waiver if their bachelor institution was English medium?", "uni": "KAIST", "type": "english_test", "cat": "language"},
    {"q": "Does KAIST AI require GRE General Test for international applicants?", "uni": "KAIST", "type": "english_test", "cat": "gre_gate"}, # explicitly noted in english_test notes as confirmed absence
    {"q": "What document checklist and recommendation letters are needed for KAIST international graduate school?", "uni": "KAIST", "type": "document_checklist", "cat": "prerequisites"},

    # --- KAIST M.S. Computer Science / Comparative Queries (8 queries) ---
    {"q": "What is the English proficiency score requirement for KAIST School of Computing?", "uni": "KAIST", "type": "english_test", "cat": "language"},
    {"q": "Is there a numeric minimum GPA requirement for international admission to KAIST?", "uni": "KAIST", "type": "qualification_basis", "cat": "gpa_qualification"},
    {"q": "When does online application open for KAIST general admission fall semester?", "uni": "KAIST", "type": "deadline", "cat": "deadlines"},
    {"q": "What tuition fee is charged for KAIST graduate programs without scholarship?", "uni": "KAIST", "type": "tuition_fees", "cat": "tuition_funding"},
    {"q": "Is GRE required for KAIST computer science graduate school?", "uni": "KAIST", "type": "english_test", "cat": "gre_gate"},
    {"q": "What citizenship documents are required for KAIST international graduate application?", "uni": "KAIST", "type": "document_checklist", "cat": "prerequisites"},
    {"q": "What bachelor degree qualification is needed for KAIST graduate school?", "uni": "KAIST", "type": "qualification_basis", "cat": "gpa_qualification"},
    {"q": "What are the accepted English tests at KAIST including IELTS, TOEIC, and TEPS?", "uni": "KAIST", "type": "english_test", "cat": "language"},
]

def is_ground_truth(record, item):
    uni_match = item["uni"].lower() in record.university.lower()
    type_match = record.requirement_type == item["type"]
    return uni_match and type_match

def evaluate_config(name, rank_fn):
    recall_at_5_hits = 0
    rr_sum = 0.0
    total = len(EVAL_QUERIES)

    for item in EVAL_QUERIES:
        ranked_indices = rank_fn(item["q"])
        # Find position of first ground truth match (1-based rank)
        matched_rank = None
        for rank_pos, idx in enumerate(ranked_indices, start=1):
            rec = corpus_records[idx]
            if is_ground_truth(rec, item):
                matched_rank = rank_pos
                break
        
        if matched_rank is not None and matched_rank <= 5:
            recall_at_5_hits += 1
        
        if matched_rank is not None:
            rr_sum += 1.0 / matched_rank

    recall_at_5 = recall_at_5_hits / total
    mrr = rr_sum / total
    return recall_at_5, mrr

# 1. BM25 only
def rank_bm25(query):
    scores = bm25.get_scores(query.lower().split())
    return sorted(range(len(corpus_records)), key=lambda i: scores[i], reverse=True)

# 2. Dense only
def rank_dense(query):
    q_emb = embedder.encode([query])[0]
    q_norm = np.linalg.norm(q_emb)
    if q_norm == 0:
        q_norm = 1e-8
    sims = (doc_embeddings @ q_emb) / (doc_norms * q_norm)
    return sorted(range(len(corpus_records)), key=lambda i: sims[i], reverse=True)

# 3. BM25 + Dense with RRF
def rank_rrf(query):
    bm25_ranking = rank_bm25(query)
    dense_ranking = rank_dense(query)
    fused = rrf([bm25_ranking, dense_ranking], k=60)
    return sorted(fused.keys(), key=lambda i: fused[i], reverse=True)

# 4. RRF + Cross-Encoder Reranker
def rank_rerank(query, top_k_candidates=15):
    candidate_indices = rank_rrf(query)[:top_k_candidates]
    candidates = [corpus_records[idx] for idx in candidate_indices]
    pairs = [(query, f"{c.university} — {c.program}: {c.requirement_type}: {c.value}") for c in candidates]
    scores = cross_encoder.predict(pairs)
    reranked_order = sorted(range(len(candidate_indices)), key=lambda i: scores[i], reverse=True)
    return [candidate_indices[i] for i in reranked_order]

print("\n--- RUNNING RETRIEVAL ABLATION EXPERIMENT ---")
r_bm25, mrr_bm25 = evaluate_config("BM25 only", rank_bm25)
r_dense, mrr_dense = evaluate_config("Dense only (MiniLM)", rank_dense)
r_rrf, mrr_rrf = evaluate_config("BM25 + Dense (RRF)", rank_rrf)
r_rerank, mrr_rerank = evaluate_config("RRF + Cross-Encoder Reranker", rank_rerank)

print("\n=== ABLATION RESULTS ===")
print(f"BM25 only                      | Recall@5: {r_bm25*100:.1f}% ({r_bm25:.4f}) | MRR: {mrr_bm25:.4f}")
print(f"Dense only (MiniLM)            | Recall@5: {r_dense*100:.1f}% ({r_dense:.4f}) | MRR: {mrr_dense:.4f}")
print(f"BM25 + Dense (RRF)             | Recall@5: {r_rrf*100:.1f}% ({r_rrf:.4f}) | MRR: {mrr_rrf:.4f}")
print(f"RRF + Cross-Encoder Reranker   | Recall@5: {r_rerank*100:.1f}% ({r_rerank:.4f}) | MRR: {mrr_rerank:.4f}")

# 3. Conflict Detection Evaluation
print("\n=== CONFLICT DETECTION EVALUATION ===")
from bs4 import BeautifulSoup
all_test_reqs = []
for s_cls in scrapers + [TUMEnglishMyGermanUniversityScraper, TUMEnglishYocketScraper]:
    try:
        all_test_reqs.extend(scraper_cache.get_cached_or_fetch(s_cls))
    except Exception:
        # Fallback to parse with mock soup if live site blocks with 403 Cloudflare
        try:
            inst = s_cls()
            dummy_soup = BeautifulSoup("<html><body>2026/27</body></html>", "html.parser")
            all_test_reqs.extend(inst.parse(dummy_soup))
        except Exception as e:
            print(f"Fallback parse failed for {s_cls}: {e}")

detected = detect_conflicts(all_test_reqs)
print(f"Total Tier-1 vs Tier-4 conflicts detected: {len(detected)}")
for idx, c in enumerate(detected, 1):
    print(f"\nConflict #{idx}:")
    print(f"  Target: {c.university} ({c.program}) - {c.requirement_type}")
    print(f"  Authoritative (Tier {c.authoritative.source_tier}, {c.authoritative.source_url}):")
    print(f"    {c.authoritative.value[:100]}...")
    for s in c.secondary:
        print(f"  Secondary (Tier {s.source_tier}, {s.source_url}):")
        print(f"    {s.value[:100]}...")
    print(f"  Message: {c.message}")

# 4. Cache Benchmark
print("\n=== CACHE BENCHMARK VERIFICATION ===")
# Benchmark 100 requests
times_cached = []
for _ in range(100):
    t0 = time.perf_counter()
    res = scraper_cache.get_cached_or_fetch(TUMInformaticsScraper)
    t1 = time.perf_counter()
    times_cached.append((t1 - t0) * 1000)

print(f"Cache hit latency (over 100 requests):")
print(f"  Mean: {np.mean(times_cached):.3f} ms")
print(f"  Median: {np.median(times_cached):.3f} ms")
print(f"  P95: {np.percentile(times_cached, 95):.3f} ms")
print(f"  Min/Max: {np.min(times_cached):.3f} ms / {np.max(times_cached):.3f} ms")

# Benchmark live scrape for TUM
t_live_start = time.perf_counter()
try:
    TUMInformaticsScraper().run()
    t_live_end = time.perf_counter()
    live_duration = (t_live_end - t_live_start)
    print(f"Live network scrape duration for TUM: {live_duration:.2f} s")
except Exception as e:
    print(f"Live network scrape failed: {e}")

