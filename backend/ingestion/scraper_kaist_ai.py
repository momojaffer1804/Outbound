"""
outbound/backend/ingestion/scraper_kaist_ai.py

Scraper for: KAIST -- M.S. Artificial Intelligence (Graduate School of AI / GSAI)
Sources (two, deliberately kept separate -- see note below):
  1. https://admission.kaist.ac.kr/intl-graduate/Admission/Eligibility
     (Office of Admissions, university-wide eligibility rules)
  2. https://ai-systems.kaist.ac.kr/admission-grad.html
     (GSAI department's own admission/schedule page)
Tier: 1 for both (official university and official department pages)

STATUS: hardcoded-but-verified, same pattern as TUM/RWTH. Not live-HTML-parsed.

Why two source URLs instead of one:
- KAIST's admissions process is split across two levels: general eligibility
  (citizenship, English proficiency) is centrally administered by the Office
  of Admissions and applies university-wide; but SCHEDULE/deadline data and
  advisor-selection rules are published per-department, on GSAI's own page,
  not on the central eligibility page. Forcing both into one source_url would
  misrepresent where each fact actually came from -- so each RawRequirement
  records the specific page it was verified against, not a single blended URL.

Site notes:
- Program identity: KAIST runs a dedicated Graduate School of AI (GSAI, also
  called the Department of AI Systems -- ai-systems.kaist.ac.kr), distinct
  from the general M.S. Computer Science route via KAIST's School of
  Computing. Central eligibility rules (citizenship gate, English test
  structure) are administered university-wide and apply to GSAI applicants
  the same way as any other KAIST graduate program.
- Citizenship gate: applicants must NOT hold Korean citizenship to apply via
  this international track. No TUM/RWTH equivalent -- a genuinely new
  requirement_type, not a variant of an existing one.
- No GRE requirement appears anywhere on the eligibility page. Confirmed
  absence, not an extraction gap -- a real difference from TUM and RWTH,
  which both require GRE conditionally.
- English test: four accepted test types, a mid-cycle TOEFL scoring-scale
  change (83 on old scale before 21 Jan 2026, 4.5 on new scale after), and a
  two-tier citizenship/institution-based waiver system.
- No numeric GPA cutoff for the standard international Master's route. A
  GPA 3.7+ figure exists elsewhere on KAIST's site but applies ONLY to the
  KAIST-undergraduate-to-master's integrated track, not a general
  international applicant -- explicitly flagged so it is not misapplied.
- Deadlines: GSAI's Fall 2026 schedule is dated using a single-year academic
  notation ("2026학년도 가을학기" = "Academic Year 2026, Fall Semester"),
  structurally different from TUM/RWTH's split-year "2026/27" convention.
  base_scraper's regex-based extract_academic_year() targets the split-year
  pattern and would NOT catch this single-year Korean-style notation, so
  academic_year for these deadline records is set explicitly here rather
  than run through that regex -- documented, not silently wrong.
- KAIST also runs an integrated UG-to-MS-PhD track and MS-PhD integrated
  track with separate, KAIST-current-student-only eligibility (69+ credits,
  3.7+ GPA) -- out of scope for external international applicants and not
  included as a general requirement here, to avoid it being misread as
  applying to a standard applicant.
"""

from __future__ import annotations

from base_scraper import BaseUniversityScraper, RawRequirement

ELIGIBILITY_URL = "https://admission.kaist.ac.kr/intl-graduate/Admission/Eligibility"
GSAI_SCHEDULE_URL = "https://ai-systems.kaist.ac.kr/admission-grad.html"


class KAISTAIScraper(BaseUniversityScraper):
    country = "South Korea"
    university = "KAIST"
    program = "M.S. Artificial Intelligence (Graduate School of AI)"
    source_url = ELIGIBILITY_URL  # primary/default; deadline records override below
    source_tier = 1

    def parse(self, soup) -> list[RawRequirement]:
        retrieved_date = self.stamp_retrieved_date()
        full_text = soup.get_text(" ", strip=True) if soup else ""
        eligibility_academic_year = self.extract_academic_year(full_text) if soup else "unknown_year"
        if soup:
            assert eligibility_academic_year == "unknown_year", (
            f"Expected 'unknown_year' for KAIST eligibility page (no admissions"
            f"-cycle year string found during manual verification); got "
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

        # --- Citizenship eligibility gate ---
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
            notes="Requirement type with no TUM/RWTH equivalent.",
        )

        # --- Academic qualification (no numeric GPA) ---
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
                  "Master's route. A separate GPA 3.7+ figure exists on "
                  "KAIST's site but applies only to the KAIST-undergraduate-"
                  "to-master's integrated track (current KAIST students, "
                  "3-4 completed semesters, 69+ credits) -- do not apply "
                  "that figure to a general international applicant.",
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
                  "anywhere on this official page -- confirmed absence, a "
                  "real difference from TUM and RWTH's conditional GRE rules.",
        )

        # --- Program identity note ---
        add(
            requirement_type="program_identity",
            value=(
                "This is KAIST's Graduate School of AI (GSAI / Department of "
                "AI Systems), a dedicated AI-focused graduate school, distinct "
                "from the general M.S. Computer Science route via KAIST's "
                "School of Computing."
            ),
        )

        # --- Deadlines: sourced from the GSAI department page, which uses a
        # single-year academic notation, not TUM/RWTH's split-year format ---
        add(
            requirement_type="deadline",
            value=(
                "Fall 2026 semester, general admission (all programs): "
                "online application 27 Mar 2026 10:00 - 07 Apr 2026 17:30 "
                "KST via gradapply.kaist.ac.kr. 1st round results from 14 "
                "May 2026. 2nd round interviews 16-26 May 2026. Final "
                "results from 25 Jun 2026."
            ),
            source_url=GSAI_SCHEDULE_URL,
            academic_year="2026",
            notes="Source page uses a single-year academic notation "
                  "('2026학년도 가을학기' = AY2026 Fall), structurally "
                  "different from TUM/RWTH's split-year '2026/27' format. "
                  "Set explicitly rather than run through the split-year "
                  "regex, which would not match this notation.",
        )
        add(
            requirement_type="deadline_note",
            value=(
                "KAIST also runs a separate Spring-intake cycle (application "
                "typically in the preceding autumn) in addition to the Fall "
                "cycle above -- unlike TUM/RWTH's simpler two-fixed-window "
                "model, KAIST's exact Spring dates were not independently "
                "verified against an official page during this scrape and "
                "are left out rather than estimated."
            ),
            source_url=GSAI_SCHEDULE_URL,
            academic_year="2026",
            notes="Known gap: Spring intake dates not yet verified.",
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
    scraper = KAISTAIScraper()
    for r in scraper.run():
        print(r)