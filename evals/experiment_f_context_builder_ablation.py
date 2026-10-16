"""
T-M4.14's Experiment F: does T-M4.6's context builder (exact-text dedup +
greedy token-budget fill, app/generation/context_builder.py) actually
change generation quality versus the naive thing it replaced -- concatenate
whatever the retriever handed back, unconditionally, with no dedup and no
budget check?

Fixed to hybrid_rrf (M3's overall retrieval winner) -- this ablates the
context-assembly stage specifically, not the retrieval stage, so holding
retrieval constant isolates the one variable this experiment is about,
same principle as D-013/Experiment A holding retrieval constant to isolate
chunking.

Same 36-question stratified sample T-M4.14's main ladder used (identical
category counts), so the two context-builder variants are compared on
the exact same questions, not just the same category proportions.

Run: python3 -m evals.experiment_f_context_builder_ablation
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from app.chunking.registry import get_chunks_by_ids
from app.core.db import get_pool
from app.documents.registry import get_document
from app.embeddings.gemini import get_embedding_provider
from app.evaluation import judge_answer
from app.generation import ContextSource, build_context, generate_answer
from app.generation.context_builder import BuiltContext, Citation
from app.generation.gemini import get_llm_provider
from app.retrieval import DenseRetriever, RRFFusion
from app.retrieval.sparse import get_sparse_retriever
from evals.golden_set.loader import load_golden_set
from evals.run_m4_experiment import SAMPLE_PER_CATEGORY, K, _sample_questions

_DOCUMENT_TITLE_CACHE: dict = {}


def _resolve_chunks_batch(pool, chunk_ids: list[str]) -> list[ContextSource]:
    if not chunk_ids:
        return []
    records = get_chunks_by_ids(pool, chunk_ids)
    sources = []
    for chunk_id in chunk_ids:
        record = records.get(chunk_id)
        if record is None:
            continue
        doc_id = record.document_id
        if doc_id not in _DOCUMENT_TITLE_CACHE:
            document = get_document(pool, doc_id)
            _DOCUMENT_TITLE_CACHE[doc_id] = document.title if document else "(unknown)"
        sources.append(
            ContextSource(
                chunk_id=chunk_id, document_title=_DOCUMENT_TITLE_CACHE[doc_id],
                section_path=record.section_path, text=record.text,
            )
        )
    return sources


def naive_build_context(sources: list[ContextSource]) -> BuiltContext:
    """The thing T-M4.6 replaced: every source gets a citation bracket,
    unconditionally -- no exact-text dedup, no token-budget check. Same
    bracket format as the real build_context() (citation-grounded
    generation needs that either way), so this isolates dedup+budget
    specifically, not the whole context-assembly mechanism."""
    citations: list[Citation] = []
    blocks: list[str] = []
    for source in sources:
        n = len(citations) + 1
        blocks.append(f"[{n}] {source.document_title} → §{source.section_path}: {source.text}")
        citations.append(
            Citation(number=n, chunk_id=source.chunk_id, document_title=source.document_title,
                      section_path=source.section_path)
        )
    return BuiltContext(context="\n\n".join(blocks), citations=citations, dropped_for_budget=0, deduped_count=0)


@dataclass
class VariantResult:
    faithfulness: list[float]
    correctness: list[float]
    citation_support: list[float]
    dedupe_events: int
    budget_drop_events: int


def run_variant(sample, pool, use_naive: bool) -> VariantResult:
    dense = DenseRetriever(get_embedding_provider())
    bm25 = get_sparse_retriever()
    provider = get_llm_provider()

    result = VariantResult([], [], [], 0, 0)
    for i, q in enumerate(sample, start=1):
        print(f"    [{'naive' if use_naive else 'current'}] {i}/{len(sample)} ({q.id})", flush=True)
        dense_hits = dense.retrieve(q.question, K)
        bm25_hits = bm25.retrieve(q.question, K)
        hits = RRFFusion().fuse({"dense": dense_hits, "bm25": bm25_hits})[:K]
        sources = _resolve_chunks_batch(pool, [h.chunk_id for h in hits[:5]])

        if use_naive:
            context = naive_build_context(sources)
        else:
            context = build_context(sources)
            if context.deduped_count:
                result.dedupe_events += 1
            if context.dropped_for_budget:
                result.budget_drop_events += 1

        try:
            answer = generate_answer(q.question, context, provider)
        except Exception as e:
            print(f"    generation failed for {q.id}: {e}")
            continue
        score = judge_answer(q.question, q.expected_answer, answer, context, provider)
        result.faithfulness.append(score.faithfulness)
        result.correctness.append(score.correctness)
        result.citation_support.append(score.citation_support_rate)
    return result


def _avg(xs: list[float]) -> float | None:
    return sum(xs) / len(xs) if xs else None


def main() -> None:
    pool = get_pool()
    sample = _sample_questions([q for q in load_golden_set()])
    print(f"Running context-builder ablation over {len(sample)}-question sample, hybrid_rrf retrieval fixed\n")

    print("=== Current build_context() (dedup + token budget) ===")
    current = run_variant(sample, pool, use_naive=False)
    print(f"  faithfulness={_avg(current.faithfulness):.3f} correctness={_avg(current.correctness):.3f} "
          f"citation_support={_avg(current.citation_support):.3f} n={len(current.faithfulness)}")
    print(f"  dedup fired on {current.dedupe_events}/{len(sample)} questions; "
          f"budget drop fired on {current.budget_drop_events}/{len(sample)} questions")

    print("\n=== Naive context (no dedup, no budget check) ===")
    naive = run_variant(sample, pool, use_naive=True)
    print(f"  faithfulness={_avg(naive.faithfulness):.3f} correctness={_avg(naive.correctness):.3f} "
          f"citation_support={_avg(naive.citation_support):.3f} n={len(naive.faithfulness)}")

    print("\n=== Delta (current - naive) ===")
    print(f"  faithfulness {_avg(current.faithfulness) - _avg(naive.faithfulness):+.3f}")
    print(f"  correctness {_avg(current.correctness) - _avg(naive.correctness):+.3f}")
    print(f"  citation_support {_avg(current.citation_support) - _avg(naive.citation_support):+.3f}")


if __name__ == "__main__":
    main()
