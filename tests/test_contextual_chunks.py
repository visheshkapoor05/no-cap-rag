"""T-M2.5: contextual prefixes and the full chunk schema, tested against
real corpus text and a real Postgres chunks table."""
from pathlib import Path

from app.chunking import (
    build_contextual_prefix,
    chunk_with_context,
    delete_chunks_for_document,
    get_chunks_for_document,
    insert_chunks,
)
from app.documents import insert_document

CLEAN_DIR = Path(__file__).resolve().parent.parent / "corpus" / "synthetic" / "clean"


def _read(name: str) -> str:
    return (CLEAN_DIR / name).read_text(encoding="utf-8")


def test_prefix_with_version_and_section():
    prefix = build_contextual_prefix(title="Returns Policy", version="3.0", section_path="3.2 Discounted Items")
    assert prefix == "Returns Policy v3.0 → §3.2 Discounted Items: "


def test_prefix_with_no_version():
    """Postmortems, ADRs, and public pages have no version -- must not
    render as the literal string "None"."""
    prefix = build_contextual_prefix(title="POS Outage Postmortem", version=None, section_path="Impact")
    assert prefix == "POS Outage Postmortem → §Impact: "
    assert "None" not in prefix


def test_prefix_with_no_section_path():
    """The preamble chunk (before any heading) has an empty section_path."""
    prefix = build_contextual_prefix(title="Shift Policy", version="1.0", section_path="")
    assert prefix == "Shift Policy v1.0: "


def test_chunk_with_context_makes_the_severed_sentence_self_contained():
    """The actual T-M2.3 example, now with a prefix: the "not a blanket
    denial" chunk should be findable and self-contained by its label
    alone, without reading the text to know what document/section it's
    from."""
    chunks = chunk_with_context(_read("price-match-policy.md"), title="Price Match Policy", version="1.0")

    match = next(c for c in chunks if "Repeated or Suspicious Requests" in c.section_path)
    assert match.contextual_prefix == "Price Match Policy v1.0 → §4. Repeated or Suspicious Requests: "
    assert "not a blanket denial" in " ".join(match.text.split())


def test_insert_and_retrieve_chunks_round_trip(clean_documents):
    document = insert_document(
        clean_documents,
        type="customer_policy",
        title="Price Match Policy",
        content_hash="hash-for-chunk-test",
        version="1.0",
    )
    chunks = chunk_with_context(_read("price-match-policy.md"), title="Price Match Policy", version="1.0")

    inserted = insert_chunks(clean_documents, document.id, chunks)
    fetched = get_chunks_for_document(clean_documents, document.id)

    assert len(inserted) == len(chunks) == 8  # 7 headings + 1 unmergeable preamble, per T-M2.4's real numbers
    assert len(fetched) == len(inserted)
    assert {c.id for c in inserted} == {c.id for c in fetched}
    # embedding_id/sparse_terms reserved for M3, not populated yet
    assert all(c.embedding_id is None and c.sparse_terms is None for c in fetched)


def test_deleting_a_documents_chunks_removes_only_that_documents_chunks(clean_documents):
    doc_a = insert_document(clean_documents, type="staff", title="A", content_hash="hash-a")
    doc_b = insert_document(clean_documents, type="staff", title="B", content_hash="hash-b")
    chunks = chunk_with_context(_read("shift-policy.md"), title="Shift Policy", version="1.0")

    insert_chunks(clean_documents, doc_a.id, chunks)
    insert_chunks(clean_documents, doc_b.id, chunks)

    delete_chunks_for_document(clean_documents, doc_a.id)

    assert get_chunks_for_document(clean_documents, doc_a.id) == []
    assert len(get_chunks_for_document(clean_documents, doc_b.id)) == len(chunks)
