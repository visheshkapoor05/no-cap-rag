"""
Files a document's chunks away in Postgres, and looks them back up. Mirrors
app/documents/registry.py's shape on purpose -- same kind of clerk, filing
a different kind of card. See ../../ANALOGY.md.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg_pool import ConnectionPool

from app.chunking.contextual import ContextualChunk
from app.chunking.models import ChunkRecord

_SELECT_COLUMNS = (
    "id, document_id, section_path, contextual_prefix, text, token_count, "
    "embedding_id, sparse_terms, created_at"
)


def _row_to_record(row: dict[str, Any]) -> ChunkRecord:
    return ChunkRecord(
        id=row["id"],
        document_id=row["document_id"],
        section_path=row["section_path"],
        contextual_prefix=row["contextual_prefix"],
        text=row["text"],
        token_count=row["token_count"],
        embedding_id=row["embedding_id"],
        sparse_terms=row["sparse_terms"],
        created_at=row["created_at"],
    )


def insert_chunks(
    pool: ConnectionPool, document_id: UUID, chunks: list[ContextualChunk]
) -> list[ChunkRecord]:
    """Inserts every chunk for one document in a single transaction — a
    document's chunks are only ever meaningful as a complete set, so a
    failure partway through shouldn't leave 6 of a document's 9 chunks
    filed and the rest silently missing."""
    if not chunks:
        return []

    inserted: list[ChunkRecord] = []
    with pool.connection() as conn:
        with conn.transaction():
            for chunk in chunks:
                row = conn.execute(
                    f"""
                    INSERT INTO chunks
                        (document_id, section_path, contextual_prefix, text, token_count)
                    VALUES
                        (%(document_id)s, %(section_path)s, %(contextual_prefix)s, %(text)s, %(token_count)s)
                    RETURNING {_SELECT_COLUMNS}
                    """,
                    {
                        "document_id": document_id,
                        "section_path": chunk.section_path,
                        "contextual_prefix": chunk.contextual_prefix,
                        "text": chunk.text,
                        "token_count": chunk.token_count,
                    },
                ).fetchone()
                inserted.append(_row_to_record(row))
    return inserted


def get_chunks_for_document(pool: ConnectionPool, document_id: UUID) -> list[ChunkRecord]:
    with pool.connection() as conn:
        rows = conn.execute(
            f"SELECT {_SELECT_COLUMNS} FROM chunks WHERE document_id = %s ORDER BY created_at",
            (document_id,),
        ).fetchall()
    return [_row_to_record(row) for row in rows]


def delete_chunks_for_document(pool: ConnectionPool, document_id: UUID) -> None:
    """For re-chunking a document (a different guard threshold, a chunker
    bugfix) without leaving the old chunks behind as orphaned duplicates."""
    with pool.connection() as conn:
        conn.execute("DELETE FROM chunks WHERE document_id = %s", (document_id,))
