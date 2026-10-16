"""
T-M4.14's Experiment E: does the contextual prefix (T-M2.5 --
"Returns Policy v3.0 -> Section 3.2 Discounted Items: " prepended to every
chunk before embedding) actually earn its keep at retrieval time?

Same chunk_id space as production (get_all_chunks() reads the real,
already-ingested 149 chunks -- no re-chunking, no re-derivation, unlike
D-013's Experiment A which had to re-chunk at different boundaries). Only
the embedding/tokenization input changes: `text` alone instead of
`contextual_prefix + text`. Entirely in-memory and read-only -- does not
touch the real Milvus collection or write anything to Postgres.

One extra cell, not a full grid (same D-013 economy-of-effort principle):
re-tests hybrid_rrf (M3's overall winner) with vs without the prefix,
over the real 127 answerable questions, real ground truth (identical
chunk_ids, so no approximate-match machinery needed here either).

Run: python3 -m evals.experiment_e_contextual_prefix
"""
from __future__ import annotations

import math

from rank_bm25 import BM25Okapi

from app.chunking.registry import get_all_chunks
from app.core.db import get_pool
from app.embeddings.gemini import get_embedding_provider
from app.evaluation.metrics import r_precision, recall_at_k, reciprocal_rank
from app.retrieval.fusion import RRFFusion
from app.retrieval.sparse import tokenize
from app.retrieval.strategy import RetrievedChunk
from evals.golden_set.loader import load_golden_set
from evals.golden_set.resolve import resolve_chunk_ids

K = 10

# Production's real plus_hybrid numbers from this same run (T-M4.14,
# WITH the contextual prefix) -- the baseline this experiment compares
# against. Not re-measured here because they're already the real,
# current-pipeline numbers; re-deriving them a second time from the
# production Milvus index would just reproduce the same inputs.
WITH_PREFIX = {"recall_at_5": 0.9133858267716537, "mrr": 0.8877952755905512, "r_precision": 0.6876640419947507}


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def main() -> None:
    pool = get_pool()
    chunks = get_all_chunks(pool)
    print(f"Loaded {len(chunks)} real chunks")

    provider = get_embedding_provider()
    print("Embedding every chunk's text WITHOUT its contextual prefix (real Gemini calls)...")
    vectors = {}
    for i, c in enumerate(chunks, start=1):
        vectors[str(c.id)] = provider.embed_document(c.text)
        if i % 50 == 0 or i == len(chunks):
            print(f"  {i}/{len(chunks)}", flush=True)

    print("Building in-memory BM25 over chunk text alone (no prefix)...")
    corpus_tokens = [tokenize(c.text) for c in chunks]
    bm25 = BM25Okapi(corpus_tokens)
    chunk_ids = [str(c.id) for c in chunks]

    questions = [q for q in load_golden_set() if q.answerable]
    print(f"Scoring hybrid_rrf (no prefix) against {len(questions)} answerable questions...\n")

    r5s, rrs, rprecs = [], [], []
    for i, q in enumerate(questions, start=1):
        if i % 20 == 0 or i == len(questions):
            print(f"  {i}/{len(questions)} ({q.id})", flush=True)
        relevant = set(resolve_chunk_ids(pool, q))
        if not relevant:
            continue

        query_vec = provider.embed_query(q.question)
        dense_scores = [(cid, cosine(query_vec, vectors[cid])) for cid in chunk_ids]
        dense_scores.sort(key=lambda t: t[1], reverse=True)
        dense_hits = [RetrievedChunk(chunk_id=cid, score=s) for cid, s in dense_scores[:K]]

        bm25_scores = bm25.get_scores(tokenize(q.question))
        ranked = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:K]
        bm25_hits = [
            RetrievedChunk(chunk_id=chunk_ids[i], score=float(bm25_scores[i])) for i in ranked if bm25_scores[i] > 0
        ]

        fused = RRFFusion().fuse({"dense": dense_hits, "bm25": bm25_hits})[:K]
        ids = [h.chunk_id for h in fused]

        r5 = recall_at_k(ids, relevant, 5)
        rr = reciprocal_rank(ids, relevant)
        rp = r_precision(ids, relevant)
        if r5 is not None:
            r5s.append(r5)
        if rr is not None:
            rrs.append(rr)
        if rp is not None:
            rprecs.append(rp)

    without_prefix = {
        "recall_at_5": sum(r5s) / len(r5s),
        "mrr": sum(rrs) / len(rrs),
        "r_precision": sum(rprecs) / len(rprecs),
        "n": len(r5s),
    }
    print(f"\nn={without_prefix['n']} questions")
    print(f"WITHOUT contextual prefix + hybrid_rrf: {without_prefix}")
    print(f"WITH contextual prefix + hybrid_rrf (production, this run): {WITH_PREFIX}")
    print(f"\nDelta (with - without): Recall@5 {WITH_PREFIX['recall_at_5'] - without_prefix['recall_at_5']:+.3f}, "
          f"MRR {WITH_PREFIX['mrr'] - without_prefix['mrr']:+.3f}, "
          f"R-Precision {WITH_PREFIX['r_precision'] - without_prefix['r_precision']:+.3f}")


if __name__ == "__main__":
    main()
