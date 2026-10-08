"""A chunk as it actually exists in Postgres -- matches
migrations/0002_create_chunks_table.sql column for column. See ../../ANALOGY.md."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class ChunkRecord:
    id: UUID
    document_id: UUID
    section_path: str
    contextual_prefix: str
    text: str
    token_count: int
    embedding_id: str | None
    sparse_terms: dict[str, Any] | None
    created_at: datetime
