"""
outbound/backend/api/main.py

Central FastAPI service connecting ingestion, eligibility, hybrid retrieval,
asymmetric conflict resolution, persistent SQLite caching, and coursework/document auditing.
"""

from __future__ import annotations

import sys
import os
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY", "missing_key_fallback"))

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(BACKEND_ROOT / "ingestion"))
sys.path.append(str(BACKEND_ROOT / "eligibility"))
sys.path.append(str(BACKEND_ROOT / "retrieval"))
sys.path.append(str(BACKEND_ROOT / "conflict_detection"))
sys.path.append(str(BACKEND_ROOT / "cache"))
sys.path.append(str(BACKEND_ROOT / "extraction"))

from base_checker import UserProfile

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

from scraper_tum_english_mygermanuniversity import TUMEnglishMyGermanUniversityScraper
from scraper_tum_english_yocket import TUMEnglishYocketScraper

from checker_tum import TUMEligibilityChecker
from checker_rwth import RWTHEligibilityChecker
from checker_kaist_ai import KAISTAIEligibilityChecker
from checker_kaist_cs import KAISTCSEligibilityChecker
from checker_tu_berlin import TUBerlinEligibilityChecker
from checker_stuttgart import StuttgartEligibilityChecker
from checker_tu_darmstadt import TUDarmstadtEligibilityChecker
from checker_tu_delft import TUDelftEligibilityChecker
from checker_eth_zurich import ETHZurichEligibilityChecker
from checker_nus import NUSEligibilityChecker

from hybrid_retriever import retrieve as hybrid_retrieve
from reranker import rerank
from detect_conflicts import detect_conflicts
from scraper_cache import scraper_cache
from coursework_auditor import audit_coursework

app = FastAPI(title="Outbound Eligibility API")

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
    (TUBerlinCSScraper, TUBerlinEligibilityChecker),
    (StuttgartCSScraper, StuttgartEligibilityChecker),
    (TUDarmstadtCSScraper, TUDarmstadtEligibilityChecker),
    (TUDelftCSScraper, TUDelftEligibilityChecker),
    (ETHZurichCSScraper, ETHZurichEligibilityChecker),
    (NUSComputingScraper, NUSEligibilityChecker),
]

SEARCH_SCRAPERS = [cls for cls, _ in UNIVERSITIES]
ALL_SCRAPERS = SEARCH_SCRAPERS + [TUMEnglishMyGermanUniversityScraper, TUMEnglishYocketScraper]


class UniversityInfoOut(BaseModel):
    university: str
    program: str
    country: str
    active_requirements: list[str]


@app.get("/universities", response_model=list[UniversityInfoOut])
def list_universities() -> list[UniversityInfoOut]:
    results = []
    for scraper_cls, checker_cls in UNIVERSITIES:
        uni = getattr(checker_cls, "university", checker_cls.__name__)
        prog = getattr(checker_cls, "program", "")
        country = getattr(scraper_cls, "country", "Unknown")

        reqs = ["cgpa", "english_test"]
        if "TUM" in uni or "Munich" in uni:
            reqs.extend(["gre", "gate"])
        elif "RWTH" in uni or "Aachen" in uni:
            reqs.extend(["gre", "german_test"])
        elif "Berlin" in uni:
            reqs.extend(["german_test"])
        elif "Stuttgart" in uni:
            reqs.extend(["gre"])
        elif "Darmstadt" in uni:
            reqs.extend(["gre"])
        elif "Delft" in uni:
            reqs.extend(["gre"])
        elif "ETH" in uni or "Zurich" in uni:
            reqs.extend(["gre"])
        elif "NUS" in uni or "Singapore" in uni:
            reqs.extend(["gre", "gate"])

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
            raw_requirements = scraper_cache.get_cached_or_fetch(scraper_cls)
            result = checker_cls().check(profile, raw_requirements)
            country = raw_requirements[0].country if raw_requirements else getattr(scraper_cls, "country", "unknown")
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
                country=getattr(scraper_cls, "country", "unknown"),
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
    retrieve_k: int = Query(25, ge=1, le=50),
) -> list[SearchResultOut]:
    all_reqs = []
    for scraper_cls in SEARCH_SCRAPERS:
        try:
            all_reqs.extend(scraper_cache.get_cached_or_fetch(scraper_cls))
        except Exception:
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
    all_reqs = []
    for scraper_cls in ALL_SCRAPERS:
        try:
            all_reqs.extend(scraper_cache.get_cached_or_fetch(scraper_cls))
        except Exception:
            pass

    use_emb = os.getenv("ENABLE_NEURAL_RETRIEVAL", "false").lower() == "true"
    candidates = hybrid_retrieve(request.question, top_k=8, requirements=all_reqs, use_embeddings=use_emb)
    retrieved_reqs = [c.requirement for c in candidates]

    all_conflicts = detect_conflicts(all_reqs)
    relevant_conflicts = []

    for conflict in all_conflicts:
        for req in retrieved_reqs:
            if req.university == conflict.university and req.requirement_type == conflict.requirement_type:
                relevant_conflicts.append(conflict)
                break

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

    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.question}
            ],
            model="openai/gpt-oss-120b"
        )
        answer_text = chat_completion.choices[0].message.content
    except Exception as e:
        # Fallback to smaller model if rate limited or model not found
        try:
            chat_completion = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": request.question}
                ],
                model="openai/gpt-oss-20b"
            )
            answer_text = chat_completion.choices[0].message.content
        except Exception as e2:
            answer_text = f"Error communicating with LLM: {str(e2)}. Please check your GROQ_API_KEY."

    unique_sources = list({r.source_url for r in retrieved_reqs})
    return AskResponse(answer=answer_text, sources=unique_sources)


