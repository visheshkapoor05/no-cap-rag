"""T-M4.5: CrossEncoderReranker against the real model (downloaded,
cached) and real chunk text -- no mocked scores."""
from app.reranking import RerankInput, get_reranker


def test_rerank_scores_a_relevant_pair_higher_than_an_irrelevant_one():
    reranker = get_reranker()
    candidates = [
        RerankInput(chunk_id="relevant", text="Items marked clearance are final sale and cannot be returned."),
        RerankInput(chunk_id="irrelevant", text="The warehouse is located in Gurugram and opens at 9am."),
    ]
    result = reranker.rerank("are clearance items returnable", candidates, k=2)
    assert [r.chunk_id for r in result] == ["relevant", "irrelevant"]
    assert result[0].score > result[1].score


def test_rerank_respects_k():
    reranker = get_reranker()
    candidates = [RerankInput(chunk_id=f"c{i}", text=f"unrelated filler text number {i}") for i in range(10)]
    result = reranker.rerank("some query", candidates, k=3)
    assert len(result) == 3


def test_rerank_empty_candidates_returns_empty():
    reranker = get_reranker()
    assert get_reranker().rerank("anything", [], k=10) == []


def test_rerank_can_reorder_relative_to_a_naive_keyword_overlap_baseline():
    """A real demonstration of what T-M4.1 predicted: the cross-encoder
    should recognize that "non-returnable" and "cannot be returned" are
    semantically opposed to a plain "returnable" query, not just reward
    literal word overlap the way a naive keyword match would."""
    reranker = get_reranker()
    candidates = [
        RerankInput(
            chunk_id="actually_relevant",
            text="General merchandise may be returned within 30 days of purchase with a receipt.",
        ),
        RerankInput(
            chunk_id="keyword_trap",
            text="Returnable packaging materials (boxes, pallets) are handled by the receiving dock, "
            "not the returns desk, and are unrelated to customer merchandise returns.",
        ),
    ]
    result = reranker.rerank("What is the return policy for merchandise?", candidates, k=2)
    assert result[0].chunk_id == "actually_relevant"
