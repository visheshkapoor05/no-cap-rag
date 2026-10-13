"""
T-M3.11: the desk where a query actually gets answered-from. Built the
timing breakdown in now, not retrofitted later (per BLUEPRINT.md's own
note on this task) -- every stage of the pipeline a strategy touches gets
its own millisecond entry, so a slow `/retrieve` call can be diagnosed
from the response alone, no profiler needed.

`strategy` is a config choice, not a code branch per caller — the whole
point of T-M3.8/T-M3.9/T-M3.10's interfaces is that this endpoint doesn't
need to know how "dense" or "hybrid_rrf" actually work internally.
"""
from __future__ import annotations

import time
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, model_validator

from app.chunking import get_chunks_by_ids
from app.core.db import get_pool
from app.documents import get_document
from app.embeddings.gemini import get_embedding_provider
from app.retrieval import DenseRetriever, RetrievedChunk, RRFFusion, WeightedFusion
from app.retrieval.sparse import get_sparse_retriever

router = APIRouter(tags=["retrieval"])

Strategy = Literal["dense", "bm25", "hybrid_rrf", "hybrid_weighted"]


class RetrieveRequest(BaseModel):
    query: str
    k: int = 10
    strategy: Strategy = "hybrid_rrf"
    rrf_k: int = 60
    weights: dict[str, float] | None = None  # only used by hybrid_weighted

    @model_validator(mode="after")
    def _weights_required_for_weighted(self) -> "RetrieveRequest":
        if self.strategy == "hybrid_weighted" and not self.weights:
            raise ValueError("weights is required when strategy is hybrid_weighted")
        return self


class RetrievedChunkResponse(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    section_path: str
    text: str
    score: float


class RetrieveResponse(BaseModel):
    query: str
    strategy: Strategy
    results: list[RetrievedChunkResponse]
    timings_ms: dict[str, float]


def _resolve(chunks: list[RetrievedChunk]) -> list[RetrievedChunkResponse]:
    pool = get_pool()
    records = get_chunks_by_ids(pool, [c.chunk_id for c in chunks])

    title_cache: dict[str, str] = {}
    resolved: list[RetrievedChunkResponse] = []
    for chunk in chunks:
        record = records.get(chunk.chunk_id)
        if record is None:
            # Stale Milvus/BM25 entry pointing at a chunk since deleted
            # from Postgres (a re-chunk, a document removed) -- skip it
            # rather than 500 the whole response for one dangling id.
            continue
        doc_id = str(record.document_id)
        if doc_id not in title_cache:
            document = get_document(pool, record.document_id)
            title_cache[doc_id] = document.title if document else "(unknown document)"
        resolved.append(RetrievedChunkResponse(
            chunk_id=chunk.chunk_id,
            document_id=doc_id,
            document_title=title_cache[doc_id],
            section_path=record.section_path,
            text=record.text,
            score=chunk.score,
        ))
    return resolved


@router.post("/retrieve", response_model=RetrieveResponse)
def retrieve(request: RetrieveRequest) -> RetrieveResponse:
    timings: dict[str, float] = {}
    t_start = time.perf_counter()

    ranked_lists: dict[str, list[RetrievedChunk]] = {}

    if request.strategy in ("dense", "hybrid_rrf", "hybrid_weighted"):
        t0 = time.perf_counter()
        dense = DenseRetriever(get_embedding_provider())
        ranked_lists["dense"] = dense.retrieve(request.query, request.k)
        timings["dense_ms"] = (time.perf_counter() - t0) * 1000

    if request.strategy in ("bm25", "hybrid_rrf", "hybrid_weighted"):
        t0 = time.perf_counter()
        bm25 = get_sparse_retriever()
        ranked_lists["bm25"] = bm25.retrieve(request.query, request.k)
        timings["bm25_ms"] = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    if request.strategy == "dense":
        fused = ranked_lists["dense"]
    elif request.strategy == "bm25":
        fused = ranked_lists["bm25"]
    elif request.strategy == "hybrid_rrf":
        fused = RRFFusion(k=request.rrf_k).fuse(ranked_lists)
    else:  # hybrid_weighted
        try:
            fused = WeightedFusion(weights=request.weights).fuse(ranked_lists)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    timings["fusion_ms"] = (time.perf_counter() - t0) * 1000

    fused = fused[: request.k]

    t0 = time.perf_counter()
    results = _resolve(fused)
    timings["resolve_ms"] = (time.perf_counter() - t0) * 1000

    timings["total_ms"] = (time.perf_counter() - t_start) * 1000
    timings = {k: round(v, 2) for k, v in timings.items()}

    return RetrieveResponse(
        query=request.query, strategy=request.strategy, results=results, timings_ms=timings
    )
