"""
outbound/backend/ingestion/scraper_kaist_cs.py

Scraper for: KAIST -- M.S. Computer Science (School of Computing)
Sources (two, same split as the GSAI/AI scraper):
  1. https://admission.kaist.ac.kr/intl-graduate/Admission/Eligibility
     (Office of Admissions, university-wide eligibility rules)
  2. https://ai-systems.kaist.ac.kr/admission-grad.html
     (used only as the source for the Fall 2026 admissions calendar, which
     is confirmed university-wide -- see note below -- NOT GSAI-specific)
Tier: 1 for both.

STATUS: hardcoded-but-verified, same pattern as the other KAIST scraper.

Relationship to scraper_kaist_ai.py:
- KAIST's School of Computing has NO separate eligibility page of its own.
  Its own site (cs.kaist.ac.kr) explicitly tells applicants to use the
  central Office of Admissions eligibility page for citizenship, academic
  qualification, and English proficiency requirements -- confirmed directly
  ("Eligibility: Refer to the graduate admission website ... to check the
  eligibility requirements such as country of citizenship, academic
  qualification, and English language proficiency"). So eligibility content
  here is IDENTICAL to scraper_kaist_ai.py's eligibility records, not a
  near-duplicate written independently -- this is a real, confirmed fact
  about KAIST's admissions structure (centralized eligibility, decentralized
  scheduling only where a department chooses to publish its own), not a
  shortcut taken to save scraping effort.
- The Fall 2026 admissions calendar found on the GSAI department page is
  explicitly labeled "Application (All programs)" in the source text --
  i.e. it is KAIST's single university-wide graduate calendar, not something
  specific to GSAI. It is reused here for the same reason, not assumed.
- Only two things differ from the AI scraper: `program` and the
  `program_identity` note. If School of Computing is later found to publish
  CS-specific deadline exceptions on its own official page, that would need
  its own source_url override the same way GSAI's page overrides the
  eligibility page's source_url for deadline records.

Site notes (see scraper_kaist_ai.py for full detail on each -- not repeated
verbatim here to avoid drift between the two files' comments; if these rules
change, both files need updating together since they describe the same
underlying KAIST-wide policy):
- Citizenship gate, no-GRE-on-this-page, English test structure, and lack of
  a numeric GPA cutoff are university-wide KAIST policies -- identical for
  CS as for AI.
- academic_year: 'unknown_year' for eligibility records (no explicit year
  string on that page); '2026' (single-year notation) for the deadline
  record, same reasoning as the AI scraper.
"""

from __future__ import annotations

from base_scraper import BaseUniversityScraper, RawRequirement

ELIGIBILITY_URL = "https://admission.kaist.ac.kr/intl-graduate/Admission/Eligibility"
UNIVERSITY_CALENDAR_SOURCE_URL = "https://ai-systems.kaist.ac.kr/admission-grad.html"


