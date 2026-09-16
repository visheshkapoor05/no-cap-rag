"""
The archive room: the permanent, versioned record of every ingested
document — what chunks/embeddings (M2/M3) get derived from, and re-derived
from again whenever the chunking or embedding strategy changes. See
../../ANALOGY.md.
"""
from app.documents.hashing import compute_content_hash
from app.documents.ingest import IngestResult, ingest_document
from app.documents.models import Document
from app.documents.registry import (
    find_by_content_hash,
    get_document,
    insert_document,
    update_supersedes,
)

__all__ = [
    "Document",
    "insert_document",
    "get_document",
    "find_by_content_hash",
    "update_supersedes",
    "compute_content_hash",
    "ingest_document",
    "IngestResult",
]
