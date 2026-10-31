# Outbound

**Outbound** is a source-grounded Masters eligibility engine designed to help applicants determine which countries, universities, and graduate programs they are eligible for when planning studies abroad.

---

### Problem
When researching Masters programs abroad, applicants must manually compare dozens of universities across different countries, each with disparate GPA cutoffs, prerequisites, credit-point requirements, language thresholds, deadlines, and application rules. Information is scattered across university portals, DAAD, and commercial aggregators—sources that frequently contradict each other or display outdated criteria.

This makes it difficult to answer a simple question: **"Which universities am I actually eligible for, and what requirements do I still need to meet?"**

Outbound automates this evaluation while preserving strict source provenance, cross-referencing Tier-1 official university admissions pages against Tier-4 secondary aggregators, and surfacing conflicts before generating answers.

---

### Architecture & System Design
- **Backend:** FastAPI modular service decoupling ingestion, eligibility evaluation, hybrid retrieval, cross-encoder reranking, conflict resolution, and persistent caching.
- **Frontend:** React 19 + Vite responsive SPA featuring four dedicated viewports:
  - *Eligibility Engine:* Progressive disclosure form supporting early-stage planners and near-term applicants with granular requirement status pills (`MET`, `UNMET`, `REVIEW`, `N/A`, `INFO`).
  - *Program Comparison:* Side-by-side evaluation matrix benchmarking up to 3 programs simultaneously across all extracted requirements.
  - *Grounding Assistant:* Source-grounded RAG chatbot powered by Groq, rendering markdown answers, conflict alert banners, and source tier badges.
  - *Cache Monitor:* Live administrative dashboard with real-time TTL metrics, stale-while-revalidate status indicators, and an interactive roundtrip latency benchmark.
