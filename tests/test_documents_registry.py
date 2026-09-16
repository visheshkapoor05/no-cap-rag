"""The archive clerk, tested against a real Postgres (see conftest.py's
pg_pool fixture) — insert, look up by id, look up by content_hash, and the
schema-level constraints T-M1.7's idempotency logic will rely on."""
from uuid import uuid4

import psycopg
import pytest

from app.documents.registry import find_by_content_hash, get_document, insert_document


def test_insert_then_get_round_trips(clean_documents):
    inserted = insert_document(
        clean_documents,
        type="customer_policy",
        title="Returns Policy",
        content_hash="hash-returns-v3",
        version="3.0",
        source_url=None,
        metadata={"policy_id": "RET-POL-001"},
    )

    fetched = get_document(clean_documents, inserted.id)

    assert fetched is not None
    assert fetched.title == "Returns Policy"
    assert fetched.version == "3.0"
    assert fetched.content_hash == "hash-returns-v3"
    assert fetched.metadata == {"policy_id": "RET-POL-001"}
    assert fetched.fetched_at is not None  # DB default populated it


def test_find_by_content_hash(clean_documents):
    inserted = insert_document(
        clean_documents, type="sop", title="Cash Handling SOP", content_hash="hash-cash-sop"
    )

    found = find_by_content_hash(clean_documents, "hash-cash-sop")
    missing = find_by_content_hash(clean_documents, "no-such-hash")

    assert found is not None
    assert found.id == inserted.id
    assert missing is None


def test_duplicate_content_hash_is_rejected_by_the_schema(clean_documents):
    insert_document(clean_documents, type="sop", title="A", content_hash="dup-hash")

    with pytest.raises(psycopg.errors.UniqueViolation):
        insert_document(clean_documents, type="sop", title="B", content_hash="dup-hash")


def test_supersedes_references_another_document(clean_documents):
    old = insert_document(
        clean_documents, type="customer_policy", title="Returns v2", content_hash="hash-v2", version="2.0"
    )
    new = insert_document(
        clean_documents,
        type="customer_policy",
        title="Returns v3",
        content_hash="hash-v3",
        version="3.0",
        supersedes=old.id,
    )

    fetched = get_document(clean_documents, new.id)

    assert fetched.supersedes == old.id


def test_get_document_returns_none_for_unknown_id(clean_documents):
    assert get_document(clean_documents, uuid4()) is None
