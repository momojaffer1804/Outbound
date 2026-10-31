"""
outbound/backend/eligibility/coursework_auditor.py

Automated Coursework & ECTS Credit Gap Auditor.
Evaluates applicant undergraduate course coverage against core European CS competency clusters:
- Theoretical Computer Science
- Practical Computer Science
- Technical Computer Science / Systems
- Higher Mathematics

Applies university-specific gap thresholds (e.g. RWTH Aachen 42 CP bridgeable limit,
TU Berlin mandatory subject minimums, TU Darmstadt 30 CP limit).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class CourseworkCategoryResult:
    category: str
    label: str
    required_ects: float
    completed_ects: float
    gap_ects: float
    is_satisfied: bool
    description: str


@dataclass
class CourseworkAuditResult:
    total_required_ects: float
    total_completed_ects: float
    total_gap_ects: float
    category_breakdown: List[CourseworkCategoryResult]
    rwth_eligible: bool
    rwth_verdict: str
    tu_berlin_eligible: bool
    tu_berlin_verdict: str
    tu_darmstadt_eligible: bool
    tu_darmstadt_verdict: str
    recommendations: List[str]


# Standard reference requirements (based on RWTH Aachen B.Sc. Informatik curriculum)
STANDARD_REQUIREMENTS = {
    "theoretical_cs": {
        "label": "Theoretical Computer Science",
        "required_ects": 28.0,
        "description": "Formal languages, automata theory, computability, complexity theory, and mathematical logic.",
        "tu_berlin_min": 12.0
    },
    "practical_cs": {
        "label": "Practical Computer Science",
        "required_ects": 32.0,
        "description": "Programming paradigms, data structures & algorithms, databases, software engineering, and ML/data science.",
        "tu_berlin_min": 0.0
    },
    "technical_cs": {
        "label": "Technical Computer Science / Systems",
        "required_ects": 22.0,
        "description": "Computer architecture, operating systems, data communications/networking, and system programming.",
        "tu_berlin_min": 12.0
    },
    "mathematics": {
        "label": "Higher Mathematics",
        "required_ects": 28.0,
        "description": "Discrete structures, linear algebra, calculus/analysis, and probability & applied statistics.",
        "tu_berlin_min": 18.0
    }
}


def audit_coursework(
    credits: Dict[str, float],
    credit_system: str = "ECTS"  # "ECTS", "US_SEMESTER" (1 credit = 1.8 ECTS), "INDIAN_CREDIT" (1 credit = 1.5 ECTS)
) -> CourseworkAuditResult:
    """
    Audits completed credits against the four CS clusters.
    credits: dict mapping category keys to numeric completed values.
    """
    # Conversion factor to ECTS
    factor = 1.0
    if credit_system.upper() in ("US_SEMESTER", "US"):
        factor = 1.8
    elif credit_system.upper() in ("INDIAN_CREDIT", "INDIA", "IN"):
        factor = 1.5

    breakdown: List[CourseworkCategoryResult] = []
    total_required = 0.0
    total_completed = 0.0
    total_gap = 0.0
    recommendations: List[str] = []

    for key, spec in STANDARD_REQUIREMENTS.items():
        req_ects = spec["required_ects"]
        raw_val = float(credits.get(key, 0.0))
        completed_ects = round(raw_val * factor, 1)
        gap = max(0.0, round(req_ects - completed_ects, 1))

        is_satisfied = gap <= 0.0
        total_required += req_ects
        total_completed += completed_ects
        total_gap += gap

        breakdown.append(CourseworkCategoryResult(
            category=key,
            label=spec["label"],
            required_ects=req_ects,
            completed_ects=completed_ects,
            gap_ects=gap,
            is_satisfied=is_satisfied,
            description=spec["description"]
        ))

        if gap > 0:
            recommendations.append(f"Consider bridge courses or self-study in {spec['label']} to close a {gap} ECTS deficit.")

    total_gap = round(total_gap, 1)

    # 1. RWTH Aachen Assessment (Max 42 CP gap limit)
    rwth_eligible = total_gap <= 42.0
    if total_gap == 0:
        rwth_verdict = "Fully Eligible: No coursework deficit detected. Unconditional academic equivalence."
    elif rwth_eligible:
        rwth_verdict = f"Conditionally Eligible: Total deficit of {total_gap} ECTS is within RWTH's 42 CP bridgeable ceiling. You will be assigned bridge modules during your Master's."
    else:
        rwth_verdict = f"Ineligible: Coursework deficit of {total_gap} ECTS exceeds RWTH's strict 42 CP maximum bridge limit. Direct admission is not possible."

    # 2. TU Berlin Assessment (12 Theory, 12 Systems, 18 Math)
    theory_completed = next((b.completed_ects for b in breakdown if b.category == "theoretical_cs"), 0.0)
    systems_completed = next((b.completed_ects for b in breakdown if b.category == "technical_cs"), 0.0)
    math_completed = next((b.completed_ects for b in breakdown if b.category == "mathematics"), 0.0)

    tu_berlin_eligible = (theory_completed >= 12.0) and (systems_completed >= 12.0) and (math_completed >= 18.0)
    if tu_berlin_eligible:
        tu_berlin_verdict = "Eligible: Meets TU Berlin's mandatory subject minimums (>=12 Theory, >=12 Systems, >=18 Math)."
    else:
        failed_parts = []
        if theory_completed < 12.0:
            failed_parts.append(f"Theoretical CS ({theory_completed}/12 ECTS)")
        if systems_completed < 12.0:
            failed_parts.append(f"Systems/Architecture ({systems_completed}/12 ECTS)")
        if math_completed < 18.0:
            failed_parts.append(f"Mathematics ({math_completed}/18 ECTS)")
        tu_berlin_verdict = f"Ineligible: Fails TU Berlin minimum threshold in: {', '.join(failed_parts)}."

    # 3. TU Darmstadt Assessment (30 CP deficit ceiling)
    tu_darmstadt_eligible = total_gap <= 30.0
    if tu_darmstadt_eligible:
        tu_darmstadt_verdict = f"Eligible: Total gap ({total_gap} ECTS) is within the 30 CP entrance examination limit."
    else:
        tu_darmstadt_verdict = f"Ineligible: Total gap ({total_gap} ECTS) exceeds TU Darmstadt's 30 CP deficit limit."

    return CourseworkAuditResult(
        total_required_ects=total_required,
        total_completed_ects=total_completed,
        total_gap_ects=total_gap,
        category_breakdown=breakdown,
        rwth_eligible=rwth_eligible,
        rwth_verdict=rwth_verdict,
        tu_berlin_eligible=tu_berlin_eligible,
        tu_berlin_verdict=tu_berlin_verdict,
        tu_darmstadt_eligible=tu_darmstadt_eligible,
        tu_darmstadt_verdict=tu_darmstadt_verdict,
        recommendations=recommendations
    )
