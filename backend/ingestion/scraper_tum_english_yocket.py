"""
outbound/backend/ingestion/scraper_tum_english_yocket.py

Scraper for: Yocket's page on TUM's M.Sc. Informatics admissions data
Source: https://yocket.com/universities/technical-university-of-munich/informatics-35041
Tier: 4 (education-consultancy aggregator; has some community/forum
elements but its admissions data table is compiled/editorial, not
user-submitted forum chatter, so tier 4 rather than tier 5 -- a judgment
call, not a clean-cut case.)

STATUS: hardcoded-but-verified against real page content (retrieved via
search, 2026-09-26).

WHY THIS SCRAPER EXISTS: a second, INDEPENDENT tier-4 source stating the
same "IELTS 6.5 / TOEFL 88" figure as mygermanuniversity.com strengthens
the case that this is a genuinely widespread secondary-source claim.

Real finding: Yocket's admissions data table states TOEFL 88 and IELTS 6.5
as specific figures, and separately notes GRE as "Required" with no
citizenship-conditional caveat -- LESS precise than TUM's own tier-1 page,
which says GRE is required only for a specific list of five countries.

FIXED 2026-09-29: academic_year was previously hand-typed as "2025/26"
without ever being checked against this page's real content -- the page
was fetched (soup was passed into parse()) but soup was never actually
used. Now runs the same already-tested extract_academic_year() helper
used by every other scraper in this project, against the real fetched
text, instead of a guessed literal.
"""

from __future__ import annotations

from base_scraper import BaseUniversityScraper, RawRequirement


class TUMEnglishYocketScraper(BaseUniversityScraper):
    country = "Germany"
    university = "TU Munich (TUM)"
    program = "M.Sc. Informatics"
    source_url = "https://yocket.com/universities/technical-university-of-munich/informatics-35041"
    source_tier = 4

    def parse(self, soup) -> list[RawRequirement]:
        retrieved_date = self.stamp_retrieved_date()
        # Use the already-tested extraction helper against the REAL fetched
        # page, instead of a hand-typed guess. Earlier draft set
        # academic_year="2025/26" directly without ever checking it against
        # this page's actual content -- found and fixed 2026-09-29. If this
        # page states no explicit year (plausible for a general-info
        # aggregator page), this correctly resolves to "unknown_year"
        # rather than fabricating a number.
        academic_year = self.extract_academic_year(soup.get_text(" ", strip=True))

        return [
            RawRequirement(
                requirement_type="english_test",
                value="TOEFL 88; IELTS 6.5; PTE 65.",
                source_tier=self.source_tier,
                country=self.country,
                university=self.university,
                program=self.program,
                source_url=self.source_url,
                retrieved_date=retrieved_date,
                grading_system=None,
                academic_year=academic_year,
                notes="CONFLICT: same discrepancy as mygermanuniversity.com's record for "
                      "this program -- a second, independent tier-4 source states a "
                      "specific English score figure that TUM's own tier-1 page does not "
                      "commit to.",
                extraction_method="verified_manual",
            ),
            RawRequirement(
                requirement_type="gre",
                value="GRE: Required.",
                source_tier=self.source_tier,
                country=self.country,
                university=self.university,
                program=self.program,
                source_url=self.source_url,
                retrieved_date=retrieved_date,
                grading_system=None,
                academic_year=academic_year,
                notes="CONFLICT: TUM's own tier-1 page states GRE is required ONLY for "
                      "applicants from Bangladesh/China/India/Iran/Pakistan, with GATE "
                      "accepted as an Indian alternative. This tier-4 source states GRE "
                      "as unconditionally 'Required', dropping that citizenship condition "
                      "entirely.",
                extraction_method="verified_manual",
            ),
        ]


if __name__ == "__main__":
    scraper = TUMEnglishYocketScraper()
    for r in scraper.run():
        print(r)