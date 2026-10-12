"""The two research assistants and the manager who merges their shortlists
— dense retrieval, BM25, and RRF fusion. See ../../ANALOGY.md."""
from app.retrieval.milvus_client import (
    CHUNK_ID_MAX_LEN,
    COLLECTION_NAME,
    DOCUMENT_ID_MAX_LEN,
    EMBEDDING_DIM,
    close_client,
    ensure_collection,
    get_client,
)

__all__ = [
    "get_client",
    "close_client",
    "ensure_collection",
    "COLLECTION_NAME",
    "EMBEDDING_DIM",
    "CHUNK_ID_MAX_LEN",
    "DOCUMENT_ID_MAX_LEN",
]
