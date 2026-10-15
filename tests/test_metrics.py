"""T-M2.8: recall_at_k() and mrr(); T-M4.9: precision_at_k(), r_precision()
and ndcg() -- all checked against hand-computed toy examples
(learnings/02-cleaning-chunking-metadata/notes.md for the first two,
T-M4.2's by-hand walkthrough on the same 5-query set for the new three) --
if these don't match the hand calculation, one of the two is wrong."""
import math

import pytest

from app.evaluation import mrr, ndcg, precision_at_k, r_precision, reciprocal_rank, recall_at_k

# The exact 5-query toy set from T-M2.7, K=3.
Q1 = (["C7", "C2", "C9", "C1", "C4"], {"C7"})  # factual lookup
Q2 = (["C4", "C15", "C2", "C9", "C1"], {"C15"})  # exact identifier
Q3 = (["C8", "C3", "C5", "C11", "C2"], {"C3", "C11"})  # multi-hop
Q4 = (["C6", "C2", "C9", "C1", "C4"], set())  # unanswerable
Q5 = (["C20", "C19", "C2", "C1", "C4"], {"C19"})  # version-sensitive, C20 is the stale chunk


def test_recall_at_k_matches_the_hand_computed_toy_example():
    assert recall_at_k(*Q1, k=3) == 1.0
    assert recall_at_k(*Q2, k=3) == 1.0
    assert recall_at_k(*Q3, k=3) == 0.5
    assert recall_at_k(*Q5, k=3) == 1.0


def test_recall_at_k_is_none_not_zero_for_an_unanswerable_question():
    """0/0 is undefined, not a failure -- scoring it 0.0 would penalize a
    retriever for correctly having nothing relevant to find."""
    assert recall_at_k(*Q4, k=3) is None


def test_recall_at_k_is_blind_to_order_within_k():
    """The stale v1.0 chunk (C20) outranks the actually-relevant C19, but
    recall_at_k only cares whether C19 made the top 3 at all."""
    retrieved, relevant = Q5
    assert retrieved[0] not in relevant  # C20 is rank 1 and NOT relevant
    assert recall_at_k(retrieved, relevant, k=3) == 1.0  # still perfect recall


def test_reciprocal_rank_matches_the_hand_computed_toy_example():
    assert reciprocal_rank(*Q1) == 1.0
    assert reciprocal_rank(*Q2) == 0.5
    assert reciprocal_rank(*Q3) == 0.5
    assert reciprocal_rank(*Q5) == 0.5


def test_reciprocal_rank_is_none_for_an_unanswerable_question():
    assert reciprocal_rank(*Q4) is None


def test_reciprocal_rank_is_zero_not_none_when_relevant_chunks_exist_but_are_never_retrieved():
    """A real miss (relevant chunks exist, none were retrieved) is 0.0,
    distinct from the 0/0-undefined case above."""
    assert reciprocal_rank(["X", "Y", "Z"], {"C99"}) == 0.0


def test_mrr_excludes_the_unanswerable_query_and_matches_the_hand_computed_average():
    assert mrr([Q1, Q2, Q3, Q4, Q5]) == 0.625  # (1.0 + 0.5 + 0.5 + 0.5) / 4, Q4 excluded


def test_mrr_raises_if_every_query_is_unanswerable():
    with pytest.raises(ValueError):
        mrr([Q4])


def test_recall_at_3_average_across_the_four_answerable_queries_matches_notes_md():
    recalls = [recall_at_k(r, rel, k=3) for r, rel in [Q1, Q2, Q3, Q5]]
    assert sum(recalls) / len(recalls) == 0.875


# T-M4.9: precision_at_k(), r_precision(), ndcg() -- hand-computed at K=3
# on the exact same toy set, per T-M4.2's worked comparison across all
# five metrics.

def test_precision_at_k_matches_the_hand_computed_toy_example():
    assert precision_at_k(*Q1, k=3) == pytest.approx(1 / 3)
    assert precision_at_k(*Q2, k=3) == pytest.approx(1 / 3)
    assert precision_at_k(*Q3, k=3) == pytest.approx(1 / 3)  # only C3 of {C3,C11} is in the top 3
    assert precision_at_k(*Q5, k=3) == pytest.approx(1 / 3)


def test_precision_at_k_is_none_not_zero_for_an_unanswerable_question():
    assert precision_at_k(*Q4, k=3) is None


def test_precision_at_k_ceiling_is_capped_by_relevant_count_not_just_k():
    """D-014's concrete case: a PERFECT retriever on a 1-relevant-chunk
    question (Q1) scores only 1/3 at k=3 -- identical to a retriever that
    merely got lucky and found a different single relevant chunk at the
    same rank. Fixed-K precision cannot tell "found everything there was
    to find" apart from "found a fraction of a larger set" without
    already knowing R, which is exactly what r_precision() fixes below."""
    retrieved, relevant = Q1
    assert len(relevant) == 1
    assert retrieved[0] in relevant  # the only relevant chunk is already rank 1 -- as perfect as retrieval gets
    assert precision_at_k(retrieved, relevant, k=3) < 1.0  # yet P@3 still can't show "perfect"


def test_r_precision_matches_the_hand_computed_toy_example():
    assert r_precision(*Q1) == 1.0  # R=1, C7 is rank 1 -- perfect, and R-Precision shows it
    assert r_precision(*Q2) == 0.0  # R=1, rank-1 pick (C4) isn't C15 at all
    assert r_precision(*Q3) == 0.5  # R=2, top-2 = [C8, C3] -- only C3 is relevant
    assert r_precision(*Q5) == 0.0  # R=1, rank-1 pick is the stale C20, not C19


def test_r_precision_is_none_for_an_unanswerable_question():
    assert r_precision(*Q4) is None


def test_r_precision_distinguishes_perfect_from_flawed_where_fixed_k_precision_could_not():
    """The exact D-014 fix in action: Q1's retriever is perfect (its one
    relevant chunk is rank 1); Q2's is flawed (its one relevant chunk is
    rank 2, not retrieved first). precision_at_k(k=3) scored them
    identically (1/3 each, asserted above) -- r_precision tells them
    apart."""
    assert r_precision(*Q1) > r_precision(*Q2)


def test_ndcg_matches_the_hand_computed_toy_example():
    assert ndcg(*Q1, k=3) == pytest.approx(1.0)  # the only relevant chunk is already rank 1 -- ideal ranking
    assert ndcg(*Q2, k=3) == pytest.approx(1 / math.log2(3))  # C15 at rank 2, 1 relevant chunk total
    assert ndcg(*Q3, k=3) == pytest.approx((1 / math.log2(3)) / (1 / math.log2(2) + 1 / math.log2(3)))
    assert ndcg(*Q5, k=3) == pytest.approx(1 / math.log2(3))  # C19 at rank 2


def test_ndcg_is_none_for_an_unanswerable_question():
    assert ndcg(*Q4, k=3) is None


def test_ndcg_rewards_rank_position_where_recall_and_precision_cannot():
    """Q1 (relevant chunk at rank 1) and Q2 (relevant chunk at rank 2)
    score IDENTICALLY on recall_at_k and precision_at_k -- neither metric
    looks at WHERE within the top k a hit landed. NDCG is the one metric
    here that tells them apart."""
    assert recall_at_k(*Q1, k=3) == recall_at_k(*Q2, k=3)
    assert precision_at_k(*Q1, k=3) == precision_at_k(*Q2, k=3)
    assert ndcg(*Q1, k=3) > ndcg(*Q2, k=3)
