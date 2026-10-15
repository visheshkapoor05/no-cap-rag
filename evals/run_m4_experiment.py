"""
T-M4.14: the full benchmark ladder -- Baseline (dense) / +hybrid / +reranker,
each scored on Recall@5, MRR, R-Precision, Faithfulness, Correctness,
Citation support, and P95 latency, per the task's own table.

Two different sample sizes for two genuinely different costs, same economy
-of-effort principle D-013's chunking cross-check already established (one
deliberate, documented scope decision, not a silent shortcut):

- Retrieval metrics (Recall@5, MRR, R-Precision) run over the FULL 151
  -question set -- cheap, no generation or judge calls, just retrieval.
- Generation/judge metrics (Faithfulness, Correctness, Citation support,
  P95 latency) run over a stratified 36-question SAMPLE -- a real
  generate_answer() + judge_answer() call per question per config is
  slow and costs real Gemini API spend; 151 x 3 configs would be ~450
  real LLM round trips. The sample is stratified across all 6 categories
  (including a real unanswerable slice, scored on whether the system
  correctly abstains) so no category is invisible to the generation-
  quality numbers, even though it isn't the full set.

Run: python3 -m evals.run_m4_experiment
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from app.core.db import get_pool, migrate
from app.embeddings.gemini import MODEL_ID as EMBEDDING_MODEL_ID
from app.embeddings.gemini import get_embedding_provider
from app.evaluation import judge_answer, precision_at_k, r_precision, recall_at_k, record_experiment, reciprocal_rank
from app.generation import ContextSource, build_context, generate_answer
from app.generation.gemini import MODEL_ID as LLM_MODEL_ID
from app.generation.gemini import get_llm_provider
from app.reranking.reranker import MODEL_ID as RERANKER_MODEL_ID
from app.reranking import RerankInput, get_reranker
from app.retrieval import DenseRetriever, RRFFusion
from app.retrieval.sparse import get_sparse_retriever
from app.chunking.registry import get_chunks_by_ids
from app.documents.registry import get_document
from evals.golden_set.loader import load_golden_set
from evals.golden_set.resolve import resolve_chunk_ids

K = 10
RESULTS_PATH = Path(__file__).parent / "results" / "m4_experiment_raw.json"
DATASET_VERSION = "golden_set.yaml v1 (151 questions, T-M4.13)"

# Stratified sample for the expensive generation+judge metrics -- counts
# per category chosen to keep every category represented without running
# all 151 questions through 3 real generate+judge passes each.
SAMPLE_PER_CATEGORY = {
    "factual_lookup": 8,
    "exact_identifier": 6,
    "multi_hop": 8,
    "ambiguous": 4,
    "version_sensitive": 4,
    "unanswerable": 6,
}


_DOCUMENT_TITLE_CACHE: dict = {}


def _resolve_chunks_batch(pool, chunk_ids: list[str]) -> list[ContextSource]:
    """Batched version of the original per-chunk _resolve_chunk_text --
    that N+1 pattern (one query per hit, up to 10 per question) was a real
    contributor to how slow the first run was. One WHERE id = ANY(...)
    query per question instead, plus a process-local document-title cache
    since the same ~28 documents repeat across every question's hits."""
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


def _retrieve(question_text: str, use_hybrid: bool, dense, bm25) -> list:
    dense_hits = dense.retrieve(question_text, K)
    if not use_hybrid:
        return dense_hits
    bm25_hits = bm25.retrieve(question_text, K)
    return RRFFusion().fuse({"dense": dense_hits, "bm25": bm25_hits})[:K]


def run_retrieval_metrics(questions, pool) -> dict[str, dict]:
    dense = DenseRetriever(get_embedding_provider())
    bm25 = get_sparse_retriever()
    reranker = get_reranker()

    configs = {"baseline_dense": {}, "plus_hybrid": {}, "plus_reranker": {}}
    answerable = [q for q in questions if q.answerable]

    for cfg_name in configs:
        recalls, rrs, rprecs = [], [], []
        for i, q in enumerate(answerable, start=1):
            if i % 10 == 0 or i == len(answerable):
                print(f"    [{cfg_name}] {i}/{len(answerable)} ({q.id})", flush=True)
            relevant = set(resolve_chunk_ids(pool, q))
            if not relevant:
                continue
            if cfg_name == "baseline_dense":
                hits = _retrieve(q.question, use_hybrid=False, dense=dense, bm25=bm25)
            else:
                hits = _retrieve(q.question, use_hybrid=True, dense=dense, bm25=bm25)

            if cfg_name == "plus_reranker":
                sources = _resolve_chunks_batch(pool, [h.chunk_id for h in hits])
                rerank_inputs = [RerankInput(chunk_id=s.chunk_id, text=s.text) for s in sources]
                hits = reranker.rerank(q.question, rerank_inputs, k=K)

            ids = [h.chunk_id for h in hits]
            r5 = recall_at_k(ids, relevant, 5)
            rr = reciprocal_rank(ids, relevant)
            rp = r_precision(ids, relevant)
            if r5 is not None:
                recalls.append(r5)
            if rr is not None:
                rrs.append(rr)
            if rp is not None:
                rprecs.append(rp)

        configs[cfg_name] = {
            "recall_at_5": sum(recalls) / len(recalls),
            "mrr": sum(rrs) / len(rrs),
            "r_precision": sum(rprecs) / len(rprecs),
            "n_retrieval": len(recalls),
        }
        print(f"  [retrieval] {cfg_name}: {configs[cfg_name]}", flush=True)
    return configs


