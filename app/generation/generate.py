"""
T-M4.8: turns a question + a built context (T-M4.6) into a citation
-grounded, structured answer (T-M4.7's generate_structured + the
GeneratedAnswer schema). The one validation generate_structured can't do
on its own: a citation_number that's syntactically valid JSON but doesn't
correspond to any [n] marker actually in the context -- an out-of-range
citation, not a malformed response. Caught here with its own repair pass,
separate from GeminiLLMProvider's schema-shape repair.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.generation.context_builder import BuiltContext, Citation
from app.generation.provider import LLMProvider
from app.generation.schema import GeneratedAnswer

SYSTEM_PROMPT = """You are a retail-policy question-answering assistant. You answer ONLY using \
the numbered context chunks provided -- never from general knowledge or assumption.

Rules:
1. Every claim in your answer must cite at least one bracket number from the context, e.g. [1], \
via citation_numbers. Cite the NUMBER shown before the chunk, never any other identifier.
2. Never cite a number that isn't shown in the provided context.
3. Break your answer into atomic claims -- one factual statement per claim, not several bundled together.
4. If the context does not contain enough information to answer the question, set answerable=false, \
leave claims empty, and explain what's missing in summary. Do not guess or use outside knowledge.
"""

_PROMPT_TEMPLATE = """Question: {question}

Context:
{context}

Answer the question using only the context above, following the system rules exactly."""


class CitationError(Exception):
    """Raised when the model cites a bracket number not present in the
    real context, even after one repair attempt."""


@dataclass(frozen=True)
class ResolvedClaim:
    """A claim with its citation_numbers resolved to real chunk
    references -- what the API layer (T-M4.12) actually returns, since a
    caller outside this module has no use for a bare integer."""

    statement: str
    citations: list[Citation]


def generate_answer(
    question: str, built_context: BuiltContext, provider: LLMProvider, *, temperature: float = 0.0
) -> GeneratedAnswer:
    valid_numbers = {c.number for c in built_context.citations}

    prompt = _PROMPT_TEMPLATE.format(question=question, context=built_context.context)
    answer = provider.generate_structured(prompt, GeneratedAnswer, system=SYSTEM_PROMPT, temperature=temperature)

    invalid = _invalid_numbers(answer, valid_numbers)
    if not invalid:
        return answer

    repair_prompt = (
        f"{prompt}\n\nYour previous answer cited bracket number(s) not present in the context: "
        f"{sorted(invalid)}. Only cite numbers that literally appear as [n] in the context above."
    )
    retried = provider.generate_structured(repair_prompt, GeneratedAnswer, system=SYSTEM_PROMPT, temperature=temperature)
    still_invalid = _invalid_numbers(retried, valid_numbers)
    if still_invalid:
        raise CitationError(
            f"model cited bracket number(s) not in context after repair: {sorted(still_invalid)}"
        )
    return retried


def resolve_claims(answer: GeneratedAnswer, built_context: BuiltContext) -> list[ResolvedClaim]:
    """Turns each claim's bare citation_numbers into real Citation
    objects (chunk_id, document_title, section_path) -- callers outside
    this module (the API layer, the judge) work with real references,
    never the internal [n] numbering scheme."""
    by_number = {c.number: c for c in built_context.citations}
    return [
        ResolvedClaim(statement=claim.statement, citations=[by_number[n] for n in claim.citation_numbers])
        for claim in answer.claims
    ]


def _invalid_numbers(answer: GeneratedAnswer, valid_numbers: set[int]) -> set[int]:
    cited = {n for claim in answer.claims for n in claim.citation_numbers}
    return cited - valid_numbers
