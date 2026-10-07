"""Auto-detection of a document's effective date from its own text, used as
a fallback when a caller doesn't supply one explicitly (mainly the upload
endpoint, where there's no YAML frontmatter to read it from)."""
from datetime import date

from app.corpus_plan import plan_synthetic
from app.ingestion import FileSource
from app.ingestion.extract import extract_effective_date


def test_extracts_bold_markdown_effective_date():
    text = "**Policy ID:** PM-POL-001 · **Version:** 1.0 · **Effective:** February 1, 2026"
    assert extract_effective_date(text) == date(2026, 2, 1)


def test_extracts_plain_effective_date_from_a_pdf_style_extraction():
    text = "Policy ID: WAR-POL-001 | Version: 1.0 | Effective: April 1, 2026"
    assert extract_effective_date(text) == date(2026, 4, 1)


def test_extracts_the_start_of_an_effective_date_range():
    text = 'Campaign Brief: Summer BOGO\nEffective June 15 – July 31, 2026'
    assert extract_effective_date(text) == date(2026, 6, 15)


def test_extracts_iso_date_for_postmortems_and_adrs_which_dont_say_effective():
    text = "Incident ID: POS-ERR-3021 | Date: 2026-03-18 | Severity: SEV-2"
    assert extract_effective_date(text) == date(2026, 3, 18)


def test_returns_none_when_no_date_pattern_is_present():
    assert extract_effective_date("Just some ordinary text with no date in it.") is None


def test_resolves_correctly_for_every_real_synthetic_document():
    """Not a guessed pattern -- every one of the 28 real corpus documents'
    actual header conventions, checked directly. A list, not a dict keyed by
    title -- two titles (Returns Policy, Loyalty Program Rules) legitimately
    repeat across versions."""
    results = []
    for plan in plan_synthetic():
        raw = FileSource().fetch(plan.ref)
        results.append((plan.title, plan.version, extract_effective_date(raw.text)))

    missing = [(title, version) for title, version, found in results if found is None]
    assert not missing, missing
    assert len(results) == 28
