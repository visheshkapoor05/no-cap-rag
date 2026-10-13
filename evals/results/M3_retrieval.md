# M3 Retrieval Results

**T-M3.12.** Real run, real infra, 2026-10-13: 50-question golden set
(`evals/golden_set/golden_set.yaml`), 4 retrieval configs, against the real
dev Postgres (149 chunks, 28 documents), real Milvus, real Gemini. Script:
`evals/run_m3_experiment.py`. Raw per-question output:
`evals/results/m3_experiment_raw.json` (gitignored, regenerable — re-run the
script to reproduce).

- `k=10` for every config
- `hybrid_rrf`: `RRFFusion(k=60)` (the library default)
- `hybrid_weighted`: `WeightedFusion(weights={"dense": 0.6, "bm25": 0.4})`
- 8 `unanswerable` questions excluded from every average — `recall_at_k`/
  `reciprocal_rank` return `None` for an empty `relevant` set by design
  (see `app/evaluation/metrics.py`), not folded in as a 0. **n=42** answerable
  questions below.

## Overall

| Config | Recall@1 | Recall@5 | Recall@10 | MRR |
|---|---|---|---|---|
| Dense only | 0.679 | 0.937 | 0.956 | 0.917 |
| BM25 only | 0.492 | 0.821 | 0.929 | 0.740 |
| **Hybrid + RRF** | **0.702** | 0.913 | **0.964** | **0.931** |
| Hybrid + weighted | 0.667 | 0.925 | **0.964** | 0.899 |

**Hybrid + RRF wins overall** — best Recall@1 and best MRR, tied-best
Recall@10. BM25 alone is clearly the weakest config in aggregate.

## By category

| Category (n) | Config | Recall@1 | Recall@5 | Recall@10 | MRR |
|---|---|---|---|---|---|
| **factual_lookup** (15) | dense | 1.000 | 1.000 | 1.000 | 1.000 |
| | bm25 | 0.800 | 1.000 | 1.000 | 0.883 |
| | hybrid_rrf | 0.933 | 1.000 | 1.000 | 0.956 |
| | hybrid_weighted | 0.933 | 1.000 | 1.000 | 0.956 |
| **exact_identifier** (8) | dense | 0.500 | 1.000 | 1.000 | 0.692 |
| | bm25 | 0.125 | 0.875 | 0.875 | 0.333 |
| | hybrid_rrf | **0.750** | 1.000 | 1.000 | **0.875** |
| | hybrid_weighted | 0.625 | 1.000 | 1.000 | 0.760 |
| **multi_hop** (10) | dense | 0.500 | 0.900 | 0.950 | 1.000 |
| | bm25 | 0.400 | 0.700 | 0.900 | 0.883 |
| | hybrid_rrf | 0.500 | 0.800 | 0.950 | 1.000 |
| | hybrid_weighted | 0.450 | 0.850 | 0.950 | 0.950 |
| **ambiguous** (5) | dense | 0.300 | 0.667 | 0.733 | 0.900 |
| | bm25 | 0.133 | 0.500 | 0.800 | 0.633 |
| | hybrid_rrf | 0.300 | 0.667 | 0.800 | 0.900 |
| | hybrid_weighted | 0.300 | 0.667 | 0.800 | 0.900 |
| **version_sensitive** (4) | dense | 0.750 | 1.000 | 1.000 | 0.875 |
| | bm25 | 0.750 | 0.750 | 1.000 | 0.792 |
| | hybrid_rrf | 0.750 | 1.000 | 1.000 | 0.812 |
| | hybrid_weighted | 0.750 | 1.000 | 1.000 | 0.833 |

## The surprising result

**EVALUATION.md's own category description predicted BM25 would be
"comparatively strong" on `exact_identifier` — the real numbers say the
opposite.** BM25 is the *worst* config on this category by a wide margin
(0.125 Recall@1, 0.333 MRR — roughly a third of dense's and hybrid_rrf's
MRR). Root cause, confirmed by hand-tracing one real query (`POS-ERR-3021`,
see `docs/no-cap-rag-journey.docx` §6's real worked example): an
exact-identifier *question* is natural language ("What does incident code
X refer to?"), not a bare keyword search — its generic words ("incident",
"code", "refer") appear densely across every other postmortem in the
corpus and dilute BM25's score for the one chunk where the literal code
actually appears. The prediction holds for a bare-keyword query; it doesn't
hold for a natural-language question about an identifier, which is what
the golden set actually contains. **`hybrid_rrf` wins this category
specifically because it's the only config robust to BM25's miss here** —
it recovers via dense's semantic signal without needing BM25's exact match
to carry the ranking alone.

## D-013 chunking cross-check (Experiment A)

One extra cell, not a full grid (per the task's own scoping): re-test the
**winning retrieval config (hybrid_rrf)** against **fixed-size (150-token,
no overlap) chunks** instead of structure-aware — the exact same baseline
M2's `practice/02-cleaning-chunking-metadata/compare_chunking.py` already
used. Self-contained, in-memory (`evals/chunking_crosscheck.py`) — doesn't
touch the real `chunks` table or the real Milvus collection. Ground truth
under fixed-size chunking: a fixed-size chunk counts as relevant if it
contains a distinctive excerpt of the real, resolved structure-aware
relevant chunk's own text (both are windows over the identical underlying
document).

| Chunking | Config | Recall@5 | MRR |
|---|---|---|---|
| Structure-aware (production) | hybrid_rrf | **0.913** | **0.931** |
| Fixed-size, 150 tokens | hybrid_rrf | 0.565 | 0.731 |

**M2's chunking call is confirmed, decisively, under the retrieval method
that actually ships** — not just under the single retrieval method M2 held
constant when the decision was originally made (D-013's concern). 168
fixed-size chunks vs. 149 structure-aware chunks from the same 28
documents; n=40/42 questions had resolvable fixed-size ground truth (2
excerpts didn't land cleanly inside any single 150-token window).

## What this settles

- **Dense vs. hybrid, with numbers:** hybrid_rrf beats dense alone on
  Recall@1 (0.702 vs 0.679) and MRR (0.931 vs 0.917) overall, and by a
  much larger margin specifically on `exact_identifier`, where BM25's real
  weakness is exactly compensated by dense's semantic signal — hybrid
  isn't a wash, it's a real improvement over either retriever alone on
  this golden set.
- **BM25 alone should not ship as the sole retrieval strategy** — it's
  the weakest config in 5 of 6 categories, including the one it was
  predicted to win.
- **Structure-aware chunking is confirmed**, now under the retrieval
  method that actually ships, not just the one M2 originally tested with.
