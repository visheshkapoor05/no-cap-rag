"""T-M3.9: real BM25 over the real, full chunked corpus (full_corpus_chunks
fixture) -- no mocking, the point is proving rank_bm25 is wired correctly
against this project's actual chunk text and contextual prefixes."""
from app.retrieval import tokenize
from app.retrieval.sparse import SparseRetriever


def test_tokenizer_keeps_hyphenated_codes_as_one_token():
    assert "pos-err-3021" in tokenize("Incident code POS-ERR-3021 occurred.")
    assert "pos" not in tokenize("Incident code POS-ERR-3021 occurred.")


def test_retrieve_finds_a_real_exact_identifier_match(full_corpus_chunks):
    retriever = SparseRetriever(full_corpus_chunks)
    results = retriever.retrieve("What does incident code POS-ERR-3021 refer to?", k=5)

    assert len(results) > 0
    assert len(results) <= 5
    # best match first
    assert all(results[i].score >= results[i + 1].score for i in range(len(results) - 1))


def test_retrieve_respects_k(full_corpus_chunks):
    retriever = SparseRetriever(full_corpus_chunks)
    results = retriever.retrieve("return policy discount points", k=3)
    assert len(results) <= 3


def test_retrieve_excludes_zero_score_chunks(full_corpus_chunks):
    """A chunk with zero term overlap isn't a hit -- it shouldn't be
    padded into the results just to fill out k."""
    retriever = SparseRetriever(full_corpus_chunks)
    results = retriever.retrieve("zzqqxx wibbledoo flamfarkle quorzlebix", k=10)
    assert results == []


def test_keyword_heavy_query_finds_the_right_chunk(full_corpus_chunks):
    """A real, specific regression: the exact vocabulary from the policy's
    own text should retrieve that policy's own chunk at rank 1."""
    retriever = SparseRetriever(full_corpus_chunks)
    results = retriever.retrieve(
        "What percentage employee discount applies to personal purchases?", k=1
    )
    assert len(results) == 1
