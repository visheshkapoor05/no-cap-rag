# Decisions — what we chose, and what we rejected

`Project_1_Advanced_RAG_PRD_Architecture.pdf` is the source-of-truth planning
doc and is never edited directly. Every place we knowingly build something
different from it — or make a choice it left open — gets logged here with the
reasoning and the rejected alternatives.

This file is also a portfolio artifact in its own right. "I chose X over Y
for reason Z, and here's the ablation that proves it" is the single most
useful thing a reader of this repo can find.

---

## D-001 · Vector database: Milvus

**PRD says:** Qdrant or LanceDB.
**We're doing:** Milvus.

**Why:** Prior hands-on experience from an earlier RAG build. Vector-DB
concepts (collections, ANN index types, scalar filtering, partitioning) are
transferable regardless of engine, so the learning value is unchanged, and
the time saved on tooling goes into the parts that are actually new.

**Rejected:** Qdrant (excellent filtering, but a second tool to learn for no
new concepts); LanceDB (embedded/serverless is genuinely simpler, but the
in-process model hides the client/server and connection-lifecycle concerns
that a production system has to handle).

**Reversible?** Yes, cheaply — dense retrieval sits behind a strategy
interface (`app/retrieval`), so the engine swap is one adapter.

---

## D-002 · Corpus domain: retail

**PRD says:** "public corporate sources + synthetic enterprise corpus",
domain unspecified.
**We're doing:** Retail — public retail policy pages plus synthetic retail
enterprise documents (SOPs, loyalty rules, incident postmortems, runbooks).

**Why:**
1. **Domain expertise.** Prior retail work means golden questions can be
   written from real knowledge instead of guessed at — the single biggest
   quality lever on the whole evaluation set.
2. **Exact identifiers everywhere.** SKU codes, tier names, SOP numbers,
   error codes, promo codes. This is what makes BM25 genuinely earn its
   place next to dense retrieval instead of being a token gesture — the
   dense-vs-hybrid ablation will show a real gap, not noise.
3. **Natural version conflicts.** Returns policies, loyalty tiers and
   promotion rules are revised constantly and supersede each other. V3's
   version-aware retrieval has real material to work with rather than
   synthetic version numbers bolted onto static documents.
4. **Natural multi-hop.** "If a Gold member returns a discounted item bought
   partly with points, what happens to the points?" genuinely requires the
   returns policy *and* the loyalty policy *and* the promotions policy.
   Multi-hop questions that are real rather than contrived.

**Rejected:** Cloud provider docs (no cloud access right now); financial
filings (long-context strength, but golden-question authoring would be slow
without domain knowledge); OSS project docs (good identifier density, but no
"corporate knowledge" framing and no natural version conflicts).

---

## D-003 · Models: Gemini API now, local models at the end

**PRD says:** "Pluggable LLM/embedding/reranker" — provider unspecified.
**We're doing:** Gemini API for embeddings and generation through V1/V2. A
local embedding model (BGE-M3 or equivalent) added at V3 as a *second*
provider, not a replacement.

**Why:** Gemini access already exists, and no local GPU is available. Adding
a local model at the end is deliberately sequenced: by then the provider
abstraction is written and tested, so plugging in a second provider is the
thing that *proves* the abstraction works. Doing it first would just be
setup with nothing to prove.

**Consequence to design around:** you will re-embed the corpus many times
while tuning chunking (M2) and that costs money per run. An embedding cache
keyed on `hash(text + model_id)` is therefore a **required** M2 task, not a
nice-to-have. See T-M2.6.

**Rejected:** All-local from the start (no GPU, and weaker generation would
undercut the faithfulness verification that is the entire point of V2);
all-hosted forever (locks the scale benchmark behind API spend, and never
exercises the provider abstraction).

**Note:** verify current Gemini model IDs against Google's docs when
implementing — don't hardcode from memory.

---

## D-004 · Seed golden set moves earlier (M2, not M4)

**PRD says:** golden evaluation set is step 9 of V1, after retrieval and
generation are built.
**We're doing:** a ~50-question *seed* golden set at M2, expanded to the full
set at M4.

**Why:** M3 asks you to choose between dense, BM25, and several fusion
configurations. Without a golden set at M3, those choices get made on
eyeballed results — which is exactly the "vibes-based RAG tuning" this whole
project exists to argue against. Fifty labelled questions is enough to see a
real Recall@K difference between dense-only and hybrid, and cheap enough to
write in an afternoon.

The full set (150–200 questions, all categories, with the harder multi-hop
and adversarial cases) still lands at M4 as the PRD intends — the seed set is
an addition, not a replacement.

**Rejected:** following the PRD ordering literally (would make every M3
decision unmeasured); building the full set at M2 (front-loads a week of
question authoring before you know what the pipeline's actual failure modes
look like — the best adversarial questions are written *after* you've seen
the system fail).

---

## D-005 · BM25 engine: `rank_bm25` in-process, not OpenSearch

**PRD says:** "BM25" — engine unspecified.
**We're doing:** `rank_bm25` (pure Python, in-memory) at M3.

