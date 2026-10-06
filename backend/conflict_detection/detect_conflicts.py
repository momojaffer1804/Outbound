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
    program: str = ""


def detect_conflicts(requirements: list) -> list[ConflictRecord]:
    # Group by (university, program, requirement_type) so 
    # different degree programs at the same university don't clash.
    groups: dict[tuple, list] = {}
    for req in requirements:
        prog = getattr(req, "program", "")
        key = (req.university, prog, req.requirement_type)
        groups.setdefault(key, []).append(req)

    conflicts: list[ConflictRecord] = []
    for (university, program, requirement_type), reqs in groups.items():
        distinct_values = {r.value for r in reqs}
        if len(distinct_values) <= 1:
            continue

        reqs_sorted = sorted(reqs, key=lambda r: r.source_tier)
        
        # An official tier must be Tier 1 (or Tier 2 maximum).
        # If the highest source available is Tier 4/5, we have NO official baseline.
        highest_tier = reqs_sorted[0].source_tier
        if highest_tier > 2:
            continue

        # Gather all official baseline records
        auth_records = [r for r in reqs_sorted if r.source_tier == highest_tier]
        authoritative = auth_records[0]
        
        # Set of all accepted official values and URLs
        auth_values = {r.value for r in auth_records}
        auth_urls = {r.source_url for r in auth_records}

        # Secondary sources MUST have a lower tier (higher tier number),
        # must differ from ALL official values, and cannot be from an official URL.
        secondary = [
            r for r in reqs_sorted
            if r.source_tier > highest_tier
            and r.value not in auth_values
            and r.source_url not in auth_urls
        ]

        if not secondary:
            continue

        conflicts.append(ConflictRecord(
            university=university,
            program=program,
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
        prog_label = f" ({c.program})" if c.program else ""
        lines.append(f"\n=== {c.university}{prog_label} — {c.requirement_type} ===")
        lines.append(f"  AUTHORITATIVE (tier {c.authoritative.source_tier}, {c.authoritative.source_url}):")
        lines.append(f"    {c.authoritative.value}")
        for s in c.secondary:
            lines.append(f"  SECONDARY (tier {s.source_tier}, {s.source_url}):")
            lines.append(f"    {s.value}")
        lines.append(f"  -> {c.message}")
    return "\n".join(lines)


if __name__ == "__main__":
    import os
    import sys
    # Adding the parent directory's 'ingestion' folder to the path dynamically
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