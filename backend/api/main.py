"""
outbound/backend/api/main.py

The ONLY module allowed to wire ingestion -> eligibility together, per the
project's modularity rule (base_scraper.py's own docstring: "Scrapers never
talk to each other or to other modules directly -- only api/ sequences
ingestion -> extraction -> everything else"). Nothing in ingestion/ or
eligibility/ imports from here or from each other directly.

Endpoints:
    POST /eligibility
        body: a JSON profile (see EligibilityRequest below)
        optional query param: universities (repeated) -- filter to only the
                 named universities instead of checking all registered ones.
                 Matched against each checker's `university` attribute.
        returns: a list of per-university eligibility results, one per
                 checked university, each with overall_status and a full
                 breakdown of individual requirement judgments.

    GET /universities
        No scraping, no live network call -- just name + program metadata
        for every registered university, for building a picker UI fast
        (e.g. a comparison-view checkbox list) without paying the cost of
        a full live eligibility check just to show the available options.
        Includes country and active_requirements for frontend dynamic rendering.

    GET /search?q=...&top_k=5
        Free-text search over the requirements corpus, for questions like
        "what language do I need for RWTH?" without knowing the answer
        lives in a record called `german_test`. Two-stage pipeline:
        hybrid_retriever.retrieve() casts a wide net (BM25 + embeddings,
        fused via RRF) over ALL requirement records across every
        registered university, then reranker.rerank() re-scores that
        shortlist with a cross-encoder for final precision. Per
        hybrid_retriever.py's own docstring, this is explicitly NOT used
        by eligibility-checking (that stays direct dictionary lookup by
        requirement_type, in the checkers) -- this is a separate,
        additive feature.

    GET /health

    POST /ask
        RAG Generation endpoint. Retrieves context, runs the conflict engine, 
        and synthesizes an answer using Groq.

Design notes:
- Scraper .run() calls hit the LIVE university pages over the network on
  every request. For a v1/demo slice this is acceptable (matches the
  project's "always-current, never-cached-silently" philosophy), but it
  does mean these endpoints are slow (N real HTTP fetches per call) and
  will fail loudly if a university site is down or blocks the request --
  that failure is surfaced per-university for /eligibility (see
  UNIVERSITIES loop below), not used to fail the whole request, so one
  broken site doesn't take down the other three. /search currently has no
  equivalent per-university isolation -- if ANY scraper fails while
  building the corpus, the whole search fails. Flagged as a known gap,
  not fixed here, since /eligibility already established the right
  pattern and /search should eventually follow it -- left as a documented
  next step rather than solved speculatively.
- A results cache (by university, refreshed on some interval) is a natural
  v2 improvement once this is proven end-to-end -- not built now, to keep
  this slice's failure modes easy to reason about (every call is a fresh,
  honest fetch, nothing silently stale). This matters MORE for /search
  than /eligibility, since every search re-scrapes AND re-embeds the full
  corpus from scratch -- noticeably slower than /eligibility. Acceptable
  for now, same "prove it works before optimizing" reasoning as elsewhere
  in this project, but the first thing to fix if /search feels too slow
  in practice.
- `country` is included per-university in the /eligibility response so the
  frontend can offer a "filter by country" dropdown without needing a
  separate endpoint.
"""

from __future__ import annotations

import sys
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from groq import Groq

# 1. LOAD ENV VARS FIRST
load_dotenv()

# 2. INITIALIZE GROQ SAFELY
# Passing a fallback string prevents Uvicorn from crashing on startup if the .env file is missing.
# The /ask route's try/except block will cleanly catch the resulting auth error.
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY", "missing_key_fallback"))

# --- Make sibling packages importable (ingestion/, eligibility/, retrieval/) ---
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(BACKEND_ROOT / "ingestion"))
sys.path.append(str(BACKEND_ROOT / "eligibility"))
sys.path.append(str(BACKEND_ROOT / "retrieval"))
sys.path.append(str(BACKEND_ROOT / "conflict_detection"))

from base_checker import UserProfile  # noqa: E402

from scraper_tum_informatics import TUMInformaticsScraper  # noqa: E402
from scraper_rwth_computer_science import RWTHComputerScienceScraper  # noqa: E402
from scraper_kaist_ai import KAISTAIScraper  # noqa: E402
from scraper_kaist_cs import KAISTCSScraper  # noqa: E402
from scraper_tum_english_mygermanuniversity import TUMEnglishMyGermanUniversityScraper # noqa: E402
from scraper_tum_english_yocket import TUMEnglishYocketScraper # noqa: E402

