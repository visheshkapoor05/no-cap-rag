"""
T-M4.5: the `Reranker` interface + a local cross-encoder implementation.
Runs on CPU for a top-50 candidate set -- local, not an API, per the
task's own reasoning: free to iterate on, reproducible across runs, and
running the model yourself teaches more than calling an endpoint does.

See T-M4.1's bi-encoder-vs-cross-encoder comparison for why this exists as
a SECOND stage rather than replacing DenseRetriever/SparseRetriever: a
cross-encoder can't be precomputed (it needs the real query at inference
time), so it only ever runs on the handful of candidates stage one already
narrowed things down to, never the full corpus.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from sentence_transformers import CrossEncoder

from app.retrieval.strategy import RetrievedChunk

# ms-marco-MiniLM-L-6-v2: a small (~80MB), CPU-friendly cross-encoder
# trained specifically for passage reranking (MS MARCO), the standard
# baseline choice for this exact two-stage-retrieval pattern -- verified
# against the real sentence-transformers cross-encoder model card, not
# picked from memory.
MODEL_ID = "cross-encoder/ms-marco-MiniLM-L-6-v2"


@dataclass(frozen=True)
class RerankInput:
    """What the reranker needs per candidate -- chunk_id plus the actual
    text to score, since (unlike DenseRetriever/SparseRetriever) a
    cross-encoder reads real text, not a precomputed vector or a token
    index."""

    chunk_id: str
    text: str


@runtime_checkable
class Reranker(Protocol):
    def rerank(self, query: str, candidates: list[RerankInput], k: int) -> list[RetrievedChunk]:
        """Returns up to `k` of `candidates`, re-scored and re-sorted by
        the cross-encoder, best first."""
        ...


class CrossEncoderReranker:
    model_id = MODEL_ID

    def __init__(self) -> None:
        self._model = CrossEncoder(MODEL_ID)

    def rerank(self, query: str, candidates: list[RerankInput], k: int) -> list[RetrievedChunk]:
        if not candidates:
            return []
        pairs = [(query, c.text) for c in candidates]
        scores = self._model.predict(pairs)
        ranked = sorted(zip(candidates, scores), key=lambda pair: pair[1], reverse=True)
        return [RetrievedChunk(chunk_id=c.chunk_id, score=float(score)) for c, score in ranked[:k]]


_reranker: CrossEncoderReranker | None = None


def get_reranker() -> CrossEncoderReranker:
    """Built once, lazily -- loading the model has real cost (reading
    weights from disk/cache), the same reason every other provider in
    this app is a startup-time singleton, not constructed per request."""
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoderReranker()
    return _reranker


def close_reranker() -> None:
    global _reranker
    _reranker = None
