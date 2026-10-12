"""T-M3.8: DenseRetriever's own logic -- does it call embed_query (never
embed_document) and wire Milvus search correctly -- tested against the
real Milvus test collection with a stub embedding provider. Gemini's
actual embedding quality is already verified for real in
test_gemini_embeddings.py; re-paying for API calls here would only prove
the same thing twice."""
from app.core.config import get_settings
from app.retrieval import DenseRetriever, ensure_collection, get_client


class StubEmbeddingProvider:
    """Deterministic, zero-cost stand-in. Records which method was called
    so the task_type distinction (T-M3.7) is provably respected here too."""

    model_id = "stub"
    dim = 768

    def __init__(self):
        self.calls: list[str] = []

    def embed_query(self, text: str) -> list[float]:
        self.calls.append(f"query:{text}")
        return [1.0, 0.0] + [0.0] * 766

    def embed_document(self, text: str) -> list[float]:
        self.calls.append(f"document:{text}")
        return [0.0, 1.0] + [0.0] * 766


def _reset_collection():
    client = get_client()
    name = get_settings().milvus.collection
    if client.has_collection(collection_name=name):
        client.drop_collection(collection_name=name)
    ensure_collection(client)
    return client, name


def test_retrieve_calls_embed_query_not_embed_document():
    client, name = _reset_collection()
    client.insert(collection_name=name, data=[{
        "chunk_id": "1" * 36, "document_id": "d" * 36, "embedding": [1.0, 0.0] + [0.0] * 766,
    }])
    client.flush(collection_name=name)

    stub = StubEmbeddingProvider()
    DenseRetriever(stub).retrieve("a question", k=1)

    assert stub.calls == ["query:a question"]


def test_retrieve_returns_best_match_first_with_real_milvus_search():
    client, name = _reset_collection()
    client.insert(collection_name=name, data=[
        {"chunk_id": "A" * 36, "document_id": "d" * 36, "embedding": [1.0, 0.0] + [0.0] * 766},
        {"chunk_id": "B" * 36, "document_id": "d" * 36, "embedding": [0.7, 0.7] + [0.0] * 766},
        {"chunk_id": "C" * 36, "document_id": "d" * 36, "embedding": [0.0, 1.0] + [0.0] * 766},
    ])
    client.flush(collection_name=name)

    # stub's embed_query always returns [1,0,...] -- closest to A, then B, then C
    results = DenseRetriever(StubEmbeddingProvider()).retrieve("anything", k=3)

    assert [r.chunk_id for r in results] == ["A" * 36, "B" * 36, "C" * 36]
    assert results[0].score > results[1].score > results[2].score


def test_retrieve_respects_k():
    client, name = _reset_collection()
    client.insert(collection_name=name, data=[
        {"chunk_id": f"{i:036d}", "document_id": "d" * 36, "embedding": [1.0, 0.0] + [0.0] * 766}
        for i in range(5)
    ])
    client.flush(collection_name=name)

    results = DenseRetriever(StubEmbeddingProvider()).retrieve("q", k=2)
    assert len(results) == 2