# --- COURSEWORK & ECTS AUDITOR ENDPOINT ---

class CourseworkAuditRequest(BaseModel):
    credits: Dict[str, float]
    credit_system: str = "ECTS"


@app.post("/audit/coursework")
def audit_coursework_endpoint(request: CourseworkAuditRequest):
    return audit_coursework(credits=request.credits, credit_system=request.credit_system)


# --- CACHE ADMIN ENDPOINTS ---

@app.get("/cache/status")
def cache_status():
    return scraper_cache.get_cache_stats()


class CacheRefreshRequest(BaseModel):
    force: bool = True
    university: Optional[str] = None


@app.post("/cache/refresh")
def cache_refresh(request: CacheRefreshRequest = CacheRefreshRequest()):
    refreshed = []
    for scraper_cls in ALL_SCRAPERS:
        if request.university and request.university.lower() not in scraper_cls.university.lower():
            continue
        try:
            reqs = scraper_cache.get_cached_or_fetch(scraper_cls, force_refresh=request.force)
            refreshed.append({
                "university": scraper_cls.university,
                "program": scraper_cls.program,
                "records": len(reqs),
                "status": "refreshed",
            })
        except Exception as exc:
            refreshed.append({
                "university": scraper_cls.university,
                "program": scraper_cls.program,
                "records": 0,
                "status": f"failed: {exc}",
            })
    return {"refreshed": refreshed}


# --- STARTUP EVENT ---

import threading

@app.on_event("startup")
def on_startup():
    def background_warmup():
        try:
            scraper_cache.warm_up(ALL_SCRAPERS)
            reqs = []
            for s in ALL_SCRAPERS:
                try:
                    reqs.extend(scraper_cache.get_cached_or_fetch(s))
                except Exception:
                    pass
            if reqs:
                hybrid_retrieve("admission requirements", top_k=5, requirements=reqs)
        except Exception as exc:
            logger.warning("Background warm-up failed: %s", exc)

    # Launch in background so uvicorn binds and responds to Render health checks instantly (<10ms)
    threading.Thread(target=background_warmup, daemon=True).start()


# --- STATIC ASSET SERVING ---
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

possible_dist_dirs = [
    BACKEND_ROOT.parent / "frontend" / "dist",
    BACKEND_ROOT / "frontend" / "dist",
    BACKEND_ROOT / "dist",
    Path("/app/frontend/dist"),
    Path("/app/dist"),
]
frontend_dist = next((d for d in possible_dist_dirs if (d / "index.html").exists()), None)

if frontend_dist:
    if (frontend_dist / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/")
    def serve_root():
        return FileResponse(frontend_dist / "index.html")

    @app.get("/{full_path:path}")
    def serve_frontend_catchall(full_path: str):
        target = frontend_dist / full_path
        if target.exists() and target.is_file():
            return FileResponse(target)
        return FileResponse(frontend_dist / "index.html")