from checker_tum import TUMEligibilityChecker  # noqa: E402
from checker_rwth import RWTHEligibilityChecker  # noqa: E402
from checker_kaist_ai import KAISTAIEligibilityChecker  # noqa: E402
from checker_kaist_cs import KAISTCSEligibilityChecker  # noqa: E402

from hybrid_retriever import retrieve as hybrid_retrieve  # noqa: E402
from reranker import rerank  # noqa: E402
from detect_conflicts import detect_conflicts  # noqa: E402


app = FastAPI(title="Outbound Eligibility API")

# Wide open for local frontend dev. Tighten to specific origins before any
# real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


UNIVERSITIES = [
    (TUMInformaticsScraper, TUMEligibilityChecker),
    (RWTHComputerScienceScraper, RWTHEligibilityChecker),
    (KAISTAIScraper, KAISTAIEligibilityChecker),
    (KAISTCSScraper, KAISTCSEligibilityChecker),
]

SEARCH_SCRAPERS = [cls for cls, _ in UNIVERSITIES]


class UniversityInfoOut(BaseModel):
    """Lightweight metadata only -- no scraping, no live network call."""
    university: str
    program: str
    country: str
    active_requirements: list[str]


@app.get("/universities", response_model=list[UniversityInfoOut])
def list_universities() -> list[UniversityInfoOut]:
    results = []
    for _, checker_cls in UNIVERSITIES:
        uni = getattr(checker_cls, "university", checker_cls.__name__)
        prog = getattr(checker_cls, "program", "")
        
        country = "Unknown"
        reqs = ["cgpa", "english_test"]
        
        if "TUM" in uni or "Munich" in uni:
            country = "Germany"
            reqs.extend(["gre", "gate"])
        elif "RWTH" in uni or "Aachen" in uni:
            country = "Germany"
            reqs.extend(["gre", "german_test"])
        elif "KAIST" in uni or "Seoul" in uni:
            country = "South Korea"
            
        results.append(
            UniversityInfoOut(
                university=uni,
                program=prog,
                country=country,
                active_requirements=reqs,
            )
        )
    return results


class EligibilityRequest(BaseModel):
    model_config = {"extra": "allow"}

    flow: str

    citizenship: Optional[str] = None
    undergrad_country: Optional[str] = None
    cgpa: Optional[float] = None

    gre_quant_scaled: Optional[int] = None
    gre_quant_percentile: Optional[int] = None
    gre_verbal_percentile: Optional[int] = None
    gre_awa: Optional[float] = None
    gate_score_reported: bool = False

    english_test_type: Optional[str] = None
    english_score: Optional[float] = None
    toefl_test_date_on_or_after_2026_01_21: Optional[bool] = None
    undergrad_institution_english_medium: Optional[bool] = None

    german_level: Optional[str] = None

    is_eu_eea_citizen: Optional[bool] = None
    is_bildungsinlaender: Optional[bool] = None

    def to_user_profile(self) -> UserProfile:
        known_fields = self.model_dump(exclude_unset=True)
        return UserProfile(**{k: v for k, v in known_fields.items() if hasattr(UserProfile, k) or k in UserProfile.__annotations__})


class RequirementJudgmentOut(BaseModel):
    requirement_type: str
    status: str
    detail: str
    source_value: str


class UniversityResultOut(BaseModel):
    university: str
    program: str
    country: str
    academic_year: str
    overall_status: str
    judgments: list[RequirementJudgmentOut]
    error: Optional[str] = None


@app.post("/eligibility", response_model=list[UniversityResultOut])
def check_eligibility(
    request: EligibilityRequest,
    universities: Optional[list[str]] = Query(default=None),
) -> list[UniversityResultOut]:
    profile = request.to_user_profile()
    results: list[UniversityResultOut] = []

    universities_to_check = UNIVERSITIES
    if universities:
        wanted = set(universities)
        universities_to_check = [
            (scraper_cls, checker_cls)
            for scraper_cls, checker_cls in UNIVERSITIES
            if getattr(checker_cls, "university", None) in wanted
        ]

    for scraper_cls, checker_cls in universities_to_check:
        try:
            raw_requirements = scraper_cls().run()
            result = checker_cls().check(profile, raw_requirements)
            country = raw_requirements[0].country if raw_requirements else "unknown"
            results.append(UniversityResultOut(
                university=result.university,
                program=result.program,
                country=country,
                academic_year=result.academic_year,
                overall_status=result.overall_status,
                judgments=[
                    RequirementJudgmentOut(
                        requirement_type=j.requirement_type,
                        status=j.status,
                        detail=j.detail,
                        source_value=j.source_value,
                    )
                    for j in result.judgments
                ],
            ))
        except Exception as exc:
            results.append(UniversityResultOut(
                university=getattr(checker_cls, "university", checker_cls.__name__),
                program=getattr(checker_cls, "program", ""),
                country="unknown",
                academic_year="unknown_year",
                overall_status="needs_review",
                judgments=[],
                error=f"{type(exc).__name__}: {exc}",
            ))

    return results


