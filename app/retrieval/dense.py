"""T-M3.8: dense retrieval over Milvus's FLAT index (D-006). Embeds the
query with RETRIEVAL_QUERY task_type (never RETRIEVAL_DOCUMENT -- see
app/embeddings/provider.py's docstring for why that distinction is load
-bearing), then runs an exact cosine search.

Milvus's COSINE metric returns `distance` as the actual similarity score
(higher = more similar, verified directly against a live search rather
than assumed -- COSINE is not L2, where lower would mean closer) and
already returns hits sorted best-first."""
from __future__ import annotations

from app.core.config import get_settings
from app.embeddings.provider import EmbeddingProvider
from app.retrieval.milvus_client import get_client
from app.retrieval.strategy import RetrievedChunk


class DenseRetriever:
    def __init__(self, embedding_provider: EmbeddingProvider) -> None:
        self._embeddings = embedding_provider

    def retrieve(self, query: str, k: int) -> list[RetrievedChunk]:
        query_vector = self._embeddings.embed_query(query)
        client = get_client()
        collection = get_settings().milvus.collection

        results = client.search(
            collection_name=collection,
            data=[query_vector],
            limit=k,
            output_fields=["chunk_id"],
        )
        return [
            RetrievedChunk(chunk_id=hit["entity"]["chunk_id"], score=hit["distance"])
            for hit in results[0]
        ]
