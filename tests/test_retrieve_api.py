"""T-M3.11: real end-to-end calls through the FastAPI app against the real
Postgres + Milvus + Gemini stack (`indexed_test_corpus` populates and
embeds the real test corpus into both) -- proving the whole
T-M3.8-T-M3.11 chain actually works wired together, not just each piece
in isolation."""


def test_dense_strategy_finds_a_real_relevant_chunk(client, indexed_test_corpus):
    resp = client.post("/retrieve", json={
        "query": "What percentage employee discount applies to personal purchases?",
        "k": 3,
        "strategy": "dense",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["strategy"] == "dense"
    assert len(body["results"]) > 0
    assert body["results"][0]["document_title"] == "Employee Discount Policy"
    assert "dense_ms" in body["timings_ms"]
    assert "bm25_ms" not in body["timings_ms"]  # strategy=dense shouldn't run BM25 at all
    assert "total_ms" in body["timings_ms"]


def test_bm25_strategy_does_not_call_dense_at_all(client, indexed_test_corpus):
    resp = client.post("/retrieve", json={
        "query": "What percentage employee discount applies to personal purchases?",
        "k": 3,
        "strategy": "bm25",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "bm25_ms" in body["timings_ms"]
    assert "dense_ms" not in body["timings_ms"]  # no wasted Gemini call for a pure-BM25 request


def test_hybrid_rrf_runs_both_and_fuses(client, indexed_test_corpus):
    resp = client.post("/retrieve", json={
        "query": "What does incident code POS-ERR-3021 refer to?",
        "k": 5,
        "strategy": "hybrid_rrf",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "dense_ms" in body["timings_ms"]
    assert "bm25_ms" in body["timings_ms"]
    assert "fusion_ms" in body["timings_ms"]
    assert len(body["results"]) > 0
    # best match first
    scores = [r["score"] for r in body["results"]]
    assert scores == sorted(scores, reverse=True)


def test_hybrid_weighted_requires_weights(client):
    resp = client.post("/retrieve", json={
        "query": "anything",
        "strategy": "hybrid_weighted",
    })
    assert resp.status_code == 422


def test_hybrid_weighted_with_explicit_weights(client, indexed_test_corpus):
    resp = client.post("/retrieve", json={
        "query": "What percentage employee discount applies to personal purchases?",
        "k": 3,
        "strategy": "hybrid_weighted",
        "weights": {"dense": 0.6, "bm25": 0.4},
    })
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["results"]) > 0


def test_results_include_resolved_chunk_content(client, indexed_test_corpus):
    resp = client.post("/retrieve", json={
        "query": "What percentage employee discount applies to personal purchases?",
        "k": 1,
        "strategy": "bm25",
    })
    result = resp.json()["results"][0]
    assert result["document_title"]
    assert result["section_path"]
    assert "20%" in result["text"] or "discount" in result["text"].lower()
    assert len(result["chunk_id"]) == 36  # a real UUID string
