"""
The front desk for the archive room: the first desk that actually does
something beyond "are you open" — accepts a document reference, runs it
through the mailroom (T-M1.5) and the archive clerk's idempotent filing
(T-M1.6/T-M1.7), and lets a visitor look up what's on file. See
../../ANALOGY.md.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile, status
from pydantic import BaseModel

from app.core.db import get_pool
from app.documents import get_document, ingest_document
from app.ingestion import FetchStatus, FileSource, RawDocument, Source, URLSource
from app.ingestion.extract import extract_effective_date, extract_text, guess_kind

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
        effective_date=request.effective_date or extract_effective_date(raw.text),
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


@router.post("/upload", response_model=IngestResponse)
async def upload(
    response: Response,
    file: UploadFile = File(..., description="The document itself — PDF, DOCX, Markdown, or TXT."),
    type: str = Form(...),
    title: str = Form(...),
    version: str | None = Form(None),
    effective_date: date | None = Form(None, description="Optional — auto-detected from the document's own text if omitted (e.g. \"Effective: February 1, 2026\"); an explicit value here always wins over the guess."),
    supersedes: UUID | None = Form(None),
    metadata: str | None = Form(None, description="Optional JSON object, as a string (multipart forms can't carry nested JSON directly)."),
) -> IngestResponse:
    """
    The actual "attach a file" endpoint — distinct from POST /ingest, which
    only ever points at a ref (URL or server-local path) the server already
    has access to. This one takes bytes the caller supplies directly, right
    here in the request body, same as attaching a file in any other web
    form. Reuses the exact same extraction (T-M1.5's extract_text/guess_kind
    — pure functions, never cared whether the bytes came from a URLSource
    fetch or an upload) and the exact same idempotent ingest_document()
    (T-M1.7) the CLI and POST /ingest both already use — a fourth way in,
    not a fourth copy of the pipeline.
    """
    raw_bytes = await file.read()
    kind = guess_kind(file.content_type, file.filename or "")
    text = extract_text(raw_bytes, kind)

    if text is None:
        raise HTTPException(
            status_code=422,
            detail=f"could not extract text from {file.filename!r} (content_type={file.content_type!r}, guessed kind={kind!r})",
        )

    try:
        parsed_metadata = json.loads(metadata) if metadata else None
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail=f"metadata is not valid JSON: {exc}") from None

    raw = RawDocument(
        source_ref=file.filename or "upload",
        content_type=file.content_type,
        raw_bytes=raw_bytes,
        text=text,
        status=FetchStatus.OK,
    )

    result = ingest_document(
        get_pool(),
        raw,
        type=type,
        title=title,
        source_url=None,
        version=version,
        effective_date=effective_date or extract_effective_date(text),
        supersedes=supersedes,
        metadata=parsed_metadata,
    )

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
