"""
outbound/backend/eligibility/checker_rwth.py

Eligibility checker for: RWTH Aachen -- M.Sc. Computer Science
Hand-written against the real verified values in scraper_rwth_computer_science.py.

Structural differences from TUM this checker must respect (per the scraper's
own docstring -- do not treat these as interchangeable with TUM's logic):
- GRE exemption is by CITIZENSHIP/EDUCATION-LOCATION (EU/EEA citizen or
  Bildungsinlaender), not a named non-EU country list like TUM's.
- GRE, when required, is scored by PERCENTILE (Quant >75th, Verbal >15th),
  not TUM's scaled score (164). Different scale entirely -- never compare
  a percentile input against TUM's scaled thresholds or vice versa.
- German at C1 is a real, separate, additional gate -- unlike TUM, which is
  fully English-taught. A profile with strong English but no German should
  come back "not_met" here, not "needs_review".

What this checker CANNOT judge:
- qualification_basis: RWTH gates on a prior-coursework OVERLAP check
  (specific modules in Practical/Technical/Theoretical CS + Math, up to 42
  credit-point gap closable via bridge modules). A CGPA number cannot
  confirm this -- would need an actual transcript/course list, which this
  profile schema does not collect. Always "needs_review".
- english_test: B2, provable via specific documents (Abitur, or an English
  Bachelor's thesis + Examination Board application) -- not a simple test
  score comparison this profile collects. Always "needs_review".
"""

from __future__ import annotations

from base_checker import BaseEligibilityChecker, UserProfile, RequirementJudgment, UniversityEligibilityResult


class RWTHEligibilityChecker(BaseEligibilityChecker):
    university = "RWTH Aachen"
    program = "M.Sc. Computer Science"

    def check(self, profile: UserProfile, raw_requirements: list) -> UniversityEligibilityResult:
        judgments: list[RequirementJudgment] = []
        academic_year = raw_requirements[0].academic_year if raw_requirements else "unknown_year"

        # --- qualification_basis: coursework overlap, never judgeable from CGPA ---
        qb = self._find(raw_requirements, "qualification_basis")
        if qb:
            judgments.append(RequirementJudgment(
                "qualification_basis", "needs_review",
                "Gated by a specific prior-coursework overlap check (Practical/Technical/"
                "Theoretical CS + Math modules), with up to 42 credit points of gap closable "
                "via bridge modules. Requires a transcript/course list review, not a CGPA figure.",
                qb[0].value,
            ))

        # --- english_test: B2, provable only via specific documents ---
        et = self._find(raw_requirements, "english_test")
        if et:
            judgments.append(RequirementJudgment(
                "english_test", "needs_review",
                "B2 English is provable via a German Abitur certificate or an English-language "
                "Bachelor's thesis/seminar paper plus Examination Board approval — not a simple "
                "test-score comparison.",
                et[0].value,
            ))

        # --- german_test: real additional gate, C1 required ---
        gt = self._find(raw_requirements, "german_test")
        if gt:
            if profile.flow == "early_planner":
                judgments.append(RequirementJudgment(
                    "german_test", "needs_review",
                    "German C1 required (this program is not fully English-taught, unlike TUM) "
                    "— add this to your future checklist if not yet started.",
                    gt[0].value,
                ))
            elif profile.german_level is None:
                judgments.append(RequirementJudgment(
                    "german_test", "not_met",
                    "German C1 is required for this program and no German level was provided.",
                    gt[0].value,
                ))
            elif profile.german_level.upper() == "C1" or profile.german_level.upper() == "C2":
                judgments.append(RequirementJudgment(
                    "german_test", "met", f"German level {profile.german_level} meets the C1 requirement.",
                    gt[0].value,
                ))
            else:
                judgments.append(RequirementJudgment(
                    "german_test", "not_met",
                    f"German level {profile.german_level} does not meet the required C1.",
                    gt[0].value,
                ))

        # --- gre: exemption by citizenship/education-location, percentile-scored ---
        gre = self._find(raw_requirements, "gre")
        if gre:
            exempt = bool(profile.is_eu_eea_citizen) or bool(profile.is_bildungsinlaender)
            if exempt:
                judgments.append(RequirementJudgment(
                    "gre", "met", "Exempt as an EU/EEA citizen or Bildungsinländer.", gre[0].value,
                ))
            elif profile.flow == "early_planner":
                judgments.append(RequirementJudgment(
                    "gre", "needs_review",
                    "GRE required unless EU/EEA citizen or Bildungsinländer — not yet assessed "
                    "(early planner flow).",
                    gre[0].value,
                ))
            elif (profile.gre_quant_percentile is not None
                  and profile.gre_verbal_percentile is not None
                  and profile.gre_awa is not None):
                if (profile.gre_quant_percentile > 75
                        and profile.gre_verbal_percentile > 15
                        and profile.gre_awa >= 3.5):
                    judgments.append(RequirementJudgment(
                        "gre", "met",
                        f"GRE Quant {profile.gre_quant_percentile}th pctl (>75th), Verbal "
                        f"{profile.gre_verbal_percentile}th pctl (>15th), AWA {profile.gre_awa} (>=3.5) all met.",
                        gre[0].value,
                    ))
                else:
                    judgments.append(RequirementJudgment(
                        "gre", "not_met",
                        f"GRE Quant {profile.gre_quant_percentile}th/Verbal {profile.gre_verbal_percentile}th/"
                        f"AWA {profile.gre_awa} does not meet Quant>75th, Verbal>15th, AWA>=3.5.",
                        gre[0].value,
                    ))
            else:
                judgments.append(RequirementJudgment(
                    "gre", "needs_review",
                    "GRE required (not exempt) but percentile scores were not provided. Note: "
                    "RWTH scores GRE by PERCENTILE, not the scaled score TUM uses — don't reuse a "
                    "TUM-style GRE input here.",
                    gre[0].value,
                ))

        # --- informational-only records ---
        for r in self._find(raw_requirements, "deadline"):
            judgments.append(RequirementJudgment("deadline", "informational", r.value, r.value))

        return UniversityEligibilityResult(
            university=self.university,
            program=self.program,
            academic_year=academic_year,
            overall_status=self._overall_from_judgments(judgments),
            judgments=judgments,
        )