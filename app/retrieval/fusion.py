"""
T-M3.10: both RRFFusion and WeightedFusion behind one `FusionStrategy`
interface, so Experiment C (T-M3.12) is a config change, not a code
change. Both take `dict[str, list[RetrievedChunk]]` -- one ranked list
per retriever, already sorted best-first -- and return one fused,
re-sorted list.

RRFFusion is T-M3.3's practice `rrf_fuse()` promoted to production,
operating on RetrievedChunk instead of bare ids, and now generic over
however many retrievers are passed (not hardcoded to exactly two).

WeightedFusion is the counterpart T-M3.2's docs argued against using
blindly: it needs the per-query min-max normalization T-M3.2's "What
breaks, concretely" callout described, because combining a dense
retriever's bounded cosine scores with BM25's unbounded scores without
normalizing first would let whichever retriever's scores happen to be
numerically larger dominate for reasons that have nothing to do with
relevance.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Protocol, runtime_checkable

from app.retrieval.strategy import RetrievedChunk


@runtime_checkable
class FusionStrategy(Protocol):
    def fuse(self, ranked_lists: dict[str, list[RetrievedChunk]]) -> list[RetrievedChunk]:
        ...


class RRFFusion:
    """score(d) = sum over retrievers of 1/(k + rank(d)). k=60 is the
    standard default (D-010 era reasoning, and the doc X/doc Y crossover
    in docs/no-cap-rag-journey.docx M3 §2): it favors a chunk that ranks
    decently across multiple retrievers over one retriever's single
    standout pick, which is the more robust default when you can't know
    in advance which retriever to trust on a given query."""

    def __init__(self, k: int = 60) -> None:
        self.k = k

    def fuse(self, ranked_lists: dict[str, list[RetrievedChunk]]) -> list[RetrievedChunk]:
        scores: dict[str, float] = defaultdict(float)
        for chunks in ranked_lists.values():
            for rank, chunk in enumerate(chunks, start=1):
                scores[chunk.chunk_id] += 1 / (self.k + rank)
        return sorted(
            (RetrievedChunk(chunk_id=cid, score=s) for cid, s in scores.items()),
            key=lambda c: c.score,
            reverse=True,
        )


class WeightedFusion:
    """fused = alpha*normalized_dense + (1-alpha)*normalized_sparse.
    Normalizes each retriever's scores to [0, 1] via min-max *within this
    call*, i.e. per query -- never against a global min/max, since BM25's
    actual score range shifts from query to query (T-M3.2). A retriever
    name not present in `weights` is dropped, not weighted at 0 silently,
    so a config typo fails loudly instead of quietly discarding a
    retriever's results."""

    def __init__(self, weights: dict[str, float]) -> None:
        total = sum(weights.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"weights must sum to 1.0, got {total}")
        self.weights = weights

    @staticmethod
    def _min_max_normalize(chunks: list[RetrievedChunk]) -> dict[str, float]:
        if not chunks:
            return {}
        scores = [c.score for c in chunks]
        lo, hi = min(scores), max(scores)
        if hi == lo:
            # every chunk scored identically -- can't distinguish them,
            # so treat them as equally (maximally) relevant rather than
            # dividing by zero.
            return {c.chunk_id: 1.0 for c in chunks}
        return {c.chunk_id: (c.score - lo) / (hi - lo) for c in chunks}

    def fuse(self, ranked_lists: dict[str, list[RetrievedChunk]]) -> list[RetrievedChunk]:
        missing = set(ranked_lists) - set(self.weights)
        if missing:
            raise ValueError(f"no weight configured for retriever(s): {missing}")

        combined: dict[str, float] = defaultdict(float)
        for name, chunks in ranked_lists.items():
            normalized = self._min_max_normalize(chunks)
            weight = self.weights[name]
            for chunk_id, norm_score in normalized.items():
                combined[chunk_id] += weight * norm_score

        return sorted(
            (RetrievedChunk(chunk_id=cid, score=s) for cid, s in combined.items()),
            key=lambda c: c.score,
            reverse=True,
        )
