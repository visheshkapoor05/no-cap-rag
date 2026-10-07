"""
The grading rubric: Recall@K and MRR, hand-written (D-008) rather than
imported from Ragas/DeepEval, so the shape of each metric — and what each
is blind to — is something we actually understand, not a number a library
handed us. See ../../ANALOGY.md and T-M2.7's hand-computed toy example in
learnings/02-cleaning-chunking-metadata/notes.md, which these functions are
tested against.
"""
from __future__ import annotations

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
