"""
T-M3.8: the interface the PRD calls for explicitly ("interchangeable
strategy interfaces") -- one shape both `DenseRetriever` (T-M3.8) and
`SparseRetriever` (T-M3.9) implement, so `RRFFusion`/`WeightedFusion`
(T-M3.10) and the `/retrieve` endpoint (T-M3.11) don't need to know or
care which kind of retrieval produced a result.

Deliberately minimal: `RetrievedChunk` carries only `chunk_id` and
`score`, not chunk text or section_path. Milvus doesn't store those
(T-M3.6) and BM25 doesn't need to -- resolving a fused ranking back to
full chunk records is the `/retrieve` endpoint's job, against Postgres,
the one place content is actually read from.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    score: float


@runtime_checkable
class RetrievalStrategy(Protocol):
    """Anything that can turn a query into a ranked list of chunks."""

    def retrieve(self, query: str, k: int) -> list[RetrievedChunk]:
        """Returns up to `k` chunks, best match first."""
        ...
