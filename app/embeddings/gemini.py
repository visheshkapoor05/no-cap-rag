"""
T-M3.7: the Gemini adapter behind `EmbeddingProvider`.

Model ID and dimension verified directly against
ai.google.dev/gemini-api/docs/embeddings (fetched live, not recalled from
memory, per D-003's "verify current Gemini model IDs" instruction):
gemini-embedding-001 is the text-only model (this corpus is text-only);
it supports flexible (Matryoshka) output sizing from 128-3072, with
768/1536/3072 as Google's recommended sizes. 768 chosen to keep Milvus's
FLAT index (D-006) and storage cheap at this corpus's scale -- the same
constant `app/retrieval/milvus_client.py` imports from here, so the
Postgres-adjacent vector store and the provider can never silently drift
out of dimensional agreement.
"""
from __future__ import annotations

from google import genai
from google.genai import types

from app.core.config import get_settings
from app.embeddings.cache import EmbeddingCache

MODEL_ID = "gemini-embedding-001"
EMBEDDING_DIM = 768


class GeminiEmbeddingProvider:
    """Every call goes through `EmbeddingCache` first (T-M2.6) -- the real,
    paid API is only ever hit on a genuine cache miss."""

    model_id = MODEL_ID
    dim = EMBEDDING_DIM

    def __init__(self, cache: EmbeddingCache | None = None) -> None:
        settings = get_settings()
        self._client = genai.Client(api_key=settings.gemini.api_key.get_secret_value())
        # NOT `cache or EmbeddingCache()` -- EmbeddingCache defines
        # __len__, so a freshly-created, still-empty cache is falsy, and
        # `or` would silently fall through to the shared default cache
        # even when a real cache was explicitly passed in. Caught by this
        # exact failure mode in tests/test_gemini_embeddings.py.
        self._cache = cache if cache is not None else EmbeddingCache()

    def _call_gemini(self, text: str, task_type: str) -> list[float]:
        result = self._client.models.embed_content(
            model=MODEL_ID,
            contents=text,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=EMBEDDING_DIM,
            ),
        )
        return list(result.embeddings[0].values)

    def embed_document(self, text: str) -> list[float]:
        # Cache key folds task_type into model_id -- a document embedding
        # and a query embedding of the identical string are NOT the same
        # vector (see provider.py's docstring), so they must not collide
        # in the cache either.
        return self._cache.get_or_embed(
            text, f"{MODEL_ID}:document",
            lambda t: self._call_gemini(t, "RETRIEVAL_DOCUMENT"),
        )

    def embed_query(self, text: str) -> list[float]:
        return self._cache.get_or_embed(
            text, f"{MODEL_ID}:query",
            lambda t: self._call_gemini(t, "RETRIEVAL_QUERY"),
        )


_provider: GeminiEmbeddingProvider | None = None


def get_embedding_provider() -> GeminiEmbeddingProvider:
    """Built once, lazily — reuses one genai.Client and one EmbeddingCache
    connection across every request, same singleton pattern as
    get_pool()/get_client()."""
    global _provider
    if _provider is None:
        _provider = GeminiEmbeddingProvider()
    return _provider


def close_embedding_provider() -> None:
    global _provider
    _provider = None
