"""The stamp itself: turns extracted text into the fingerprint T-M1.6's
`content_hash` column stores. See ../../ANALOGY.md."""
from __future__ import annotations

import hashlib


def compute_content_hash(text: str) -> str:
    """sha256 over the *extracted text*, deliberately never over raw bytes
    — see DECISIONS.md and the proof in this session that re-saving a
    .docx with zero edits still changes its raw bytes."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
