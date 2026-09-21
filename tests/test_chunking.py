"""T-M2.4: the structure-aware chunker with token guards, tested against
the real corpus — including a direct proof that T-M2.3's motivating
failure case (a rule severed from its own exception) is actually fixed,
not just theoretically addressed."""
from pathlib import Path

import pytest

from app.chunking import MAX_CHUNK_TOKENS, MIN_CHUNK_TOKENS, chunk_structure_aware

CLEAN_DIR = Path(__file__).resolve().parent.parent / "corpus" / "synthetic" / "clean"


def _read(name: str) -> str:
    return (CLEAN_DIR / name).read_text(encoding="utf-8")


def test_price_match_repeated_requests_stays_one_chunk():
    """The exact case T-M2.3 found: fixed-size chunking severed 'this is
    not a blanket denial' from its own explanation. Structure-aware should
    never do that -- Section 4 is short enough to survive as one chunk."""
    chunks = chunk_structure_aware(_read("price-match-policy.md"))

    matches = [c for c in chunks if "Repeated or Suspicious Requests" in c.section_path]
    assert len(matches) == 1
    normalized = " ".join(matches[0].text.split())  # source has a mid-sentence line wrap here
    assert "not a blanket denial" in normalized
    assert "legitimate frequent shoppers" in normalized


def test_h3_subsections_keep_their_own_identity():
    """returns-policy-v3.0.md is one of only two clean/ docs with real H2->H3
    nesting. 3.3 is large enough to stand alone; 3.1 (31 tok) and 3.2 (96
    tok) are individually small enough to trigger the merge guard -- real
    bug caught here during T-M2.4: a naive "keep the earlier breadcrumb"
    merge rule silently dropped 3.1's identity entirely once merged into
    3.2. Fixed to combine both leaf labels instead of picking one."""
    chunks = chunk_structure_aware(_read("returns-policy-v3.0.md"))
    paths = [c.section_path for c in chunks]

    assert any("3.1 Electronics" in p for p in paths), paths
    assert any("3.2 Discounted Items" in p for p in paths), paths
    assert any(p.endswith("3.3 Items Purchased Partly or Fully with Loyalty Points") for p in paths)
    # nested breadcrumb, not a flat one
    assert any(" > " in p for p in paths)


def test_oversized_checklist_sections_get_split():
    """T-M2.3's practice run found two real oversized sections here (350 and
    408 tokens under the naive per-heading split) -- confirm the guard
    actually catches them, not just that it exists in the code."""
    chunks = chunk_structure_aware(_read("opening-closing-checklist.md"))

    assert all(c.token_count <= MAX_CHUNK_TOKENS for c in chunks)
    # confirms the guard did real work: a naive heading-only split produced
    # these two sections as single oversized pieces (per T-M2.3's notes);
    # here each must now be 2+ pieces sharing the same section_path
    pre_closing = [c for c in chunks if c.section_path == "4. Post-Closing (after doors lock)"]
    assert len(pre_closing) >= 2


def test_no_chunk_exceeds_max_across_the_full_clean_corpus():
    for path in sorted(CLEAN_DIR.glob("*.md")):
        chunks = chunk_structure_aware(path.read_text(encoding="utf-8"))
        offenders = [c for c in chunks if c.token_count > MAX_CHUNK_TOKENS]
        assert offenders == [], f"{path.name} has a chunk over {MAX_CHUNK_TOKENS} tokens: {offenders}"


def test_merging_eliminates_undersized_chunks_across_the_full_clean_corpus():
    for path in sorted(CLEAN_DIR.glob("*.md")):
        chunks = chunk_structure_aware(path.read_text(encoding="utf-8"))
        offenders = [c for c in chunks if c.token_count < MIN_CHUNK_TOKENS]
        assert offenders == [], f"{path.name} has a chunk under {MIN_CHUNK_TOKENS} tokens: {offenders}"


def test_frontmatter_is_stripped_not_chunked_as_content():
    """YAML frontmatter is metadata (already captured separately at
    ingestion, T-M1.6/T-M1.9), not retrievable prose -- it must never show
    up inside a chunk's text."""
    chunks = chunk_structure_aware(_read("shift-policy.md"))

    assert not any("policy_id: STAFF-POL-001" in c.text for c in chunks)


def test_real_preambles_are_legitimately_large_enough_to_stand_alone():
    """Checked against real data before asserting anything: every clean/
    doc's SYNTHETIC banner + title runs 69-98 tokens once frontmatter is
    stripped -- comfortably over MIN_CHUNK_TOKENS on its own. So the
    preamble correctly stands alone here; this is not the merge guard
    failing to fire, there's nothing undersized for it to catch."""
    for path in sorted(CLEAN_DIR.glob("*.md")):
        chunks = chunk_structure_aware(path.read_text(encoding="utf-8"))
        preamble = next((c for c in chunks if c.section_path == ""), None)
        if preamble is not None:
            assert preamble.token_count >= MIN_CHUNK_TOKENS, (path.name, preamble)


def test_a_genuinely_undersized_preamble_merges_forward():
    """The merge guard itself, isolated from real corpus data (which never
    happens to produce a small-enough preamble to exercise this path) --
    a tiny fabricated intro before the first heading must not survive as
    its own orphan chunk."""
    text = "Note.\n\n## 1. Real Section\n\n" + ("This is real section content. " * 20)
    chunks = chunk_structure_aware(text)

    assert not any(c.section_path == "" for c in chunks)
    assert chunks[0].text.startswith("Note.")


@pytest.mark.parametrize("path", sorted(CLEAN_DIR.glob("*.md")), ids=lambda p: p.name)
def test_every_chunk_text_is_non_empty(path):
    chunks = chunk_structure_aware(path.read_text(encoding="utf-8"))
    assert len(chunks) > 0
    assert all(c.text.strip() for c in chunks)
