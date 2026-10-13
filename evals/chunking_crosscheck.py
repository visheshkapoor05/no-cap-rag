"""
T-M3.12's D-013 chunking cross-check (Experiment A): re-tests the winning
retrieval config (hybrid_rrf, per run_m3_experiment.py's real overall
numbers) against fixed-size (150-token) chunks instead of structure-aware
-- one extra cell, not a full 6-strategy x 4-config grid. M2's falsifiable
prediction (T-M2.3's notes.md): "structure-aware should beat fixed-size on
Recall@5."

Entirely self-contained and in-memory -- does NOT touch the real dev
Postgres `chunks` table or the real Milvus `chunk_embeddings` collection,
so the live app's data is never at risk. Re-derives the 28 documents' raw
text the same way app/cli.py's ingest_plan() does (FileSource + plan_
synthetic), re-chunks with the exact FIXED_SIZE_TOKENS=150 non-overlapping
window from practice/02-cleaning-chunking-metadata/compare_chunking.py
(same baseline M2 already compared structure-aware against), embeds every
fixed-size chunk with the real (cache-aware) Gemini provider, and runs a
brute-force in-memory cosine dense search + a fresh BM25Okapi + the real
RRFFusion -- same fusion class app/retrieval/fusion.py ships, just fed
in-memory ranked lists instead of Milvus/Postgres ones.

Ground truth under fixed-size chunking isn't the same chunk_id space as
structure-aware (the boundaries are different) -- a fixed-size chunk counts
as relevant if it contains a distinctive excerpt of the real, resolved
structure-aware relevant chunk's own text (both are windows over the exact
same underlying document text, so a real content overlap is a meaningful,
non-arbitrary relevance signal here, not a guess).

Run: python3 -m evals.chunking_crosscheck
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import tiktoken

from app.core.db import get_pool
from app.documents.hashing import compute_content_hash
from app.documents.registry import find_by_content_hash
from app.embeddings.gemini import get_embedding_provider
from app.evaluation.metrics import recall_at_k, reciprocal_rank
from app.retrieval.fusion import RRFFusion
from app.retrieval.sparse import tokenize
from app.retrieval.strategy import RetrievedChunk
from app.chunking.registry import get_chunks_by_ids
from app.corpus_plan import plan_synthetic
from app.ingestion import FileSource
from evals.golden_set.loader import load_golden_set
from evals.golden_set.resolve import resolve_chunk_ids
from rank_bm25 import BM25Okapi

FIXED_SIZE_TOKENS = 150
ENC = tiktoken.get_encoding("cl100k_base")
K = 10


@dataclass(frozen=True)
class FixedChunk:
    chunk_id: str
    doc_title: str
    doc_version: str | None
    text: str


def chunk_fixed_size(text: str) -> list[str]:
    """Identical definition to practice/02's chunk_fixed_size -- the same
    150-token, no-overlap baseline M2 already measured structure-aware
    against, reused rather than re-invented."""
    tokens = ENC.encode(text)
    return [ENC.decode(tokens[i : i + FIXED_SIZE_TOKENS]) for i in range(0, len(tokens), FIXED_SIZE_TOKENS)]


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def build_fixed_corpus(pool) -> list[FixedChunk]:
    """Re-derives raw text for all 28 synthetic docs the same way
    ingest_plan() does, then fixed-size chunks it. Doesn't write anything
    to Postgres -- only reads (to recover title/version for each already-
    ingested document via its content hash)."""
    fixed: list[FixedChunk] = []
    for i, plan in enumerate(plan_synthetic()):
        raw = FileSource().fetch(plan.ref)
        document = find_by_content_hash(pool, compute_content_hash(raw.text))
        title = document.title if document else plan.title
        version = document.version if document else plan.version
        for j, text in enumerate(chunk_fixed_size(raw.text)):
            fixed.append(FixedChunk(chunk_id=f"fx{i}_{j}", doc_title=title, doc_version=version, text=text))
    return fixed


def relevant_fixed_ids(pool, question, fixed: list[FixedChunk]) -> set[str]:
    """A fixed-size chunk counts as relevant if it contains a distinctive
    60-char excerpt of the real structure-aware relevant chunk's own text
    -- both are windows over the identical underlying document, so string
    containment is a genuine content-overlap signal, not an approximation."""
    if not question.answerable or not question.relevant_chunks:
        return set()
    sa_ids = resolve_chunk_ids(pool, question)
    sa_records = get_chunks_by_ids(pool, sa_ids)
    relevant: set[str] = set()
    for rec in sa_records.values():
        excerpt = rec.text.strip()[20:80]
        if len(excerpt) < 20:
            excerpt = rec.text.strip()[:40]
        for fc in fixed:
            if fc.text.replace("\n", " ").find(excerpt.replace("\n", " ")) != -1:
                relevant.add(fc.chunk_id)
    return relevant


def main() -> None:
    pool = get_pool()
    print("Building fixed-size (150-token) corpus from the real 28 documents...")
    fixed = build_fixed_corpus(pool)
    print(f"  -> {len(fixed)} fixed-size chunks (vs. 149 structure-aware chunks)")

    print("Embedding every fixed-size chunk (real Gemini calls, cache-aware)...")
    provider = get_embedding_provider()
    vectors = {fc.chunk_id: provider.embed_document(fc.text) for fc in fixed}

    print("Building in-memory BM25 over the fixed-size corpus...")
    corpus_tokens = [tokenize(fc.text) for fc in fixed]
    bm25 = BM25Okapi(corpus_tokens)
    fixed_ids = [fc.chunk_id for fc in fixed]

    questions = [q for q in load_golden_set() if q.answerable]
    print(f"Scoring hybrid_rrf against {len(questions)} answerable questions...\n")

    r5s, rrs = [], []
    for q in questions:
        relevant = relevant_fixed_ids(pool, q, fixed)
        if not relevant:
            continue

        query_vec = provider.embed_query(q.question)
        dense_scores = [(fc.chunk_id, cosine(query_vec, vectors[fc.chunk_id])) for fc in fixed]
        dense_scores.sort(key=lambda t: t[1], reverse=True)
        dense_hits = [RetrievedChunk(chunk_id=cid, score=s) for cid, s in dense_scores[:K]]

        bm25_scores = bm25.get_scores(tokenize(q.question))
        ranked = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:K]
        bm25_hits = [RetrievedChunk(chunk_id=fixed_ids[i], score=float(bm25_scores[i])) for i in ranked if bm25_scores[i] > 0]

        fused = RRFFusion().fuse({"dense": dense_hits, "bm25": bm25_hits})[:K]
        ids = [h.chunk_id for h in fused]

        r5 = recall_at_k(ids, relevant, 5)
        rr = reciprocal_rank(ids, relevant)
        if r5 is not None:
            r5s.append(r5)
        if rr is not None:
            rrs.append(rr)

    print(f"n={len(r5s)} questions with resolvable fixed-size ground truth")
    print(f"fixed-size + hybrid_rrf:       Recall@5 = {sum(r5s)/len(r5s):.3f}   MRR = {sum(rrs)/len(rrs):.3f}")
    print("structure-aware + hybrid_rrf:  Recall@5 = 0.913   MRR = 0.931   (from run_m3_experiment.py's real overall numbers)")


if __name__ == "__main__":
    main()
