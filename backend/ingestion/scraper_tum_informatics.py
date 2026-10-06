"""
outbound/backend/ingestion/scraper_tum_informatics.py

Tier-1 scraper for TU Munich (TUM) Master's in Informatics.
Updated to scrape BOTH the program-specific page and the central TUM 
language requirements page to capture exact IELTS/TOEFL minimums.
"""

import requests
from bs4 import BeautifulSoup
from base_scraper import BaseUniversityScraper, RawRequirement

class TUMInformaticsScraper(BaseUniversityScraper):
    country = "Germany"
    university = "TU Munich (TUM)"
    program = "Master's in Informatics"
    source_url = "https://www.in.tum.de/en/in/future-students/masters-programs/informatics/"
    source_tier = 1

    def parse(self, soup: BeautifulSoup) -> list[RawRequirement]:
        # Required by the ABC, but we override run() directly below 
        # to handle the dual-URL fetching logic.
        return []

    def run(self) -> list[RawRequirement]:
        records = []
        retrieved_date = self.stamp_retrieved_date()
        
        # 1. SCRAPE PROGRAM-SPECIFIC PAGE
        try:
            resp = requests.get(self.source_url, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                content = soup.find('main') or soup.find('body')
                if content:
                    # Extract the academic year dynamically using the base class method
                    text_block = content.get_text(separator=" ")
                    academic_year = self.extract_academic_year(text_block)

                    for p in content.find_all('p'):
                        text = p.get_text(strip=True)
                        if len(text) > 30:
                            req_type = "general_admission"
                            if "grade" in text.lower() or "gpa" in text.lower():
                                req_type = "cgpa"
                            elif "gre" in text.lower() or "gate" in text.lower():
                                req_type = "gre"
                            
                            records.append(RawRequirement(
                                requirement_type=req_type,
                                value=text,
                                source_tier=self.source_tier,
                                country=self.country,
                                university=self.university,
                                program=self.program,
                                source_url=self.source_url,
                                retrieved_date=retrieved_date,
                                academic_year=academic_year,
                                extraction_method="live_parsed"
                            ))
        except Exception as e:
            print(f"Warning: Failed to scrape TUM Program page - {e}")

        # 2. SCRAPE CENTRAL LANGUAGE REQUIREMENTS PAGE
        language_url = "https://www.tum.de/en/studies/application/application-info-portal/admission-requirements/language-certificates"
        try:
            resp = requests.get(language_url, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                content = soup.find('main') or soup.find('body')
                if content:
                    text_block = content.get_text(separator=" ")
                    academic_year = self.extract_academic_year(text_block)

                    for tag in content.find_all(['p', 'li']):
                        text = tag.get_text(strip=True)
                        text_lower = text.lower()
                        # Only grab chunks that actually contain the test names
                        if "ielts" in text_lower or "toefl" in text_lower or "cambridge" in text_lower:
                            records.append(RawRequirement(
                                requirement_type="english_test",
                                value=text,
                                source_tier=self.source_tier,
                                country=self.country,
                                university=self.university,
                                program=self.program,
                                source_url=language_url,
                                retrieved_date=retrieved_date,
                                academic_year=academic_year,
                                extraction_method="live_parsed"
                            ))
        except Exception as e:
            print(f"Warning: Failed to scrape TUM Language page - {e}")

        # Fallback if both fail (network issues) so the checker doesn't crash
        if not records:
            records.append(RawRequirement(
                requirement_type="general_admission",
                value="Could not fetch live requirements. Please check TUM website directly.",
                source_tier=self.source_tier,
                country=self.country,
                university=self.university,
                program=self.program,
                source_url=self.source_url,
                retrieved_date=retrieved_date,
                academic_year="unknown_year",
                extraction_method="fallback"
            ))

        return records

if __name__ == "__main__":
    scraper = TUMInformaticsScraper()
    for req in scraper.run():
        print(f"[{req.requirement_type}] {req.value[:80]}...")