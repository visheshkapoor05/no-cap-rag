"""Two mail carriers, one receipt shape: FileSource against real corpus
files, URLSource against a mocked transport so tests don't hit the network."""
from pathlib import Path

import httpx
import pytest

from app.ingestion import FetchStatus, FileSource, URLSource

CORPUS = Path(__file__).resolve().parent.parent / "corpus"


class TestFileSource:
    def test_reads_clean_markdown(self):
        doc = FileSource().fetch(str(CORPUS / "synthetic" / "clean" / "shift-policy.md"))

        assert doc.status == FetchStatus.OK
        assert "Shift Policy" in doc.text
        assert len(doc.text) > 500

    def test_reads_mixed_docx(self):
        doc = FileSource().fetch(str(CORPUS / "synthetic" / "mixed" / "shipping-policy.docx"))

        assert doc.status == FetchStatus.OK
        assert len(doc.text) > 200

    def test_reads_mixed_pdf(self):
        doc = FileSource().fetch(str(CORPUS / "synthetic" / "mixed" / "warranty-policy-v1.0.pdf"))

        assert doc.status == FetchStatus.OK
        assert len(doc.text) > 200

    def test_reads_mixed_txt_with_zero_structure(self):
        doc = FileSource().fetch(
            str(CORPUS / "synthetic" / "mixed" / "inventory-sync-failure-postmortem.txt")
        )

        assert doc.status == FetchStatus.OK
        assert len(doc.text) > 200

    def test_missing_file_is_not_found(self):
        doc = FileSource().fetch(str(CORPUS / "synthetic" / "clean" / "does-not-exist.md"))

        assert doc.status == FetchStatus.NOT_FOUND
        assert doc.text is None


class TestURLSource:
    """Mocks httpx's transport rather than the real network — these assert
    the *classification logic* (T-M1.4's real outcomes), not that any given
    retailer URL is reachable today."""

    def _fake_get(self, monkeypatch, response: httpx.Response):
        client = httpx.Client(transport=httpx.MockTransport(lambda request: response))
        monkeypatch.setattr(
            "app.ingestion.url_source.httpx.get",
            lambda url, **kwargs: client.get(url),
        )

    def test_ok_page(self, monkeypatch):
        body = (
            b"<html><body><h1>Return Policy</h1><p>Returns are accepted "
            b"within 90 days of purchase with a valid receipt, no further "
            b"conditions apply beyond the standard exceptions list.</p>"
            b"</body></html>"
        )
        self._fake_get(monkeypatch, httpx.Response(200, headers={"content-type": "text/html"}, content=body))

        doc = URLSource().fetch("https://example.com/returns")

        assert doc.status == FetchStatus.OK
        assert "Return Policy" in doc.text

    def test_detects_blocked_interstitial(self, monkeypatch):
        body = b"<html><body><p>Please select your country to continue shopping.</p></body></html>"
        self._fake_get(monkeypatch, httpx.Response(200, headers={"content-type": "text/html"}, content=body))

        doc = URLSource().fetch("https://example.com/international")

        assert doc.status == FetchStatus.BLOCKED
        assert "select your country" in doc.detail

    def test_http_error_status(self, monkeypatch):
        self._fake_get(monkeypatch, httpx.Response(403, content=b"forbidden"))

        doc = URLSource().fetch("https://example.com/blocked-403")

        assert doc.status == FetchStatus.HTTP_ERROR
        assert "403" in doc.detail

    def test_no_text_extracted_when_extraction_fails(self, monkeypatch):
        # Stands in for the real image-only-PDF case (Nordstrom size guide):
        # HTTP 200, bytes that don't yield a text layer either way.
        self._fake_get(
            monkeypatch,
            httpx.Response(200, headers={"content-type": "application/pdf"}, content=b"not actually a pdf"),
        )

        doc = URLSource().fetch("https://example.com/sizeguide.pdf")

        assert doc.status == FetchStatus.NO_TEXT_EXTRACTED
