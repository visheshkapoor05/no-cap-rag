# Evaluation

How this project measures itself, starting with the golden set built at M2.
Metrics are introduced here deliberately early — see
[D-010](./DECISIONS.md#d-010--recallk-and-mrr-move-earlier-m2-not-m4) — so
M3's retrieval comparisons have real numbers to report from day one instead
of a promise to measure things later.

## The golden set

`evals/golden_set/golden_set.yaml` — 50 questions, hand-authored against the
real, fully-chunked corpus (`evals/golden_set/build.py` resolves every
relevant chunk against live Postgres at build time; a spec that doesn't
resolve to exactly one real chunk fails the build immediately, so a typo in
a question's reference can't silently ship).

### Schema

```yaml
id: multi_hop-01
category: multi_hop
question: "A GOLD_TIER member returns an item..."
expected_answer: "The points portion is refunded back..."
relevant_docs:
  - { title: "Loyalty Program Rules", version: "2.0" }
relevant_chunks:
  - { title: "Loyalty Program Rules", version: "2.0", section: "4. Points Handling on Returns" }
answerable: true
difficulty: hard
tags: [multi_hop, loyalty, returns]
```

`relevant_docs`/`relevant_chunks` are **natural-key references** (title +
version + section), never raw Postgres UUIDs — see
[D-015](./DECISIONS.md#d-015--golden-set-references-chunks-by-natural-key-titleversionsection-never-by-postgres-uuid).
`evals/golden_set/resolve.py` turns a spec into the UUID a retrieval
evaluation actually needs, re-resolved at the point of use rather than
frozen once — a UUID baked in at authoring time goes stale the instant the
corpus is re-ingested, since `gen_random_uuid()` assigns a new id on every
insert, not a deterministic one derived from content.

### Categories, and why each one exists

| Category | n | What it's actually testing |
|---|---|---|
| Factual lookup | 15 | The baseline case — one clear answer in one chunk. If this category fails, nothing more advanced is worth measuring yet. |
| Exact identifier | 8 | Codes like `POS-ERR-3021`, `SOP-RET-014` — the specific case dense embeddings are comparatively weak at and BM25 is comparatively strong at. The dense-vs-hybrid discriminator. |
| Multi-hop | 10 | Answers that genuinely require combining evidence from two chunks (sometimes two documents) — not just two facts that happen to be near each other. |
| Unanswerable | 8 | Questions with no answer anywhere in the corpus, confirmed absent by checking the real corpus, not assumed. The system should abstain, not invent an answer (V2 concern) — but Recall@K/MRR need to know these exist today, since folding them into a retrieval average would silently distort it (see `relevant_chunks: []`, `answerable: false`). |
| Ambiguous | 5 | Questions with a genuinely different correct answer depending on context (e.g. "when do points expire?" has three different real answers depending on account type) — multiple `relevant_chunks` entries, all legitimately correct. |
| Version-sensitive | 4 | Where two real document versions disagree (e.g. `GOLD_TIER` threshold: $1,000 under v1.0, $1,500 under v2.0) — `relevant_docs`/`relevant_chunks` point at the *currently effective* version only, so a retriever surfacing the stale version gets penalized correctly. |

### How chunk labels were assigned

Every `expected_answer` and every `relevant_chunks` entry was written by
reading the real chunk text directly (via `evals/chunk_stats.py`-style
queries against the live corpus), not recalled from memory or guessed from
a document title. The multi-hop questions specifically reuse the corpus's
own documented cross-references (e.g. the Cash Handling SOP ↔ Failed Refund
Runbook circular escalation, the Loyalty Platform ADR's explicit note that
it wasn't revisited after the double-credit incident) rather than
constructing artificial combinations.

### Known limitations — stated now, not discovered later

- **Single author, no inter-rater check.** Every label was assigned by the
  same person who built the corpus and already knows the intended answer —
  there's no second labeler to catch a case where the "obvious" answer
  reflects authoring intent more than what the text actually, unambiguously
  supports.
- **Synthetic-only coverage.** All 50 questions reference the `synthetic/`
  corpus (22 of 28 documents touched); **zero reference the 16 `public/`
  documents** — the public half was ingested (T-M1.4/T-M1.9) but never
  chunked for this seed set. A real gap, not a deliberate exclusion;
  worth a public-corpus pass before the set is considered representative
  of the *whole* corpus rather than just its synthetic half.
- **50 is a seed, not a benchmark.** T-M4.13 explicitly expands this to
  150–200 questions once M3's real failure modes are known — writing
  adversarial cases *after* watching the system fail for real produces
  better questions than inventing them up front. **Done as of M4** — see
  the M4 section below; the set is now 151 questions.
- **A synthetic corpus can't fully replace real-world messiness.** The
  `mixed/` documents deliberately inject real extraction failure modes
  (broken tables, scrambled columns), but the underlying language is still
  one author's writing style — more uniform than a genuinely heterogeneous
  real corpus would be.

## Metrics

**Implemented now (M2), hand-written per
[D-008](./DECISIONS.md#d-008--metrics-implemented-by-hand-before-reaching-for-ragas):**

- **Recall@K** — of the chunks that are actually relevant, how many did the
  top K retrieved results contain? Blind to order within K.
- **MRR (Mean Reciprocal Rank)** — how high up was the *first* relevant
  result, averaged across questions? Blind to everything after the first
  hit.

Both hand-computed on a toy 5-query set first (T-M2.7,
`learnings/02-cleaning-chunking-metadata/notes.md`) before being
implemented (`app/evaluation/metrics.py`, T-M2.8) and tested against the
real 50-question golden set's actual structure — including the real edge
cases a toy example surfaced: an unanswerable question is a genuine `0/0`
(excluded from the mean, not scored `0.0`), and a real miss (relevant
chunks exist, none retrieved) is `0.0`, which is a different claim than
"nothing was relevant to find" and must stay distinguishable in code, not
just in prose.

**Deferred to M4:** Precision@K, R-Precision, and NDCG — see
[D-010](./DECISIONS.md#d-010--recallk-and-mrr-move-earlier-m2-not-m4) for
why the split, and
[D-014](./DECISIONS.md#d-014--precisionk-at-a-fixed-k-is-the-wrong-headline-precision-metric--use-r-precision)
for why R-Precision, not fixed-K Precision@K, is the one that actually gets
reported once they exist.

## M4: 151 questions, generation-quality metrics, and an LLM judge

The golden set grew from 50 to 151 questions at T-M4.13
(`evals/golden_set/build.py`), all newly authored against a fresh full
read of all 28 documents' real chunk text — not reused or paraphrased
from the original 50. `version_sensitive` grew from 4 to 7 (not
proportionally to ~12): the corpus has exactly two genuinely versioned
document pairs, every real version-to-version difference was enumerated
by hand, and inventing a fake one to hit a round number would violate
the golden set's whole reason to exist.

### R-Precision and NDCG (deferred from M2, implemented at M4)

`app/evaluation/metrics.py` (T-M4.9) adds `precision_at_k()`,
`r_precision()`, and `ndcg()`. **R-Precision**, not fixed-K Precision@K,
is the headline precision metric reported — see
[D-014](./DECISIONS.md#d-014--precisionk-at-a-fixed-k-is-the-wrong-headline-precision-metric--use-r-precision)
for why a fixed K systematically under-reports precision on a corpus
where most questions have exactly one relevant chunk. NDCG rewards rank
position via `1/log2(rank+1)` discounting, normalized against the ideal
ordering — implemented but not yet the headline metric in any report;
R-Precision and MRR together already cover what this corpus's question
mix needs distinguished.

### Generation-quality metrics

Three dimensions, scored by an LLM judge (`app/evaluation/judge.py`,
`judge_rubric_v2`) against the real context a generation call was shown,
and a reference answer when one exists:

- **Faithfulness** — of the answer's claims, how many are actually
  supported by the specific context chunk(s) they cite? A claim citing
  a real, valid bracket number whose chunk doesn't say what the claim
  states is unfaithful even though the citation itself is "valid."
- **Correctness** — does the answer's summary correctly and completely
  address the question, compared against the reference answer when one
  exists?
- **Citation support rate** — the same faithfulness fraction, reported
  as its own explicit number: how many claims hold up under direct
  scrutiny of their cited context.

The rubric names three specific failure modes to resist rather than
hoping against them generically: position bias, verbosity bias, and
self-preference (the judge is the same model family as the generator —
a real, honestly-stated limitation the rubric can instruct against but
not structurally eliminate; see below). `judge_rubric_v2` (bumped from
v1 at T-M4.16) also requires the judge to verify an abstention's premise
against the context's own version markers before accepting it as
correct — v1 accepted `answerable=false` at face value, which T-M4.15's
hand-scoring caught as a real bug, not a hypothetical one.

### T-M4.15: hand-score agreement — the gate on everything above

20 real answers, independently scored before reading the judge's own
verdict, specifically to test whether the judge's structural
self-preference risk shows up in practice. **18/20 (90%) exact or
near-exact three-way agreement, zero disagreement on Faithfulness or
Citation support.** The two real disagreements were both on
Correctness and both traced to one concrete, fixable bug (version never
reaching the prompt — fixed at T-M4.16) rather than a broken rubric.
Full writeup, including the raw comparison table:
[`evals/results/M4_handscore_agreement.md`](./evals/results/M4_handscore_agreement.md).

### The full benchmark ladder

Three retrieval configs (baseline dense, +hybrid, +reranker) × seven
metrics (Recall@5, MRR, R-Precision, Faithfulness, Correctness, Citation
support, P95 latency), plus two ablations — does the contextual prefix
earn its keep (Experiment E), does the context builder's dedup/budget
logic change generation quality (Experiment F). Full numbers and
reading: [`evals/results/M4_benchmark.md`](./evals/results/M4_benchmark.md).
Three documented real failures, one fixed and measured, two left as
honestly-reported open limitations:
[`evals/results/M4_failure_analysis.md`](./evals/results/M4_failure_analysis.md).

## Supporting proofs

- **Chunk statistics** (T-M2.10, `evals/chunk_stats.py`) — token-count
  distribution, orphan rate, MAX-cap violations, and `section_path`
  resolution over the real, full corpus. Orphan rate 2.7%, 0 cap
  violations, confirming the chunking guards (T-M2.4) hold at population
  scale, not just on the 3-document sample they were tuned from.
- **Embedding cache correctness** (T-M2.11, `tests/test_embedding_cache.py`)
  — proven against the real 149-chunk corpus: a fresh cache embeds every
  chunk once; a brand-new cache instance pointed at the same file makes
  zero further calls. The actual cross-run scenario M3's repeated tuning
  passes depend on, not just an in-process cache hit.
