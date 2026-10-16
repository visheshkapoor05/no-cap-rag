"""
T-M4.6: assembles retrieved chunks into one prompt-ready context block,
fitting a token budget, with every surviving chunk keeping a citation
number the generation step (T-M4.8) can point back at.

Three real problems, not one: (1) a fused ranking can still contain two
chunks with near-identical text (M3's real finding: a superseded document
version embeds almost identically to its replacement, so both can surface
for the same query) -- a human reading two copies of the same policy
wastes context budget and can make the model cite the stale one. (2) the
context has to fit a real token budget, not "all of it". (3) every chunk
that survives both of those has to keep a stable, traceable ID so a
citation in the generated answer can be resolved back to a real chunk, not
just a position in a list that changes next request.

T-M4.16 failure case #1: dedup catches an *identical* superseded chunk,
but a superseded document can also contain a chunk that's genuinely
*different* text from its replacement (a changed number, a changed rule)
-- not caught by dedup, and not resolvable at all if the version that
produced it never reaches the prompt. The document's version is now part
of the citation block specifically so the model (and the judge) can tell
"these two candidate chunks disagree" apart from "these two candidate
chunks disagree, and this one is current."
"""
from __future__ import annotations

from dataclasses import dataclass

import tiktoken

_ENC = tiktoken.get_encoding("cl100k_base")

DEFAULT_MAX_CONTEXT_TOKENS = 4000


@dataclass(frozen=True)
class ContextSource:
    """One resolved, citable chunk -- the context builder's input shape.
    Deliberately independent of app/api's response models: this module
    shouldn't need to import the API layer to do its job."""

    chunk_id: str
    document_title: str
    document_version: str | None
    section_path: str
    text: str


@dataclass(frozen=True)
class Citation:
    number: int
    chunk_id: str
    document_title: str
    document_version: str | None
    section_path: str


@dataclass(frozen=True)
class BuiltContext:
    """context is the literal prompt-ready block: each surviving chunk's
    text, prefixed with its [n] citation marker. citations maps citation
    number back to the real chunk_id/document/section -- what T-M4.8's
    structured answer validates its claims' chunk_ids against, and what
    the API layer resolves a citation into a user-facing reference."""

    context: str
    citations: list[Citation]
    dropped_for_budget: int
    deduped_count: int


def _normalize(text: str) -> str:
    """Collapses whitespace and case for duplicate-detection only -- never
    used for the actual context text, which keeps its real formatting."""
    return " ".join(text.lower().split())


def _dedupe(sources: list[ContextSource]) -> tuple[list[ContextSource], int]:
    """Drops a chunk whose normalized text exactly matches one already
    kept, in rank order -- the first (best-ranked) copy wins, later
    duplicates (e.g. a superseded document version's near-identical
    section) are the ones dropped. Exact-text matching only, not fuzzy --
    a near-but-not-identical rewrite is a different, both-worth-keeping
    claim, not a duplicate."""
    seen: set[str] = set()
    kept: list[ContextSource] = []
    dropped = 0
    for source in sources:
        key = _normalize(source.text)
        if key in seen:
            dropped += 1
            continue
        seen.add(key)
        kept.append(source)
    return kept, dropped


def build_context(
    sources: list[ContextSource], max_tokens: int = DEFAULT_MAX_CONTEXT_TOKENS
) -> BuiltContext:
    """`sources` must already be in rank order (best first) -- this
    function never re-ranks, it only dedupes, budgets, and labels.
    Greedy token-budget fill: walks the ranked list in order, keeping a
    chunk only if it fits in what's left of the budget, and stops
    entirely once nothing more can fit (a lower-ranked chunk that's
    merely smaller never jumps ahead of a higher-ranked one that didn't
    fit -- preserving rank order is more important than packing the
    budget tighter)."""
    deduped, deduped_count = _dedupe(sources)

    citations: list[Citation] = []
    blocks: list[str] = []
    used_tokens = 0
    dropped_for_budget = 0

    for source in deduped:
        title = f"{source.document_title} {source.document_version}" if source.document_version else source.document_title
        block = f"[{len(citations) + 1}] {title} → §{source.section_path}: {source.text}"
        block_tokens = len(_ENC.encode(block))
        if used_tokens + block_tokens > max_tokens:
            dropped_for_budget += len(deduped) - len(citations)
            break
        citations.append(
            Citation(
                number=len(citations) + 1,
                chunk_id=source.chunk_id,
                document_title=source.document_title,
                document_version=source.document_version,
                section_path=source.section_path,
            )
        )
        blocks.append(block)
        used_tokens += block_tokens

    return BuiltContext(
        context="\n\n".join(blocks),
        citations=citations,
        dropped_for_budget=dropped_for_budget,
        deduped_count=deduped_count,
    )
