"""
outbound/backend/conflict_detection/detect_conflicts.py

Implements the project's core "headline feature": source-hierarchy conflict
resolution. NOT a symmetric "sources disagree" -- resolved by authority
tier, tier-1 always wins, output style is "Secondary source contradicts
official requirement -- official given priority", never treating a
tier-4/5 source as equal to a tier-1 one.

DELIBERATE DESIGN CHOICE: this module does not try to semantically parse
two prose values and decide WHETHER they actually disagree. That kind of
auto-interpretation is exactly the "runs cleanly, silently wrong" risk this
project has already rejected. Detection here is TIER-AWARE BUT
TEXT-AGNOSTIC: if more than one DISTINCT raw value string exists across
different source tiers for a (university, requirement_type), that's
surfaced as a conflict -- full stop. The tier-1 record is always shown as
authoritative; every other record is shown as a secondary claim for a
human to read and judge.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ConflictRecord:
    university: str
    requirement_type: str
    authoritative: object
    secondary: list = field(default_factory=list)
    message: str = ""


def detect_conflicts(requirements: list) -> list[ConflictRecord]:
    groups: dict[tuple, list] = {}
    for req in requirements:
        key = (req.university, req.requirement_type)
        groups.setdefault(key, []).append(req)

    conflicts: list[ConflictRecord] = []
    for (university, requirement_type), reqs in groups.items():
        distinct_values = {r.value for r in reqs}
        if len(distinct_values) <= 1:
            continue

        reqs_sorted = sorted(reqs, key=lambda r: r.source_tier)
        authoritative = reqs_sorted[0]
        # A differing value only counts as a genuine CONFLICT if it comes
        # from a DIFFERENT source than the authoritative record. Two rows
        # sharing the same requirement_type from the SAME source_url (e.g.
        # a university's own page legitimately listing both a winter
        # deadline and a summer deadline under requirement_type="deadline")
        # are multiple real facts, not disagreement -- grouping by
        # requirement_type alone is too coarse to distinguish "two sources
        # disagree" from "one source states two true things". Bug found
        # 2026-09-29 via live run: TUM's winter/summer deadlines (both
        # tier-1, same source_url) were being flagged as a false-positive
        # conflict before this check existed.
        secondary = [
            r for r in reqs_sorted[1:]
            if r.value != authoritative.value and r.source_url != authoritative.source_url
        ]

        if not secondary:
            continue

        conflicts.append(ConflictRecord(
            university=university,
            requirement_type=requirement_type,
            authoritative=authoritative,
            secondary=secondary,
            message=(
                f"{len(secondary)} secondary source(s) (tier {sorted(set(r.source_tier for r in secondary))}) "
                f"state a different value for '{requirement_type}' than {university}'s own tier-{authoritative.source_tier} "
                f"source. Official source given priority -- secondary claims shown for reference, not "
                f"used to override it."
            ),
        ))

    return conflicts


def format_conflict_report(conflicts: list[ConflictRecord]) -> str:
    if not conflicts:
        return "No conflicts detected."

    lines = []
    for c in conflicts:
        lines.append(f"\n=== {c.university} — {c.requirement_type} ===")
        lines.append(f"  AUTHORITATIVE (tier {c.authoritative.source_tier}, {c.authoritative.source_url}):")
        lines.append(f"    {c.authoritative.value}")
        for s in c.secondary:
            lines.append(f"  SECONDARY (tier {s.source_tier}, {s.source_url}):")
            lines.append(f"    {s.value}")
        lines.append(f"  -> {c.message}")
    return "\n".join(lines)


if __name__ == "__main__":
    # Scrapers live in a sibling directory (backend/ingestion/), not here
    # (backend/conflict_detection/). Python doesn't search sibling folders
    # by default, so add it to sys.path explicitly. This matches the
    # project's existing flat-script-import convention (no __init__.py
    # package structure) rather than introducing a different import system
    # just for this file.
    import sys
    import os
    sys.path.insert(
        0,
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ingestion")
    )

    from scraper_tum_informatics import TUMInformaticsScraper
    from scraper_tum_english_mygermanuniversity import TUMEnglishMyGermanUniversityScraper
    from scraper_tum_english_yocket import TUMEnglishYocketScraper

    all_reqs = (
        TUMInformaticsScraper().run()
        + TUMEnglishMyGermanUniversityScraper().run()
        + TUMEnglishYocketScraper().run()
    )
    conflicts = detect_conflicts(all_reqs)
    print(format_conflict_report(conflicts))