"""The filing clerk's desk — structure-aware chunking, contextual prefixes,
and the Postgres record of every chunk. See ../../ANALOGY.md."""
from app.chunking.chunker import MAX_CHUNK_TOKENS, MIN_CHUNK_TOKENS, Chunk, chunk_structure_aware
from app.chunking.contextual import ContextualChunk, build_contextual_prefix, chunk_with_context
from app.chunking.models import ChunkRecord
from app.chunking.registry import delete_chunks_for_document, get_chunks_for_document, insert_chunks

__all__ = [
    "Chunk",
    "chunk_structure_aware",
    "MIN_CHUNK_TOKENS",
    "MAX_CHUNK_TOKENS",
    "ContextualChunk",
    "build_contextual_prefix",
    "chunk_with_context",
    "ChunkRecord",
    "insert_chunks",
    "get_chunks_for_document",
    "delete_chunks_for_document",
]
