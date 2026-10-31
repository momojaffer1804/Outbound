# Outbound

**Outbound** is a source-grounded Masters eligibility engine designed to help applicants determine which countries, universities, and graduate programs they are eligible for when planning studies abroad.

---

### Problem
When researching Masters programs abroad, applicants must manually compare dozens of universities across different countries, each with disparate GPA cutoffs, prerequisites, credit-point requirements, language thresholds, deadlines, and application rules. Information is scattered across university portals, DAAD, and commercial aggregators—sources that frequently contradict each other or display outdated criteria.

This makes it difficult to answer a simple question: **"Which universities am I actually eligible for, and what requirements do I still need to meet?"**

Outbound automates this evaluation while preserving strict source provenance, cross-referencing Tier-1 official university admissions pages against Tier-4 secondary aggregators, and surfacing conflicts before generating answers.

---

### System Architecture
- **Backend:** FastAPI service with decoupled modules for data ingestion, eligibility evaluation, hybrid retrieval, cross-encoder reranking, conflict resolution, and persistent caching.
- **Frontend:** React 19 + Vite responsive single-page application featuring four interactive viewports:
  - **Eligibility Engine:** Progressive disclosure profile form supporting early-stage planners (CGPA-only) and near-term applicants with granular requirement status judgments (`MET`, `UNMET`, `REVIEW`, `N/A`, `INFO`).
  - **Program Comparison:** Side-by-side evaluation matrix benchmarking up to 3 programs simultaneously across all extracted requirements.
  - **Grounding Assistant:** Source-grounded RAG chatbot powered by Groq, rendering formatted markdown responses, conflict alert warnings, and verified source citations.
  - **Cache Monitor:** Live administrative dashboard with real-time TTL metrics, stale-while-revalidate status indicators, force-refresh controls, and an interactive roundtrip latency benchmark.
