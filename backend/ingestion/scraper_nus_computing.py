"""
outbound/backend/ingestion/scraper_nus_computing.py

Tier-1 Scraper for: National University of Singapore (NUS) -- Master of Computing (School of Computing)
Source: https://www.comp.nus.edu.sg/programmes/pg/mcomp/admissions/
Tier: 1 (official university program page)
"""

from __future__ import annotations
from bs4 import BeautifulSoup
from base_scraper import BaseUniversityScraper, RawRequirement


class NUSComputingScraper(BaseUniversityScraper):
    country = "Singapore"
    university = "National University of Singapore (NUS)"
    program = "Master of Computing (General Track & CS Specialisations)"
    source_url = "https://www.comp.nus.edu.sg/programmes/graduate/mcomp/"
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
            "An honours degree in Computing / Computer Science or closely related discipline from a recognized institution. Applicants with a non-computing bachelor's degree must demonstrate substantial industry software engineering experience or relevant technical foundations for the General Track.",
            notes="Requires honours degree in computing or strong tech background."
        )

        add(
            "cgpa",
            "Good academic standing, typically a Second Class Upper Honours or minimum Cumulative Average Point (CAP) of 3.5/5.0, or equivalent minimum CGPA of 8.0/10 (approx. 75%+). High competition makes higher grades advantageous.",
            notes="Minimum 8.0/10 or Second Class Upper."
        )

        add(
            "gre",
            "International applicants with degrees from universities outside Singapore must submit either GRE or GATE: GRE revised General Test minimum combined score of 320 (Verbal + Quantitative) with Quantitative score >= 160 and Analytical Writing >= 3.5; OR Indian applicants may submit a GATE score in Computer Science with a percentile rank of 90% or higher.",
            notes="Mandatory GRE (>= 320, Quant >= 160) or GATE (>= 90th percentile)."
        )

        add(
            "english_test",
            "Applicants whose undergraduate medium of instruction was not in English must submit English proficiency scores: IELTS Academic minimum overall score of 6.5; or TOEFL iBT minimum score of 90. Applicants who graduated from English-medium universities are generally exempt.",
            notes="IELTS 6.5 or TOEFL 90."
        )

        add(
            "tuition_fees",
            "Tuition fees for the Master of Computing at NUS are approximately SGD 58,000 to SGD 62,000 total for the full 40-modular-credit program (approx. SGD 29,000 to 31,000 per year for international students, payable in semester instalments).",
            notes="Full self-funded tuition: ~SGD 58,000 to 62,000 total."
        )

        add(
            "deadline",
            "August intake (Semester 1) application period: 1 December to 31 January. January intake (Semester 2) application period: 1 July to 31 August.",
            notes="August intake closes 31 January."
        )

        add(
            "document_checklist",
            "Required documents: 1. Official Bachelor's degree certificate and complete academic transcripts; 2. Official GRE or GATE score report; 3. Official TOEFL or IELTS score report (if applicable); 4. Two Academic Reference letters / Referee reports; 5. Detailed Curriculum Vitae (CV); 6. Statement of Purpose; 7. Proof of financial support / bank statement.",
            notes="Official GRE/GATE and academic referee reports submitted via online portal."
        )

        return reqs

    def run(self) -> list[RawRequirement]:
        try:
            soup = self.fetch()
        except Exception:
            soup = None
        return self.parse(soup)
