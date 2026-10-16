"""
T-M4.12: the full V1 API surface the PRD specifies for actually asking a
question and getting a cited, judged answer back -- not just ranked
chunks the way T-M3.11's /retrieve does. `/query` composes everything
M4 built: retrieve (T-M3.11, reused directly, not reimplemented) ->
rerank (T-M4.5) -> build context (T-M4.6) -> generate (T-M4.7/T-M4.8).
`/evaluate` adds the judge (T-M4.10) on top for a single question with a
known reference answer.
"""
from __future__ import annotations

import time
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.retrieve import RetrieveRequest, Strategy, retrieve
from app.evaluation.judge import JudgeScore, judge_answer
from app.generation import BuiltContext, ContextSource, GeneratedAnswer, build_context, generate_answer, resolve_claims
from app.generation.context_builder import DEFAULT_MAX_CONTEXT_TOKENS
from app.generation.gemini import get_llm_provider
from app.reranking import RerankInput, get_reranker

router = APIRouter(tags=["query"])


class QueryRequest(BaseModel):
    question: str
    strategy: Strategy = "hybrid_rrf"
    k: int = 10
    rrf_k: int = 60
    weights: dict[str, float] | None = None
    use_reranker: bool = True
    rerank_k: int = 5
    max_context_tokens: int = DEFAULT_MAX_CONTEXT_TOKENS


class CitationResponse(BaseModel):
    number: int
    chunk_id: str
    document_title: str
    document_version: str | None
    section_path: str


class ClaimResponse(BaseModel):
    statement: str
    citations: list[CitationResponse]


class QueryResponse(BaseModel):
    trace_id: str
    question: str
    answerable: bool
    summary: str
    claims: list[ClaimResponse]
    timings_ms: dict[str, float]


def _run_query(request: QueryRequest) -> tuple[QueryResponse, GeneratedAnswer, BuiltContext]:
    """The shared core: everything /query returns, plus the raw
    GeneratedAnswer/BuiltContext /evaluate needs to hand to the judge --
    the judge scores the real objects, not a re-parse of the serialized
    response."""
    timings: dict[str, float] = {}
    t_start = time.perf_counter()
    trace_id = str(uuid4())

    retrieve_request = RetrieveRequest(
        query=request.question, k=request.k, strategy=request.strategy,
        rrf_k=request.rrf_k, weights=request.weights,
    )
    t0 = time.perf_counter()
    retrieved = retrieve(retrieve_request)
    timings["retrieval_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    for stage, ms in retrieved.timings_ms.items():
        timings[f"retrieve.{stage}"] = ms

    candidates = retrieved.results
    if request.use_reranker and candidates:
        t0 = time.perf_counter()
        rerank_inputs = [RerankInput(chunk_id=c.chunk_id, text=c.text) for c in candidates]
        reranked = get_reranker().rerank(request.question, rerank_inputs, k=request.rerank_k)
        by_id = {c.chunk_id: c for c in candidates}
        candidates = [by_id[r.chunk_id] for r in reranked if r.chunk_id in by_id]
        timings["rerank_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    else:
        candidates = candidates[: request.rerank_k]

    t0 = time.perf_counter()
    sources = [
        ContextSource(
            chunk_id=c.chunk_id, document_title=c.document_title, document_version=c.document_version,
            section_path=c.section_path, text=c.text,
        )
        for c in candidates
    ]
    context = build_context(sources, max_tokens=request.max_context_tokens)
    timings["context_ms"] = round((time.perf_counter() - t0) * 1000, 2)

    t0 = time.perf_counter()
    answer = generate_answer(request.question, context, get_llm_provider())
    timings["generate_ms"] = round((time.perf_counter() - t0) * 1000, 2)

    resolved = resolve_claims(answer, context)
    timings["total_ms"] = round((time.perf_counter() - t_start) * 1000, 2)

    response = QueryResponse(
        trace_id=trace_id,
        question=request.question,
        answerable=answer.answerable,
        summary=answer.summary,
        claims=[
            ClaimResponse(
                statement=claim.statement,
                citations=[
                    CitationResponse(
                        number=c.number, chunk_id=c.chunk_id, document_title=c.document_title,
                        document_version=c.document_version, section_path=c.section_path,
                    )
                    for c in claim.citations
                ],
            )
            for claim in resolved
        ],
        timings_ms=timings,
    )
    return response, answer, context


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    response, _answer, _context = _run_query(request)
    return response


class EvaluateRequest(BaseModel):
    question: str
    expected_answer: str | None = None
    strategy: Strategy = "hybrid_rrf"
    k: int = 10
    rrf_k: int = 60
    weights: dict[str, float] | None = None
    use_reranker: bool = True
    rerank_k: int = 5


class JudgeScoreResponse(BaseModel):
    faithfulness: float
    correctness: float
    citation_support_rate: float
    reasoning: str


class EvaluateResponse(BaseModel):
    query: QueryResponse
    judge: JudgeScoreResponse


@router.post("/evaluate", response_model=EvaluateResponse)
def evaluate(request: EvaluateRequest) -> EvaluateResponse:
    query_request = QueryRequest(
        question=request.question, strategy=request.strategy, k=request.k, rrf_k=request.rrf_k,
        weights=request.weights, use_reranker=request.use_reranker, rerank_k=request.rerank_k,
    )
    response, answer, context = _run_query(query_request)

    score: JudgeScore = judge_answer(
        request.question, request.expected_answer, answer, context, get_llm_provider()
    )
    return EvaluateResponse(
        query=response,
        judge=JudgeScoreResponse(
            faithfulness=score.faithfulness,
            correctness=score.correctness,
            citation_support_rate=score.citation_support_rate,
            reasoning=score.reasoning,
        ),
    )
