"""
outbound/backend/ingestion/scraper_rwth_computer_science.py

Scraper for: RWTH Aachen -- M.Sc. Computer Science
Source: https://sc.informatik.rwth-aachen.de/en/studium/master/informatik/start-ins-studium/
Tier: 1 (official department admission page)

STATUS: hardcoded-but-verified, same pattern as TUM. Not live-HTML-parsed.

Site notes:
- This is the department's own WordPress-based site, structurally different
  from TUM's TYPO3 site -- confirms the "one scraper per university" decision
  was right: a generic scraper tuned for TUM's layout would not transfer here
  either.
- No numeric GPA cutoff -- admission is gated on specific prior-coursework
  overlap (Practical/Technical/Theoretical CS + Math modules from RWTH's own
  Bachelor's). A gap of up to 42 credit points can be closed with bridge
  modules taken during the Master's; beyond 42 CP, admission is not possible.
- German at C1 level is REQUIRED, in addition to English at B2 -- a real
  structural difference from TUM (which is fully English-taught). This is
  meaningful eligibility-blocking information, not a minor detail.
- GRE is required UNLESS the applicant is an EU/EEA citizen or completed
  secondary education in Germany ("Bildungsinländer"). This exemption logic
  is structurally different from TUM's (TUM exempts everyone except a named
  list of countries; RWTH exempts based on citizenship/education location,
  not a country list). Downstream eligibility logic must not assume all
  "GRE required unless X" rules share the same X.
- academic_year: NO explicit year string exists anywhere on this page (no
  "2026/27"-style text). Per project rule, this must resolve to
  'unknown_year' rather than being guessed or copied from another
  university's scrape. This is the staleness-safety mechanism working as
  intended, not a scraper defect.
"""

from __future__ import annotations

from base_scraper import BaseUniversityScraper, RawRequirement


class RWTHComputerScienceScraper(BaseUniversityScraper):
    country = "Germany"
    university = "RWTH Aachen"
    program = "M.Sc. Computer Science"
    source_url = "https://sc.informatik.rwth-aachen.de/en/studium/master/informatik/start-ins-studium/"
    source_tier = 1

    def parse(self, soup) -> list[RawRequirement]:
        retrieved_date = self.stamp_retrieved_date()
        full_text = soup.get_text(" ", strip=True)
        academic_year = self.extract_academic_year(full_text)
        # Expected to be 'unknown_year' for this page -- confirmed no explicit
        # year string exists here as of the verification date below. Assert
        # loudly if that ever silently changes without re-verification.
        assert academic_year == "unknown_year", (
            f"Expected 'unknown_year' for RWTH page (no year string was found "
            f"during manual verification); got '{academic_year}' instead. "
            f"The page may have added an explicit year -- re-verify manually "
            f"before trusting this value, do not silently accept it."
        )

        reqs: list[RawRequirement] = []

        def add(requirement_type, value, grading_system=None, notes=None):
            reqs.append(RawRequirement(
                requirement_type=requirement_type,
                value=value,
                source_tier=self.source_tier,
                country=self.country,
                university=self.university,
                program=self.program,
                source_url=self.source_url,
                retrieved_date=retrieved_date,
                grading_system=grading_system,
                academic_year=academic_year,
                notes=notes,
                extraction_method="verified_manual",
            ))

        # --- Qualification basis: coursework overlap, not a numeric GPA ---
        add(
            requirement_type="qualification_basis",
            value=(
                "Completed Bachelor's degree required (not necessarily in "
                "Computer Science). Admission requires coverage of specific "
                "prior coursework: Practical CS (programming, data structures "
                "and algorithms, databases, software engineering, ML/data "
                "science basics), Technical CS (technical CS, operating "
                "systems, data communication, system programming, IT security), "
                "Theoretical CS (formal systems, automata, computability, "
                "mathematical logic), and Mathematics (discrete structures, "
                "analysis, linear algebra, applied stochastics). A coursework "
                "gap of up to 42 credit points can be closed via bridge modules "
                "taken during the Master's; beyond 42 CP, admission is not "
                "possible."
            ),
            notes="No single numeric GPA cutoff stated on this page -- gated by "
                  "coursework-overlap check instead, same pattern as TUM but "
                  "with a different mechanism (RWTH uses a credit-point gap "
                  "ceiling; TUM uses an aptitude test).",
        )

        # --- English proficiency ---
        add(
            requirement_type="english_test",
            value="English at B2 level. Provable via German Abitur certificate, "
                  "or via an English-language Bachelor's thesis/seminar paper "
                  "at a German university plus an application to the Computer "
                  "Science Examination Board.",
        )

        # --- German proficiency (real structural difference from TUM) ---
        add(
            requirement_type="german_test",
            value="German at C1 level required. Both admission requirements and "
                  "many course subjects are offered exclusively in German, so "
                  "strong German proficiency is mandatory for this program "
                  "(unlike TUM's M.Sc. Informatics, which is fully English-taught).",
            notes="CONFLICT/COMPARISON WATCH: this is a real eligibility-blocking "
                  "requirement that does not exist for TUM's equivalent program. "
                  "A user comparing TUM vs RWTH needs this surfaced explicitly, "
                  "not just an English-score comparison.",
        )

        # --- GRE (different exemption logic than TUM) ---
        add(
            requirement_type="gre",
            value="Required unless the applicant is an EU/EEA citizen or "
                  "completed secondary education in Germany ('Bildungsinländer'). "
                  "When required: quantitative reasoning above the 75th "
                  "percentile, verbal reasoning above the 15th percentile, "
                  "analytical writing at least 3.5. Must be submitted before "
                  "the application deadline; cannot be submitted late.",
            notes="Exemption logic differs structurally from TUM's GRE rule: "
                  "TUM exempts everyone except a named list of countries; RWTH "
                  "exempts based on citizenship/education location, not a "
                  "country list. Eligibility logic must not assume these two "
                  "rules are interchangeable.",
        )

        # --- Deadlines (three-way split by applicant category) ---
        add(
            requirement_type="deadline",
            value="Bachelor's from Germany: 15 July (winter semester), "
                  "15 January (summer semester).",
        )
        add(
            requirement_type="deadline",
            value="EU/EEA citizen: 15 July (winter semester), "
                  "15 January (summer semester).",
        )
        add(
            requirement_type="deadline",
            value="Applicant from a third country: 1 March (winter semester), "
                  "1 September (summer semester).",
        )

        return reqs


if __name__ == "__main__":
    scraper = RWTHComputerScienceScraper()
    for r in scraper.run():
        print(r)