**Why:** At corpus scale (a few thousand chunks) an in-memory BM25 index is
instant and completely inspectable — you can print per-term IDF and see
exactly why a document scored what it did, which is the entire point of
learning BM25 rather than calling it. OpenSearch would add a JVM service,
index mappings and analyzer configuration: real infrastructure learning, but
*not* retrieval learning, and it obscures the scoring you're trying to
understand.

**Revisit at:** M10 (scale benchmark). If the corpus grows past what fits
comfortably in memory, migrate to OpenSearch or Milvus's native sparse/BM25
support. Sparse retrieval sits behind the same strategy interface as dense,
so this is an adapter swap.

**Rejected:** OpenSearch at M3 (infrastructure cost with no learning payoff
at this scale); Milvus native hybrid search (it would do dense + sparse +
fusion in one call — convenient, but it hides the RRF step, and implementing
RRF yourself is an explicit M3 learning goal).

---

## D-006 · Milvus index: FLAT first, HNSW at scale

**PRD says:** nothing about index type.
**We're doing:** `FLAT` (exact search) for V1/V2, `HNSW` from M10.

**Why:** FLAT is exact brute-force search — no recall loss. At a few thousand
chunks it's fast enough that approximate search buys nothing measurable.
Critically: an ANN index has its own recall/speed tradeoff knobs, and any
recall shortfall it introduces would be **indistinguishable from a bug in
your retrieval logic**. Starting exact means every recall number you see in
M3/M4 is attributable to your chunking and retrieval choices alone.

Switch to HNSW at M10 where the scale benchmark makes it meaningful — and
then measure the recall you trade away for the speed you gain. That
measurement is a much better portfolio artifact than "I used HNSW because
everyone uses HNSW."

**Rejected:** HNSW from the start (introduces an unmeasured confounder into
every retrieval number in V1); IVF_FLAT (cluster-based, better suited to much
larger corpora than this).

---

## D-007 · LangGraph from V2, orchestration only

**PRD says:** "LangGraph from V2".
**We're doing:** exactly that — and explicitly *not* using it for retrieval,
fusion, reranking, or evaluation.

**Why:** V1 is a linear pipeline; plain Python is clearer and has less
indirection. V2 introduces conditional branching (simple vs. complex routing)
and a bounded retry loop, which is genuinely a state machine — hand-rolling
that with flags and while-loops gets messy fast, and LangGraph's checkpointing
makes the retry state inspectable in traces.

But the retrieval/fusion/evaluation core stays hand-written. The portfolio
argument of this project is *end-to-end ownership of measurable retrieval*;
if that core lives inside a framework's abstractions, the argument weakens to
"wired a framework together."

**Rejected:** LangGraph from V1 (indirection with no branching to justify it);
full LangChain (would absorb exactly the components this project needs to own);
hand-rolled state machine at V2 (doable, but the retry/checkpoint plumbing is
real work with no learning payoff).

---

## D-008 · Metrics implemented by hand before reaching for Ragas

**PRD says:** "Python harness + optional Ragas/DeepEval".
**We're doing:** implement Recall@K, Precision@K, MRR and NDCG ourselves at
M4. Optionally cross-check against Ragas afterwards.

**Why:** These metrics are ~20 lines each, and the differences between them
(why NDCG rewards rank position and Recall@K doesn't; why MRR only cares
about the first hit) are precisely what needs to be understood to interpret
the results. Calling a library returns numbers without that understanding —
and misreading a metric is how you optimize the wrong thing for two weeks.

Cross-checking against Ragas afterwards is a genuinely useful validation step
and worth doing.

**Rejected:** Ragas-first (faster to numbers, much slower to understanding,
and it becomes very hard to debug a metric you didn't write when a result
looks wrong).

---

## D-009 · Superseded documents: filter at query time

**PRD says:** version-aware retrieval with `effective_date`, `version` and
`supersedes` links — mechanism unspecified.
**We're doing:** index every version; filter to the currently-effective one at
query time unless the question is explicitly historical.

**Why:** it preserves history, so "what was the return window in March?"
stays answerable and the PRD's provenance requirement holds. Milvus scalar
filtering handles it natively, so it costs nothing structurally.

**Rejected:** *delete-on-supersede* (simple, but destroys history and breaks
provenance — you can no longer show what the system would have said last
quarter); *recency re-ranking* (a soft scoring boost, which means a
strongly-matching old document can still outrank a weakly-matching current
one — wrong for policy, where currency is binary rather than a preference).

**Decided at:** M8. Logged here at planning time so the M1 corpus was built
with real version chains to support it.

---

## Open questions

Things deliberately not decided yet, with the milestone that will settle them.

| Question | Decide at | Why not now |
|---|---|---|
| Template vs. LLM-generated contextual prefix | M4 (Experiment E) | Needs measurement — start with the free deterministic version and only pay for LLM prefixes if the numbers justify it |
| Parent-document retrieval (small-to-big) | M4 | Only worth the indirection if evidence analysis shows chunks are too small to answer from |
| Keep `rank_bm25` or migrate to OpenSearch / Milvus sparse | M10 | Depends entirely on whether in-memory BM25 is still viable at scale-benchmark size |
| Cheap classifier vs. LLM call for routing | post-V2 | Needs routing data to train on; optimizing first is what the PRD warns against |
