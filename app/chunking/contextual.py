"""
Makes each chunk self-contained: prepends a short breadcrumb (document
title + version + section) so a sentence like "this exception does not
apply during clearance events" isn't meaningless once it's isolated from
the document it came from. See ../../ANALOGY.md.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.chunking.chunker import chunk_structure_aware


@dataclass(frozen=True)
class ContextualChunk:
    text: str
    token_count: int
    section_path: str
    contextual_prefix: str  # the breadcrumb alone, e.g. "Returns Policy v3.0 → §3.2 Discounted Items: "
    # NOT concatenated into `text` -- M3 builds the actual embedded string
    # (prefix + text) at embed time, so the two stay separately queryable.


def build_contextual_prefix(*, title: str, version: str | None, section_path: str) -> str:
    """`"Returns Policy v3.0 → §3.2 Discounted Items: "` — or, for a
    document with no version (postmortems, ADRs, public pages) or a chunk
    with no section (the preamble), the parts that don't apply are simply
    left out rather than rendered as "None"."""
    label = f"{title} v{version}" if version else title
    if section_path:
        return f"{label} → §{section_path}: "
    return f"{label}: "


def chunk_with_context(text: str, *, title: str, version: str | None) -> list[ContextualChunk]:
    """T-M2.4's chunker plus a contextual prefix on every resulting chunk."""
    return [
        ContextualChunk(
            text=c.text,
            token_count=c.token_count,
            section_path=c.section_path,
            contextual_prefix=build_contextual_prefix(
                title=title, version=version, section_path=c.section_path
            ),
        )
        for c in chunk_structure_aware(text)
    ]
