"""The archive card's exact shape — one per ingested document, matching
migrations/0001_create_documents_table.sql column for column. See
../../ANALOGY.md."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class Document:
    id: UUID
    source_url: str | None
    type: str
    title: str
    version: str | None
    effective_date: date | None
    fetched_at: datetime
    content_hash: str
    supersedes: UUID | None
    metadata: dict[str, Any]
