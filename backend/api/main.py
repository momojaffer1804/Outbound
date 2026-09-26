"""
outbound/backend/api/main.py

The ONLY module allowed to wire ingestion -> eligibility together, per the
project's modularity rule (base_scraper.py's own docstring: "Scrapers never
talk to each other or to other modules directly -- only api/ sequences
ingestion -> extraction -> everything else"). Nothing in ingestion/ or
eligibility/ imports from here or from each other directly.

Endpoint:
    POST /eligibility
        body: a JSON profile (see EligibilityRequest below)
        returns: a list of per-university eligibility results, one per
                 registered university, each with overall_status and a
                 full breakdown of individual requirement judgments.

Design notes:
- Scraper .run() calls hit the LIVE university pages over the network on
  every request. For a v1/demo slice this is acceptable (matches the
  project's "always-current, never-cached-silently" philosophy), but it
  does mean this endpoint is slow (4 real HTTP fetches per call) and will
  fail loudly if a university site is down or blocks the request -- that
  failure is surfaced per-university (see UNIVERSITIES loop below), not
  used to fail the whole request, so one broken site doesn't take down
  the other three.
- A results cache (by university, refreshed on some interval) is a natural
  v2 improvement once this is proven end-to-end -- not built now, to keep
  this slice's failure modes easy to reason about (every call is a fresh,
  honest fetch, nothing silently stale).
- `country` is included per-university in the response so the frontend can
  offer a "filter by country" dropdown without needing a separate endpoint.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --- Make sibling packages importable (ingestion/, eligibility/) ---
# Assumes the standard repo layout: outbound/backend/{ingestion,eligibility,api}/
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(BACKEND_ROOT / "ingestion"))
sys.path.append(str(BACKEND_ROOT / "eligibility"))

from base_checker import UserProfile  # noqa: E402

from scraper_tum_informatics import TUMInformaticsScraper  # noqa: E402
from scraper_rwth_computer_science import RWTHComputerScienceScraper  # noqa: E402
from scraper_kaist_ai import KAISTAIScraper  # noqa: E402
from scraper_kaist_cs import KAISTCSScraper  # noqa: E402

from checker_tum import TUMEligibilityChecker  # noqa: E402
from checker_rwth import RWTHEligibilityChecker  # noqa: E402
from checker_kaist_ai import KAISTAIEligibilityChecker  # noqa: E402
from checker_kaist_cs import KAISTCSEligibilityChecker  # noqa: E402


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
def check_eligibility(request: EligibilityRequest) -> list[UniversityResultOut]:
    profile = request.to_user_profile()
    results: list[UniversityResultOut] = []

    for scraper_cls, checker_cls in UNIVERSITIES:
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


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}