"""
T-M3.6: the scent-sorted filing cabinet's connection and shelving plan —
opened once in the app's lifespan (never per-request, the same rule
`app/core/db.py`'s Postgres pool already follows), with a collection
schema and FLAT index (D-006) created idempotently on first use.

Milvus itself stays schema-source-of-truth-free on purpose: it holds only
what vector search needs (the embedding, plus the two UUIDs needed to
join back to Postgres), never chunk text or section_path. Postgres's
`chunks` table remains the one place that's actually read for content —
the same "don't duplicate the source of truth" rule T-M1.6 already applies
to `documents` not storing raw extracted text.
"""
from __future__ import annotations

from pymilvus import DataType, MilvusClient

from app.core.config import get_settings

# Verified against ai.google.dev/gemini-api/docs/embeddings (fetched
# directly, not recalled from memory, per D-003's "verify current Gemini
# model IDs" instruction): gemini-embedding-001 is the text-only model
# this text-only corpus calls for; it supports flexible output
# dimensionality (Matryoshka) at 128-3072, with 768/1536/3072 as Google's
# recommended sizes. 768 chosen over the 3072 native size to keep FLAT
# search and storage cheap at this corpus's scale (D-006's whole point is
# that FLAT stays fast enough to not need an ANN tradeoff) — revisit if
# T-M3.12's recall numbers suggest dimensionality, not chunking or fusion,
# is the bottleneck.
EMBEDDING_DIM = 768

COLLECTION_NAME_DEFAULT = "chunk_embeddings"
CHUNK_ID_MAX_LEN = 36   # a UUID4 string, matches Postgres chunks.id
DOCUMENT_ID_MAX_LEN = 36  # matches Postgres documents.id

# Re-exported for callers that want the configured name without importing
# settings themselves; ensure_collection() always reads the live setting.
COLLECTION_NAME = COLLECTION_NAME_DEFAULT

_client: MilvusClient | None = None


def get_client() -> MilvusClient:
    """Opens the connection once, lazily, and hands out the same one after
    that — the same singleton pattern as `get_pool()` / `get_settings()`."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = MilvusClient(uri=settings.milvus.uri)
    return _client


def close_client() -> None:
    """Closes the connection at shutdown; mainly here so tests can reset
    state between runs against different settings — same role as
    `close_pool()`."""
    global _client
    if _client is not None:
        _client.close()
        _client = None


def _build_schema() -> "MilvusClient.create_schema":
    schema = MilvusClient.create_schema(auto_id=False, enable_dynamic_field=False)
    schema.add_field(
        field_name="chunk_id", datatype=DataType.VARCHAR,
        is_primary=True, max_length=CHUNK_ID_MAX_LEN,
    )
    schema.add_field(
        field_name="document_id", datatype=DataType.VARCHAR,
        max_length=DOCUMENT_ID_MAX_LEN,
    )
    schema.add_field(
        field_name="embedding", datatype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM,
    )
    return schema


def ensure_collection(client: MilvusClient | None = None) -> bool:
    """Creates the collection with a FLAT index (D-006: exact search, so
    any recall shortfall in M3/M4 is attributable to chunking/fusion
    logic, not an ANN index's approximation error) if it doesn't already
    exist. Running this twice is a no-op the second time — the same
    idempotency principle `migrate()` applies to the Postgres schema.
    Returns True if the collection was actually created this call."""
    client = client or get_client()
    settings = get_settings()
    name = settings.milvus.collection

    if client.has_collection(collection_name=name):
        return False

    index_params = client.prepare_index_params()
    index_params.add_index(
        field_name="embedding",
        index_type="FLAT",
        metric_type="COSINE",
    )
    client.create_collection(
        collection_name=name,
        schema=_build_schema(),
        index_params=index_params,
    )
    return True
