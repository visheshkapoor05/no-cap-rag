"""
The mailroom: brings raw material in from outside (URLSource) or from the
office's own practice files (FileSource) and hands every visitor back the
same shape of receipt, regardless of where it came from. See ../../ANALOGY.md.
"""
from app.ingestion.file_source import FileSource
from app.ingestion.source import FetchStatus, RawDocument, Source
from app.ingestion.url_source import URLSource

__all__ = ["FetchStatus", "RawDocument", "Source", "URLSource", "FileSource"]
