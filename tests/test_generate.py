"""T-M4.8: generate_answer() -- a real end-to-end test against the real
corpus and real Gemini, plus deterministic unit tests of the
hallucinated-citation repair path against a fake provider (so that path
doesn't depend on actually provoking the real model into hallucinating)."""
from __future__ import annotations

import pytest

from app.chunking.registry import get_chunks_for_document
from app.core.db import get_pool
from app.documents.registry import find_by_content_hash
from app.documents.hashing import compute_content_hash
from app.generation import (
    CitationError,
    ContextSource,
    GeneratedAnswer,
    build_context,
    generate_answer,
    resolve_claims,
)
from app.generation.gemini import GeminiLLMProvider
from app.generation.schema import Claim
from app.corpus_plan import plan_synthetic
from app.ingestion import FileSource


class FakeProvider:
    """Deterministic stand-in for LLMProvider -- returns pre-scripted
    answers so the hallucination-repair path can be tested without
    depending on the real model actually hallucinating."""

    model_id = "fake"

    def __init__(self, answers: list[GeneratedAnswer]) -> None:
        self._answers = iter(answers)
        self.calls = 0

    def generate_text(self, prompt, *, system=None, temperature=0.7):
        raise NotImplementedError

    def generate_structured(self, prompt, schema, *, system=None, temperature=0.0):
        self.calls += 1
        return next(self._answers)


def _context():
    return build_context(
        [
            ContextSource(chunk_id="real-1", document_title="Returns Policy", document_version=None, section_path="1", text="Items may be returned within 30 days."),
            ContextSource(chunk_id="real-2", document_title="Returns Policy", document_version=None, section_path="3.2", text="Clearance items are final sale."),
        ]
    )


def test_generate_answer_accepts_a_valid_first_response_without_a_repair_call():
    good = GeneratedAnswer(
        answerable=True,
        summary="General items can be returned within 30 days; clearance items are final sale.",
        claims=[
            Claim(statement="General items may be returned within 30 days.", citation_numbers=[1]),
            Claim(statement="Clearance items are final sale.", citation_numbers=[2]),
        ],
    )
    provider = FakeProvider([good])
    result = generate_answer("What's the return policy?", _context(), provider)
    assert result is good
    assert provider.calls == 1  # no repair needed


def test_generate_answer_repairs_an_out_of_range_citation_and_succeeds():
    out_of_range = GeneratedAnswer(
        answerable=True,
        summary="...",
        claims=[Claim(statement="...", citation_numbers=[1, 99])],  # context only has [1] and [2]
    )
    fixed = GeneratedAnswer(
        answerable=True, summary="...", claims=[Claim(statement="...", citation_numbers=[1])]
    )
    provider = FakeProvider([out_of_range, fixed])
    result = generate_answer("question", _context(), provider)
    assert result is fixed
    assert provider.calls == 2


def test_generate_answer_raises_citation_error_if_still_out_of_range_after_repair():
    bad1 = GeneratedAnswer(answerable=True, summary="x", claims=[Claim(statement="x", citation_numbers=[50])])
    bad2 = GeneratedAnswer(answerable=True, summary="x", claims=[Claim(statement="x", citation_numbers=[51])])
    provider = FakeProvider([bad1, bad2])
    with pytest.raises(CitationError):
        generate_answer("question", _context(), provider)
    assert provider.calls == 2


def test_resolve_claims_maps_citation_numbers_back_to_real_chunk_references():
    answer = GeneratedAnswer(
        answerable=True,
        summary="...",
        claims=[Claim(statement="General items may be returned within 30 days.", citation_numbers=[1])],
    )
    resolved = resolve_claims(answer, _context())
    assert len(resolved) == 1
    assert resolved[0].statement == "General items may be returned within 30 days."
    assert resolved[0].citations[0].chunk_id == "real-1"
    assert resolved[0].citations[0].document_title == "Returns Policy"


def test_generate_answer_against_the_real_corpus_and_real_gemini():
    pool = get_pool()
    plan = next(p for p in plan_synthetic() if p.title == "Returns Policy")
    raw = FileSource().fetch(plan.ref)
    document = find_by_content_hash(pool, compute_content_hash(raw.text))
    assert document is not None, "run `python -m app.cli ingest --scope synthetic` first"
    records = get_chunks_for_document(pool, document.id)
    assert records, "Returns Policy has no chunks -- run ingest first"

    sources = [
        ContextSource(
            chunk_id=str(r.id), document_title=document.title, document_version=document.version,
            section_path=r.section_path, text=r.text,
        )
        for r in records[:6]
    ]
    context = build_context(sources)

    provider = GeminiLLMProvider()
    result = generate_answer("What is the return window for a general item?", context, provider)

    assert isinstance(result, GeneratedAnswer)
    assert result.answerable is True
    assert result.claims
    valid_numbers = {c.number for c in context.citations}
    for claim in result.claims:
        assert set(claim.citation_numbers) <= valid_numbers

    # resolve_claims() must turn those numbers back into real chunk references,
    # each one actually among the sources that were offered as context.
    resolved = resolve_claims(result, context)
    valid_ids = {s.chunk_id for s in sources}
    for claim in resolved:
        for citation in claim.citations:
            assert citation.chunk_id in valid_ids


def test_generate_answer_abstains_when_context_does_not_support_the_question():
    sources = [
        ContextSource(
            chunk_id="unrelated",
            document_title="Opening/Closing Checklist",
            document_version=None,
            section_path="1",
            text="Unlock the front doors and disarm the alarm system at the start of the shift.",
        )
    ]
    context = build_context(sources)
    provider = GeminiLLMProvider()
    result = generate_answer(
        "What percentage employee discount applies to personal purchases?", context, provider
    )
    assert result.answerable is False
    assert not result.claims
