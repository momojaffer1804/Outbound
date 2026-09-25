# Outbound

A source-grounded Masters eligibility engine for Indian students applying abroad.
Checks eligibility across universities, resolves conflicting admission requirements
by source authority, and flags outdated or stale requirement data.

## Problem

Admission requirements (GPA cutoffs, language scores, prerequisites, deadlines) are
scattered across official university pages, government/recognized authority guidance
(e.g. DAAD), and secondary or forum sources — and these sources frequently disagree
with each other or go stale. Most tools either ignore this entirely or silently pick
one source without disclosing the conflict. Outbound resolves conflicts by source
authority instead of treating all sources as equal, and tracks when data was retrieved
so staleness can be flagged rather than assumed away.

## Structure

```
outbound/
├── backend/                  FastAPI backend
│   ├── ingestion/            HTML scraping (BeautifulSoup), one scraper per university
│   ├── retrieval/            hybrid search: BM25 + embeddings
│   ├── eligibility/          GPA conversion, criteria matching
│   ├── conflict_detection/   source-hierarchy resolution
│   ├── temporal/             staleness / version checks
│   ├── ects_mapping/         credit conversion + user-tagged course mapping (v1 scope)
│   └── api/                  routes — only place that wires modules together
├── frontend/                 React (Vite)
└── eval/                     RAG evaluation harness (Project 2, built after v1 works)
```

Each backend module exposes a clean function/class interface and modules never call
each other directly — only `api/` sequences them. This is a deliberate architecture
decision: adding a future feature should mean adding one module, not touching existing
ones.

Requirement data follows a fixed schema regardless of source:

```
{
  requirement_type, value, source_tier, country, university, program,
  grading_system, academic_year, source_url, retrieved_date, extraction_method
}
```

`source_tier` ranks authority (1: official admission page, 2: official
regulations/PDF, 3: DAAD/government/recognized authority, 4: secondary/consultancy,
5: forums). `extraction_method` records whether a value was extracted live from HTML
or hand-verified against the source, so downstream consumers always know how a given
data point was obtained rather than treating all data as equally automated.

## Progress

**Phase 0 — Setup: done.** Repository created, folder structure in place, `.gitignore`
excludes `venv/`, `node_modules/`, and raw/processed scrape data.

**Phase 1 — Data ingestion: in progress.**

Universities covered so far: 1 of 10 (TU Munich, M.Sc. Informatics).

For TUM, the following requirement categories have been extracted and verified against
the live official page: qualification basis (no numeric GPA cutoff — gated by degree
equivalence and a two-stage aptitude assessment instead), English proficiency status,
conditional GRE/GATE requirement, conditional APS certificate requirement, application
deadlines for both semesters, ECTS credits, and program duration. Each record carries
`retrieved_date`, an `academic_year` extracted from admissions-context text on the page
(not assumed), and an `extraction_method` flag.

A concrete conflict case was found and logged during this phase: several tier-4
secondary sources (mygermanuniversity, tutopiya) state a specific IELTS/TOEFL cutoff
for TUM's program, while the official tier-1 page does not state a number at all and
links out to a separate page instead. This is real evidence the conflict-detection
layer this project is built around addresses an actual, current problem — not a
hypothetical one.

Remaining in Phase 1: find the exact admission-requirements page (not just the landing
page) for each of the remaining 9 universities, and write a scraper for each.

**Phases 2 through 9** (structured extraction, retrieval, eligibility, conflict
detection, comparison view, ECTS mapping, frontend integration, evaluation harness):
not started.

## Difficulties

**Live HTML parsing vs. hardcoded-but-verified data.** The TUM scraper was first
built to extract values live from the page (heading-text matching plus regex over
sibling content), since TUM's site has no consistent CSS classes to hook into. This
was unreliable in practice: two requirement categories (GRE, APS certificate) were
silently dropped with no error when the heading search failed, and another field
picked up an unrelated adjacent sentence. A scraper that runs cleanly and quietly
omits a real requirement is a worse outcome than one that visibly fails, since it
looks trustworthy while actually being incomplete. The decision was to revert TUM to
manually verified values (checked against the live page on the date recorded) rather
than spend further time perfecting one site's parser before the per-university
pattern is proven across more, structurally different sites. This is tracked via the
`extraction_method` field so verified-manual and live-parsed data are never presented
with the same implied confidence.

**Academic year extraction.** An early version of the year-extraction logic took the
first year-like string anywhere on a page, which picked up an unrelated fee-policy
date rather than the actual admissions-cycle year. Fixed by anchoring extraction to
year strings that appear near admissions-context keywords (test dates, application
deadlines, intake wording) instead of taking the first match on the page. This is the
kind of error that would otherwise pass silently, since the output still looks like a
plausible year.

**Per-site heterogeneity.** Scrapers are being built one university at a time rather
than as a single generic scraper, since a blind generic approach would mean discarding
assumptions repeatedly as each new site's HTML structure turns out to differ. The
trade-off is more files (one scraper per university sharing a common base class) in
exchange for each site's quirks being isolated and independently debuggable.

## Status

In progress — Phase 1 (data ingestion), 1 of 10 universities complete.