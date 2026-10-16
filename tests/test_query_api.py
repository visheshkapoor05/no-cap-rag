"""T-M4.12: POST /query and POST /evaluate end to end -- real FastAPI app,
real Postgres, real Milvus, real Gemini, real reranker. Reuses the
indexed_test_corpus fixture (T-M3.11) so the real retrieval layer
underneath /query is already populated."""


def test_query_returns_a_grounded_answer_with_citations(client, indexed_test_corpus):
    resp = client.post("/query", json={
        "question": "What percentage employee discount applies to personal purchases?",
        "use_reranker": True,
        "rerank_k": 3,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["answerable"] is True
    assert body["claims"]
    assert body["trace_id"]
    for claim in body["claims"]:
        assert claim["citations"]
        for citation in claim["citations"]:
            assert citation["chunk_id"]
            assert citation["document_title"]
    assert "retrieval_ms" in body["timings_ms"]
    assert "rerank_ms" in body["timings_ms"]
    assert "generate_ms" in body["timings_ms"]
    assert "total_ms" in body["timings_ms"]


def test_query_without_reranker_skips_the_rerank_stage(client, indexed_test_corpus):
    resp = client.post("/query", json={
        "question": "What percentage employee discount applies to personal purchases?",
        "use_reranker": False,
        "rerank_k": 3,
    })
    assert resp.status_code == 200
    assert "rerank_ms" not in resp.json()["timings_ms"]


def test_query_abstains_on_an_unanswerable_question(client, indexed_test_corpus):
    resp = client.post("/query", json={
        "question": "What is the policy on cryptocurrency payments?",
        "k": 5,
        "rerank_k": 3,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["answerable"] is False
    assert body["claims"] == []


def test_evaluate_returns_both_the_answer_and_a_judge_score(client, indexed_test_corpus):
    resp = client.post("/evaluate", json={
        "question": "What percentage employee discount applies to personal purchases?",
        "expected_answer": "Employees receive a 20% discount on personal purchases.",
        "rerank_k": 3,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["query"]["answerable"] is True
    judge = body["judge"]
    assert 0.0 <= judge["faithfulness"] <= 1.0
    assert 0.0 <= judge["correctness"] <= 1.0
    assert 0.0 <= judge["citation_support_rate"] <= 1.0
    assert judge["reasoning"]
