"""
The mail carrier: fetches a document from a public retailer URL. See
../../ANALOGY.md. Reused unchanged by M8's freshness recrawl.
"""
from __future__ import annotations

import httpx

from app.ingestion.extract import extract_text, guess_kind
from app.ingestion.source import FetchStatus, RawDocument, Source

_USER_AGENT = "no-cap-rag-ingestion/0.1 (+portfolio RAG project; contact via repo)"

# Substrings actually observed in T-M1.4's manual fetch log when a "200 OK"
# response was really a country/language interstitial or a bot-check page,
# not the target content. Best-effort and not exhaustive by construction —
# a retailer can always phrase a block in a way this doesn't catch, which is
# exactly why `BLOCKED` exists as a distinct, loggable outcome rather than a
# silent false "OK".
_BLOCK_MARKERS = (
    "captcha",
    "robot or human",
    "are you a robot",
    "verify you are human",
    "verify you're human",
    "select your country",
    "choose your country",
    "shop in canada",
    "united states or canada",
)


class URLSource(Source):
    """Fetches a public URL and extracts its text. Classifies the response
    into the same outcomes T-M1.4 hit by hand, instead of only knowing
    "200" vs "raised"."""

    def __init__(self, timeout: float = 15.0) -> None:
        self._timeout = timeout

    def fetch(self, ref: str) -> RawDocument:
        try:
            response = httpx.get(
                ref,
                timeout=self._timeout,
                headers={"User-Agent": _USER_AGENT},
                follow_redirects=True,
            )
        except httpx.HTTPError as exc:
            return RawDocument(
                source_ref=ref,
                content_type=None,
                raw_bytes=None,
                text=None,
                status=FetchStatus.HTTP_ERROR,
                detail=f"request failed: {exc}",
            )

        if response.status_code != 200:
            return RawDocument(
                source_ref=ref,
                content_type=response.headers.get("content-type"),
                raw_bytes=response.content,
                text=None,
                status=FetchStatus.HTTP_ERROR,
                detail=f"HTTP {response.status_code}",
            )

        content_type = response.headers.get("content-type")
        kind = guess_kind(content_type, ref)
        text = extract_text(response.content, kind)

        if text is None:
            return RawDocument(
                source_ref=ref,
                content_type=content_type,
                raw_bytes=response.content,
                text=None,
                status=FetchStatus.NO_TEXT_EXTRACTED,
                detail=f"HTTP 200 but no extractable text (format: {kind}) — e.g. an image-only PDF",
            )

        lowered = text.lower()
        matched = next((marker for marker in _BLOCK_MARKERS if marker in lowered), None)
        if matched is not None:
            return RawDocument(
                source_ref=ref,
                content_type=content_type,
                raw_bytes=response.content,
                text=text,
                status=FetchStatus.BLOCKED,
                detail=f"HTTP 200, but the body matched interstitial/CAPTCHA marker: {matched!r}",
            )

        return RawDocument(
            source_ref=ref,
            content_type=content_type,
            raw_bytes=response.content,
            text=text,
            status=FetchStatus.OK,
        )
