"""T-M3.10. RRFFusion is checked against the exact same doc X / doc Y
hand-computed reference practice/03-dense-bm25-rrf/rrf_practice.py already
verified (k=60: X=0.0255/Y=0.0286; k=1: X=0.520/Y=0.182) -- same math,
now operating on RetrievedChunk instead of bare ids."""
import pytest

from app.retrieval.fusion import RRFFusion, WeightedFusion
from app.retrieval.strategy import RetrievedChunk


def _ranked(chunk_ids: list[str]) -> list[RetrievedChunk]:
    """Builds a ranked list where only ORDER matters (RRF ignores score),
    descending placeholder scores just to keep RetrievedChunk honest."""
    return [RetrievedChunk(chunk_id=cid, score=1.0 / (i + 1)) for i, cid in enumerate(chunk_ids)]


FILLERS = [f"F{i}" for i in range(1, 49)]
DENSE_RANKED = ["X"] + FILLERS[:8] + ["Y"] + FILLERS[8:]
BM25_RANKED = FILLERS[:9] + ["Y"] + FILLERS[9:48] + ["X"]


def test_rrf_matches_the_hand_computed_reference_at_k60():
    fused = RRFFusion(k=60).fuse({"dense": _ranked(DENSE_RANKED), "bm25": _ranked(BM25_RANKED)})
    scores = {c.chunk_id: c.score for c in fused}
    assert abs(scores["X"] - 0.0255) < 0.0005
    assert abs(scores["Y"] - 0.0286) < 0.0005
    assert scores["Y"] > scores["X"]  # Y wins narrowly at the standard k
    # (some filler docs rank even higher than both -- they sit near the
    # top of BOTH lists, which is correctly an even stronger consensus
    # signal than X or Y have; fused[0] is not expected to be Y here.)


def test_rrf_matches_the_hand_computed_reference_at_k1():
    fused = RRFFusion(k=1).fuse({"dense": _ranked(DENSE_RANKED), "bm25": _ranked(BM25_RANKED)})
    scores = {c.chunk_id: c.score for c in fused}
    assert abs(scores["X"] - 0.520) < 0.001
    assert abs(scores["Y"] - 0.182) < 0.001
    assert scores["X"] > scores["Y"]  # flips at low k, relative to k=60's Y > X


def test_rrf_rewards_appearing_in_multiple_retrievers():
    """A chunk ranked mediocre-but-present in both lists should beat one
    ranked #1 in only one list and absent from the other -- RRF's core
    consensus property, at the standard k."""
    dense = _ranked(["A", "B", "C"])
    bm25 = _ranked(["Z", "B", "Y"])  # B appears in both, mid-rank each time
    fused = RRFFusion(k=60).fuse({"dense": dense, "bm25": bm25})
    assert fused[0].chunk_id == "B"


def test_weighted_fusion_requires_weights_summing_to_one():
    with pytest.raises(ValueError):
        WeightedFusion(weights={"dense": 0.5, "bm25": 0.3})


def test_weighted_fusion_rejects_an_unweighted_retriever():
    fusion = WeightedFusion(weights={"dense": 1.0})
    with pytest.raises(ValueError):
        fusion.fuse({"dense": _ranked(["A"]), "bm25": _ranked(["B"])})


def test_weighted_fusion_normalizes_before_blending():
    """The actual point of T-M3.2's normalization problem: dense scores in
    [0.7, 0.9] and BM25 scores in [2, 40] must not let BM25 dominate
    purely because its raw numbers are bigger."""
    dense = [RetrievedChunk("A", 0.9), RetrievedChunk("B", 0.7)]
    bm25 = [RetrievedChunk("B", 40.0), RetrievedChunk("A", 2.0)]

    fused = WeightedFusion(weights={"dense": 0.5, "bm25": 0.5}).fuse(
        {"dense": dense, "bm25": bm25}
    )
    scores = {c.chunk_id: c.score for c in fused}
    # dense normalized: A=1.0, B=0.0. bm25 normalized: B=1.0, A=0.0.
    # combined at 0.5/0.5: both land at exactly 0.5 -- a genuine tie,
    # which raw unnormalized scores would NOT have produced (BM25's 40
    # vs 2 would have swamped dense's signal entirely).
    assert scores["A"] == pytest.approx(0.5)
    assert scores["B"] == pytest.approx(0.5)


def test_weighted_fusion_all_identical_scores_treated_as_tied_not_div_by_zero():
    dense = [RetrievedChunk("A", 0.5), RetrievedChunk("B", 0.5)]
    fused = WeightedFusion(weights={"dense": 1.0}).fuse({"dense": dense})
    scores = {c.chunk_id: c.score for c in fused}
    assert scores["A"] == scores["B"] == pytest.approx(1.0)
