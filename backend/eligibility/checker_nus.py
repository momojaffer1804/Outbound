"""
outbound/backend/eligibility/checker_nus.py

Eligibility checker for: National University of Singapore (NUS) -- Master of Computing
"""

from __future__ import annotations
from base_checker import BaseEligibilityChecker, UserProfile, RequirementJudgment, UniversityEligibilityResult


class NUSEligibilityChecker(BaseEligibilityChecker):
    university = "National University of Singapore (NUS)"
    program = "Master of Computing (General Track & CS Specialisations)"

    def check(self, profile: UserProfile, raw_requirements: list) -> UniversityEligibilityResult:
        judgments: list[RequirementJudgment] = []
        academic_year = raw_requirements[0].academic_year if raw_requirements else "2026/27"
        country = profile.undergrad_country or profile.citizenship

        # 1. Qualification basis
        qb = self._find(raw_requirements, "qualification_basis")
        judgments.append(RequirementJudgment(
            requirement_type="qualification_basis",
            status="needs_review",
            detail="Requires an Honours degree in Computing / CS or strong technical background for the General Track.",
            source_value=qb[0].value if qb else ""
        ))

        # 2. CGPA (min 8.0/10 or CAP 3.5/5.0)
        cgpa_val = self._find(raw_requirements, "cgpa")
        source_cgpa = cgpa_val[0].value if cgpa_val else ""
        if profile.cgpa is not None:
            if profile.cgpa >= 8.0:
                judgments.append(RequirementJudgment("cgpa", "met", f"CGPA {profile.cgpa:.2f}/10 meets the minimum academic standard (>= 8.0/10 or 2nd Class Upper).", source_cgpa))
            elif profile.cgpa >= 7.5:
                judgments.append(RequirementJudgment("cgpa", "needs_review", f"CGPA {profile.cgpa:.2f}/10 is borderline; strong GRE/GATE and industry experience can compensate.", source_cgpa))
            else:
                judgments.append(RequirementJudgment("cgpa", "not_met", f"CGPA {profile.cgpa:.2f}/10 is below the recommended 8.0/10 benchmark.", source_cgpa))
        else:
            judgments.append(RequirementJudgment("cgpa", "needs_review", "CGPA not provided (requires min 8.0/10).", source_cgpa))

        # 3. GRE / GATE (Mandatory for non-Singapore degrees: GRE >= 320 with Quant >= 160, or GATE >= 90%ile)
        gre_val = self._find(raw_requirements, "gre")
        source_gre = gre_val[0].value if gre_val else ""
        if country == "Singapore":
            judgments.append(RequirementJudgment("gre", "not_applicable", "GRE/GATE not required for Singapore university graduates.", source_gre))
        elif profile.flow == "near_term":
            gate_reported = profile.gate_score_reported
            gre_quant = profile.gre_quant_scaled

            if gate_reported and country == "India":
                judgments.append(RequirementJudgment("gre", "met", "GATE score in Computer Science reported as alternative to GRE (requires >= 90th percentile).", source_gre))
            elif gre_quant is not None:
                if gre_quant >= 160:
                    judgments.append(RequirementJudgment("gre", "met", f"GRE Quant scaled {gre_quant} meets the quantitative threshold (>= 160).", source_gre))
                else:
                    judgments.append(RequirementJudgment("gre", "not_met", f"GRE Quant scaled {gre_quant} is below the required 160 cutoff.", source_gre))
            else:
                judgments.append(RequirementJudgment("gre", "not_met", "Mandatory GRE (Quant >= 160) or GATE score for non-Singapore university graduates.", source_gre))
        else:
            judgments.append(RequirementJudgment("gre", "needs_review", "Requires GRE (Quant >= 160) or GATE score for non-Singapore graduates.", source_gre))

        # 4. English proficiency (IELTS >= 6.5 or TOEFL >= 90; waiver if English medium)
        eng_val = self._find(raw_requirements, "english_test")
        source_eng = eng_val[0].value if eng_val else ""
        if profile.undergrad_institution_english_medium:
            judgments.append(RequirementJudgment("english_test", "met", "Exempt from English test based on English-medium undergraduate instruction.", source_eng))
        elif profile.flow == "near_term":
            if profile.english_test_type == "IELTS":
                if profile.english_score and profile.english_score >= 6.5:
                    judgments.append(RequirementJudgment("english_test", "met", f"IELTS {profile.english_score} meets NUS requirement (>= 6.5).", source_eng))
                else:
                    judgments.append(RequirementJudgment("english_test", "not_met", f"IELTS {profile.english_score} is below minimum 6.5.", source_eng))
            elif profile.english_test_type == "TOEFL":
                if profile.english_score and profile.english_score >= 90:
                    judgments.append(RequirementJudgment("english_test", "met", f"TOEFL iBT {profile.english_score} meets NUS requirement (>= 90).", source_eng))
                else:
                    judgments.append(RequirementJudgment("english_test", "not_met", f"TOEFL iBT {profile.english_score} is below minimum 90.", source_eng))
            else:
                judgments.append(RequirementJudgment("english_test", "needs_review", "Requires IELTS >= 6.5 or TOEFL >= 90 (or English-medium bachelor proof).", source_eng))
        else:
            judgments.append(RequirementJudgment("english_test", "needs_review", "Requires IELTS >= 6.5 or TOEFL >= 90.", source_eng))

        # 5. Tuition & Deadlines
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
