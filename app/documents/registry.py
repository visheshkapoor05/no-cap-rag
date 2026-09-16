"""
The archive clerk: writes a new document card and looks existing ones up.
T-M1.7's idempotency check and T-M1.8's ingest endpoint are both built on
top of just these three operations — nothing here decides *whether* to
insert, only *how*. See ../../ANALOGY.md.
"""
from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from app.documents.models import Document

_SELECT_COLUMNS = (
    "id, source_url, type, title, version, effective_date, "
    "fetched_at, content_hash, supersedes, metadata"
)


def _row_to_document(row: dict[str, Any]) -> Document:
    return Document(
        id=row["id"],
        source_url=row["source_url"],
        type=row["type"],
        title=row["title"],
        version=row["version"],
        effective_date=row["effective_date"],
        fetched_at=row["fetched_at"],
        content_hash=row["content_hash"],
        supersedes=row["supersedes"],
        metadata=row["metadata"],
    )


def insert_document(
    pool: ConnectionPool,
    *,
    type: str,
    title: str,
    content_hash: str,
    source_url: str | None = None,
    version: str | None = None,
    effective_date: date | None = None,
    supersedes: UUID | None = None,
    metadata: dict[str, Any] | None = None,
) -> Document:
    """
    Inserts one row and returns it. Does **not** check for an existing
    `content_hash` first — that check-then-skip decision is T-M1.7's job,
    built on `find_by_content_hash` below. Calling this twice with the same
    `content_hash` raises (the unique index in migrations/0001), it does
    not silently upsert.
    """
    with pool.connection() as conn:
        row = conn.execute(
            f"""
            INSERT INTO documents
                (source_url, type, title, version, effective_date, content_hash, supersedes, metadata)
            VALUES
                (%(source_url)s, %(type)s, %(title)s, %(version)s, %(effective_date)s,
                 %(content_hash)s, %(supersedes)s, %(metadata)s)
            RETURNING {_SELECT_COLUMNS}
            """,
            {
                "source_url": source_url,
                "type": type,
                "title": title,
                "version": version,
                "effective_date": effective_date,
                "content_hash": content_hash,
                "supersedes": supersedes,
                "metadata": Jsonb(metadata or {}),
            },
        ).fetchone()
    return _row_to_document(row)


def get_document(pool: ConnectionPool, document_id: UUID) -> Document | None:
    with pool.connection() as conn:
        row = conn.execute(
            f"SELECT {_SELECT_COLUMNS} FROM documents WHERE id = %s",
            (document_id,),
        ).fetchone()
    return _row_to_document(row) if row else None


def update_supersedes(pool: ConnectionPool, document_id: UUID, supersedes: UUID) -> None:
    """
    Points an already-inserted document at the older one it replaces.
    Exists as a separate call, not an `insert_document` parameter that's
    always available, because the CLI (T-M1.9) resolves version chains in
    two passes: ingest everything first (so every document has a real id),
    then wire up `supersedes` once the id being pointed at is actually
    known — a document can't reference another document's id before that
    id exists.
    """
    with pool.connection() as conn:
        conn.execute(
            "UPDATE documents SET supersedes = %s WHERE id = %s",
            (supersedes, document_id),
        )


def find_by_content_hash(pool: ConnectionPool, content_hash: str) -> Document | None:
    """The lookup T-M1.7's idempotency check is built on: if this returns a
    row, ingestion should skip inserting a duplicate rather than call
    `insert_document` and let the unique constraint reject it."""
    with pool.connection() as conn:
        row = conn.execute(
            f"SELECT {_SELECT_COLUMNS} FROM documents WHERE content_hash = %s",
            (content_hash,),
        ).fetchone()
    return _row_to_document(row) if row else None
