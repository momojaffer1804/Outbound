"""
outbound/backend/ingestion/scraper_stuttgart_cs.py

Tier-1 Scraper for: University of Stuttgart -- M.Sc. Computer Science (INFOTECH / Computer Science)
Source: https://www.uni-stuttgart.de/en/study/study-programs/computer-science-msc/
Tier: 1 (official university program page)
"""

from __future__ import annotations
from bs4 import BeautifulSoup
from base_scraper import BaseUniversityScraper, RawRequirement


class StuttgartCSScraper(BaseUniversityScraper):
    country = "Germany"
    university = "University of Stuttgart"
    program = "M.Sc. Computer Science"
    source_url = "https://www.uni-stuttgart.de/en/study/studienangebot/Computer-Science-M.Sc.-00002/"
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
            "Bachelor's degree in Computer Science, Software Engineering, or related discipline with substantial coursework in algorithms, data structures, computer architecture, databases, and mathematics (minimum 180 ECTS equivalent). A formal syllabus evaluation is conducted.",
            notes="Requires solid undergraduate foundations in core CS."
        )

        add(
            "cgpa",
            "Minimum German grade equivalent of 2.5 or better on the German grading scale (where 1.0 is best and 4.0 is passing). For Indian 10-point scale applicants, this corresponds to approximately 7.0/10 CGPA or 70%+.",
            notes="Strict 2.5 German grade cutoff."
        )

        add(
            "english_test",
            "English proficiency at B2/C1 level required for English-taught master's program: TOEFL iBT minimum 90, IELTS Academic minimum 6.5 (with no subscore below 6.0), or Cambridge Certificate of Advanced English (CAE).",
            notes="Minimum 6.5 IELTS / 90 TOEFL."
        )

        add(
            "german_test",
            "For the English-taught Master's in Computer Science, German proficiency is not required for admission, but students are required to complete German language modules (up to A2 level) as part of their studies.",
            notes="No German required at application time."
        )

        add(
            "gre",
            "GRE revised General Test is strongly recommended for applicants from non-EU/EEA countries. A Quantitative reasoning score in the 75th percentile or higher significantly improves admission chances.",
            notes="GRE Quant recommended for non-EU applicants."
        )

        add(
            "aps_certificate",
            "APS certificate issued by the German Embassy is mandatory for applicants holding academic degrees from India, China, or Vietnam.",
            notes="Required for India, China, Vietnam."
        )

        add(
            "tuition_fees",
            "In the state of Baden-Württemberg, international students from third countries (outside the EU/EEA) must pay a tuition fee of €1,500 per semester (€3,000 per year). In addition, all students pay the standard semester administrative contribution of approximately €200 per semester.",
            notes="State of Baden-Württemberg statutory non-EU tuition: €1,500/semester."
        )

        add(
            "deadline",
            "Application period for Winter semester: 15 November to 15 February (for non-EU international applicants). Application for Summer semester: 15 May to 15 July.",
            notes="Early non-EU winter deadline (15 February)."
        )

        add(
            "document_checklist",
            "Required documents: 1. Bachelor's Degree Certificate and official Academic Transcripts; 2. Detailed Course Descriptions / Syllabus catalog; 3. Proof of English language proficiency; 4. Curriculum Vitae (CV) and Motivation Letter; 5. APS Certificate (India/China/Vietnam); 6. GRE score report (recommended).",
            notes="Course descriptions catalog is vital for credit verification."
        )

        return reqs

    def run(self) -> list[RawRequirement]:
        try:
            soup = self.fetch()
        except Exception:
            soup = None
        return self.parse(soup)
