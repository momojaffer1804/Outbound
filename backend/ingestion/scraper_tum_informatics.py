"""
outbound/backend/ingestion/scraper_tum_informatics.py

Scraper for: TU Munich — M.Sc. Informatics
Source: https://www.cit.tum.de/en/cit/studies/degree-programs/master-informatics/
Tier: 1 (official university admission page)

STATUS: hardcoded-but-verified, NOT live HTML parsing.
Tried live extraction (heading-text search + regex over sibling text) and it
was unreliable on this specific page: TYPO3 gives no useful class names, so
section boundaries are fuzzy, some fields (GRE, APS) were silently dropped
with no error, and others bled into unrelated adjacent sentences. Per project
decision (2026-09-26): reverting to values manually verified against the live
page on this date, rather than sinking more time into one site's parser
before proving the per-university pattern across all 10. Live-parsing this
page properly is a valid future improvement, not a blocker.

Site notes:
- No single numeric GPA cutoff exists on this page — TUM gates entry via a
  Bachelor's-equivalence check + 2-stage aptitude assessment instead. Do NOT
  force a numeric gpa_min field here; downstream eligibility logic must
  handle "no numeric cutoff" as a valid, common case, not missing data.
- English proficiency requirement is a LINK OUT to a separate university-wide
  page, not a number stated in-page. Do not fabricate an IELTS/TOEFL number
  here even though secondary sources (mygermanuniversity, tutopiya, etc.)
  confidently state 6.5 / 88 — that's exactly the kind of tier-4 claim this
  project's conflict detection is meant to catch and flag against a tier-1
  page that deliberately doesn't commit to a figure in-page.
- academic_year: the only explicit year string relevant to the current cycle
  appears in the aptitude-test-date sentence ("Test date for application for
  winter semester 2026/27: Thu, 20 Aug, 2026"). Anchor extraction there via
  base_scraper's context-aware extract_academic_year (fixed 2026-09-25 to
  prefer year strings near admissions-context keywords over the first year
  string on the page, which was an unrelated fee-policy date).
"""

from __future__ import annotations

from base_scraper import BaseUniversityScraper, RawRequirement


class TUMInformaticsScraper(BaseUniversityScraper):
    country = "Germany"
    university = "TU Munich (TUM)"
    program = "M.Sc. Informatics"
    source_url = "https://www.cit.tum.de/en/cit/studies/degree-programs/master-informatics/"
    source_tier = 1

    def parse(self, soup) -> list[RawRequirement]:
        # Still fetches the live page (self.fetch() in base class hits the
        # real URL) and still computes retrieved_date + academic_year live
        # from the fetched text. Only the requirement VALUES below are
        # hand-verified against the live page rather than regex-extracted.
        retrieved_date = self.stamp_retrieved_date()
        full_text = soup.get_text(" ", strip=True)
        academic_year = self.extract_academic_year(full_text)

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

        # --- Qualification basis (no numeric GPA cutoff on this page) ---
        add(
            requirement_type="qualification_basis",
            value=(
                "Bachelor's degree in Informatics/Computer Science equivalent "
                "to TUM's own B.Sc. Informatics; other programs do not qualify. "
                "Two-stage aptitude assessment required (written test, 90 min, "
                "~20-30 questions covering general foundations, mathematical "
                "foundations, theory of computation, practical foundations)."
            ),
            notes="No single numeric GPA cutoff stated on this page.",
        )

        # --- English proficiency: page links out, does not state a figure ---
        add(
            requirement_type="english_test",
            value="Proof of sufficient English proficiency required; no specific "
                  "score stated on this page (links to university-wide language "
                  "certificate requirements page).",
            notes="CONFLICT WATCH: several tier-4 sources (e.g. mygermanuniversity, "
                  "tutopiya) state 'IELTS 6.5 / TOEFL 88' for this program. This "
                  "tier-1 page does not commit to a number in-page. Flag as "
                  "secondary-source claim pending verification against the "
                  "linked TUM-wide language page, not treat as confirmed.",
        )

        # --- GRE (conditional on applicant's undergrad country) ---
        add(
            requirement_type="gre",
            value="Required only for applicants with a Bachelor's from Bangladesh, "
                  "China, India, Iran, or Pakistan. Quantitative reasoning >= 164, "
                  "Analytical writing >= 4.0 (Verbal no longer considered). "
                  "Indian applicants may submit GATE (Computer Science) instead.",
        )

        # --- APS certificate (conditional) ---
        add(
            requirement_type="aps_certificate",
            value="Required for applicants with an undergraduate degree from "
                  "China, India, or Vietnam.",
        )

        # --- Deadlines ---
        add(
            requirement_type="deadline",
            value="Winter semester: compulsory Feb 1 - May 31; recommended "
                  "Feb 1 - Mar 31 for applicants who need a visa.",
        )
        add(
            requirement_type="deadline",
            value="Summer semester: compulsory Oct 1 - Nov 30; recommended "
                  "Oct 1 - Oct 31 for applicants who need a visa.",
        )

        # --- Structural facts ---
        add(requirement_type="ects_credits", value="120 ECTS", grading_system="ECTS")
        add(requirement_type="duration", value="4 semesters")

        return reqs


if __name__ == "__main__":
    scraper = TUMInformaticsScraper()
    for r in scraper.run():
        print(r)