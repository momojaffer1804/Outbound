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
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --- Make sibling packages importable (ingestion/, eligibility/, retrieval/) ---
# Assumes the standard repo layout: outbound/backend/{ingestion,eligibility,api,retrieval}/
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(BACKEND_ROOT / "ingestion"))
sys.path.append(str(BACKEND_ROOT / "eligibility"))
sys.path.append(str(BACKEND_ROOT / "retrieval"))

from base_checker import UserProfile  # noqa: E402

from scraper_tum_informatics import TUMInformaticsScraper  # noqa: E402
from scraper_rwth_computer_science import RWTHComputerScienceScraper  # noqa: E402
from scraper_kaist_ai import KAISTAIScraper  # noqa: E402
from scraper_kaist_cs import KAISTCSScraper  # noqa: E402

from checker_tum import TUMEligibilityChecker  # noqa: E402
from checker_rwth import RWTHEligibilityChecker  # noqa: E402
from checker_kaist_ai import KAISTAIEligibilityChecker  # noqa: E402
from checker_kaist_cs import KAISTCSEligibilityChecker  # noqa: E402

from hybrid_retriever import retrieve as hybrid_retrieve  # noqa: E402
from reranker import rerank  # noqa: E402


app = FastAPI(title="Outbound Eligibility API")

# Wide open for local frontend dev. Tighten to specific origins before any
# real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# One (scraper_class, checker_class) pair per registered university.
# Adding a 5th university = adding one line here, per the project's own
# "add one module, touch nothing else" architecture goal.
UNIVERSITIES = [
    (TUMInformaticsScraper, TUMEligibilityChecker),
    (RWTHComputerScienceScraper, RWTHEligibilityChecker),
    (KAISTAIScraper, KAISTAIEligibilityChecker),
    (KAISTCSScraper, KAISTCSEligibilityChecker),
]

# Same scraper list, used by /search for building the retrieval corpus.
# Deliberately the scraper classes only (not paired with checkers) --
# /search works over raw requirement TEXT, it has no notion of a user
# profile or eligibility judgment.
SEARCH_SCRAPERS = [cls for cls, _ in UNIVERSITIES]


class UniversityInfoOut(BaseModel):
    """Lightweight metadata only -- no scraping, no live network call. For
    building a university picker UI (e.g. a comparison-view checkbox list)
    without paying the cost of a full live eligibility check just to show
    the list of available options."""
    university: str
    program: str


@app.get("/universities", response_model=list[UniversityInfoOut])
def list_universities() -> list[UniversityInfoOut]:
    return [
        UniversityInfoOut(
            university=getattr(checker_cls, "university", checker_cls.__name__),
            program=getattr(checker_cls, "program", ""),
        )
        for _, checker_cls in UNIVERSITIES
    ]


class EligibilityRequest(BaseModel):
    """Mirrors base_checker.UserProfile field-for-field. Kept as a separate
    Pydantic model (rather than reusing the dataclass directly) so FastAPI
    owns request validation/JSON schema, while UserProfile stays a plain
    dataclass the checkers can depend on without a FastAPI/pydantic import."""

    flow: str  # "early_planner" or "near_term"

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
        return UserProfile(**self.model_dump())


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
    error: Optional[str] = None  # set only if this university's scrape/check failed


@app.post("/eligibility", response_model=list[UniversityResultOut])
def check_eligibility(
    request: EligibilityRequest,
    universities: Optional[list[str]] = Query(
        default=None,
        description=(
            "Optional repeated param to filter which universities get "
            "scraped/checked, e.g. ?universities=TU Munich (TUM)&universities=KAIST. "
            "Names are matched against each checker's `university` attribute. "
            "Omit to check all registered universities (default, unchanged "
            "behavior). NOTE: this param needs the explicit Query() annotation "
            "below -- without it, FastAPI cannot tell whether this list belongs "
            "in the query string or the JSON body alongside `request`, and "
            "returns a confusing 422 'field request missing' error instead of "
            "a clear one. If this signature is edited later and that error "
            "reappears, check this annotation is still here first."
        ),
    ),
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
            # One university's scrape/check failing (site down, structure
            # changed, network blocked) must never take down the other
            # three -- surfaced per-university instead, per the project's
            # "never silently blend confidence levels" principle applied
            # to failures too.
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
    q: str = Query(..., min_length=1, description="Free-text question, e.g. 'what language do I need for RWTH?'"),
    top_k: int = Query(5, ge=1, le=20, description="How many results to return after reranking"),
    retrieve_k: int = Query(15, ge=1, le=50, description="How many candidates hybrid retrieval pulls BEFORE reranking narrows it down"),
) -> list[SearchResultOut]:
    """Two-stage search: hybrid_retriever casts a wide net (retrieve_k
    candidates), reranker narrows that down to the final top_k by actually
    scoring query+candidate pairs together. retrieve_k is deliberately
    larger than top_k and exposed as a param rather than hardcoded, since
    the right ratio between "how wide to search" and "how many to keep"
    is a tuning knob, not a fixed constant -- see reranker.py's own
    docstring on why reranking only reorders a SMALL shortlist rather than
    being run over the entire corpus directly.
    """
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