"""
T-M4.8: the structured shape every generated answer takes. Decomposed into
atomic, individually-cited claims rather than one prose blob -- the
forward-looking reason, per TASKS.md: M7 must verify claims individually,
and free text would mean M7 starts by parsing claims back out of prose.
Structured claims here make that extraction nearly free later.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class Claim(BaseModel):
    """One atomic, factual statement, grounded in specific cited chunks.
    "Atomic" matters: "returns are free within 30 days and clearance
    items are final sale" is two claims bundled into one sentence -- M7's
    per-claim verification needs them separated, or a verification
    failure on the second half would incorrectly flag the whole thing.

    Cites by the small integer `[n]` marker shown before each chunk in
    the prompt, never the chunk's real chunk_id -- a real bug caught by
    testing against the actual model: the context text only ever shows
    the bracket number, never the underlying UUID, so a model asked to
    cite "chunk_ids" cited the bracket numbers it could actually see
    (literally the string "2") instead of hallucinating a UUID it was
    never shown. Small integers are also just more reliable for a model
    to transcribe correctly than a 36-character UUID. generate_answer()
    resolves citation_numbers back to real chunk_ids against the same
    BuiltContext that produced the numbering."""

    statement: str
    citation_numbers: list[int] = Field(min_length=1, description="The [n] bracket numbers from the context that support this claim")


class GeneratedAnswer(BaseModel):
    """The full structured response. `answerable=False` means the
    provided context doesn't support an answer -- claims stays empty and
    `summary` explains why, rather than the model inventing a plausible
    -sounding answer the context doesn't actually contain. This is
    citation-grounded generation only (T-M4.8); the full evidence-graded
    retry loop and per-claim verification with abstention are M6/M7's
    job, not reimplemented here."""

    answerable: bool
    summary: str = Field(description="A natural-reading answer, or the reason no answer is supported")
    claims: list[Claim] = Field(default_factory=list)
