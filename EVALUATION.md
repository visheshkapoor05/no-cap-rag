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
  better questions than inventing them up front.
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
