# Outbound

**Outbound** is a source-grounded Masters eligibility engine designed to help me decide which countries, universities, and programs I am actually eligible for when planning my studies abroad.

### Problem
When researching Masters programs abroad, I have to manually compare dozens of universities across different countries, each with different GPA requirements, prerequisites, language scores, ECTS requirements, deadlines, and application rules. Information is scattered across university websites, DAAD, and secondary sources, and these sources sometimes contradict each other or contain outdated information.

This makes it difficult to answer a simple question: **“Which universities am I actually eligible for, and what requirements do I still need to meet?”**

Outbound automates this comparison while showing where each requirement came from and flagging conflicting or potentially outdated information.

### Architecture
- **Backend:** FastAPI with separate modules for ingestion, retrieval, eligibility, conflict detection, temporal checks, and ECTS mapping.
- **Frontend:** React + Vite.
- **Retrieval:** Hybrid BM25 + embeddings.
- **Evaluation:** RAG evaluation harness planned for later.
- Modules communicate through the API layer to keep the system modular.

### Progress
**Phase 0 — Setup:** Complete.

**Phase 1 — Data ingestion:** In progress.
- **1/10 universities completed:** TU Munich — M.Sc. Informatics.
- Extracted and verified qualification, language, GRE/GATE, APS, deadlines, ECTS, and program duration.
- Each requirement records its source, academic year, retrieval date, and extraction method.
- Found a real conflict between secondary sources and TUM's official requirements regarding language-score cutoffs.

### Key Challenges
- **Unreliable HTML parsing:** TUM's inconsistent structure caused some requirements to be silently missed, leading to verified manual extraction for now.
- **Incorrect academic-year extraction:** Fixed by identifying years specifically within admissions-related context.
- **Different university structures:** Individual scrapers are being developed for each university rather than relying on one generic parser.

### Current Status
**Phase 1 — Data ingestion: 1 of 10 universities complete.**