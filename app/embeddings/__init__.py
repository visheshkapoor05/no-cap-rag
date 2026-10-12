"""The clerk writing a "topic scent" tag on each card. See ../../ANALOGY.md."""
from app.embeddings.cache import DEFAULT_CACHE_PATH, EmbeddingCache
from app.embeddings.gemini import EMBEDDING_DIM, MODEL_ID, GeminiEmbeddingProvider
from app.embeddings.provider import EmbeddingProvider

__all__ = [
    "EmbeddingCache",
    "DEFAULT_CACHE_PATH",
    "EmbeddingProvider",
    "GeminiEmbeddingProvider",
    "MODEL_ID",
    "EMBEDDING_DIM",
]
