"""
T-M3.12: the real 4-config x 50-question experiment. Runs every answerable
golden question through DenseRetriever, SparseRetriever, RRFFusion, and
WeightedFusion -- the exact same classes app/api/retrieve.py uses, not a
reimplementation -- against the real dev Postgres + Milvus + Gemini, and
scores every run with the real recall_at_k()/reciprocal_rank() from
app/evaluation/metrics.py (T-M2.8).

Unanswerable questions (relevant_chunks == []) are run through resolve
trivially (relevant = set()) -- recall_at_k/reciprocal_rank both return
None for them, per their own documented behavior, and are excluded from
every average exactly the way mrr() already excludes them.

Writes a JSON dump of every per-question result to
evals/results/m3_experiment_raw.json (gitignored -- regenerable) so
Experiment A (evals/chunking_crosscheck.py) and the final results doc can
both build on the same real run without re-querying Gemini/Milvus twice.

Run: python3 evals/run_m3_experiment.py
"""
from __future__ import annotations

import json
import time
from collections import defaultdict
from pathlib import Path

from app.core.db import get_pool
from app.embeddings.gemini import get_embedding_provider
from app.evaluation.metrics import reciprocal_rank, recall_at_k
from app.retrieval import DenseRetriever, RRFFusion, WeightedFusion
from app.retrieval.sparse import get_sparse_retriever
from evals.golden_set.loader import load_golden_set
from evals.golden_set.resolve import resolve_chunk_ids

K = 10
CONFIGS = ("dense", "bm25", "hybrid_rrf", "hybrid_weighted")
OUT_PATH = Path(__file__).parent / "results" / "m3_experiment_raw.json"


def run_one(question, pool, dense, bm25) -> dict:
    relevant: set[str] = set()
    if question.answerable and question.relevant_chunks:
        relevant = set(resolve_chunk_ids(pool, question))

    dense_hits = dense.retrieve(question.question, K)
    bm25_hits = bm25.retrieve(question.question, K)
    ranked_lists = {"dense": dense_hits, "bm25": bm25_hits}
    rrf_hits = RRFFusion().fuse(ranked_lists)[:K]
    wt_hits = WeightedFusion(weights={"dense": 0.6, "bm25": 0.4}).fuse(ranked_lists)[:K]

    results = {}
    for name, hits in zip(CONFIGS, (dense_hits, bm25_hits, rrf_hits, wt_hits)):
        ids = [h.chunk_id for h in hits]
        results[name] = {
            "retrieved": ids,
            "recall_at_1": recall_at_k(ids, relevant, 1),
            "recall_at_5": recall_at_k(ids, relevant, 5),
            "recall_at_10": recall_at_k(ids, relevant, 10),
            "rr": reciprocal_rank(ids, relevant),
        }
    return {
        "id": question.id,
        "category": question.category,
        "answerable": question.answerable,
        "relevant": sorted(relevant),
        "results": results,
    }


def aggregate(rows: list[dict], configs=CONFIGS) -> dict:
    agg = {}
    for cfg in configs:
        r1 = [row["results"][cfg]["recall_at_1"] for row in rows if row["results"][cfg]["recall_at_1"] is not None]
        r5 = [row["results"][cfg]["recall_at_5"] for row in rows if row["results"][cfg]["recall_at_5"] is not None]
        r10 = [row["results"][cfg]["recall_at_10"] for row in rows if row["results"][cfg]["recall_at_10"] is not None]
        rr = [row["results"][cfg]["rr"] for row in rows if row["results"][cfg]["rr"] is not None]
        agg[cfg] = {
            "recall_at_1": sum(r1) / len(r1) if r1 else None,
            "recall_at_5": sum(r5) / len(r5) if r5 else None,
            "recall_at_10": sum(r10) / len(r10) if r10 else None,
            "mrr": sum(rr) / len(rr) if rr else None,
            "n": len(r1),
        }
    return agg


def main() -> None:
    pool = get_pool()
    dense = DenseRetriever(get_embedding_provider())
    bm25 = get_sparse_retriever()

    questions = load_golden_set()
    print(f"Loaded {len(questions)} golden questions")

    t0 = time.perf_counter()
    rows = []
    for i, q in enumerate(questions, start=1):
        rows.append(run_one(q, pool, dense, bm25))
        print(f"  [{i}/{len(questions)}] {q.id} ({q.category})")
    elapsed = time.perf_counter() - t0
    print(f"Done in {elapsed:.1f}s")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(rows, indent=2))
    print(f"Wrote {OUT_PATH}")

    answerable_rows = [r for r in rows if r["answerable"]]
    overall = aggregate(answerable_rows)

    print(f"\n=== OVERALL (n={len(answerable_rows)} answerable questions) ===")
    print(f"{'Config':<20}{'Recall@1':>10}{'Recall@5':>10}{'Recall@10':>10}{'MRR':>10}")
    for cfg in CONFIGS:
        a = overall[cfg]
        print(f"{cfg:<20}{a['recall_at_1']:>10.3f}{a['recall_at_5']:>10.3f}{a['recall_at_10']:>10.3f}{a['mrr']:>10.3f}")

    by_category = defaultdict(list)
    for r in answerable_rows:
        by_category[r["category"]].append(r)

    print("\n=== BY CATEGORY ===")
    for category, cat_rows in sorted(by_category.items()):
        cat_agg = aggregate(cat_rows)
        print(f"\n-- {category} (n={len(cat_rows)}) --")
        print(f"{'Config':<20}{'Recall@1':>10}{'Recall@5':>10}{'Recall@10':>10}{'MRR':>10}")
        for cfg in CONFIGS:
            a = cat_agg[cfg]
            print(f"{cfg:<20}{a['recall_at_1']:>10.3f}{a['recall_at_5']:>10.3f}{a['recall_at_10']:>10.3f}{a['mrr']:>10.3f}")


if __name__ == "__main__":
    main()
