"""
outbound/backend/eligibility/checker_tum.py

Eligibility checker for: TU Munich -- M.Sc. Informatics
Hand-written against the real verified values in scraper_tum_informatics.py.

What this checker CAN judge from a profile:
- gre: TUM states an exact, numeric, unconditional rule (Quant scaled score
  >= 164, AWA >= 4.0, for a named list of 5 countries; GATE accepted as an
  Indian alternative). This is judgeable.
- aps_certificate: a clear citizenship-based document requirement. Judgeable
  as "needs_review" (it's a document to submit, not a score to compare) --
  NOT "not_met", since lacking it yet doesn't mean permanently ineligible,
  just that it must be arranged.

What this checker CANNOT judge (and must say so, not guess):
- qualification_basis: "Bachelor's degree equivalent to TUM's own B.Sc.
  Informatics" plus a 2-stage aptitude test is not something a CGPA number
  can confirm or deny. Always "needs_review".
- english_test: the source page itself states NO number -- it links out to
  a separate page. Fabricating a pass/fail against a "6.5 IELTS" figure some
  tier-4 sites claim would be exactly the conflict the project's own
  conflict-detection layer exists to catch, not something this checker
  should quietly assume. Always "needs_review", regardless of profile input.
"""

from __future__ import annotations

from base_checker import BaseEligibilityChecker, UserProfile, RequirementJudgment, UniversityEligibilityResult

GRE_REQUIRED_COUNTRIES = {"Bangladesh", "China", "India", "Iran", "Pakistan"}
APS_REQUIRED_COUNTRIES = {"China", "India", "Vietnam"}


class TUMEligibilityChecker(BaseEligibilityChecker):
    university = "TU Munich (TUM)"
    program = "M.Sc. Informatics"

    def check(self, profile: UserProfile, raw_requirements: list) -> UniversityEligibilityResult:
        judgments: list[RequirementJudgment] = []
        academic_year = raw_requirements[0].academic_year if raw_requirements else "unknown_year"
        country = profile.undergrad_country or profile.citizenship

        # --- qualification_basis: never programmatically judgeable ---
        qb = self._find(raw_requirements, "qualification_basis")
        if qb:
            judgments.append(RequirementJudgment(
                "qualification_basis", "needs_review",
                "Requires a Bachelor's judged equivalent to TUM's own B.Sc. Informatics, "
                "plus a 2-stage aptitude test — not something a CGPA figure alone can confirm.",
                qb[0].value,
            ))

        # --- english_test: page states no number, never fabricate a pass/fail ---
        et = self._find(raw_requirements, "english_test")
        if et:
            note = ("This tier-1 page deliberately states no specific score — do not trust "
                    "tier-4 sources claiming a fixed IELTS/TOEFL number for this program.")
            judgments.append(RequirementJudgment("english_test", "needs_review", note, et[0].value))

        # --- gre: judgeable, exact numeric rule ---
        gre = self._find(raw_requirements, "gre")
        if gre:
            if country not in GRE_REQUIRED_COUNTRIES:
                judgments.append(RequirementJudgment(
                    "gre", "not_applicable",
                    f"GRE not required for applicants from {country or 'your country'}.",
                    gre[0].value,
                ))
            elif profile.flow == "early_planner":
                judgments.append(RequirementJudgment(
                    "gre", "needs_review",
                    f"GRE required for {country} applicants (Quant>=164, AWA>=4.0, or GATE for India) "
                    "— not yet assessed since no GRE/GATE score was provided (early planner flow).",
                    gre[0].value,
                ))
            elif country == "India" and profile.gate_score_reported:
                judgments.append(RequirementJudgment(
                    "gre", "met", "GATE (Computer Science) accepted in place of GRE for Indian applicants.",
                    gre[0].value,
                ))
            elif profile.gre_quant_scaled is not None and profile.gre_awa is not None:
                if profile.gre_quant_scaled >= 164 and profile.gre_awa >= 4.0:
                    judgments.append(RequirementJudgment(
                        "gre", "met",
                        f"GRE Quant {profile.gre_quant_scaled} (>=164) and AWA {profile.gre_awa} (>=4.0) both met.",
                        gre[0].value,
                    ))
                else:
                    judgments.append(RequirementJudgment(
                        "gre", "not_met",
                        f"GRE Quant {profile.gre_quant_scaled}/AWA {profile.gre_awa} does not meet the "
                        f"required Quant>=164 and AWA>=4.0.",
                        gre[0].value,
                    ))
            else:
                judgments.append(RequirementJudgment(
                    "gre", "needs_review",
                    f"GRE required for {country} applicants but no GRE (Quant+AWA) or GATE score was provided.",
                    gre[0].value,
                ))

        # --- aps_certificate: document requirement, not a score ---
        aps = self._find(raw_requirements, "aps_certificate")
        if aps:
            if country in APS_REQUIRED_COUNTRIES:
                judgments.append(RequirementJudgment(
                    "aps_certificate", "needs_review",
                    f"APS certificate required for applicants from {country} — arrange this document; "
                    "not a pass/fail score.",
                    aps[0].value,
                ))
            else:
                judgments.append(RequirementJudgment(
                    "aps_certificate", "not_applicable",
                    f"Not required for applicants from {country or 'your country'}.",
                    aps[0].value,
                ))

        # --- informational-only records ---
        for rtype in ("deadline", "ects_credits", "duration"):
            for r in self._find(raw_requirements, rtype):
                judgments.append(RequirementJudgment(rtype, "informational", r.value, r.value))

        return UniversityEligibilityResult(
            university=self.university,
            program=self.program,
            academic_year=academic_year,
            overall_status=self._overall_from_judgments(judgments),
            judgments=judgments,
        )