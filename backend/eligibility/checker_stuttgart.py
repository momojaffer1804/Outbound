"""
outbound/backend/eligibility/checker_stuttgart.py

Eligibility checker for: University of Stuttgart -- M.Sc. Computer Science
"""

from __future__ import annotations
from base_checker import BaseEligibilityChecker, UserProfile, RequirementJudgment, UniversityEligibilityResult

APS_REQUIRED_COUNTRIES = {"China", "India", "Vietnam"}


class StuttgartEligibilityChecker(BaseEligibilityChecker):
    university = "University of Stuttgart"
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
            detail="Requires Bachelor's in CS / related discipline with solid core foundations — evaluated via course syllabus.",
            source_value=qb[0].value if qb else ""
        ))

        # 2. CGPA (Cutoff is 2.5 German grade / approx 7.0 CGPA)
        cgpa_val = self._find(raw_requirements, "cgpa")
        source_cgpa = cgpa_val[0].value if cgpa_val else ""
        if profile.cgpa is not None:
            if profile.cgpa >= 7.0:
                judgments.append(RequirementJudgment("cgpa", "met", f"CGPA {profile.cgpa:.2f}/10 meets the minimum German grade 2.5 cutoff (approx. 7.0/10).", source_cgpa))
            else:
                judgments.append(RequirementJudgment("cgpa", "not_met", f"CGPA {profile.cgpa:.2f}/10 falls below the strict 2.5 German grade cutoff (min. 7.0/10).", source_cgpa))
        else:
            judgments.append(RequirementJudgment("cgpa", "needs_review", "CGPA not provided (requires min. 7.0/10).", source_cgpa))

        # 3. English (B2/C1 - IELTS 6.5 / TOEFL 90)
        eng_val = self._find(raw_requirements, "english_test")
        source_eng = eng_val[0].value if eng_val else ""
        if profile.flow == "near_term":
            if profile.english_test_type == "IELTS":
                if profile.english_score and profile.english_score >= 6.5:
                    judgments.append(RequirementJudgment("english_test", "met", f"IELTS {profile.english_score} satisfies minimum requirement (>= 6.5).", source_eng))
                else:
                    judgments.append(RequirementJudgment("english_test", "not_met", f"IELTS {profile.english_score} is below minimum 6.5.", source_eng))
            elif profile.english_test_type == "TOEFL":
                if profile.english_score and profile.english_score >= 90:
                    judgments.append(RequirementJudgment("english_test", "met", f"TOEFL iBT {profile.english_score} satisfies minimum requirement (>= 90).", source_eng))
                else:
                    judgments.append(RequirementJudgment("english_test", "not_met", f"TOEFL iBT {profile.english_score} is below minimum 90.", source_eng))
            else:
                judgments.append(RequirementJudgment("english_test", "needs_review", "English test score required (IELTS >= 6.5 or TOEFL >= 90).", source_eng))
        else:
            judgments.append(RequirementJudgment("english_test", "needs_review", "Requires English proficiency (IELTS >= 6.5 or TOEFL >= 90).", source_eng))

        # 4. GRE (Recommended for non-EU)
        gre_val = self._find(raw_requirements, "gre")
        if profile.gre_quant_percentile is not None and profile.gre_quant_percentile >= 75:
            judgments.append(RequirementJudgment("gre", "met", f"GRE Quant {profile.gre_quant_percentile}th percentile meets competitive benchmark (>= 75th).", gre_val[0].value if gre_val else ""))
        elif profile.gre_quant_scaled is not None and profile.gre_quant_scaled >= 160:
            judgments.append(RequirementJudgment("gre", "met", f"GRE Quant scaled {profile.gre_quant_scaled} satisfies recommendation.", gre_val[0].value if gre_val else ""))
        else:
            judgments.append(RequirementJudgment("gre", "informational", "GRE is strongly recommended for non-EU applicants to improve competitiveness.", gre_val[0].value if gre_val else ""))

        # 5. APS Certificate
        if country in APS_REQUIRED_COUNTRIES:
            aps_val = self._find(raw_requirements, "aps_certificate")
            judgments.append(RequirementJudgment("aps_certificate", "needs_review", f"APS certificate mandatory for applicants from {country}.", aps_val[0].value if aps_val else ""))

        # 6. Tuition & Deadlines
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
