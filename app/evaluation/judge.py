"""
T-M4.10: an LLM judge scoring a generated answer against the context it
was shown, on a fixed, versioned rubric. Temperature 0 -- the same input
should always get the same score, or T-M4.15's hand-score-vs-judge
agreement measurement would be comparing against a moving target.

T-M4.3's failure modes are named explicitly in the rubric, not just hoped
against: position bias (favoring claims because they're first), verbosity
bias (longer reads as better), self-preference. That last one has a real,
honest limitation this project doesn't hide: the judge is Gemini scoring
Gemini's own generation (T-M4.7/T-M4.8 use the same provider) -- same
-family self-grading is a genuine bias risk the rubric can only ask the
model to resist, not structurally eliminate. T-M4.15's hand-scoring
against 20 real answers is what actually tests whether that risk shows up
in practice, not an assumption that the rubric fixes it.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.generation.context_builder import BuiltContext
from app.generation.provider import LLMProvider
from app.generation.schema import GeneratedAnswer

RUBRIC_VERSION = "judge_rubric_v1"

JUDGE_SYSTEM_PROMPT = f"""You are an impartial evaluator ({RUBRIC_VERSION}) scoring a RAG system's \
generated answer against the context it was given and, if provided, a reference answer. Score three \
dimensions independently, each a float from 0.0 to 1.0:

1. FAITHFULNESS: For EACH claim in the answer, check whether the bracket-numbered context chunk(s) it \
cites actually support that exact claim's statement. Score = (claims genuinely supported by their cited \
context) / (total claims). A claim citing a real, valid bracket number whose chunk does NOT actually say \
what the claim states is NOT faithful, even though the citation itself points at a real chunk.
2. CORRECTNESS: Does the answer's summary correctly and completely address the question? If a reference \
answer is provided, compare against it directly -- 1.0 for correct and complete, 0.0 for wrong or missing \
the point, partial credit for incomplete-but-correct-as-far-as-it-goes. If no reference answer is \
provided, judge correctness against the context alone.
3. CITATION_SUPPORT_RATE: report the same fraction computed for FAITHFULNESS's numerator/denominator as \
its own explicit number -- how many of the answer's claims hold up under direct scrutiny of their cited \
context.

Resist these specific, known judge failure modes:
- Position bias: do not favor a claim or citation merely because it appears earlier in the answer or context.
- Verbosity bias: a longer, more detailed answer is not automatically more correct or more faithful than a \
shorter one that says the same true thing.
- Self-preference: you are evaluating text, not judging whether it "sounds like" a good answer from a \
model like yourself -- check each claim against the literal context text, nothing else.

If the answer declares itself unanswerable (answerable=false) and the context genuinely does not support \
an answer, that is a CORRECT response -- score correctness 1.0, faithfulness 1.0 (there are no claims to \
be unfaithful), citation_support_rate 1.0 (vacuously -- zero claims, zero unsupported claims)."""

_PROMPT_TEMPLATE = """Question: {question}

Reference answer (if available): {expected_answer}

Context shown to the system being judged:
{context}

The system's answer:
answerable: {answerable}
summary: {summary}
claims:
{claims_block}

Score this answer now, following the rubric exactly."""


class JudgeScore(BaseModel):
    faithfulness: float = Field(ge=0.0, le=1.0)
    correctness: float = Field(ge=0.0, le=1.0)
    citation_support_rate: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(description="Brief justification, for human audit against hand-scoring (T-M4.15)")


def judge_answer(
    question: str,
    expected_answer: str | None,
    answer: GeneratedAnswer,
    built_context: BuiltContext,
    provider: LLMProvider,
) -> JudgeScore:
    claims_block = (
        "\n".join(f"  - statement: {c.statement}\n    cites: {c.citation_numbers}" for c in answer.claims)
        if answer.claims
        else "  (no claims -- the system declared the question unanswerable from this context)"
    )
    prompt = _PROMPT_TEMPLATE.format(
        question=question,
        expected_answer=expected_answer or "(none provided)",
        context=built_context.context,
        answerable=answer.answerable,
        summary=answer.summary,
        claims_block=claims_block,
    )
    return provider.generate_structured(prompt, JudgeScore, system=JUDGE_SYSTEM_PROMPT, temperature=0.0)
