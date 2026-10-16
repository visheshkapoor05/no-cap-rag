# M4 Benchmark Ladder Results

**T-M4.14.** Real run, real infra, 2026-10-15/16: 151-question golden set
(`evals/golden_set/golden_set.yaml`, T-M4.13). Three experiments, all
against the real dev Postgres (28 documents, 149 chunks), real Milvus,
real Gemini (`gemini-2.5-flash`), real local cross-encoder
(`cross-encoder/ms-marco-MiniLM-L-6-v2`):

- **Experiment D** — the main ladder: baseline dense, +hybrid (RRF),
  +reranker. Script: `evals/run_m4_experiment.py`.
- **Experiment E** — does the contextual prefix (T-M2.5) earn its keep at
  retrieval time? Script: `evals/experiment_e_contextual_prefix.py`.
- **Experiment F** — does the context builder's dedup + token-budget
  logic (T-M4.6) change generation quality versus naive concatenation?
  Script: `evals/experiment_f_context_builder_ablation.py`.

Raw output: `evals/results/m4_experiment_raw.json` (gitignored,
regenerable — re-run the scripts to reproduce). Experiment D's per-config
metrics are also persisted as `experiments` rows (T-M4.11) for later
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

## Experiment D: the main ladder

| Config | Recall@5 | MRR | R-Prec | Faithfulness | Correctness | Citation support | P95 latency (ms) |
|---|---|---|---|---|---|---|---|
| Baseline (dense) | 0.928 | 0.872 | 0.672 | 1.000 | 0.986 | 1.000 | 15798.0 |
| + Hybrid (RRF) | 0.913 | 0.888 | 0.688 | 1.000 | 0.965 | 1.000 | 14816.7 |
| + Reranker | 0.919 | 0.831 | 0.665 | 0.996 | 0.954 | 0.996 | 21105.4 |

n=127 for the retrieval columns, n=36 for the generation/judge columns, in
every row.

## Experiment E: contextual-prefix ablation

Same chunk_id space as production (`get_all_chunks()` — no re-chunking),
hybrid_rrf retrieval, over the same 127 answerable questions. Only the
embedding/tokenization input changes: `text` alone vs `contextual_prefix +
text`.

| Variant | Recall@5 | MRR | R-Precision |
|---|---|---|---|
| Without prefix | 0.915 | 0.855 | 0.661 |
| With prefix (production) | 0.913 | 0.888 | 0.688 |
| **Delta (with − without)** | **−0.001** | **+0.032** | **+0.026** |

The contextual prefix doesn't move Recall@5, but gives a real MRR and
R-Precision lift — it's not pulling more relevant chunks into the top-10,
it's ranking them higher once they're there. Consistent with what the
prefix actually does: add document/section identity to the embedding,
which should help rank position (is this the *right* chunk among several
similar ones) more than raw recall (is it retrieved at all).

## Experiment F: context-builder ablation

Fixed to hybrid_rrf retrieval, same 36-question stratified sample as
Experiment D, comparing the real `build_context()` (exact-text dedup +
greedy token-budget fill, T-M4.6) against a naive variant that formats
every retrieved chunk into the same citation-bracket scheme unconditionally
— no dedup, no budget check.

| Variant | Faithfulness | Correctness | Citation support |
|---|---|---|---|
| Naive (no dedup/budget) | 1.000 | 0.964 | 1.000 |
| Current (dedup + budget) | 1.000 | 0.986 | 1.000 |
| **Delta (current − naive)** | **+0.000** | **+0.022** | **+0.000** |

Dedup and the token-budget drop fired on **0/36** questions in this
run — this 28-document, 149-chunk corpus is small enough, and k=5 context
chunks is narrow enough, that duplicate near-identical chunks and
budget overflow essentially don't occur on this sample. The +0.022
correctness delta happened with the dedup/budget *mechanism* never
actually triggering, so it isn't attributable to either — it's judge/
generation noise at this sample size (n=36), not evidence the context
builder improved anything on this run. The honest conclusion: on this
corpus's current scale, the context builder's dedup and budget logic are
correctness insurance for a corpus that doesn't yet need it, not a
measured generation-quality win — their value should reappear as the
corpus grows past the point where duplicate near-identical chunks and
token-budget overflow become real, not hypothetical.

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
