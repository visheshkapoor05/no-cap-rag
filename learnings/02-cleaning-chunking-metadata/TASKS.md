# M2 — Chunking & Seed Golden Set

**Sep 13 – Sep 19** · Reasoning: [BLUEPRINT.md §5](../../project/BLUEPRINT.md#5-m2--chunking--seed-golden-set)

**Goal:** a defensible retrievable unit, plus 50 labelled questions so M3's choices are measured rather than eyeballed.

> Chunking bounds every downstream metric. If an answer spans two chunks, no
> retrieval strategy, fusion algorithm or reranker can fully recover it.

---

## Learn & decide

- [ ] **T-M2.1** `[LEARN]` — Write up all six chunking strategies
  Mechanism, best-fit case, failure mode for each:
  - [ ] Fixed-size — splits mid-clause; keep as the ablation baseline
  - [ ] Recursive character — treats a heading as just another newline
  - [ ] Semantic / percentile — *you already know this; focus on articulating why it's the wrong fit here*
  - [ ] **Structure-aware** ← the choice
  - [ ] **Contextual prefix** ← layered on top
  - [ ] Parent-document / small-to-big — revisit at M4 only if chunks prove too small
- [ ] **T-M2.2** `[DECIDE]` — Record the choice with a falsifiable expectation
  > "Structure-aware should beat fixed-size on Recall@5. If it doesn't, my model of this corpus is wrong."

  Writing the prediction *before* the experiment is what makes it an experiment.

## Practice & implement

- [ ] **T-M2.3** `[PRACTICE]` — Chunk 3 documents three ways, read the boundaries
  Print side by side. **Find one concrete case where fixed-size severs a rule from its exception** — save it verbatim, it goes in the README as the argument for structure-aware chunking.
- [ ] **T-M2.4** `[IMPLEMENT]` — Structure-aware chunker with token guards
  Split oversized sections at sub-headings or paragraphs; merge undersized ones into their neighbour. The guards are what stop a 4000-token section and a 12-token one both becoming single chunks.
- [ ] **T-M2.5** `[IMPLEMENT]` — Contextual prefix + full chunk schema
  `id, document_id, section_path, contextual_prefix, text, token_count, embedding_id, sparse_terms`.
  Target shape: `"Returns Policy v3.0 → §3.2 Discounted Items: <text>"`

  *Why this matters:* "This exception does not apply to items purchased during clearance events" has no subject when embedded alone. Prefixed, it becomes self-contained for both dense embedding and BM25.
- [ ] **T-M2.6** `[IMPLEMENT]` — Embedding cache keyed on `hash(text + model_id)`
  **Mandatory, not optional.** You will re-embed this corpus a dozen times while tuning in M3, and every run costs money. The `model_id` in the key is what keeps the cache correct when you add a second provider at V3.

## Author & verify

- [ ] **T-M2.7** `[AUTHOR]` — Write the 50-question seed golden set
  Budget 1–1.5 days — the chunk-level labelling is the slow part, not the question writing.
  Schema: `question, expected_answer, relevant_doc_ids, relevant_chunk_ids, answerable, difficulty, tags`

  | Category | n | Example | Done |
  |---|---|---|---|
  | Factual lookup | 15 | "How many days do I have to return an unopened item?" | [ ] |
  | Exact identifier | 8 | "What does error code POS-ERR-3021 mean?" *(the BM25-vs-dense discriminator)* | [ ] |
  | Multi-hop | 10 | "If a Gold member returns a discounted item bought partly with points, what happens to the points?" | [ ] |
  | Unanswerable | 8 | "What is the policy on cryptocurrency payments?" *(must abstain, not invent)* | [ ] |
  | Ambiguous | 5 | "What's the return window?" — differs by category | [ ] |
  | Version-sensitive | 4 | "What is the current Gold tier threshold?" — v1.0 and v2.0 disagree | [ ] |

  > The `answerable: false` rows are **the most valuable in the file.** They make
  > V2's abstention measurable, and almost no portfolio RAG project has them.

- [ ] **T-M2.8** `[MEASURE]` — Chunk statistics
  Token-count distribution · orphans under 50 tokens · chunks over the cap · % with a resolved `section_path`. A high orphan rate means your token guards are wrong — better to know now than after indexing.
- [ ] **T-M2.9** `[VERIFY]` — Prove the embedding cache works
  Run ingestion twice, assert the second run makes **zero** embedding API calls. Easy to believe and easy to get wrong.

## Deliver

- [ ] **T-M2.10** `[DOCS]` — Start `EVALUATION.md`
  Golden-set methodology: how questions were chosen, what the categories mean, how chunk labels were assigned, and the known limitations of a self-authored evaluation set.
- [ ] **T-M2.11** `[GIT]` — Branch → PR → merge `feat/m2-chunking-golden-set`
  Commit the golden set as a data file. Confirm the embeddings cache directory is gitignored — it's regenerable and large.

---

## Exit criteria

- [ ] Every chunk carries `section_path` and `contextual_prefix`
- [ ] Orphan rate under 5%; token distribution inspected
- [ ] Embedding cache proven — second identical run makes zero API calls
- [ ] 50 golden questions, all six categories, with chunk-level labels
- [ ] Written three-way chunking comparison with a concrete fixed-size failure example
