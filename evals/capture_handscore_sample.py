"""
T-M4.15: captures the raw material for hand-scoring -- 20 real question/
answer/judge-score records, fixed to hybrid_rrf (T-M4.14's balance of
retrieval metrics vs. the simpler dense-only config). Deliberately a
*different* 20 questions than T-M4.14's 36-question generation sample
(skips past the first SAMPLE_PER_CATEGORY per category before taking
HANDSCORE_PER_CATEGORY) -- scoring the exact same answers the aggregate
metrics already covers wouldn't test anything new about the judge.

Writes the full record per question (question, expected_answer, the
actual context the model saw, the generated answer's claims, and the
judge's score+reasoning) to disk -- hand-scoring happens separately,
reading this file, specifically WITHOUT this script computing or
suggesting a hand-score itself. That would defeat the point: T-M4.15
exists to check whether an independent read of the raw material agrees
with the judge, and an independent read can't be anchored by a score
this same pipeline already produced.

Run: python3 -m evals.capture_handscore_sample
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from app.chunking.registry import get_chunks_by_ids
from app.core.db import get_pool
from app.documents.registry import get_document
from app.embeddings.gemini import get_embedding_provider
from app.evaluation import judge_answer
from app.generation import ContextSource, build_context, generate_answer
from app.generation.gemini import get_llm_provider
from app.retrieval import DenseRetriever, RRFFusion
from app.retrieval.sparse import get_sparse_retriever
from evals.golden_set.loader import load_golden_set
from evals.run_m4_experiment import K, SAMPLE_PER_CATEGORY

RESULTS_PATH = Path(__file__).parent / "results" / "m4_handscore_sample.json"

HANDSCORE_PER_CATEGORY = {
    "factual_lookup": 6,
    "exact_identifier": 3,
    "multi_hop": 4,
    "ambiguous": 2,
    "version_sensitive": 2,
    "unanswerable": 3,
}

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


def _pick_fresh_sample(questions):
    """Skips past the first SAMPLE_PER_CATEGORY[cat] questions in each
    category (already used by T-M4.14's generation sample) before taking
    the next HANDSCORE_PER_CATEGORY[cat]."""
    by_category: dict[str, list] = {}
    for q in questions:
        by_category.setdefault(q.category, []).append(q)
    sample = []
    for category, n in HANDSCORE_PER_CATEGORY.items():
        already_used = SAMPLE_PER_CATEGORY.get(category, 0)
        pool_for_category = by_category.get(category, [])[already_used:]
        sample.extend(pool_for_category[:n])
    return sample


def main() -> None:
    pool = get_pool()
    dense = DenseRetriever(get_embedding_provider())
    bm25 = get_sparse_retriever()
    provider = get_llm_provider()

    questions = load_golden_set()
    sample = _pick_fresh_sample(questions)
    print(f"Capturing {len(sample)} fresh question/answer/judge records (hybrid_rrf)\n")

    records = []
    for i, q in enumerate(sample, start=1):
        print(f"  {i}/{len(sample)} ({q.id})", flush=True)
        dense_hits = dense.retrieve(q.question, K)
        bm25_hits = bm25.retrieve(q.question, K)
        hits = RRFFusion().fuse({"dense": dense_hits, "bm25": bm25_hits})[:K]
        sources = _resolve_chunks_batch(pool, [h.chunk_id for h in hits[:5]])
        context = build_context(sources)

        try:
            answer = generate_answer(q.question, context, provider)
        except Exception as e:
            print(f"    generation failed for {q.id}: {e}")
            continue
        score = judge_answer(q.question, q.expected_answer, answer, context, provider)

        records.append({
            "id": q.id,
            "category": q.category,
            "question": q.question,
            "expected_answer": q.expected_answer,
            "context": context.context,
            "generated_answerable": answer.answerable,
            "generated_summary": answer.summary,
            "generated_claims": [
                {"statement": c.statement, "citation_numbers": c.citation_numbers} for c in answer.claims
            ],
            "judge_faithfulness": score.faithfulness,
            "judge_correctness": score.correctness,
            "judge_citation_support_rate": score.citation_support_rate,
            "judge_reasoning": score.reasoning,
        })

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(records, indent=2))
    print(f"\nWrote {len(records)} records to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
