"""T-M3.6: proves the collection actually gets created with the right
schema and a real FLAT index against a live Milvus, not just that the
code runs without raising. Uses the MILVUS_COLLECTION_test collection
(conftest.py), never the dev collection."""
from pymilvus import DataType

from app.core.config import get_settings
from app.retrieval import (
    CHUNK_ID_MAX_LEN,
    DOCUMENT_ID_MAX_LEN,
    EMBEDDING_DIM,
    close_client,
    ensure_collection,
    get_client,
)


def _drop_test_collection():
    client = get_client()
    name = get_settings().milvus.collection
    if client.has_collection(collection_name=name):
        client.drop_collection(collection_name=name)


def setup_function():
    _drop_test_collection()


def teardown_function():
    _drop_test_collection()
    close_client()


def test_ensure_collection_creates_it_when_missing():
    assert ensure_collection() is True

    client = get_client()
    assert client.has_collection(collection_name=get_settings().milvus.collection)


def test_ensure_collection_is_idempotent():
    assert ensure_collection() is True
    assert ensure_collection() is False  # already exists, no-op second time


def test_schema_has_the_expected_fields_and_dim():
    ensure_collection()
    client = get_client()
    info = client.describe_collection(collection_name=get_settings().milvus.collection)

    fields = {f["name"]: f for f in info["fields"]}
    assert set(fields) == {"chunk_id", "document_id", "embedding"}

    assert fields["chunk_id"]["type"] == DataType.VARCHAR
    assert fields["chunk_id"]["is_primary"] is True
    assert fields["chunk_id"]["params"]["max_length"] == CHUNK_ID_MAX_LEN

    assert fields["document_id"]["type"] == DataType.VARCHAR
    assert fields["document_id"]["params"]["max_length"] == DOCUMENT_ID_MAX_LEN

    assert fields["embedding"]["type"] == DataType.FLOAT_VECTOR
    assert fields["embedding"]["params"]["dim"] == EMBEDDING_DIM


def test_index_is_flat_not_ann():
    """D-006: exact search, not HNSW/IVF, so M3/M4 recall numbers are
    attributable to retrieval logic, not an ANN approximation error."""
    ensure_collection()
    client = get_client()
    indexes = client.list_indexes(collection_name=get_settings().milvus.collection)
    assert "embedding" in indexes

    index_info = client.describe_index(
        collection_name=get_settings().milvus.collection, index_name="embedding"
    )
    assert index_info["index_type"] == "FLAT"
    assert index_info["metric_type"] == "COSINE"


def test_get_client_returns_the_same_instance():
    """Singleton, same pattern as get_pool()/get_settings() -- opened once,
    not reconnected per call."""
    assert get_client() is get_client()


def test_insert_and_search_round_trip():
    """The actual point of all of the above: a real vector goes in, a real
    search against it comes back with the right chunk_id. Proves the
    schema and FLAT index are usable, not just declared."""
    ensure_collection()
    client = get_client()
    name = get_settings().milvus.collection

    vector = [0.1] * EMBEDDING_DIM
    client.insert(collection_name=name, data=[{
        "chunk_id": "11111111-1111-1111-1111-111111111111",
        "document_id": "22222222-2222-2222-2222-222222222222",
        "embedding": vector,
    }])
    client.flush(collection_name=name)

    results = client.search(
        collection_name=name,
        data=[vector],
        limit=1,
        output_fields=["chunk_id", "document_id"],
    )
    assert len(results[0]) == 1
    assert results[0][0]["entity"]["chunk_id"] == "11111111-1111-1111-1111-111111111111"