class SearchResultOut(BaseModel):
    university: str
    program: str
    requirement_type: str
    value: str
    source_url: str
    source_tier: int
    academic_year: str
    extraction_method: str
    rerank_score: float


@app.get("/search", response_model=list[SearchResultOut])
def search(
    q: str = Query(..., min_length=1),
    top_k: int = Query(5, ge=1, le=20),
    retrieve_k: int = Query(15, ge=1, le=50),
) -> list[SearchResultOut]:
    all_reqs = []
    for scraper_cls in SEARCH_SCRAPERS:
        all_reqs.extend(scraper_cls().run())

    candidates = hybrid_retrieve(q, top_k=retrieve_k, requirements=all_reqs)
    reranked = rerank(q, [c.requirement for c in candidates], top_k=top_k)

    return [
        SearchResultOut(
            university=r.record.university,
            program=r.record.program,
            requirement_type=r.record.requirement_type,
            value=r.record.value,
            source_url=r.record.source_url,
            source_tier=r.record.source_tier,
            academic_year=r.record.academic_year,
            extraction_method=r.record.extraction_method,
            rerank_score=r.rerank_score,
        )
        for r in reranked
    ]


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


# --- RAG CHATBOT ENDPOINT ---

class AskRequest(BaseModel):
    question: str

class AskResponse(BaseModel):
    answer: str
    sources: list[str]


@app.post("/ask", response_model=AskResponse)
def ask_question(request: AskRequest):
    """Retrieves context, runs the conflict engine, and synthesizes an answer using Groq."""
    
    # 1. Gather all requirements to search through
    all_reqs = []
    third_party_scrapers = [TUMEnglishMyGermanUniversityScraper, TUMEnglishYocketScraper]
    for scraper_cls in SEARCH_SCRAPERS + third_party_scrapers:
        try:
            all_reqs.extend(scraper_cls().run())
        except Exception:
            pass

    # 2. Retrieve top relevant facts for the user's question (expanded to 15 to prevent single-university tunnel vision)
    candidates = hybrid_retrieve(request.question, top_k=30, requirements=all_reqs)
    reranked = rerank(request.question, [c.requirement for c in candidates], top_k=15)
    retrieved_reqs = [r.record for r in reranked]

    # 3. Check if any of these retrieved facts have known conflicts
    all_conflicts = detect_conflicts(all_reqs)
    relevant_conflicts = []
    
    for conflict in all_conflicts:
        for req in retrieved_reqs:
            if req.university == conflict.university and req.requirement_type == conflict.requirement_type:
                relevant_conflicts.append(conflict)
                break

    # 4. Construct the prompt with the Context and the Conflict Warnings
    context_str = "\n".join([
        f"- {r.university} ({r.program}): {r.requirement_type} = '{r.value}' (Source Tier {r.source_tier})"
        for r in retrieved_reqs
    ])
    
    conflict_str = ""
    if relevant_conflicts:
        conflict_str = "⚠️ CRITICAL DATA CONFLICTS DETECTED (MUST WARN USER):\n"
        for c in relevant_conflicts:
            conflict_str += (
                f"- For {c.university} {c.requirement_type}, third-party sites claim '{c.secondary[0].value}', "
                f"but the OFFICIAL Tier-1 source states '{c.authoritative.value}'.\n"
            )

    system_prompt = f"""You are Outbound, an expert Master's degree admissions assistant.
Your job is to answer the user's question STRICTLY using the verified context records below.
Do not invent or assume information. If the answer is not in the context, say "The official requirements do not specify this."

CONTEXT RECORDS:
{context_str}

{conflict_str}

INSTRUCTIONS:
1. Answer clearly and concisely.
2. If there is a CRITICAL DATA CONFLICT listed above, you MUST explicitly warn the user in your response. State the false third-party claim, but emphasize that the Official Tier-1 source is the correct rule to follow.
"""

    # 5. Generate the answer using Groq (Llama 3 8B)
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.question}
            ],
            model="openai/gpt-oss-20b"
        )
        answer_text = chat_completion.choices[0].message.content
    except Exception as e:
        answer_text = f"Error communicating with LLM: {str(e)}. Please check your GROQ_API_KEY in the .env file."

    # 6. Extract unique source URLs to cite
    unique_sources = list({r.source_url for r in retrieved_reqs})
    
    return AskResponse(answer=answer_text, sources=unique_sources)