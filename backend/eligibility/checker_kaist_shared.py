"""
outbound/backend/eligibility/checker_kaist_shared.py

Shared eligibility logic for KAIST's two programs (GSAI/AI and School of
Computing/CS). Per both scrapers' own docstrings, eligibility content
(citizenship gate, qualification basis, English test rules, absence of GRE)
is CONFIRMED IDENTICAL between the two programs -- School of Computing has
no separate eligibility page of its own and explicitly defers to the same
central Office of Admissions page GSAI uses. This mirrors that fact in the
eligibility layer instead of duplicating logic across two files, but does
NOT merge the two into one checker class -- program identity, source
attribution, and deadline records still differ, and a future divergence
(e.g. CS publishing its own deadline exceptions) should only require editing
checker_kaist_cs.py, not this shared file.

What this shared logic CAN judge:
- citizenship_eligibility: a clean binary gate.
- gre: confirmed absent -- always "not_applicable", never "needs_review",
  since this isn't missing data, it's a confirmed rule.
- english_test: judgeable, but has real structure to respect -- the
  mid-cycle TOEFL scoring-scale change (83 old-scale / 4.5 new-scale) and
  the two-tier waiver system (full waiver by citizenship alone for one
  list; conditional waiver requiring BOTH citizenship AND institution
  location for a second, larger list). This checker does NOT have a
  reliable, verified list of exactly which countries fall in each tier
  beyond the few explicitly named in the scraper's value string (UK, USA,
  Canada, Ireland, Australia, New Zealand for full waiver; India,
  Pakistan, Nigeria, Singapore among others for conditional waiver) -- so
  it only judges citizenships explicitly named there and returns
  "needs_review" for anything else, rather than guessing which tier an
  unlisted country falls into. The conditional-waiver check reads
  `profile.undergrad_institution_english_medium` directly (a real yes/no
  fact the user provides) rather than inferring institution language from
  citizenship/undergrad-country matching -- an earlier version of this
  checker guessed "institution is English-medium" from
  undergrad_country == citizenship, which is wrong (e.g. an Indian citizen
  who studied at a Hindi-medium college would have been incorrectly waived).
  That guess has been replaced by this explicit field.

What this checker CANNOT judge:
- qualification_basis: degree-equivalence check, not a CGPA comparison.
  Always "needs_review".
"""

from __future__ import annotations

from base_checker import RequirementJudgment

FULL_WAIVER_CITIZENSHIPS = {"UK", "United Kingdom", "USA", "United States", "Canada",
                             "Ireland", "Australia", "New Zealand"}
CONDITIONAL_WAIVER_CITIZENSHIPS = {"India", "Pakistan", "Nigeria", "Singapore"}


def judge_citizenship_eligibility(profile, raw_req) -> RequirementJudgment:
    if profile.citizenship is None:
        return RequirementJudgment(
            "citizenship_eligibility", "needs_review",
            "Citizenship not provided — required to check KAIST's non-Korean-citizen gate.",
            raw_req.value,
        )
    if profile.citizenship in ("Korea", "South Korea"):
        return RequirementJudgment(
            "citizenship_eligibility", "not_met",
            "Korean citizens are not eligible via this international admissions track, unless "
            "renunciation is formally documented or all primary/secondary education (grades 1-12) "
            "was completed outside Korea.",
            raw_req.value,
        )
    return RequirementJudgment(
        "citizenship_eligibility", "met", f"Citizenship ({profile.citizenship}) is eligible.", raw_req.value,
    )


def judge_qualification_basis(profile, raw_req) -> RequirementJudgment:
    return RequirementJudgment(
        "qualification_basis", "needs_review",
        "Requires a Bachelor's degree judged equivalent under one of several accepted international "
        "frameworks — not something a CGPA figure alone can confirm.",
        raw_req.value,
    )


def judge_english_test(profile, raw_req) -> RequirementJudgment:
    if profile.flow == "early_planner":
        return RequirementJudgment(
            "english_test", "needs_review",
            "Not yet assessed (early planner flow) — add to your future checklist.",
            raw_req.value,
        )
    if profile.citizenship in FULL_WAIVER_CITIZENSHIPS:
        return RequirementJudgment(
            "english_test", "met", f"Full waiver by citizenship ({profile.citizenship}).", raw_req.value,
        )

    conditional_eligible_citizenship = profile.citizenship in CONDITIONAL_WAIVER_CITIZENSHIPS
    if conditional_eligible_citizenship and profile.undergrad_country == profile.citizenship:
        if profile.undergrad_institution_english_medium is True:
            return RequirementJudgment(
                "english_test", "met",
                f"Conditional waiver: citizenship and institution location both "
                f"{profile.citizenship}, and institution confirmed English-medium.",
                raw_req.value,
            )
        if profile.undergrad_institution_english_medium is False:
            return RequirementJudgment(
                "english_test", "needs_review",
                f"Citizenship and institution location both {profile.citizenship}, but institution "
                "was not English-medium — conditional waiver does not apply; a test score is needed.",
                raw_req.value,
            )
        return RequirementJudgment(
            "english_test", "needs_review",
            f"Citizenship and institution location both {profile.citizenship} — conditional waiver "
            "may apply, but whether the institution itself was English-medium was not provided.",
            raw_req.value,
        )

    if profile.english_test_type is None or profile.english_score is None:
        return RequirementJudgment(
            "english_test", "needs_review",
            "No waiver applies based on citizenship data provided, and no English test score was given.",
            raw_req.value,
        )

    test = profile.english_test_type.upper()
    score = profile.english_score
    if test == "IELTS":
        status = "met" if score >= 6.5 else "not_met"
        return RequirementJudgment("english_test", status, f"IELTS {score} vs required 6.5.", raw_req.value)
    if test == "TOEFL":
        threshold = 4.5 if profile.toefl_test_date_on_or_after_2026_01_21 else 83
        scale_note = "new scale (post 21 Jan 2026)" if profile.toefl_test_date_on_or_after_2026_01_21 else "old scale"
        status = "met" if score >= threshold else "not_met"
        return RequirementJudgment(
            "english_test", status, f"TOEFL {score} vs required {threshold} ({scale_note}).", raw_req.value,
        )
    if test == "TOEIC":
        status = "met" if score >= 720 else "not_met"
        return RequirementJudgment("english_test", status, f"TOEIC {score} vs required 720.", raw_req.value)
    if test == "TEPS":
        status = "met" if score >= 326 else "not_met"
        return RequirementJudgment("english_test", status, f"TEPS {score} vs required 326.", raw_req.value)
    return RequirementJudgment(
        "english_test", "needs_review", f"Unrecognized test type '{profile.english_test_type}'.", raw_req.value,
    )


def judge_gre(raw_req) -> RequirementJudgment:
    return RequirementJudgment(
        "gre", "not_applicable",
        "No GRE requirement appears anywhere on KAIST's official eligibility page — confirmed "
        "absence, not missing data.",
        raw_req.value,
    )