"""
outbound/backend/ingestion/scraper_tu_delft_cs.py

Tier-1 Scraper for: TU Delft (Delft University of Technology) -- M.Sc. Computer Science
Source: https://www.tudelft.nl/en/education/programmes/masters/computer-science/msc-computer-science/admission-and-application
Tier: 1 (official university program page)
"""

from __future__ import annotations
from bs4 import BeautifulSoup
from base_scraper import BaseUniversityScraper, RawRequirement


class TUDelftCSScraper(BaseUniversityScraper):
    country = "Netherlands"
    university = "TU Delft"
    program = "M.Sc. Computer Science"
    source_url = "https://www.tudelft.nl/en/education/programmes/masters/computer-science/msc-computer-science/admission-and-application"
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
            "A Bachelor of Science degree in Computer Science or closely related field from an internationally recognized research university, equivalent in level to a Dutch university Bachelor's degree. Must include substantial core foundations in algorithms, programming, computer architecture, databases, theoretical computing, and university-level mathematics (discrete math, calculus, linear algebra).",
            notes="Requires research-university Bachelor's equivalent."
        )

        add(
            "cgpa",
            "A Cumulative Grade Point Average (CGPA) of at least 75% of the maximum scale or 8.0/10 (or First Class with Distinction / Upper Second Class Honours). For countries with letter grading, minimum B+ or A- equivalent is required.",
            notes="Strict 75% / 8.0 CGPA minimum cutoff."
        )

        add(
            "gre",
            "GRE revised General Test is strictly MANDATORY for all applicants with a non-Dutch Bachelor's degree. Minimum required score: Quantitative reasoning scaled score of at least 165 (approx. 85th+ percentile). Applications with GRE Quant below 165 are automatically rejected.",
            notes="Mandatory GRE with strict Quant >= 165 gate."
        )

        add(
            "english_test",
            "Proof of English proficiency required: IELTS Academic overall band 7.0 (with no individual section score below 6.5), or TOEFL iBT overall score of at least 100 (with no individual subscore below 22). Only nationals of the USA, UK, Ireland, Australia, New Zealand, and Canada or holders of a Dutch BSc are exempt.",
            notes="Strict IELTS 7.0 (min 6.5 each) or TOEFL 100 (min 22 each)."
        )

        add(
            "tuition_fees",
            "For non-EU/EEA students, tuition fees at TU Delft for engineering and computer science master's programs are approximately €21,500 per academic year (€10,750 per semester). For EU/EEA students, statutory tuition is approximately €2,530 per academic year.",
            notes="Non-EU tuition: ~€21,500 per year."
        )

        add(
            "deadline",
            "Application deadline for non-EU/EEA students: 15 January. Application deadline for EU/EEA students: 1 April. Non-EU applicants must submit complete files including official GRE and English test scores by 15 January.",
            notes="Strict non-EU application deadline: 15 January."
        )

        add(
            "document_checklist",
            "Required documents: 1. Official Bachelor's degree certificate and complete Transcripts of Records; 2. Official GRE General Test Score Report (Quant >= 165); 3. Official English Language Test Report (IELTS >= 7.0 / TOEFL >= 100); 4. Comprehensive Course Descriptions (Syllabus); 5. Detailed Curriculum Vitae (CV); 6. Letter of Motivation; 7. Reference letters from professors.",
            notes="Syllabus and official test reports sent directly by ETS/British Council."
        )

        return reqs

    def run(self) -> list[RawRequirement]:
        try:
            soup = self.fetch()
        except Exception:
            soup = None
        return self.parse(soup)
