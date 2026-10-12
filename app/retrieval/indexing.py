"""Supporting plumbing for T-M3.8/T-M3.11, not its own numbered task:
something has to actually embed every real chunk and upsert it into
Milvus before DenseRetriever has anything to search. Embeds
`contextual_prefix + text` (the same self-contained string T-M2.6's cache
proof used), not raw text alone -- a chunk's text without its section
breadcrumb loses exactly the context T-M2.5 built the prefix to supply."""
from __future__ import annotations

from psycopg_pool import ConnectionPool

from app.chunking import get_all_chunks
from app.embeddings.provider import EmbeddingProvider
from app.retrieval.milvus_client import get_client


def index_all_chunks(
    pool: ConnectionPool, embedding_provider: EmbeddingProvider, client=None
) -> int:
    """Idempotent in the sense that matters: re-running it after a chunk's
    embedding is already cached (T-M2.6) makes zero new API calls, only a
    Milvus upsert. Returns the number of chunks indexed."""
    client = client or get_client()
    from app.core.config import get_settings

    collection = get_settings().milvus.collection

    chunks = get_all_chunks(pool)
    if not chunks:
        return 0

    rows = []
    for chunk in chunks:
        text = chunk.contextual_prefix + chunk.text
        vector = embedding_provider.embed_document(text)
        rows.append({
            "chunk_id": str(chunk.id),
            "document_id": str(chunk.document_id),
            "embedding": vector,
        })

    client.upsert(collection_name=collection, data=rows)
    client.flush(collection_name=collection)
    return len(rows)
