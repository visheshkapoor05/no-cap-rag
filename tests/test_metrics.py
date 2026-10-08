"""T-M2.8: recall_at_k() and mrr(), checked against T-M2.7's hand-computed
toy example (learnings/02-cleaning-chunking-metadata/notes.md) -- if these
don't match the hand calculation, one of the two is wrong."""
from app.evaluation import mrr, reciprocal_rank, recall_at_k

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
    import pytest

    with pytest.raises(ValueError):
        mrr([Q4])


def test_recall_at_3_average_across_the_four_answerable_queries_matches_notes_md():
    recalls = [recall_at_k(r, rel, k=3) for r, rel in [Q1, Q2, Q3, Q5]]
    assert sum(recalls) / len(recalls) == 0.875
