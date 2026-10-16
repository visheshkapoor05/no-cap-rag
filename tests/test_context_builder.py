"""T-M4.6: build_context()'s dedupe, token-budget, and citation-mapping
behavior -- pure functions, no real infra needed."""
from app.generation.context_builder import ContextSource, build_context


def _source(
    chunk_id: str, text: str, title: str = "Returns Policy", section: str = "3. Exceptions", version: str | None = None
) -> ContextSource:
    return ContextSource(chunk_id=chunk_id, document_title=title, document_version=version, section_path=section, text=text)


def test_keeps_all_chunks_and_numbers_citations_in_rank_order_when_nothing_overflows():
    sources = [_source("a", "Items may be returned within 30 days."), _source("b", "Clearance items are final sale.")]
    result = build_context(sources, max_tokens=4000)
    assert [c.chunk_id for c in result.citations] == ["a", "b"]
    assert [c.number for c in result.citations] == [1, 2]
    assert "[1]" in result.context and "[2]" in result.context
    assert result.dropped_for_budget == 0
    assert result.deduped_count == 0


def test_dedupes_exact_duplicate_text_keeping_the_higher_ranked_copy():
    """The real M3 finding this guards against: a superseded document
    version's chunk can be near-identical to the current one's. Here
    chunk 'stale' (lower rank) has the exact same text as chunk 'current'
    (higher rank) -- only the higher-ranked one should survive."""
    sources = [
        _source("current", "Items marked clearance are final sale.", title="Returns Policy v3.0"),
        _source("stale", "Items marked clearance are final sale.", title="Returns Policy v2.0"),
        _source("unique", "General items may be returned within 30 days."),
    ]
    result = build_context(sources, max_tokens=4000)
    ids = [c.chunk_id for c in result.citations]
    assert "current" in ids
    assert "stale" not in ids
    assert "unique" in ids
    assert result.deduped_count == 1


def test_dedupe_is_case_and_whitespace_insensitive_but_not_fuzzy():
    sources = [
        _source("a", "Items   may be   returned."),
        _source("b", "items may be returned."),  # same content, different case/spacing -> duplicate
        _source("c", "Items may possibly be returned."),  # genuinely different wording -> NOT a duplicate
    ]
    result = build_context(sources, max_tokens=4000)
    ids = [c.chunk_id for c in result.citations]
    assert ids == ["a", "c"]
    assert result.deduped_count == 1


def test_token_budget_stops_including_chunks_once_it_would_overflow():
    big_text = "word " * 2000  # a chunk that alone is already a few thousand tokens
    sources = [_source("first", "short chunk"), _source("second", big_text), _source("third", "short chunk two")]
    result = build_context(sources, max_tokens=50)
    ids = [c.chunk_id for c in result.citations]
    assert "first" in ids  # fits within the tiny budget
    assert "second" not in ids  # the oversized chunk doesn't fit
    assert result.dropped_for_budget > 0


def test_budget_never_reorders_a_lower_ranked_smaller_chunk_ahead_of_a_higher_ranked_one_that_didnt_fit():
    """Once a chunk doesn't fit, the function stops entirely rather than
    skipping ahead to a smaller lower-ranked chunk -- rank order is
    authoritative, not bin-packing efficiency."""
    big_text = "word " * 2000
    sources = [_source("first", "short"), _source("second_oversized", big_text), _source("third_tiny", "x")]
    result = build_context(sources, max_tokens=50)
    ids = [c.chunk_id for c in result.citations]
    assert "third_tiny" not in ids  # never promoted past the chunk that didn't fit, even though it would fit alone


def test_citation_block_includes_document_version_when_known():
    """T-M4.16 failure case #1 fix: version_sensitive-05/-06 both failed
    because the context block never told the model which chunk was
    current. The version now has to actually appear in the rendered
    block, or the model has no way to resolve a version conflict."""
    result = build_context([_source("a", "90 days.", title="Returns Policy", version="v3.0")], max_tokens=4000)
    assert "Returns Policy v3.0" in result.context
    assert result.citations[0].document_version == "v3.0"


def test_citation_block_omits_version_when_none():
    result = build_context([_source("a", "90 days.", title="Returns Policy", version=None)], max_tokens=4000)
    assert "Returns Policy →" in result.context
    assert result.citations[0].document_version is None


def test_empty_sources_returns_empty_context():
    result = build_context([], max_tokens=4000)
    assert result.context == ""
    assert result.citations == []
    assert result.dropped_for_budget == 0
    assert result.deduped_count == 0
