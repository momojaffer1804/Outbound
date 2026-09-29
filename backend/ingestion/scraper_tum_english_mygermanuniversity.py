"""
outbound/backend/ingestion/scraper_tum_english_mygermanuniversity.py

Scraper for: mygermanuniversity.com's page on TUM's M.Sc. Informatics
Source: https://www.mygermanuniversity.com/de/master/informatics/1503
Tier: 4 (secondary/consultancy database, not an official university or
government source)

STATUS: hardcoded-but-verified against real page content (retrieved via
search, 2026-09-26), same "verified_manual" pattern as the tier-1 scrapers.

WHY THIS SCRAPER EXISTS: scraper_tum_informatics.py's own english_test
record already flags this exact conflict in its notes ("CONFLICT WATCH:
several tier-4 sources (e.g. mygermanuniversity, tutopiya) state 'IELTS
6.5 / TOEFL 88' for this program. This tier-1 page does not commit to a
number in-page."). This scraper is what makes that flagged-but-unverified
claim into an actual, comparable RawRequirement record.

Real finding: mygermanuniversity states IELTS min 6.5, TOEFL iBT min 88 for
this exact program, as a specific number. TUM's own tier-1 page states no
specific number and links out instead. This is a genuine, currently-live
discrepancy between a tier-1 and a tier-4 source, not a hypothetical.

FIXED 2026-09-30: academic_year was hand-typed as "unknown_year" without
running it through extract_academic_year() against the real fetched page
(soup was fetched but unused, same pattern as the Yocket scraper's bug --
lower risk here since "unknown_year" is a safe default rather than a
specific guessed year, but still inconsistent with the rest of the
project's rule of always deriving this from the live page, never assuming).
"""

from __future__ import annotations

from base_scraper import BaseUniversityScraper, RawRequirement


class TUMEnglishMyGermanUniversityScraper(BaseUniversityScraper):
    country = "Germany"
    university = "TU Munich (TUM)"
    program = "M.Sc. Informatics"
    source_url = "https://www.mygermanuniversity.com/de/master/informatics/1503"
    source_tier = 4

    def parse(self, soup) -> list[RawRequirement]:
        retrieved_date = self.stamp_retrieved_date()
        academic_year = self.extract_academic_year(soup.get_text(" ", strip=True))

        return [RawRequirement(
            requirement_type="english_test",
            value="IELTS minimum 6.5; TOEFL iBT minimum 88; Cambridge C1 Advanced "
                  "(CAE) grades A/B/C; Cambridge C2 Proficiency (CPE) grades A/B/C.",
            source_tier=self.source_tier,
            country=self.country,
            university=self.university,
            program=self.program,
            source_url=self.source_url,
            retrieved_date=retrieved_date,
            grading_system=None,
            academic_year=academic_year,
            notes="CONFLICT: TUM's own tier-1 page (scraper_tum_informatics.py) states "
                  "no specific English score in-page for this program. This tier-4 "
                  "source states a specific figure not confirmed by the official page. "
                  "Tier-1 takes priority per project's source-hierarchy rule; this "
                  "record exists so that priority decision is visible, not assumed.",
            extraction_method="verified_manual",
        )]


if __name__ == "__main__":
    scraper = TUMEnglishMyGermanUniversityScraper()
    for r in scraper.run():
        print(r)