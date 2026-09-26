"""
outbound/backend/eligibility/base_checker.py

Base interface every per-university eligibility checker implements. Mirrors
base_scraper.py's pattern deliberately: one checker per university because
eligibility RULES differ structurally between universities (different GRE
exemption logic, different English-waiver systems, different qualification
gates), not because of laziness. A single generic engine trying to evaluate
every university's prose requirement values the same way is exactly the kind
of "runs cleanly, silently wrong" risk this project's own scrapers already
identified and rejected once (see scraper_tum_informatics.py's docstring on
the abandoned live-parsing attempt).

Every checker is HARDCODED-BUT-VERIFIED: the actual eligibility logic (GRE
thresholds, exemption rules, citizenship gates) is typed in by hand after
reading the real RawRequirement.value strings from the real scrapers, not
regex-parsed from that prose at runtime. If a university's rules change, the
corresponding checker file needs a manual update — same accepted tradeoff as
the scrapers.

Status vocabulary (used everywhere, keep consistent):
- "met"           — profile data confirms this requirement is satisfied
- "not_met"       — profile data confirms this requirement is NOT satisfied
- "needs_review"  — cannot be programmatically judged from profile inputs
                     alone (e.g. TUM's English requirement states no number
                     in-page; RWTH's coursework-overlap check needs a
                     transcript, not a single number). This is a legitimate,
                     honest output — NOT a bug to eventually "fix" by
                     guessing. Never silently upgrade "needs_review" to
                     "met" just to make a result look cleaner.
- "not_applicable"— requirement exists on the page but does not apply to
                     this profile (e.g. APS certificate for a non-China/
                     India/Vietnam applicant).
- "informational" — not an eligibility gate at all (deadlines, program
                     identity notes, ECTS/duration facts). Always shown to
                     the user, never counted in overall_status.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class UserProfile:
    flow: str  # "early_planner" or "near_term"

    citizenship: Optional[str] = None
    undergrad_country: Optional[str] = None  # country where Bachelor's was earned; defaults to citizenship if not given

    cgpa: Optional[float] = None  # 10-point scale, India-style

    # GRE — TUM uses scaled scores; RWTH uses PERCENTILES (different scales,
    # do not conflate). Collect both explicitly rather than guessing a
    # conversion.
    gre_quant_scaled: Optional[int] = None      # e.g. 164 (TUM's scale, 130-170)
    gre_quant_percentile: Optional[int] = None  # e.g. 80 (RWTH's scale, 0-100)
    gre_verbal_percentile: Optional[int] = None
    gre_awa: Optional[float] = None
    gate_score_reported: bool = False  # Indian applicants may submit GATE CS instead of GRE, for TUM

    # English
    english_test_type: Optional[str] = None  # "IELTS", "TOEFL", "TOEIC", "TEPS"
    english_score: Optional[float] = None
    toefl_test_date_on_or_after_2026_01_21: Optional[bool] = None  # needed because KAIST's TOEFL cutoff changed mid-cycle
    undergrad_institution_english_medium: Optional[bool] = None  # for KAIST's conditional English waiver — was the Bachelor's institution itself English-medium?

    # German (RWTH only)
    german_level: Optional[str] = None  # e.g. "C1", "B2", "A2", None

    # For RWTH's GRE exemption
    is_eu_eea_citizen: Optional[bool] = None
    is_bildungsinlaender: Optional[bool] = None  # completed secondary education in Germany


@dataclass
class RequirementJudgment:
    requirement_type: str
    status: str  # met / not_met / needs_review / not_applicable / informational
    detail: str
    source_value: str  # the original verified prose value, for transparency


@dataclass
class UniversityEligibilityResult:
    university: str
    program: str
    academic_year: str
    overall_status: str  # "eligible" / "not_eligible" / "needs_review"
    judgments: list[RequirementJudgment] = field(default_factory=list)


class BaseEligibilityChecker(ABC):
    university: str
    program: str

    @abstractmethod
    def check(self, profile: UserProfile, raw_requirements: list) -> UniversityEligibilityResult:
        """raw_requirements: the list[RawRequirement] this university's real
        scraper produced. Each checker reads the specific requirement_type
        records it knows how to evaluate for its own university."""
        raise NotImplementedError

    @staticmethod
    def _find(raw_requirements: list, requirement_type: str):
        """Return all RawRequirement records of a given type for this uni."""
        return [r for r in raw_requirements if r.requirement_type == requirement_type]

    @staticmethod
    def _overall_from_judgments(judgments: list[RequirementJudgment]) -> str:
        gating = [j for j in judgments if j.status not in ("informational",)]
        if any(j.status == "not_met" for j in gating):
            return "not_eligible"
        if any(j.status == "needs_review" for j in gating):
            return "needs_review"
        return "eligible"