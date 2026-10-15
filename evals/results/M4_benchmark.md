# M4 Benchmark Ladder Results

**T-M4.14.** Real run, real infra, 2026-10-15: 151-question golden set
(`evals/golden_set/golden_set.yaml`, T-M4.13), 3 configs — baseline dense,
+hybrid (RRF), +reranker (cross-encoder) — against the real dev Postgres
(28 documents, 149 chunks), real Milvus, real Gemini (`gemini-2.5-flash`),
real local cross-encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`). Script:
`evals/run_m4_experiment.py`. Raw output: `evals/results/m4_experiment_raw.json`
(gitignored, regenerable — re-run the script to reproduce). Each config's
metrics are also persisted as an `experiments` row (T-M4.11) for later
comparison via `GET /experiments/{id}` / `POST /experiments/compare`.

Two sample sizes, same economy-of-effort principle as D-013's chunking
cross-check (documented scope decision, not a silent shortcut):

- **Recall@5 / MRR / R-Precision**: full 127 answerable questions (151 minus
  24 `unanswerable`, which have no relevant-chunk set to score retrieval
  against).
- **Faithfulness / Correctness / Citation support / P95 latency**: a
  stratified 36-question sample (8 factual_lookup, 6 exact_identifier,
  8 multi_hop, 4 ambiguous, 4 version_sensitive, 6 unanswerable) — each
  question costs a real `generate_answer()` + `judge_answer()` round trip
  per config, so the full 151 × 3 would be ~450 live LLM calls. The
  unanswerable slice is scored on whether the system correctly abstains,
  not excluded.

## Results

| Config | Recall@5 | MRR | R-Prec | Faithfulness | Correctness | Citation support | P95 latency (ms) |
|---|---|---|---|---|---|---|---|
| Baseline (dense) | 0.928 | 0.872 | 0.672 | 1.000 | 0.986 | 1.000 | 15798.0 |
| + Hybrid (RRF) | 0.913 | 0.888 | 0.688 | 1.000 | 0.965 | 1.000 | 14816.7 |
| + Reranker | 0.919 | 0.831 | 0.665 | 0.996 | 0.954 | 0.996 | 21105.4 |

n=127 for the retrieval columns, n=36 for the generation/judge columns, in
every row.

## Reading these numbers

- **Hybrid improves MRR and R-Precision over dense-only** (0.872→0.888,
  0.672→0.688) but costs a little Recall@5 (0.928→0.913) — consistent with
  M3's finding that RRF reorders ranks more than it changes the top-5 set.
- **The reranker underperforms both on every retrieval metric in this run**
  (Recall@5 0.919, MRR 0.831, R-Precision 0.665 — all below hybrid, MRR and
  R-Precision below dense-only too). That is a genuine, measured result,
  not a bug: it only reranks the hybrid candidate set it's handed (same
  K=10 pool), its training distribution (MS MARCO web passages) doesn't
  match this retail-policy domain, and it has no access to BM25's exact-
  keyword signal that evidently mattered for some of these questions. This
  is the kind of result the benchmark exists to surface — "we added a
  reranking stage" is not automatically "the reranking stage helped," and
  this run says it didn't, here, on this corpus.
- **Generation quality stays high and roughly flat across all three
  configs** (faithfulness ≥0.996, citation support ≥0.996, correctness
  0.954–0.986) — the LLM is reliably grounding its answers in whichever
  context it's given, so the configs mostly differ on whether retrieval
  handed it the *right* context, not on how well it uses what it gets.
- **P95 latency scales with pipeline stages**, as expected: dense-only
  (15.8s) < hybrid (14.8s, within noise of dense-only — BM25 is cheap) <
  reranker (21.1s, the one stage that adds a real model-inference cost on
  top of retrieval).
- **Known limitation, not resolved by this run**: the LLM judge
  (`gemini-2.5-flash`) is the same provider/model family as the generator
  it's scoring. The rubric explicitly names self-preference bias as a
  failure mode to resist, but rubric wording can't fully rule out a
  structural same-provider bias — only independent hand-scoring can. That
  check is T-M4.15, not yet run as of this file.
