"""
outbound/backend/eligibility/checker_tu_delft.py

Eligibility checker for: TU Delft (Delft University of Technology) -- M.Sc. Computer Science
"""

from __future__ import annotations
from base_checker import BaseEligibilityChecker, UserProfile, RequirementJudgment, UniversityEligibilityResult

NATIVE_ENGLISH_COUNTRIES = {"Netherlands", "United States", "USA", "United Kingdom", "UK", "Canada", "Australia", "New Zealand", "Ireland"}


class TUDelftEligibilityChecker(BaseEligibilityChecker):
    university = "TU Delft"
    program = "M.Sc. Computer Science"

    def check(self, profile: UserProfile, raw_requirements: list) -> UniversityEligibilityResult:
        judgments: list[RequirementJudgment] = []
        academic_year = raw_requirements[0].academic_year if raw_requirements else "2026/27"
        country = profile.undergrad_country or profile.citizenship

        # 1. Qualification basis
        qb = self._find(raw_requirements, "qualification_basis")
        judgments.append(RequirementJudgment(
            requirement_type="qualification_basis",
            status="needs_review",
            detail="Requires a research-university Bachelor's in CS / related field equivalent to a Dutch university BSc standard.",
            source_value=qb[0].value if qb else ""
        ))

        # 2. CGPA (Strict 75% or 8.0/10 cutoff)
        cgpa_val = self._find(raw_requirements, "cgpa")
        source_cgpa = cgpa_val[0].value if cgpa_val else ""
        if profile.cgpa is not None:
            if profile.cgpa >= 8.0:
                judgments.append(RequirementJudgment("cgpa", "met", f"CGPA {profile.cgpa:.2f}/10 meets the strict minimum 8.0/10 (75%) cutoff.", source_cgpa))
            else:
                judgments.append(RequirementJudgment("cgpa", "not_met", f"CGPA {profile.cgpa:.2f}/10 is below TU Delft's mandatory 8.0/10 (75%) cutoff.", source_cgpa))
        else:
            judgments.append(RequirementJudgment("cgpa", "needs_review", "CGPA not provided — TU Delft enforces a strict minimum 8.0/10 cutoff.", source_cgpa))

        # 3. GRE (Mandatory for all non-Dutch degrees: Quant >= 165)
        gre_val = self._find(raw_requirements, "gre")
        source_gre = gre_val[0].value if gre_val else ""
        if country == "Netherlands":
            judgments.append(RequirementJudgment("gre", "not_applicable", "GRE not required for Dutch BSc degree holders.", source_gre))
        elif profile.flow == "near_term":
            if profile.gre_quant_scaled is not None:
                if profile.gre_quant_scaled >= 165:
                    judgments.append(RequirementJudgment("gre", "met", f"GRE Quant scaled {profile.gre_quant_scaled} meets the mandatory cutoff (>= 165).", source_gre))
                else:
                    judgments.append(RequirementJudgment("gre", "not_met", f"GRE Quant scaled {profile.gre_quant_scaled} is below the mandatory 165 cutoff (applications below 165 are rejected).", source_gre))
            else:
                judgments.append(RequirementJudgment("gre", "not_met", "GRE Quantitative score >= 165 is strictly mandatory for all non-Dutch degrees.", source_gre))
        else:
            judgments.append(RequirementJudgment("gre", "needs_review", "GRE Quantitative score >= 165 is strictly mandatory for all non-Dutch degrees.", source_gre))

        # 4. English proficiency (IELTS >= 7.0, TOEFL >= 100)
        eng_val = self._find(raw_requirements, "english_test")
        source_eng = eng_val[0].value if eng_val else ""
        if country in NATIVE_ENGLISH_COUNTRIES:
            judgments.append(RequirementJudgment("english_test", "not_applicable", f"Exempt based on degree country ({country}).", source_eng))
        elif profile.flow == "near_term":
            if profile.english_test_type == "IELTS":
                if profile.english_score and profile.english_score >= 7.0:
                    judgments.append(RequirementJudgment("english_test", "met", f"IELTS {profile.english_score} meets TU Delft cutoff (>= 7.0).", source_eng))
                else:
                    judgments.append(RequirementJudgment("english_test", "not_met", f"IELTS {profile.english_score} is below minimum 7.0.", source_eng))
            elif profile.english_test_type == "TOEFL":
                if profile.english_score and profile.english_score >= 100:
                    judgments.append(RequirementJudgment("english_test", "met", f"TOEFL iBT {profile.english_score} meets TU Delft cutoff (>= 100).", source_eng))
                else:
                    judgments.append(RequirementJudgment("english_test", "not_met", f"TOEFL iBT {profile.english_score} is below minimum 100.", source_eng))
            else:
                judgments.append(RequirementJudgment("english_test", "needs_review", "Requires IELTS >= 7.0 or TOEFL iBT >= 100.", source_eng))
        else:
            judgments.append(RequirementJudgment("english_test", "needs_review", "Requires IELTS >= 7.0 or TOEFL iBT >= 100.", source_eng))

        # 5. Tuition & Deadlines (Informational)
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
