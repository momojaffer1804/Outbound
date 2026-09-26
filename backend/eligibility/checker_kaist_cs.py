# checker_kaist_cs.py
"""
outbound/backend/eligibility/checker_kaist_cs.py

Eligibility checker for: KAIST -- M.S. Computer Science (School of Computing)
Same shared-logic pattern as checker_kaist_ai.py -- see that file and
checker_kaist_shared.py for why citizenship/qualification/english/gre
judgments are identical between KAIST's two programs (confirmed, not
assumed, per the scrapers' own docstrings).
"""

from __future__ import annotations

from base_checker import BaseEligibilityChecker, UserProfile, RequirementJudgment, UniversityEligibilityResult
import checker_kaist_shared as shared


class KAISTCSEligibilityChecker(BaseEligibilityChecker):
    university = "KAIST"
    program = "M.S. Computer Science (School of Computing)"

    def check(self, profile: UserProfile, raw_requirements: list) -> UniversityEligibilityResult:
        judgments: list[RequirementJudgment] = []
        academic_year = raw_requirements[0].academic_year if raw_requirements else "unknown_year"

        ce = self._find(raw_requirements, "citizenship_eligibility")
        if ce:
            judgments.append(shared.judge_citizenship_eligibility(profile, ce[0]))

        qb = self._find(raw_requirements, "qualification_basis")
        if qb:
            judgments.append(shared.judge_qualification_basis(profile, qb[0]))

        et = self._find(raw_requirements, "english_test")
        if et:
            judgments.append(shared.judge_english_test(profile, et[0]))

        gre = self._find(raw_requirements, "gre")
        if gre:
            judgments.append(shared.judge_gre(gre[0]))

        for rtype in ("program_identity", "deadline", "deadline_note"):
            for r in self._find(raw_requirements, rtype):
                judgments.append(RequirementJudgment(rtype, "informational", r.value, r.value))

        return UniversityEligibilityResult(
            university=self.university,
            program=self.program,
            academic_year=academic_year,
            overall_status=self._overall_from_judgments(judgments),
            judgments=judgments,
        )