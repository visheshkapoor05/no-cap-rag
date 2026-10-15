"""
The grading rubric: Recall@K and MRR (T-M2.8), plus Precision@K, R-Precision
and NDCG (T-M4.9) -- all hand-written (D-008) rather than imported from
Ragas/DeepEval, so the shape of each metric, and what each is blind to, is
something we actually understand, not a number a library handed us. See
../../ANALOGY.md and T-M2.7's hand-computed toy example in
learnings/02-cleaning-chunking-metadata/notes.md, which every function here
is tested against -- the same 5-query set T-M4.2 hand-computed these three
new metrics on, so all five metrics are directly comparable on one example.
"""
from __future__ import annotations

import math
from collections.abc import Iterable


def recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float | None:
    """Of the chunks that are actually relevant, how many did the top k
    retrieved chunks contain? None (not 0.0) when `relevant` is empty —
    an unanswerable question has no ground truth to recover, so the ratio
    is genuinely undefined, not a retrieval failure. Blind to order
    within the top k."""
    if not relevant:
        return None
    hits = len(set(retrieved[:k]) & relevant)
    return hits / len(relevant)


def reciprocal_rank(retrieved: list[str], relevant: set[str]) -> float | None:
    """1 / (rank of the first relevant chunk), over the *full* retrieved
    list, not just a top k. None when `relevant` is empty, same reasoning
    as recall_at_k. 0.0 (not None) when relevant chunks exist but none of
    them were retrieved at all -- that's a real miss, not an undefined case."""
    if not relevant:
        return None
    for rank, item in enumerate(retrieved, start=1):
        if item in relevant:
            return 1.0 / rank
    return 0.0


def mrr(queries: Iterable[tuple[list[str], set[str]]]) -> float:
    """Mean Reciprocal Rank across a batch of (retrieved, relevant) pairs.
    Queries with no relevant chunks (reciprocal_rank returns None) are
    excluded from the mean entirely, per T-M2.7's finding -- folding an
    unanswerable question's undefined score into the average would
    silently distort it."""
    scores = [rr for retrieved, relevant in queries if (rr := reciprocal_rank(retrieved, relevant)) is not None]
    if not scores:
        raise ValueError("mrr() needs at least one query with a non-empty relevant set")
    return sum(scores) / len(scores)


def precision_at_k(retrieved: list[str], relevant: set[str], k: int) -> float | None:
    """Of the top k retrieved chunks, how many are actually relevant?
    None (not 0.0) when `relevant` is empty, same reasoning as
    recall_at_k. Blind to how many relevant chunks exist beyond k --
    worse, its own ceiling is capped at min(len(relevant), k) / k, so a
    *perfect* retriever on a 1-relevant-chunk question scores only 0.2 at
    k=5, identical to a flawed retriever that found the same chunk buried
    at rank 2. That ceiling distortion is exactly what r_precision()
    below exists to remove."""
    if not relevant:
        return None
    hits = len(set(retrieved[:k]) & relevant)
    return hits / k


def r_precision(retrieved: list[str], relevant: set[str]) -> float | None:
    """precision_at_k() called with k = this question's own relevant-chunk
    count (R), not a fixed K -- removes the ceiling distortion fixed-K
    precision has on small-R questions (D-014). A perfect retriever
    always scores 1.0 here regardless of R, which fixed Precision@5 can't
    guarantee for R=1. None when `relevant` is empty."""
    if not relevant:
        return None
    return precision_at_k(retrieved, relevant, k=len(relevant))


def ndcg(retrieved: list[str], relevant: set[str], k: int) -> float | None:
    """Normalized Discounted Cumulative Gain at k -- the one metric here
    that actually rewards RANK POSITION within the top k, which Recall@K
    and Precision@K are both blind to (a relevant chunk at rank 1 scores
    identically to one at rank k for either of those). Binary relevance
    (a chunk is relevant or it isn't, no graded scores), discounted by
    1/log2(rank+1): DCG@k = sum of rel_i / log2(i+1) for the top k, then
    normalized against IDCG@k -- the DCG of the best possible ordering
    (every relevant chunk packed into the earliest ranks) -- so a perfect
    ranking always scores 1.0 regardless of how many relevant chunks
    exist. None when `relevant` is empty, same reasoning as recall_at_k."""
    if not relevant:
        return None
    dcg = sum(1.0 / math.log2(i + 1) for i, item in enumerate(retrieved[:k], start=1) if item in relevant)
    ideal_hits = min(len(relevant), k)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_hits + 1))
    return dcg / idcg if idcg > 0 else 0.0
