"""The filing clerk's desk — structure-aware chunking with token guards.
See ../../ANALOGY.md."""
from app.chunking.chunker import MAX_CHUNK_TOKENS, MIN_CHUNK_TOKENS, Chunk, chunk_structure_aware

__all__ = ["Chunk", "chunk_structure_aware", "MIN_CHUNK_TOKENS", "MAX_CHUNK_TOKENS"]
