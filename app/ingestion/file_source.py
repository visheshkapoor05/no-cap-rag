"""
The walk-in window: reads a document the office already has on disk — the
44 synthetic corpus files under corpus/synthetic/. See ../../ANALOGY.md.
"""
from __future__ import annotations

from pathlib import Path

from app.ingestion.extract import extract_text, guess_kind
from app.ingestion.source import FetchStatus, RawDocument, Source

_CONTENT_TYPES = {
    ".md": "text/markdown",
    ".txt": "text/plain",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


class FileSource(Source):
    """Reads a local corpus file and extracts its text. Never touches the
    network — `ref` is always a filesystem path."""

    def fetch(self, ref: str) -> RawDocument:
        path = Path(ref)
        if not path.is_file():
            return RawDocument(
                source_ref=ref,
                content_type=None,
                raw_bytes=None,
                text=None,
                status=FetchStatus.NOT_FOUND,
                detail=f"no such file: {ref}",
            )

        raw_bytes = path.read_bytes()
        content_type = _CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")
        kind = guess_kind(content_type, ref)
        text = extract_text(raw_bytes, kind)

        if text is None:
            return RawDocument(
                source_ref=ref,
                content_type=content_type,
                raw_bytes=raw_bytes,
                text=None,
                status=FetchStatus.NO_TEXT_EXTRACTED,
                detail=f"read {len(raw_bytes)} bytes but extracted no meaningful text (format: {kind})",
            )

        return RawDocument(
            source_ref=ref,
            content_type=content_type,
            raw_bytes=raw_bytes,
            text=text,
            status=FetchStatus.OK,
        )
