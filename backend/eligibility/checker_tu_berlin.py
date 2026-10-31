"""
outbound/backend/eligibility/checker_tu_berlin.py

Eligibility checker for: TU Berlin -- M.Sc. Computer Science (Informatik)
"""

from __future__ import annotations
from base_checker import BaseEligibilityChecker, UserProfile, RequirementJudgment, UniversityEligibilityResult

APS_REQUIRED_COUNTRIES = {"China", "India", "Vietnam"}


class TUBerlinEligibilityChecker(BaseEligibilityChecker):
    university = "TU Berlin"
    program = "M.Sc. Computer Science (Informatik)"

    def check(self, profile: UserProfile, raw_requirements: list) -> UniversityEligibilityResult:
        judgments: list[RequirementJudgment] = []
        academic_year = raw_requirements[0].academic_year if raw_requirements else "2026/27"
        country = profile.undergrad_country or profile.citizenship

        # 1. Qualification basis (ECTS distribution)
        qb = self._find(raw_requirements, "qualification_basis")
        source_val = qb[0].value if qb else ""
        judgments.append(RequirementJudgment(
            requirement_type="qualification_basis",
            status="needs_review",
            detail="Requires at least 180 ECTS Bachelor's with 12 ECTS Theoretical CS, 12 ECTS Systems, and 18 ECTS Math — verified via TU Berlin self-assessment form.",
            source_value=source_val
        ))

        # 2. CGPA
        cgpa_val = self._find(raw_requirements, "cgpa")
        source_cgpa = cgpa_val[0].value if cgpa_val else ""
        if profile.cgpa is not None:
            if profile.cgpa >= 7.8:
                judgments.append(RequirementJudgment(
                    requirement_type="cgpa",
                    status="met",
                    detail=f"CGPA {profile.cgpa:.2f}/10 is competitive for the German grade 2.0 selection baseline.",
                    source_value=source_cgpa
                ))
            elif profile.cgpa >= 7.0:
                judgments.append(RequirementJudgment(
                    requirement_type="cgpa",
                    status="needs_review",
                    detail=f"CGPA {profile.cgpa:.2f}/10 is around the minimum threshold; competitive ranking depends on the applicant pool.",
                    source_value=source_cgpa
                ))
            else:
                judgments.append(RequirementJudgment(
                    requirement_type="cgpa",
                    status="not_met",
                    detail=f"CGPA {profile.cgpa:.2f}/10 is below the competitive cutoff (approx. 7.5+/10).",
                    source_value=source_cgpa
                ))
        else:
            judgments.append(RequirementJudgment(
                requirement_type="cgpa",
                status="needs_review",
                detail="CGPA not provided — competitive cutoff is approximately 7.8/10.",
                source_value=source_cgpa
            ))

        # 3. English Proficiency (C1 required)
        eng_val = self._find(raw_requirements, "english_test")
        source_eng = eng_val[0].value if eng_val else ""
        if profile.flow == "near_term":
            if profile.english_test_type == "IELTS":
                if profile.english_score and profile.english_score >= 7.0:
                    judgments.append(RequirementJudgment("english_test", "met", f"IELTS {profile.english_score} meets the C1 requirement (>= 7.0).", source_eng))
                else:
                    judgments.append(RequirementJudgment("english_test", "not_met", f"IELTS {profile.english_score} does not satisfy C1 level (minimum 7.0 required).", source_eng))
            elif profile.english_test_type == "TOEFL":
                if profile.english_score and profile.english_score >= 95:
                    judgments.append(RequirementJudgment("english_test", "met", f"TOEFL iBT {profile.english_score} meets the C1 requirement (>= 95).", source_eng))
                else:
                    judgments.append(RequirementJudgment("english_test", "not_met", f"TOEFL iBT {profile.english_score} does not satisfy C1 level (minimum 95 required).", source_eng))
            elif profile.undergrad_institution_english_medium:
                judgments.append(RequirementJudgment("english_test", "needs_review", "English-medium degree must be from an English-speaking country for full waiver.", source_eng))
            else:
                judgments.append(RequirementJudgment("english_test", "needs_review", "English C1 required (IELTS 7.0 / TOEFL 95) — not yet confirmed.", source_eng))
        else:
            judgments.append(RequirementJudgment("english_test", "needs_review", "Requires English C1 (IELTS 7.0 or TOEFL 95).", source_eng))

        # 4. APS Certificate
        if country in APS_REQUIRED_COUNTRIES:
            aps_val = self._find(raw_requirements, "aps_certificate")
            judgments.append(RequirementJudgment(
                requirement_type="aps_certificate",
                status="needs_review",
                detail=f"APS certificate is mandatory for applicants with degrees from {country}.",
                source_value=aps_val[0].value if aps_val else ""
            ))

        # 5. Deadlines & Tuition (informational)
        dl = self._find(raw_requirements, "deadline")
        if dl:
            judgments.append(RequirementJudgment("deadline", "informational", dl[0].value, dl[0].value))

        tf = self._find(raw_requirements, "tuition_fees")
        if tf:
            judgments.append(RequirementJudgment("tuition_fees", "informational", tf[0].value, tf[0].value))

        overall = self._overall_from_judgments(judgments)
        return UniversityEligibilityResult(
            university=self.university,
            program=self.program,
            academic_year=academic_year,
            overall_status=overall,
            judgments=judgments
        )
