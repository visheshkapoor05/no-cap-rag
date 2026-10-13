"""
T-M3.7: the interface every embedding backend implements. One interface,
Gemini behind it (`gemini.py`) — this is what makes Experiment G (Gemini
vs. local embeddings, M10) possible by swapping the implementation behind
`get_embedding_provider()` without touching any caller.

Two methods, not one: `embed_document` and `embed_query` are NOT
interchangeable. Gemini's embedding API takes a `task_type` that measurably
changes the vector for identical text -- RETRIEVAL_DOCUMENT for what goes
into the index, RETRIEVAL_QUERY for what a search box sends. Collapsing
these into one `embed(text)` method would silently mismatch query and
document vectors at the one place in this project where it matters most.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Anything that can turn text into a fixed-length dense vector."""

    model_id: str
    dim: int

    def embed_document(self, text: str) -> list[float]:
        """Embeds text that will be stored in the index (a chunk)."""
        ...

    def embed_query(self, text: str) -> list[float]:
        """Embeds text that will be searched with (a user's question)."""
        ...
