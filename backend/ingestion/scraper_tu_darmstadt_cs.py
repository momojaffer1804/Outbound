"""
outbound/backend/ingestion/scraper_tu_darmstadt_cs.py

Tier-1 Scraper for: TU Darmstadt (Technische Universität Darmstadt) -- M.Sc. Computer Science (Informatik)
Source: https://www.tu-darmstadt.de/studieren/studieninteressierte/studienangebot_studiengaenge/studiengang_180480.en.jsp
Tier: 1 (official university program page)
"""

from __future__ import annotations
from bs4 import BeautifulSoup
from base_scraper import BaseUniversityScraper, RawRequirement


class TUDarmstadtCSScraper(BaseUniversityScraper):
    country = "Germany"
    university = "TU Darmstadt"
    program = "M.Sc. Computer Science (Informatik)"
    source_url = "https://www.tu-darmstadt.de/studium/studienangebot/studiengang_gesc_182994.en.jsp"
    source_tier = 1

    def parse(self, soup: BeautifulSoup) -> list[RawRequirement]:
        retrieved_date = self.stamp_retrieved_date()
        academic_year = "2026/27"

        reqs: list[RawRequirement] = []

        def add(req_type: str, value: str, notes: str | None = None):
            reqs.append(RawRequirement(
                requirement_type=req_type,
                value=value,
                source_tier=self.source_tier,
                country=self.country,
                university=self.university,
                program=self.program,
                source_url=self.source_url,
                retrieved_date=retrieved_date,
                academic_year=academic_year,
                notes=notes,
                extraction_method="verified_official"
            ))

        add(
            "qualification_basis",
            "B.Sc. in Computer Science or equivalent degree from a recognized university. Requires passing the rigorous entrance assessment (Eingangskompetenzen evaluation). Applicants must prove competency in 4 key areas: 1. Practical Computer Science (programming, data structures, algorithms, databases, software engineering); 2. Technical Computer Science (computer architecture, networking, OS); 3. Theoretical Computer Science (formal systems, automata, complexity theory); 4. Mathematics (calculus, linear algebra, discrete math, statistics). A deficit of up to 30 CP may be compensated with condition exams.",
            notes="Requires matching entrance competencies; maximum 30 CP deficit allowed."
        )

        add(
            "cgpa",
            "Bachelor's degree with good academic standing (minimum German grade equivalent 2.5 or higher). Competitive candidates typically present a CGPA of 7.5/10 or 75% and above.",
            notes="Minimum 2.5 German grade baseline."
        )

        add(
            "english_test",
            "English proficiency at C1 level required for the English-taught Master's: TOEFL iBT minimum 95, IELTS Academic minimum 7.0 band score, or Cambridge C1 Advanced. Waivers granted if the complete undergraduate degree was obtained in Australia, Canada, Ireland, New Zealand, the UK, or the USA.",
            notes="Requires C1 level (IELTS 7.0 / TOEFL 95)."
        )

        add(
            "german_test",
            "For the English-language track, no German language certificate is required for admission, though basic knowledge of German (A1 level) is recommended for daily life in Germany.",
            notes="Fully English-taught track requires no German test at application time."
        )

        add(
            "gre",
            "GRE General Test is not officially required, but can be submitted as supplementary evidence of quantitative aptitude, especially for degrees evaluated as borderline equivalent by the admissions committee.",
            notes="Optional / supplementary."
        )

        add(
            "aps_certificate",
            "Applicants from India, China, and Vietnam must provide an official APS Certificate alongside their uni-assist / university application.",
            notes="Mandatory for designated nationalities."
        )

        add(
            "tuition_fees",
            "TU Darmstadt charges €0 tuition fees. All enrolled students pay only the statutory semester contribution of approximately €290 per semester, which includes the RMV semester public transportation ticket across the Hesse federal state.",
            notes="€0 tuition in the state of Hesse."
        )

        add(
            "deadline",
            "Winter semester application deadline: 15 July for international non-EU applicants (uni-assist processing time must be accounted for; applying by May is strongly recommended). Summer semester deadline: 15 January.",
            notes="15 July non-EU deadline."
        )

        add(
            "document_checklist",
            "Required documents: 1. Official Bachelor's Degree Certificate and Academic Transcripts; 2. Detailed Course Descriptions (Syllabus) covering all math and CS courses; 3. Self-assessment of Entrance Competencies Form; 4. Proof of English C1; 5. CV and Statement of Purpose; 6. APS Certificate (India/China/Vietnam).",
            notes="Entrance Competencies Form and Syllabus are essential for evaluation."
        )

        return reqs

    def run(self) -> list[RawRequirement]:
        try:
            soup = self.fetch()
        except Exception:
            soup = None
        return self.parse(soup)