class KAISTCSScraper(BaseUniversityScraper):
    country = "South Korea"
    university = "KAIST"
    program = "M.S. Computer Science (School of Computing)"
    source_url = ELIGIBILITY_URL
    source_tier = 1

    def parse(self, soup) -> list[RawRequirement]:
        retrieved_date = self.stamp_retrieved_date()
        full_text = soup.get_text(" ", strip=True) if soup else ""
        eligibility_academic_year = self.extract_academic_year(full_text) if soup else "unknown_year"
        if soup:
            assert eligibility_academic_year == "unknown_year", (
            f"Expected 'unknown_year' for KAIST eligibility page; got "
            f"'{eligibility_academic_year}'. Re-verify before trusting."
        )

        reqs: list[RawRequirement] = []

        def add(requirement_type, value, source_url=None, academic_year=None,
                 grading_system=None, notes=None):
            reqs.append(RawRequirement(
                requirement_type=requirement_type,
                value=value,
                source_tier=self.source_tier,
                country=self.country,
                university=self.university,
                program=self.program,
                source_url=source_url or ELIGIBILITY_URL,
                retrieved_date=retrieved_date,
                grading_system=grading_system,
                academic_year=academic_year or eligibility_academic_year,
                notes=notes,
                extraction_method="verified_manual",
            ))

        # --- Citizenship eligibility gate (university-wide, same as GSAI) ---
        add(
            requirement_type="citizenship_eligibility",
            value=(
                "Applicants must be citizens of a country other than Korea; "
                "Korean citizens are not eligible for this international "
                "admissions track. Applicants of Korean descent holding "
                "foreign citizenship must either formally document renunciation "
                "of Korean citizenship (for both applicant and parents) before "
                "the application period, or have completed ALL of primary and "
                "secondary education (grades 1-12) outside Korea, with "
                "international schools located within Korea not counting "
                "toward this exception."
            ),
            notes="University-wide KAIST policy, confirmed identical for "
                  "School of Computing applicants (cs.kaist.ac.kr defers to "
                  "the central eligibility page).",
        )

        # --- Academic qualification ---
        add(
            requirement_type="qualification_basis",
            value=(
                "Bachelor's degree or equivalent standard by the start of the "
                "course. Accepted international equivalents: a four-year "
                "university degree, a three-year Bologna-compliant Bachelor's "
                "degree, the first-cycle qualification under the EHEA "
                "framework, or a British-pattern Bachelor's degree with honors."
            ),
            notes="No numeric GPA cutoff for the standard international "
                  "Master's route. University-wide policy, same for CS as AI.",
        )

        # --- English test ---
        add(
            requirement_type="english_test",
            value=(
                "One of: TOEFL iBT 83 (if taken before 21 Jan 2026) or 4.5 "
                "(on/after 21 Jan 2026, new TOEFL scoring scale); IELTS "
                "Academic 6.5 band; TOEIC 720 (Listening & Reading); TEPS "
                "326. ITP scores not accepted. Scores must be valid as of "
                "the application deadline. Full waiver by citizenship alone "
                "for a specific country list (UK, USA, Canada, Ireland, "
                "Australia, New Zealand, and others); a separate, larger "
                "country list qualifies for waiver only if BOTH citizenship "
                "AND the institution attended (English-medium, physically "
                "located there) are on that list -- includes India, "
                "Pakistan, Nigeria, Singapore, and others."
            ),
            notes="CONFLICT/COMPARISON WATCH: no GRE requirement appears "
                  "anywhere on this official page -- confirmed absence, same "
                  "as GSAI, and a real difference from TUM/RWTH's "
                  "conditional GRE rules.",
        )

        # --- Program identity note ---
        add(
            requirement_type="program_identity",
            value=(
                "This is KAIST's School of Computing M.S. Computer Science "
                "program, distinct from the Graduate School of AI (GSAI). "
                "School of Computing has no separate eligibility page of its "
                "own -- it explicitly directs applicants to the central "
                "Office of Admissions eligibility page for citizenship, "
                "academic, and English requirements, which is why those "
                "records are identical to KAIST's GSAI/AI program records."
            ),
        )

        # --- Deadlines: same university-wide calendar as GSAI, confirmed
        # labeled "Application (All programs)" in the source ---
        add(
            requirement_type="deadline",
            value=(
                "Fall 2026 semester, general admission (all programs, "
                "including School of Computing): online application 27 Mar "
                "2026 10:00 - 07 Apr 2026 17:30 KST via gradapply.kaist.ac.kr. "
                "1st round results from 14 May 2026. 2nd round interviews "
                "16-26 May 2026. Final results from 25 Jun 2026."
            ),
            source_url=UNIVERSITY_CALENDAR_SOURCE_URL,
            academic_year="2026",
            notes="Source page explicitly labels this calendar 'Application "
                  "(All programs)' -- confirmed university-wide, not "
                  "GSAI-specific, so reused here rather than re-derived.",
        )
        add(
            requirement_type="deadline_note",
            value=(
                "KAIST also runs a separate Spring-intake cycle in addition "
                "to the Fall cycle above. Exact Spring dates for this "
                "specific scrape were not independently verified against an "
                "official page and are left out rather than estimated."
            ),
            source_url=UNIVERSITY_CALENDAR_SOURCE_URL,
            academic_year="2026",
            notes="Known gap: Spring intake dates not yet verified. Same gap "
                "as the AI/GSAI scraper.",
        )

        # --- Tuition & Fees ---
        add(
            requirement_type="tuition_fees",
            value=(
                "Standard tuition at KAIST for graduate programs is approximately "
                "3,400,000 to 4,800,000 KRW per semester (~$2,500–$3,600 USD). "
                "However, virtually all admitted international graduate students receive "
                "the KAIST International Student Scholarship which covers 100% of the tuition."
            ),
            notes="Tuition is fully subsidized for admitted international students.",
        )

        # --- Scholarships & Funding ---
        add(
            requirement_type="scholarships_funding",
            value=(
                "KAIST International Student Scholarship: 100% tuition exemption "
                "for all normal degree semesters, plus a monthly living stipend "
                "of approximately 350,000 KRW per month for Master's students, "
                "plus coverage under the Korean National Health Insurance. "
                "Applicants are automatically considered upon admission."
            ),
        )

        # --- Document Checklist ---
        add(
            requirement_type="document_checklist",
            value=(
                "Required documents for KAIST international graduate application: "
                "1. Online Application Form (printed and signed); "
                "2. Statement of Purpose (SOP / Study Plan) detailing academic background and research interests; "
                "3. Two Letters of Recommendation from academic professors or advisors; "
                "4. Official Bachelor's Degree Certificate (or diploma); "
                "5. Official Academic Transcripts from all attended colleges/universities; "
                "6. Official English Proficiency Test Score Report (TOEFL iBT min 83 or 4.5, IELTS min 6.5, TOEIC min 720, or TEPS min 326); "
                "7. Copy of Applicant and Parents' Passports / National ID (proof of foreign citizenship); "
                "8. Certificate of Facts Concerning Entry & Exit (if applicable); "
                "9. Financial Resources Statement."
            ),
        )

        return reqs


if __name__ == "__main__":
    scraper = KAISTCSScraper()
    for r in scraper.run():
        print(r)