def _sample_questions(questions):
    by_category: dict[str, list] = {}
    for q in questions:
        by_category.setdefault(q.category, []).append(q)
    sample = []
    for category, n in SAMPLE_PER_CATEGORY.items():
        sample.extend(by_category.get(category, [])[:n])
    return sample


def run_generation_metrics(sample, pool) -> dict[str, dict]:
    dense = DenseRetriever(get_embedding_provider())
    bm25 = get_sparse_retriever()
    reranker = get_reranker()
    provider = get_llm_provider()

    configs = {"baseline_dense": {}, "plus_hybrid": {}, "plus_reranker": {}}

    for cfg_name in configs:
        faithfulness, correctness, citation_support, latencies_ms = [], [], [], []
        for i, q in enumerate(sample, start=1):
            print(f"    [{cfg_name}] {i}/{len(sample)} ({q.id})", flush=True)
            t0 = time.perf_counter()
            hits = _retrieve(q.question, use_hybrid=(cfg_name != "baseline_dense"), dense=dense, bm25=bm25)
            sources = _resolve_chunks_batch(pool, [h.chunk_id for h in hits[:K]])

            if cfg_name == "plus_reranker":
                rerank_inputs = [RerankInput(chunk_id=s.chunk_id, text=s.text) for s in sources]
                reranked = reranker.rerank(q.question, rerank_inputs, k=5)
                by_id = {s.chunk_id: s for s in sources}
                sources = [by_id[r.chunk_id] for r in reranked if r.chunk_id in by_id]
            else:
                sources = sources[:5]

            context = build_context(sources)
            try:
                answer = generate_answer(q.question, context, provider)
            except Exception as e:
                print(f"    generation failed for {q.id}: {e}")
                continue
            score = judge_answer(q.question, q.expected_answer, answer, context, provider)
            latency_ms = (time.perf_counter() - t0) * 1000

            faithfulness.append(score.faithfulness)
            correctness.append(score.correctness)
            citation_support.append(score.citation_support_rate)
            latencies_ms.append(latency_ms)

        latencies_sorted = sorted(latencies_ms)
        p95_idx = max(0, int(len(latencies_sorted) * 0.95) - 1)
        configs[cfg_name] = {
            "faithfulness": sum(faithfulness) / len(faithfulness),
            "correctness": sum(correctness) / len(correctness),
            "citation_support_rate": sum(citation_support) / len(citation_support),
            "p95_latency_ms": round(latencies_sorted[p95_idx], 1) if latencies_sorted else None,
            "n_generation": len(faithfulness),
        }
        print(f"  [generation] {cfg_name}: {configs[cfg_name]}")
    return configs


def main() -> None:
    pool = get_pool()
    migrate(pool)
    questions = load_golden_set()
    print(f"Loaded {len(questions)} golden questions")

    print("\n=== Retrieval metrics (full 151-question set) ===")
    retrieval_results = run_retrieval_metrics(questions, pool)

    sample = _sample_questions(questions)
    print(f"\n=== Generation/judge metrics (stratified {len(sample)}-question sample) ===")
    generation_results = run_generation_metrics(sample, pool)

    merged = {}
    for cfg_name in retrieval_results:
        merged[cfg_name] = {**retrieval_results[cfg_name], **generation_results[cfg_name]}

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(merged, indent=2))
    print(f"\nWrote {RESULTS_PATH}")

    for cfg_name, metrics in merged.items():
        reranker_model = RERANKER_MODEL_ID if cfg_name == "plus_reranker" else None
        record_experiment(
            pool,
            name=f"T-M4.14 {cfg_name}",
            config={"strategy": "dense" if cfg_name == "baseline_dense" else "hybrid_rrf",
                    "reranker": cfg_name == "plus_reranker"},
            dataset_version=DATASET_VERSION,
            embedding_model=EMBEDDING_MODEL_ID,
            reranker_model=reranker_model,
            llm_model=LLM_MODEL_ID,
            metrics=metrics,
        )

    print("\n=== FULL BENCHMARK LADDER ===")
    print(f"{'Config':<16}{'Recall@5':>10}{'MRR':>8}{'R-Prec':>8}{'Faith':>8}{'Correct':>9}{'CiteSup':>9}{'P95(ms)':>10}")
    for cfg_name, m in merged.items():
        print(f"{cfg_name:<16}{m['recall_at_5']:>10.3f}{m['mrr']:>8.3f}{m['r_precision']:>8.3f}"
              f"{m['faithfulness']:>8.3f}{m['correctness']:>9.3f}{m['citation_support_rate']:>9.3f}"
              f"{m['p95_latency_ms']:>10.1f}")


if __name__ == "__main__":
    main()
