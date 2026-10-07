"""
Resolves a golden-set question's natural-key chunk references
(title, version, section) into the chunk/document UUIDs currently in
Postgres. Deliberately re-resolved at the point of use rather than once at
build time -- see build.py's module docstring for why a frozen UUID goes
stale the moment the corpus is re-ingested.
"""
from __future__ import annotations

from evals.golden_set.loader import GoldenQuestion


def resolve_chunk_ids(pool, question: GoldenQuestion) -> list[str]:
    """Returns the current chunk UUID for each of this question's
    relevant_chunks specs, in order. Raises if a spec no longer resolves to
    exactly one chunk -- a golden label that's gone stale (e.g. the corpus
    was re-chunked with different guard thresholds) should fail loudly, not
    silently evaluate against nothing."""
    chunk_ids = []
    with pool.connection() as conn:
        for spec in question.relevant_chunks:
            query = "SELECT c.id FROM chunks c JOIN documents d ON d.id = c.document_id WHERE d.title = %(title)s"
            params = {"title": spec["title"]}
            if spec.get("version") is not None:
                query += " AND d.version = %(version)s"
                params["version"] = spec["version"]
            if spec.get("section") is not None:
                query += " AND c.section_path LIKE %(section)s"
                params["section"] = f"%{spec['section']}%"
            if spec.get("text") is not None:
                query += " AND c.text LIKE %(text)s"
                params["text"] = f"%{spec['text']}%"
            rows = conn.execute(query, params).fetchall()
            if len(rows) != 1:
                raise ValueError(
                    f"{question.id}: spec {spec!r} resolved to {len(rows)} chunks, expected 1 "
                    "-- golden label is stale, re-run evals/golden_set/build.py"
                )
            chunk_ids.append(str(rows[0]["id"]))
    return chunk_ids


def resolve_doc_ids(pool, question: GoldenQuestion) -> list[str]:
    doc_ids = []
    with pool.connection() as conn:
        for spec in question.relevant_docs:
            query = "SELECT id FROM documents WHERE title = %(title)s"
            params = {"title": spec["title"]}
            if spec.get("version") is not None:
                query += " AND version = %(version)s"
                params["version"] = spec["version"]
            rows = conn.execute(query, params).fetchall()
            if len(rows) != 1:
                raise ValueError(
                    f"{question.id}: doc spec {spec!r} resolved to {len(rows)} documents, expected 1"
                )
            doc_ids.append(str(rows[0]["id"]))
    return doc_ids