- **Two-Stage Retrieval Pipeline:**
  1. *First-Stage Hybrid Retrieval:* Lexical search (`rank-bm25`) combined with dense semantic embeddings (`sentence-transformers/all-MiniLM-L6-v2`), fused via Reciprocal Rank Fusion (RRF, $k=60$).
  2. *Second-Stage Reranking:* Query-candidate re-scoring using a cross-encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`) to optimize passage ordering.
- **Conflict Detection Engine:** Asymmetric, authority-weighted discrepancy analyzer ensuring Tier-1 official university portals always supersede Tier-4/5 commercial aggregators.
- **Persistent Caching Layer:** Thread-safe SQLite cache (`backend/data/cache.db`) with 24-hour TTL, server startup warm-up, and *stale-while-revalidate* fallback on network degradation.

---

### Current System Capabilities

#### Multi-University Knowledge Base
- **Technical University of Munich (TUM) — M.Sc. Informatics (Germany):** Evaluates scaled GRE thresholds ($\ge$ 164 Quant, $\ge$ 4.0 AWA) with Indian GATE CS alternatives, mandatory APS certification (India, China, Vietnam), CEFR-aligned language requirements, tuition fees (€6,000/semester for non-EU students), and curricular assessment prerequisites.
- **RWTH Aachen University — M.Sc. Computer Science (Germany):** Evaluates prior coursework credit overlap (maximum 42 CP bridgeable gap), German C1 proficiency requirements, GRE percentiles (Quant > 75th percentile), and €0 tuition confirmation.
- **KAIST — M.S. Artificial Intelligence & M.S. Computer Science (South Korea):** Evaluates non-Korean citizenship eligibility gates, English test cutoffs (accounting for the post-21 Jan 2026 TOEFL scale revision), English-medium bachelor waivers, and full international tuition scholarship coverage.
- **Secondary Aggregator Grounding:** Ingests third-party portal records (Yocket, MyGermanUniversity) specifically to benchmark and detect secondary-source inaccuracies against official baselines.

#### Verified Retrieval Performance
Evaluated across a benchmark dataset of 32 hand-labeled admissions queries spanning GPA, language minimums, GRE/GATE cutoffs, deadlines, tuition, and prerequisite credits:
- **BM25 only:** Recall@5: 78.1% | MRR: 0.6306
- **Dense only (`all-MiniLM-L6-v2`):** Recall@5: 93.8% | MRR: 0.7966
- **BM25 + Dense (RRF, $k=60$):** Recall@5: 87.5% | MRR: 0.7724
- **RRF + Cross-Encoder Reranker (`ms-marco-MiniLM-L-6-v2`):** Recall@5: 87.5% | **MRR: 0.8700** (guarantees the authoritative ground-truth passage ranks at the top).

#### Authority-Weighted Conflict Detection
- Cross-references incoming facts against official baselines with 100% precision on benchmarked aggregator claims.
- Catches real-world errors such as commercial portals reporting GRE as universally mandatory when official policies restrict it to specific nationalities, or portals publishing rigid cutoffs where official universities accept CEFR-equivalent certification paths.
- Automatically injects warning banners into the RAG generation prompt to prevent the LLM from hallucinating outdated aggregator claims.

#### High-Performance SQLite Cache Layer
- Eliminates live network scrape bottlenecks by caching parsed requirements in a local SQLite database with a 24-hour TTL.
- Tested over 100 benchmarked requests: reduces live scrape durations from **~4.71 seconds** down to a **0.88 ms median latency** (0.95 ms mean), delivering a >99.9% latency reduction.
- Implements *stale-while-revalidate*: if an upstream university portal is temporarily unreachable or blocks scrapers, the system safely falls back to the cached snapshot rather than crashing.

---

### Key Engineering Challenges & Solutions
- **Fragile University HTML Structures:** University admissions pages frequently alter layouts and CMS selectors. Resolved by developing modular, isolated scrapers per institution with fallback to hand-verified official records.
- **Ambiguous Academic Year Extraction:** University pages often mention historic fee policy years or regulation dates. Fixed by anchoring regex extraction strictly within admissions-context keyword windows.
- **Aggregator Hallucinations in RAG:** Aggregators often omit crucial eligibility nuances (e.g., country exemptions or degree waiver conditions). Resolved by enforcing strict source-hierarchy weighting where Tier-1 official facts supersede secondary claims.
- **Zero-Latency Container Startup:** Pre-cached SentenceTransformer and CrossEncoder model weights during Docker build time to eliminate cold-start download delays and Hugging Face API rate limits in production.

---

## Deployment & Running Outbound

### 1. Docker Compose (Local Deployment)

Build and start the application using Docker Compose:

```bash
docker compose up --build -d
```

Once the containers are running, access the application through the following endpoints:

- **Frontend UI:** [http://localhost:3000](http://localhost:3000)
- **Backend API:** [http://localhost:8000](http://localhost:8000)
- **Interactive API Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check Endpoint:** [http://localhost:8000/health](http://localhost:8000/health)

### 2. Live Cloud Deployment (Render)

Outbound is deployed and publicly accessible through Render.

**Production URL:**

- **Live Application:** [https://outbound-3i53.onrender.com/](https://outbound-3i53.onrender.com/)

---

### Future Roadmap
- **Broader Institutional Coverage:** Expand the program catalog from Germany and South Korea to additional top institutions across Europe (ETH Zurich, TU Delft, TU Berlin, Stuttgart) and Asia.
- **Automated Curricular Overlap & ECTS Auditing:** Implement transcript syllabus parsing to evaluate course prerequisites automatically against university-specific credit criteria.
- **Scraper Drift Monitoring:** Add recurring cron monitoring to detect university portal DOM mutations and alert before data pipelines break.
- **Automated RAG Factuality Evaluation:** Implement continuous synthetic test suites to benchmark answer hallucination rates and citation accuracy across LLM versions.
- **Document & Transcript Parsing:** Enable applicants to upload unofficial transcripts and standardized test scorecards to populate their eligibility profile automatically.
