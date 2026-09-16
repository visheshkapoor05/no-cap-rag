"""
The clerk's actual decision: given a fetched document, has this exact
content already been filed? File it only if not. This is the one function
T-M1.8's API endpoint and T-M1.9's CLI both call — neither re-implements
this decision on its own. See ../../ANALOGY.md.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID

from psycopg_pool import ConnectionPool

from app.documents.hashing import compute_content_hash
from app.documents.models import Document
from app.documents.registry import find_by_content_hash, insert_document
from app.ingestion.source import FetchStatus, RawDocument


@dataclass(frozen=True)
class IngestResult:
    document: Document
    created: bool  # True: a new row was inserted. False: identical content already existed.


def ingest_document(
    pool: ConnectionPool,
    raw: RawDocument,
    *,
    type: str,
    title: str,
    source_url: str | None = None,
    version: str | None = None,
    effective_date: date | None = None,
    supersedes: UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> IngestResult:
    """
    Hashes `raw.text`, looks for a document with that hash, and only
    inserts a new row if none exists — the actual idempotency behavior.
    Requires `raw.status is FetchStatus.OK`; deciding what to do with a
    blocked/failed fetch is the caller's job (T-M1.8/T-M1.9), not this
    function's — it only ever makes the "already filed or not" call.
    """
    if raw.status is not FetchStatus.OK or raw.text is None:
        raise ValueError(
            f"ingest_document requires a successfully fetched document "
            f"(status=OK, text present); got status={raw.status!r} for {raw.source_ref!r}"
        )

    content_hash = compute_content_hash(raw.text)

    existing = find_by_content_hash(pool, content_hash)
    if existing is not None:
        return IngestResult(document=existing, created=False)

    inserted = insert_document(
        pool,
        type=type,
        title=title,
        content_hash=content_hash,
        source_url=source_url,
        version=version,
        effective_date=effective_date,
        supersedes=supersedes,
        metadata=metadata,
    )
    return IngestResult(document=inserted, created=True)
