"""
T-M3.9: BM25 via `rank_bm25` (k1=1.5, b=0.75 -- its real defaults,
verified by reading the library's own `__init__` signature rather than
assumed, and the same values the T-M3.1 worked example used). In-memory
and fully inspectable (D-005) -- the whole corpus is tokenized once at
construction time, not per request.

Built from `contextual_prefix + text`, the same string indexing.py embeds
into Milvus for dense retrieval -- the section heading has to be
searchable by BM25 too (D-005), and dense/sparse should see the same
underlying text so a strategy comparison isn't confounded by one side
having more context than the other.
"""
from __future__ import annotations

import re

from psycopg_pool import ConnectionPool
from rank_bm25 import BM25Okapi

from app.chunking import get_all_chunks
from app.retrieval.strategy import RetrievedChunk

# Keeps hyphenated alphanumeric codes like "pos-err-3021" as one token
# instead of shattering them on the hyphen -- the same tokenizer design
# T-M3.4's practice script used, now promoted to production. Not imported
# from practice/ on purpose: practice scripts stay throwaway, isolated
# from the app (see that script's own module docstring).
_TOKEN_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class SparseRetriever:
    def __init__(self, pool: ConnectionPool) -> None:
        chunks = get_all_chunks(pool)
        self._chunk_ids = [str(c.id) for c in chunks]
        corpus = [tokenize(c.contextual_prefix + c.text) for c in chunks]
        self._bm25 = BM25Okapi(corpus) if corpus else None

    def retrieve(self, query: str, k: int) -> list[RetrievedChunk]:
        if self._bm25 is None:
            return []

        scores = self._bm25.get_scores(tokenize(query))
        ranked = sorted(
            range(len(scores)), key=lambda i: scores[i], reverse=True
        )[:k]
        return [
            RetrievedChunk(chunk_id=self._chunk_ids[i], score=float(scores[i]))
            for i in ranked
            if scores[i] > 0  # a zero score is "no term matched", not a real hit
        ]
