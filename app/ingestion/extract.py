"""
Turns raw bytes into plain text, one method per format — the same methods
already proven out by hand during the corpus audit (see
../../corpus/synthetic/INDEX.md's Status section): pdftotext -layout for
PDFs, python-docx for Word, a stripped read for HTML, direct decode for
markdown/plain text. Kept as pure functions so both URLSource and
FileSource share exactly one extraction path per format, instead of two
that could quietly diverge.
"""
from __future__ import annotations

import re
import subprocess
import tempfile
from datetime import date
from io import BytesIO
from pathlib import Path

from bs4 import BeautifulSoup
from docx import Document

_MIN_MEANINGFUL_CHARS = 20

_MONTHS = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12,
}
# "Effective:** February 1, 2026" (clean/, markdown bold) or
# "Effective June 15 – July 31, 2026" (mixed/, a date range — the START date
# is what gets captured, the optional "– End Date" is matched but discarded).
_EFFECTIVE_DATE_RE = re.compile(
    r"Effective\W{0,8}([A-Z][a-z]+)\s+(\d{1,2})(?:\s*[-–]\s*[A-Z][a-z]+\s+\d{1,2})?,?\s*(\d{4})"
)
# "Date: 2026-03-18" / "Date 2026-05-02." — the postmortems and ADRs, which
# don't use "Effective" at all.
_ISO_DATE_RE = re.compile(r"\bDate\W{0,3}(\d{4})-(\d{2})-(\d{2})")


def guess_kind(content_type: str | None, ref: str) -> str:
    """Classify `ref` into "pdf" / "docx" / "html" / "text" using the HTTP
    content-type header when there is one, falling back to the file
    extension — a URL's content-type is authoritative when present, but
    local files (FileSource) never have one."""
    ct = (content_type or "").lower()
    suffix = Path(ref.split("?")[0]).suffix.lower()

    if "pdf" in ct or suffix == ".pdf":
        return "pdf"
    if "wordprocessingml" in ct or suffix == ".docx":
        return "docx"
    if suffix in (".md", ".txt"):
        return "text"
    if "html" in ct or suffix in (".htm", ".html") or (ref.startswith("http") and suffix == ""):
        return "html"
    return "text"


def extract_text(raw_bytes: bytes, kind: str) -> str | None:
    """Returns extracted text, or None if extraction failed or produced
    nothing meaningful (the image-only-PDF case). Never raises — a broken
    or unexpected document is a `NO_TEXT_EXTRACTED` outcome for the caller,
    not a crash."""
    try:
        if kind == "pdf":
            text = _extract_pdf(raw_bytes)
        elif kind == "docx":
            text = _extract_docx(raw_bytes)
        elif kind == "html":
            text = _extract_html(raw_bytes)
        else:
            text = raw_bytes.decode("utf-8", errors="replace")
    except Exception:
        return None

    if text is None or len(text.strip()) < _MIN_MEANINGFUL_CHARS:
        return None
    return text


def extract_effective_date(text: str) -> date | None:
    """Best-effort auto-detection of a document's effective date from its
    own text, for when a caller (the upload endpoint in particular) doesn't
    supply one explicitly. Heuristic, not authoritative — a caller-supplied
    effective_date always wins; this only ever fills a gap, never overrides
    one. Verified against all 28 real synthetic documents' actual header
    conventions (28/28 resolve correctly) rather than a guessed pattern:
    "Effective:** Month Day, Year" (clean/, including date ranges like
    "Effective June 15 – July 31, 2026", where the start date is used) and
    "Date: YYYY-MM-DD" (the incident postmortems and ADRs, which don't use
    "Effective" at all)."""
    m = _EFFECTIVE_DATE_RE.search(text)
    if m:
        month_name, day, year = m.groups()
        month = _MONTHS.get(month_name)
        if month is not None:
            try:
                return date(int(year), month, int(day))
            except ValueError:
                pass  # e.g. a false-positive match producing day=32 -- fall through

    m = _ISO_DATE_RE.search(text)
    if m:
        year, month, day = m.groups()
        try:
            return date(int(year), int(month), int(day))
        except ValueError:
            pass

    return None


def _extract_pdf(raw_bytes: bytes) -> str | None:
    with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
        tmp.write(raw_bytes)
        tmp.flush()
        result = subprocess.run(
            ["pdftotext", "-layout", tmp.name, "-"],
            capture_output=True,
            timeout=30,
        )
    if result.returncode != 0:
        return None
    return result.stdout.decode("utf-8", errors="replace")


def _extract_docx(raw_bytes: bytes) -> str:
    doc = Document(BytesIO(raw_bytes))
    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            parts.append(" | ".join(cell.text.strip() for cell in row.cells))
    return "\n".join(parts)


def _extract_html(raw_bytes: bytes) -> str:
    soup = BeautifulSoup(raw_bytes, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)
