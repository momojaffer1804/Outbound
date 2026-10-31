"""
outbound/backend/eligibility/checker_eth_zurich.py

Eligibility checker for: ETH Zurich -- Master's in Computer Science
"""

from __future__ import annotations
from base_checker import BaseEligibilityChecker, UserProfile, RequirementJudgment, UniversityEligibilityResult

EU_EFTA_COUNTRIES = {
    "Switzerland", "Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czech Republic",
    "Denmark", "Estonia", "Finland", "France", "Germany", "Greece", "Hungary", "Iceland",
    "Ireland", "Italy", "Latvia", "Liechtenstein", "Lithuania", "Luxembourg", "Malta",
    "Netherlands", "Norway", "Poland", "Portugal", "Romania", "Slovakia", "Slovenia", "Spain", "Sweden"
}


class ETHZurichEligibilityChecker(BaseEligibilityChecker):
    university = "ETH Zurich"
    program = "Master's in Computer Science"

    def check(self, profile: UserProfile, raw_requirements: list) -> UniversityEligibilityResult:
        judgments: list[RequirementJudgment] = []
        academic_year = raw_requirements[0].academic_year if raw_requirements else "2026/27"
        country = profile.undergrad_country or profile.citizenship

        # 1. Qualification basis
        qb = self._find(raw_requirements, "qualification_basis")
        judgments.append(RequirementJudgment(
            requirement_type="qualification_basis",
            status="needs_review",
            detail="Evaluation against ETH's 180 ECTS Bachelor curriculum across advanced theory, systems, and mathematics.",
            source_value=qb[0].value if qb else ""
        ))

        # 2. CGPA (Top 5-10%, min 8.5/10)
        cgpa_val = self._find(raw_requirements, "cgpa")
        source_cgpa = cgpa_val[0].value if cgpa_val else ""
        if profile.cgpa is not None:
            if profile.cgpa >= 8.5:
                judgments.append(RequirementJudgment("cgpa", "met", f"CGPA {profile.cgpa:.2f}/10 meets the highly competitive benchmark (>= 8.5/10).", source_cgpa))
            elif profile.cgpa >= 8.0:
                judgments.append(RequirementJudgment("cgpa", "needs_review", f"CGPA {profile.cgpa:.2f}/10 is solid, but admissions at ETH Zurich is extremely selective (typically top 5-10% of class).", source_cgpa))
            else:
                judgments.append(RequirementJudgment("cgpa", "not_met", f"CGPA {profile.cgpa:.2f}/10 falls below the typical competitive baseline (>= 8.5/10).", source_cgpa))
        else:
            judgments.append(RequirementJudgment("cgpa", "needs_review", "CGPA not provided (requires competitive standing >= 8.5/10).", source_cgpa))

        # 3. GRE (Mandatory for non-EU/EFTA)
        gre_val = self._find(raw_requirements, "gre")
        source_gre = gre_val[0].value if gre_val else ""
        is_eu_efta = country in EU_EFTA_COUNTRIES or profile.is_eu_eea_citizen

        if is_eu_efta:
            judgments.append(RequirementJudgment("gre", "not_applicable", f"Exempt from GRE requirement (Bologna EU/EFTA degree: {country}).", source_gre))
        elif profile.flow == "near_term":
            if profile.gre_quant_scaled is not None:
                if profile.gre_quant_scaled >= 165:
                    judgments.append(RequirementJudgment("gre", "met", f"GRE Quant scaled {profile.gre_quant_scaled} satisfies competitive cutoff (>= 165).", source_gre))
                else:
                    judgments.append(RequirementJudgment("gre", "not_met", f"GRE Quant scaled {profile.gre_quant_scaled} is below the competitive benchmark (165 required).", source_gre))
            else:
                judgments.append(RequirementJudgment("gre", "not_met", "GRE General Test is strictly mandatory for all non-EU/EFTA applicants.", source_gre))
        else:
            judgments.append(RequirementJudgment("gre", "needs_review", "GRE General Test is mandatory for all non-EU/EFTA applicants (Quant >= 165).", source_gre))

        # 4. English proficiency (C1: TOEFL >= 100, IELTS >= 7.0)
        eng_val = self._find(raw_requirements, "english_test")
        source_eng = eng_val[0].value if eng_val else ""
        if profile.flow == "near_term":
            if profile.english_test_type == "IELTS":
                if profile.english_score and profile.english_score >= 7.0:
                    judgments.append(RequirementJudgment("english_test", "met", f"IELTS {profile.english_score} satisfies C1 requirement (>= 7.0).", source_eng))
                else:
                    judgments.append(RequirementJudgment("english_test", "not_met", f"IELTS {profile.english_score} is below minimum 7.0.", source_eng))
            elif profile.english_test_type == "TOEFL":
                if profile.english_score and profile.english_score >= 100:
                    judgments.append(RequirementJudgment("english_test", "met", f"TOEFL iBT {profile.english_score} satisfies C1 requirement (>= 100).", source_eng))
                else:
                    judgments.append(RequirementJudgment("english_test", "not_met", f"TOEFL iBT {profile.english_score} is below minimum 100.", source_eng))
            else:
                judgments.append(RequirementJudgment("english_test", "needs_review", "Requires IELTS >= 7.0 or TOEFL >= 100.", source_eng))
        else:
            judgments.append(RequirementJudgment("english_test", "needs_review", "Requires IELTS >= 7.0 or TOEFL >= 100.", source_eng))

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
