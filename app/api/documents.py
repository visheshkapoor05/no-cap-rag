"""
The front desk for the archive room: the first desk that actually does
something beyond "are you open" — accepts a document reference, runs it
through the mailroom (T-M1.5) and the archive clerk's idempotent filing
(T-M1.6/T-M1.7), and lets a visitor look up what's on file. See
../../ANALOGY.md.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel

from app.core.db import get_pool
from app.documents import get_document, ingest_document
from app.ingestion import FetchStatus, FileSource, Source, URLSource

router = APIRouter(prefix="/documents", tags=["documents"])


class IngestRequest(BaseModel):
    ref: str  # an https:// URL, or a local corpus file path
    type: str
    title: str
    version: str | None = None
    effective_date: date | None = None
    supersedes: UUID | None = None
    metadata: dict[str, Any] | None = None


class IngestResponse(BaseModel):
    id: UUID
    version: str | None
    content_hash: str
    index_status: str  # placeholder until M2's chunker exists — reserved so the shape doesn't change later
    created: bool  # True: newly inserted. False: identical content already existed (T-M1.7's idempotency at work)


class DocumentResponse(BaseModel):
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


def _pick_source(ref: str) -> Source:
    """A URL fetches over HTTP; anything else is read as a local corpus path."""
    return URLSource() if ref.startswith("http://") or ref.startswith("https://") else FileSource()


@router.post("/ingest", response_model=IngestResponse)
def ingest(request: IngestRequest, response: Response) -> IngestResponse:
    source = _pick_source(request.ref)
    raw = source.fetch(request.ref)

    if raw.status is not FetchStatus.OK:
        raise HTTPException(
            status_code=422,
            detail=f"could not ingest {request.ref!r}: {raw.status.value} — {raw.detail}",
        )

    result = ingest_document(
        get_pool(),
        raw,
        type=request.type,
        title=request.title,
        source_url=request.ref if isinstance(source, URLSource) else None,
        version=request.version,
        effective_date=request.effective_date,
        supersedes=request.supersedes,
        metadata=request.metadata,
    )

    # REST idempotency in practice: a brand-new row is a 201, a repeat of
    # content already on file is a 200 — same request, same end state,
    # different status code because only one of them actually created
    # something. See GLOSSARY.md's idempotency entry.
    response.status_code = status.HTTP_201_CREATED if result.created else status.HTTP_200_OK

    return IngestResponse(
        id=result.document.id,
        version=result.document.version,
        content_hash=result.document.content_hash,
        index_status="not_indexed",
        created=result.created,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
def read_document(document_id: UUID) -> DocumentResponse:
    document = get_document(get_pool(), document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="document not found")
    return DocumentResponse(**asdict(document))