- **Two-Stage Retrieval Pipeline:**
  1. *First-Stage Hybrid Retrieval:* Lexical search (`rank-bm25`) combined with dense semantic embeddings (`sentence-transformers/all-MiniLM-L6-v2`), fused via Reciprocal Rank Fusion (RRF, $k=60$).
  2. *Second-Stage Reranking:* Query-candidate re-scoring using a cross-encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`) to optimize passage ordering.
- **Conflict Detection Engine:** Asymmetric, authority-weighted discrepancy analyzer ensuring Tier-1 official university portals always supersede Tier-4/5 aggregators.
- **Persistent Caching Layer:** Thread-safe SQLite cache (`backend/data/cache.db`) with 24-hour TTL, server startup warm-up, and *stale-while-revalidate* fallback on network degradation.

---

### Implementation Progress

#### Phase 0 — Environment & Baseline Setup
- **Status:** Complete.
- Repository structure established with modular backend architecture, React frontend skeleton, and local virtual environments.

#### Phase 1 — Data Ingestion & Scrapers
- **Status:** Completed for initial multi-country benchmark set (3 universities across 4 degree tracks + 2 secondary aggregators).
- **Tier-1 Official University Scrapers:**
  - **Technical University of Munich (TUM):** *M.Sc. Informatics* — Dual-source extraction (curriculum page + central language portal) covering GPA, GRE/GATE, APS certification, deadlines, ECTS basis, and tuition fees (€6,000/semester for non-EU students).
  - **RWTH Aachen University:** *M.Sc. Computer Science* — Departmental scraper extracting prior coursework criteria (42 CP maximum bridge gap), German C1 mandate, GRE percentiles (Quant > 75th percentile), and €0 tuition confirmation.
  - **KAIST (Graduate School of AI):** *M.S. Artificial Intelligence* — Multi-level portal ingestion capturing foreign citizenship gates, English score cutoffs (including the post-21 Jan 2026 TOEFL scale revision), English-medium bachelor waivers, and full international tuition scholarships.
  - **KAIST (School of Computing):** *M.S. Computer Science* — Shared institutional eligibility alignment with computing department schedule parameters.
- **Tier-4 Aggregator Scrapers (Conflict Benchmarking):**
  - **MyGermanUniversity:** TUM Informatics admissions profile.
  - **Yocket:** TUM Informatics admissions overview.

#### Phase 2 — Rule-Based Eligibility Checkers
- **Status:** Complete for all active programs.
- Implemented deterministic per-university checkers:
  - `checker_tum.py`: Enforces scaled GRE minimums (Quant $\ge$ 164, AWA $\ge$ 4.0) or Indian GATE CS alternatives, mandatory APS documentation for India/China/Vietnam, and conservative `needs_review` statuses for aptitude assessments.
  - `checker_rwth.py`: Validates GRE percentile scores, German C1 proficiency, and evaluates exemptions for EU/EEA and Bildungsinländer applicants.
  - `checker_kaist_ai.py` & `checker_kaist_cs.py`: Evaluates citizenship eligibility, English test cutoffs across TOEFL/IELTS/TOEIC/TEPS, and conditional undergraduate institution waivers.

#### Phase 3 — Hybrid Retrieval & Reranker
- **Status:** Complete and evaluated.
- Integrated `/search` endpoint combining BM25 keyword matching with dense MiniLM vector similarity via Reciprocal Rank Fusion, followed by cross-encoder re-scoring.
- **Benchmark Ablation Results (32 hand-labeled queries across 4 programs):**
  - *BM25 only:* Recall@5: 78.1% | MRR: 0.6306
  - *Dense only (`all-MiniLM-L6-v2`):* Recall@5: 93.8% | MRR: 0.7966
  - *BM25 + Dense (RRF, $k=60$):* Recall@5: 87.5% | MRR: 0.7724
  - *RRF + Cross-Encoder Reranker:* Recall@5: 87.5% | **MRR: 0.8700** (ensures authoritative passage placement at Rank 1).

#### Phase 4 — Conflict Resolution & Grounded RAG Assistant
- **Status:** Complete.
- Detects discrepancies between Tier-1 official baselines and Tier-4 commercial aggregators with 100% precision on benchmarked records:
  - *GRE Scope Discrepancy:* Yocket marks GRE as unconditionally required; official TUM Tier-1 requirements mandate GRE only for applicants from 5 countries and accept GATE CS for Indian applicants.
  - *Language Cutoff Oversimplification:* Aggregators claim rigid minimums; official portals delegate language compliance to multi-track CEFR certification frameworks.
- The `/ask` endpoint runs retrieval, detects conflicts, and injects critical conflict warnings into the LLM context to prevent admissions hallucinations.

#### Phase 5 — Performance Optimization & Persistent Caching
- **Status:** Complete.
- Persistent SQLite cache reduces live network scrape roundtrips from **~4.71 seconds** down to a **0.88 ms median hit** (0.95 ms mean over 100 benchmarked requests), delivering a >99.9% latency reduction.

#### Phase 6 — Containerization & Deployment
- **Status:** Complete.
- Multi-stage `Dockerfile` configurations for backend and frontend.
- Production `nginx.conf` with built-in API reverse proxy and SPA routing.
- Unified single-server fallback in FastAPI to serve production static builds directly.
- Orchestrated with `docker-compose.yml`, `.env` configuration, and one-click deployment scripts (`deploy.bat` / `deploy.sh`).

---

### Key Challenges & Resolved Failure Modes
- **Unreliable HTML Layouts:** University admissions pages frequently alter DOM trees and CMS structures. Solved by creating isolated, per-university scrapers with fallback to hand-verified official records.
- **Misleading Academic Year Extraction:** University pages frequently cite historic fee policy years or old regulation dates. Resolved by anchoring regex year searches specifically within admissions-related proximity windows.
- **Aggregator Hallucinations:** Secondary aggregators omit critical conditional exemptions (e.g. GRE country lists or English-medium waivers). Solved via asymmetric conflict rules where Tier-1 always takes precedence.
- **Model Download Cold Starts:** Pre-cached SentenceTransformer and CrossEncoder model checkpoints during Docker image build time to eliminate boot delays and rate-limiting.

---

### Deployment

#### Using Docker Compose
```bash
docker compose up --build -d
```
- **Frontend:** [http://localhost:3000](http://localhost:3000)
- **Backend API:** [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

#### Automated Script
- **Windows:** Run `deploy.bat`
- **Linux / macOS:** Run `./deploy.sh`

---

### Future Plan & Roadmap
- **Expand University Coverage:** Scale coverage from the initial 3 institutions to 10+ major technical universities across Germany (TU Berlin, TU Darmstadt, Stuttgart, Karlsruhe), the Netherlands (TU Delft), and Switzerland (ETH Zurich).
- **Automated Curricular Overlap & ECTS Auditing:** Implement transcript-level syllabus parsing to evaluate course prerequisites automatically against credit requirements (e.g. RWTH's 42 CP coursework gap rule).
- **Automated Scraper Drift Detection:** Implement cron-based monitoring to detect when university portal HTML structures change, notifying maintainers before ingestion breaks.
- **RAG Factuality & Citation Verification Harness:** Build an automated evaluation suite testing generated LLM answers against authoritative records to continuously benchmark hallucination rates under varied prompt strategies.
- **User Document Upload & Profile Parsing:** Allow users to upload unofficial transcripts, CVs, and score sheets (APS, IELTS, GRE) to auto-populate their eligibility profile.
