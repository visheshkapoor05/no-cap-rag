"""The two research assistants and the manager who merges their shortlists
— dense retrieval, BM25, and RRF fusion. See ../../ANALOGY.md."""
from app.retrieval.dense import DenseRetriever
from app.retrieval.indexing import index_all_chunks
from app.retrieval.milvus_client import (
    CHUNK_ID_MAX_LEN,
    COLLECTION_NAME,
    DOCUMENT_ID_MAX_LEN,
    EMBEDDING_DIM,
    close_client,
    ensure_collection,
    get_client,
)
from app.retrieval.strategy import RetrievalStrategy, RetrievedChunk

__all__ = [
    "get_client",
    "close_client",
    "ensure_collection",
    "COLLECTION_NAME",
    "EMBEDDING_DIM",
    "CHUNK_ID_MAX_LEN",
    "DOCUMENT_ID_MAX_LEN",
    "RetrievalStrategy",
    "RetrievedChunk",
    "DenseRetriever",
    "index_all_chunks",
]
