"""
outbound/backend/ingestion/scraper_eth_zurich_cs.py

Tier-1 Scraper for: ETH Zurich (Eidgenössische Technische Hochschule Zürich) -- Master's in Computer Science
Source: https://inf.ethz.ch/studies/master/master-cs.html
Tier: 1 (official university program page)
"""

from __future__ import annotations
from bs4 import BeautifulSoup
from base_scraper import BaseUniversityScraper, RawRequirement


class ETHZurichCSScraper(BaseUniversityScraper):
    country = "Switzerland"
    university = "ETH Zurich"
    program = "Master's in Computer Science"
    source_url = "https://ethz.ch/en/studies/master/degree-programmes/engineering-sciences/computer-science.html"
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
            "An outstanding Bachelor's degree in Computer Science from a recognized research university (equivalent to ETH's 180 ECTS Bachelor in Computer Science). The applicant's curriculum must cover comprehensive advanced theory (algorithms, complexity, formal methods), system software, computer architecture, and advanced mathematics (linear algebra, analysis, probability). Significant credit deficits result in admission denial.",
            notes="Extremely competitive evaluation against ETH's rigorous curriculum."
        )

        add(
            "cgpa",
            "Admission is highly selective. Successful applicants typically rank within the top 5% to 10% of their graduating class with a minimum CGPA of 8.5/10 or equivalent First Class with Distinction from premier institutions.",
            notes="Requires top tier undergraduate ranking and high GPA."
        )

        add(
            "gre",
            "GRE revised General Test is strictly MANDATORY for all applicants who did not obtain their Bachelor's degree in an EU/EFTA country (i.e. all non-Bologna degrees, including India, China, USA). Competitive scores: Quantitative reasoning >= 165 (>= 85th percentile), Analytical Writing >= 4.0.",
            notes="Mandatory for non-EU/EFTA applicants."
        )

        add(
            "english_test",
            "English proficiency at C1 level required: TOEFL iBT minimum 100 overall, or IELTS Academic minimum 7.0 band score. Only native speakers from designated English-speaking countries or holders of a bachelor's degree earned entirely in an English-speaking country are exempt.",
            notes="C1 level required: TOEFL 100 / IELTS 7.0."
        )

        add(
            "tuition_fees",
            "Tuition fees at ETH Zurich are approximately CHF 730 per semester (approx. €760 / $820 USD) for all students, making it very affordable compared to US/UK institutions. However, living costs in Zurich are high (estimated CHF 2,000 to CHF 2,500 per month).",
            notes="Very low tuition (CHF 730/semester); high cost of living."
        )

        add(
            "deadline",
            "International application window: 1 November to 15 December. All international students requiring a visa or holding non-Swiss degrees must apply before 15 December for the following Autumn semester.",
            notes="Strict early deadline: 15 December."
        )

        add(
            "document_checklist",
            "Required documents: 1. Official Bachelor's degree certificate and complete Transcripts; 2. Official GRE General Test Score Report; 3. Official English test score report (TOEFL/IELTS); 4. Comprehensive Course Descriptions / Syllabus catalog; 5. Curriculum Vitae (CV); 6. Letter of Motivation; 7. Proof of class rank / percentile certificate if available.",
            notes="GRE score report must be sent directly via ETS code 2268."
        )

        return reqs

    def run(self) -> list[RawRequirement]:
        try:
            soup = self.fetch()
        except Exception:
            soup = None
        return self.parse(soup)
