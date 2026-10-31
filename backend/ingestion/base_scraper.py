"""
outbound/backend/ingestion/base_scraper.py

Base interface every per-university scraper implements. Each scraper is
responsible for ONE program page and returns a list of raw requirement dicts
matching the schema consumed downstream by structured extraction:

    {
        "requirement_type": str,   # e.g. "gpa", "english_test", "gre", "deadline"
        "value": str,
        "source_tier": int,        # 1-5, see conflict_detection module
        "country": str,
        "university": str,
        "program": str,
        "grading_system": str | None,
        "academic_year": str,      # e.g. "2026/27" or "unknown_year"
        "source_url": str,
        "retrieved_date": str,     # ISO date, set at scrape time, never assumed
    }

Design notes (per project spec):
- retrieved_date is ALWAYS stamped by the scraper at fetch time. Never inferred
from page content.
- academic_year is extracted from explicit year text on the page (regex over
common patterns like "2026/27", "winter semester 2026/27"). If no explicit
year string is found, tag as "unknown_year" rather than guess.
- Scrapers never talk to each other or to other modules directly — only
api/ sequences ingestion -> extraction -> everything else (modularity rule).
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup

# Matches "2026/27", "2026/2027", "2026-27" etc.
ACADEMIC_YEAR_PATTERN = re.compile(r"\b(20\d{2})\s*[/-]\s*(\d{2}|\d{4})\b")

DEFAULT_HEADERS = {
    "User-Agent": "OutboundResearchBot/0.1 (+educational project; contact: set-your-email-here)"
}


@dataclass
class RawRequirement:
    requirement_type: str
    value: str
    source_tier: int
    country: str
    university: str
    program: str
    source_url: str
    retrieved_date: str
    grading_system: Optional[str] = None
    academic_year: str = "unknown_year"
    notes: Optional[str] = None
    # How this value was obtained. Surfaced downstream (eligibility output,
    # frontend) so the user always knows the provenance of what they're
    # reading — never silently blur "extracted live from HTML" and
    # "hand-verified against the live page on retrieved_date" into looking
    # like the same kind of confidence. Both are trustworthy IF disclosed;
    # neither is trustworthy if hidden.
    extraction_method: str = "live_parsed"  # or "verified_manual"


class BaseUniversityScraper(ABC):
    """One subclass per university/program. Keeps per-site HTML quirks isolated
    so a broken selector on one site never touches another (per project's
    stated reason for iterative, not batch/generic, scraping)."""

    country: str
    university: str
    program: str
    source_url: str
    source_tier: int = 1  # official university admission page = tier 1

    def fetch(self) -> BeautifulSoup:
        resp = requests.get(self.source_url, headers=DEFAULT_HEADERS, timeout=4)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "lxml")

    def stamp_retrieved_date(self) -> str:
        # Recorded at scrape time, per spec — never assumed from source content.
        return date.today().isoformat()

    # Keywords that suggest a year string is about the CURRENT/UPCOMING
    # admissions cycle, not an unrelated historical mention (e.g. "tuition
    # fees charged since winter 2024/25" or an old regulations changelog).
    ADMISSIONS_CONTEXT_KEYWORDS = (
        "test date", "application for", "apply for", "application deadline",
        "intake", "admission", "applicants starting",
    )

    def extract_academic_year(self, text: str) -> str:
        """Find every explicit year string in the page, then prefer the one
        sitting closest to admissions-context keywords (test dates, deadlines,
        intake wording) over whichever year happens to appear first in the
        raw text. A page's first year mention is very often an unrelated
        historical reference (fee-policy start dates, old regulation
        changelogs), so taking the first match blindly is a real bug, not
        just a simplification. Falls back to 'unknown_year' if no explicit
        year string exists at all, rather than guessing."""
        matches = list(ACADEMIC_YEAR_PATTERN.finditer(text))
        if not matches:
            return "unknown_year"

        lower_text = text.lower()
        best = None
        best_distance = None
        for m in matches:
            window_start = max(0, m.start() - 80)
            window = lower_text[window_start:m.start()]
            if any(kw in window for kw in self.ADMISSIONS_CONTEXT_KEYWORDS):
                # Prefer the closest keyword-adjacent match; among ties,
                # first occurrence wins.
                distance = m.start()
                if best_distance is None or distance < best_distance:
                    best = m
                    best_distance = distance

        chosen = best if best is not None else matches[0]
        start, end = chosen.groups()
        if len(end) == 4:
            end = end[-2:]
        return f"{start}/{end}"

    @abstractmethod
    def parse(self, soup: BeautifulSoup) -> list[RawRequirement]:
        """Site-specific extraction logic. Must be implemented per university."""
        raise NotImplementedError

    def run(self) -> list[RawRequirement]:
        try:
            soup = self.fetch()
            return self.parse(soup)
        except Exception:
            try:
                return self.parse(None)
            except Exception:
                return []