"""
outbound/backend/eligibility/checker_tu_darmstadt.py

Eligibility checker for: TU Darmstadt -- M.Sc. Computer Science (Informatik)
"""

from __future__ import annotations
from base_checker import BaseEligibilityChecker, UserProfile, RequirementJudgment, UniversityEligibilityResult

APS_REQUIRED_COUNTRIES = {"China", "India", "Vietnam"}


class TUDarmstadtEligibilityChecker(BaseEligibilityChecker):
    university = "TU Darmstadt"
    program = "M.Sc. Computer Science (Informatik)"

    def check(self, profile: UserProfile, raw_requirements: list) -> UniversityEligibilityResult:
        judgments: list[RequirementJudgment] = []
        academic_year = raw_requirements[0].academic_year if raw_requirements else "2026/27"
        country = profile.undergrad_country or profile.citizenship

        # 1. Qualification basis (Entrance Competencies)
        qb = self._find(raw_requirements, "qualification_basis")
        judgments.append(RequirementJudgment(
            requirement_type="qualification_basis",
            status="needs_review",
            detail="Entrance assessment: requires evaluating competencies across Practical CS, Technical CS, Theory, and Math (max 30 CP deficit).",
            source_value=qb[0].value if qb else ""
        ))

        # 2. CGPA
        cgpa_val = self._find(raw_requirements, "cgpa")
        source_cgpa = cgpa_val[0].value if cgpa_val else ""
        if profile.cgpa is not None:
            if profile.cgpa >= 7.5:
                judgments.append(RequirementJudgment("cgpa", "met", f"CGPA {profile.cgpa:.2f}/10 satisfies competitive standing (>= 7.5/10).", source_cgpa))
            elif profile.cgpa >= 7.0:
                judgments.append(RequirementJudgment("cgpa", "needs_review", f"CGPA {profile.cgpa:.2f}/10 meets minimum 2.5 baseline, but depends on entrance exam evaluation.", source_cgpa))
            else:
                judgments.append(RequirementJudgment("cgpa", "not_met", f"CGPA {profile.cgpa:.2f}/10 is below the recommended threshold.", source_cgpa))
        else:
            judgments.append(RequirementJudgment("cgpa", "needs_review", "CGPA not provided (minimum ~7.0–7.5/10 required).", source_cgpa))

        # 3. English (C1 required: IELTS 7.0 / TOEFL 95)
        eng_val = self._find(raw_requirements, "english_test")
        source_eng = eng_val[0].value if eng_val else ""
        if profile.flow == "near_term":
            if profile.english_test_type == "IELTS":
                if profile.english_score and profile.english_score >= 7.0:
                    judgments.append(RequirementJudgment("english_test", "met", f"IELTS {profile.english_score} meets C1 requirement (>= 7.0).", source_eng))
                else:
                    judgments.append(RequirementJudgment("english_test", "not_met", f"IELTS {profile.english_score} does not meet C1 level (7.0 required).", source_eng))
            elif profile.english_test_type == "TOEFL":
                if profile.english_score and profile.english_score >= 95:
                    judgments.append(RequirementJudgment("english_test", "met", f"TOEFL iBT {profile.english_score} meets C1 requirement (>= 95).", source_eng))
                else:
                    judgments.append(RequirementJudgment("english_test", "not_met", f"TOEFL iBT {profile.english_score} does not meet C1 level (95 required).", source_eng))
            else:
                judgments.append(RequirementJudgment("english_test", "needs_review", "Requires English C1 certificate (IELTS 7.0 or TOEFL 95).", source_eng))
        else:
            judgments.append(RequirementJudgment("english_test", "needs_review", "Requires English C1 proficiency.", source_eng))

        # 4. APS Certificate
        if country in APS_REQUIRED_COUNTRIES:
            aps_val = self._find(raw_requirements, "aps_certificate")
            judgments.append(RequirementJudgment("aps_certificate", "needs_review", f"APS certificate mandatory for applicants from {country}.", aps_val[0].value if aps_val else ""))

        # 5. Tuition & Deadline
        tf = self._find(raw_requirements, "tuition_fees")
        if tf:
            judgments.append(RequirementJudgment("tuition_fees", "informational", tf[0].value, tf[0].value))
        dl = self._find(raw_requirements, "deadline")
        if dl:
            judgments.append(RequirementJudgment("deadline", "informational", dl[0].value, dl[0].value))

        overall = self._overall_from_judgments(judgments)
        return UniversityEligibilityResult(
            university=self.university,
            program=self.program,
            academic_year=academic_year,
            overall_status=overall,
            judgments=judgments
        )
