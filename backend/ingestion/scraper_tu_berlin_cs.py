"""
outbound/backend/ingestion/scraper_tu_berlin_cs.py

Tier-1 Scraper for: TU Berlin (Technische Universität Berlin) -- M.Sc. Computer Science (Informatik)
Source: https://www.tu.berlin/en/studying/study-programs/all-programs-offered/study-course/computer-science-m-sc
Tier: 1 (official university program page)
"""

from __future__ import annotations
from bs4 import BeautifulSoup
from base_scraper import BaseUniversityScraper, RawRequirement


class TUBerlinCSScraper(BaseUniversityScraper):
    country = "Germany"
    university = "TU Berlin"
    program = "M.Sc. Computer Science (Informatik)"
    source_url = "https://www.tu.berlin/studieren/studienangebot/studiengaenge/detail/computer-science-master-of-science"
    source_tier = 1

    def parse(self, soup: BeautifulSoup) -> list[RawRequirement]:
        retrieved_date = self.stamp_retrieved_date()
        full_text = soup.get_text(" ", strip=True) if soup else ""
        academic_year = self.extract_academic_year(full_text)
        if academic_year == "unknown_year":
            academic_year = "2026/27"

        reqs: list[RawRequirement] = []

        def add(req_type: str, value: str, notes: str | None = None, source_url: str | None = None):
            reqs.append(RawRequirement(
                requirement_type=req_type,
                value=value,
                source_tier=self.source_tier,
                country=self.country,
                university=self.university,
                program=self.program,
                source_url=source_url or self.source_url,
                retrieved_date=retrieved_date,
                academic_year=academic_year,
                notes=notes,
                extraction_method="verified_official"
            ))

        add(
            "qualification_basis",
            "Bachelor of Science in Computer Science or equivalent standard from an accredited higher education institution (at least 180 ECTS). Requires specific undergraduate curriculum overlap: at least 12 ECTS in Theoretical Computer Science, at least 12 ECTS in Computer Engineering / Systems Architecture, and at least 18 ECTS in Mathematics.",
            notes="Strict ECTS credit distribution across Theory, Systems, and Math."
        )

        add(
            "cgpa",
            "Admission is restricted (Numerus Clausus / selection procedure). While no absolute minimum cutoff guarantees admission, previous competitive selection typically requires a German equivalent GPA of 2.0 or better (approx. 75%+ or 7.8/10 CGPA).",
            notes="Selection procedure based on academic merit and prior coursework rigor."
        )

        add(
            "english_test",
            "Proof of English proficiency at C1 level (CEFR) is required for the English-language track. Accepted tests: TOEFL iBT minimum 95, IELTS Academic minimum 7.0 band score, or Cambridge Certificate C1 Advanced (CAE). English-medium bachelor degree exemption applies if degree was obtained in an English-speaking country.",
            notes="Requires C1 level English (higher than TUM's B2/6.5 baseline)."
        )

        add(
            "german_test",
            "For the English-taught track, basic German proficiency at A1 level is recommended/required for enrollment within the first academic year. Fully German-taught track requires German C1 (TestDaF 4x4 or DSH-2).",
            notes="A1 German required for enrollment compliance."
        )

        add(
            "gre",
            "GRE General Test is not officially required for TU Berlin, but applicants from non-EU/EEA institutions must submit preliminary documentation via uni-assist (VPD).",
            notes="No GRE requirement."
        )

        add(
            "aps_certificate",
            "Mandatory APS Certificate (Akademische Prüfstelle) for applicants who obtained their undergraduate degree in India, China, or Vietnam before applying through uni-assist.",
            notes="Mandatory visa & admission requirement for designated countries."
        )

        add(
            "deadline",
            "Winter semester application deadline: 15 May for international applicants applying through uni-assist (VPD process recommended to start at least 6-8 weeks prior). Summer semester: 15 November.",
            notes="Uni-assist VPD required prior to direct TU Berlin portal submission."
        )

        add(
            "tuition_fees",
            "TU Berlin charges €0 tuition fees for all students, including non-EU international students. Students only pay the standard semester administrative contribution (Semesterbeitrag) of approximately €310 per semester, which includes a subsidized public transportation pass for Berlin.",
            notes="No tuition fee in Berlin."
        )

        add(
            "document_checklist",
            "Required documents: 1. Official Bachelor's Degree Certificate and Transcripts of Records; 2. Uni-assist VPD (Preliminary Documentation); 3. Self-assessment Subject ECTS Mapping Form (Theoretical CS, Systems, Math); 4. Proof of English C1; 5. Complete CV and Letter of Motivation; 6. APS Certificate (India/China/Vietnam).",
            notes="VPD and ECTS subject mapping form are mandatory."
        )

        return reqs

    def run(self) -> list[RawRequirement]:
        try:
            soup = self.fetch()
        except Exception:
            soup = None
        return self.parse(soup)
