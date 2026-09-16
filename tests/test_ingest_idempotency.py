"""T-M1.7: proves ingestion is idempotent, and specifically that it's
idempotent on *text*, not on raw bytes — the actual scenario a PDF
re-exported at a different time creates."""
from pathlib import Path

import pytest

from app.documents import compute_content_hash, ingest_document
from app.ingestion import FetchStatus, FileSource, RawDocument

CORPUS = Path(__file__).resolve().parent.parent / "corpus"


def test_compute_content_hash_is_deterministic_and_content_sensitive():
    assert compute_content_hash("same text") == compute_content_hash("same text")
    assert compute_content_hash("text A") != compute_content_hash("text B")


def test_ingesting_the_same_raw_document_twice_does_not_duplicate(clean_documents):
    raw = RawDocument(
        source_ref="corpus/synthetic/clean/shift-policy.md",
        content_type="text/markdown",
        raw_bytes=b"irrelevant to this test",
        text="Shift Policy. Schedules are posted 14 days in advance.",
        status=FetchStatus.OK,
    )

    first = ingest_document(clean_documents, raw, type="staff", title="Shift Policy")
    second = ingest_document(clean_documents, raw, type="staff", title="Shift Policy")

    assert first.created is True
    assert second.created is False
    assert first.document.id == second.document.id

    with clean_documents.connection() as conn:
        count = conn.execute("SELECT COUNT(*) AS n FROM documents").fetchone()["n"]
    assert count == 1


def test_different_bytes_same_text_is_still_recognized_as_a_duplicate(clean_documents):
    """The actual point of hashing text instead of bytes: simulates a PDF
    re-exported at a different time (different bytes, e.g. a new internal
    timestamp) whose visible content did not change."""
    raw_first_export = RawDocument(
        source_ref="corpus/synthetic/mixed/warranty-policy-v1.0.pdf",
        content_type="application/pdf",
        raw_bytes=b"%PDF-1.4 first export, timestamp A, object order 1-2-3",
        text="Warranty Policy. Coverage is 12 months from the date of purchase.",
        status=FetchStatus.OK,
    )
    raw_second_export = RawDocument(
        source_ref="corpus/synthetic/mixed/warranty-policy-v1.0.pdf",
        content_type="application/pdf",
        raw_bytes=b"%PDF-1.4 re-exported later, timestamp B, object order 3-1-2, recompressed",
        text="Warranty Policy. Coverage is 12 months from the date of purchase.",
        status=FetchStatus.OK,
    )
    assert raw_first_export.raw_bytes != raw_second_export.raw_bytes  # premise actually holds

    first = ingest_document(clean_documents, raw_first_export, type="customer_policy", title="Warranty Policy")
    second = ingest_document(clean_documents, raw_second_export, type="customer_policy", title="Warranty Policy")

    assert first.created is True
    assert second.created is False
    assert first.document.id == second.document.id


def test_ingest_rejects_a_non_ok_raw_document(clean_documents):
    blocked = RawDocument(
        source_ref="https://example.com/blocked",
        content_type=None,
        raw_bytes=None,
        text=None,
        status=FetchStatus.BLOCKED,
        detail="interstitial",
    )

    with pytest.raises(ValueError):
        ingest_document(clean_documents, blocked, type="customer_policy", title="whatever")


def test_ingest_against_a_real_corpus_file(clean_documents):
    raw = FileSource().fetch(str(CORPUS / "synthetic" / "clean" / "shift-policy.md"))

    result = ingest_document(clean_documents, raw, type="staff", title="Shift Policy", version="1.0")

    assert result.created is True
    assert result.document.content_hash == compute_content_hash(raw.text)
    assert result.document.source_url is None  # file-sourced, not a public URL
