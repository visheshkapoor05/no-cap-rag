"""
The clerk's "already tagged this one" drawer: a local, disk-backed cache so
the same chunk text is never sent to an embedding API twice under the same
model. See ../../ANALOGY.md ("topic scent" tag) and T-M2.6 in
learnings/02-cleaning-chunking-metadata/TASKS.md.

Plain sqlite3 (stdlib), not a cache library -- this project hand-rolls
things it wants to fully understand (same call as D-008's hand-written
metrics). One row per (text, model_id) pair; the vector itself is stored
as a pickled blob since sqlite has no native array/list type.
"""
from __future__ import annotations

import hashlib
import pickle
import sqlite3
from pathlib import Path
from typing import Callable

DEFAULT_CACHE_PATH = Path(".embedding_cache/cache.db")

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS embedding_cache (
    cache_key  TEXT PRIMARY KEY,
    vector     BLOB NOT NULL
)
"""


def _cache_key(text: str, model_id: str) -> str:
    """sha256 over text+model_id, not a plain concatenation lookup --
    mirrors app/documents/hashing.py's content_hash: a fixed-width key
    regardless of how long the chunk text gets."""
    return hashlib.sha256(f"{text}\x00{model_id}".encode("utf-8")).hexdigest()


class EmbeddingCache:
    """One sqlite file on disk, holding every (text, model_id) -> vector
    pair embedded so far. Survives across process runs on purpose -- see
    DECISIONS.md / T-M2.6: the point is skipping re-embedding across
    separate script invocations over days of M3 tuning, not just within
    one run."""

    def __init__(self, path: Path | str = DEFAULT_CACHE_PATH) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._path)
        self._conn.execute(_CREATE_TABLE)
        self._conn.commit()

    def get(self, text: str, model_id: str) -> list[float] | None:
        key = _cache_key(text, model_id)
        row = self._conn.execute(
            "SELECT vector FROM embedding_cache WHERE cache_key = ?", (key,)
        ).fetchone()
        return pickle.loads(row[0]) if row else None

    def set(self, text: str, model_id: str, vector: list[float]) -> None:
        key = _cache_key(text, model_id)
        self._conn.execute(
            "INSERT OR REPLACE INTO embedding_cache (cache_key, vector) VALUES (?, ?)",
            (key, pickle.dumps(vector)),
        )
        self._conn.commit()

    def get_or_embed(
        self, text: str, model_id: str, embed_fn: Callable[[str], list[float]]
    ) -> list[float]:
        """The one method callers actually use: look up first, only call
        `embed_fn` (the real, paid API call) on a miss."""
        cached = self.get(text, model_id)
        if cached is not None:
            return cached
        vector = embed_fn(text)
        self.set(text, model_id, vector)
        return vector

    def __len__(self) -> int:
        (count,) = self._conn.execute("SELECT COUNT(*) FROM embedding_cache").fetchone()
        return count

    def close(self) -> None:
        self._conn.close()
