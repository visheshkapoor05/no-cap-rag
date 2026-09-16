"""
The shape every piece of incoming mail gets forced into, and the contract
both mail carriers (URLSource, FileSource) have to honor. See ../../ANALOGY.md.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class FetchStatus(str, Enum):
    """
    The outcomes T-M1.4 actually produced by hand while fetching the 16
    public sources, made explicit here instead of collapsed into a single
    try/except. A caller (T-M1.6's registry writer, T-M1.9's CLI) needs to
    tell these apart to decide what to do next.
    """

    OK = "ok"
    BLOCKED = "blocked"  # HTTP 200, but the body is an interstitial/CAPTCHA, not the real page
    HTTP_ERROR = "http_error"  # non-2xx response, or the request itself failed
    NO_TEXT_EXTRACTED = "no_text_extracted"  # fetched/read fine, nothing readable came out (e.g. an image-only PDF)
    NOT_FOUND = "not_found"  # FileSource only: the local path doesn't exist


@dataclass(frozen=True)
class RawDocument:
    """What a Source hands back, whatever it fetched. `text` is None unless
    `status is FetchStatus.OK`; `detail` explains a non-OK status."""

    source_ref: str
    content_type: str | None
    raw_bytes: bytes | None
    text: str | None
    status: FetchStatus
    detail: str | None = None


class Source(ABC):
    """
    A place a document comes from. `URLSource` and `FileSource` are the only
    two implementations M1 needs — M8's freshness recrawl reuses `URLSource`
    unchanged, which only works because both adapters return this same
    `RawDocument` shape instead of two incompatible ones.
    """

    @abstractmethod
    def fetch(self, ref: str) -> RawDocument:
        """
        Fetch/read `ref` and return a RawDocument. Never raises for an
        *expected* failure (blocked, non-2xx, no extractable text, missing
        file) — those are reported via `status`/`detail` so a caller can
        branch on them explicitly rather than wrapping every call in a
        broad try/except.
        """
        raise NotImplementedError
