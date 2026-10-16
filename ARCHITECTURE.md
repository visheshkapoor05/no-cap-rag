# Architecture

What the pipeline actually does, end to end, and why each stage exists.
This is the reasoning; [`DECISIONS.md`](./DECISIONS.md) is the record of
where the build knowingly deviated from the PRD and why — this doc links
out to it rather than repeating it.

## Pipeline

```
Question
   │
   ▼
┌─────────────────────────────────────────────┐
│  Retrieval (POST /retrieve, app/api/retrieve.py)
│                                               │
│  DenseRetriever ──┐                          │
│  (Milvus, FLAT,    ├──► RRFFusion ──► top-K  │
│   COSINE, D-006)   │    or Weighted          │
│  SparseRetriever ──┘    Fusion               │
│  (BM25, rank_bm25,                           │
│   D-005)                                     │
└─────────────────────────────────────────────┘
   │ top-K RetrievedChunk
   ▼
┌─────────────────────────────────────────────┐
│  Reranking (optional, app/reranking/)        │
│  CrossEncoderReranker (ms-marco-MiniLM)      │
│  re-scores the top-K, keeps top-rerank_k     │
└─────────────────────────────────────────────┘
   │ top-5 (default) chunks, best-first
   ▼
┌─────────────────────────────────────────────┐
│  Context assembly (app/generation/context_builder.py)
│  dedupe exact-duplicate text, greedy token-  │
│  budget fill, [n]-bracket citation numbering,│
│  document version rendered into each header  │
└─────────────────────────────────────────────┘
   │ BuiltContext (prompt-ready text + citation map)
   ▼
┌─────────────────────────────────────────────┐
│  Generation (app/generation/generate.py)     │
│  GeminiLLMProvider.generate_structured() →   │
│  GeneratedAnswer{answerable, summary, claims}│
│  one repair pass if a claim cites a bracket   │
│  number that isn't actually in the context    │
└─────────────────────────────────────────────┘
   │ GeneratedAnswer, resolve_claims() → real chunk refs
   ▼
POST /query response          POST /evaluate also runs:
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │  Judge (app/evaluation/judge.py)
                        │  Faithfulness, Correctness,│
                        │  Citation support — scored │
                        │  against the same context  │
                        │  and, if given, a reference │
                        │  answer                     │
                        └───────────────────────────┘
```

Every stage behind its own `Protocol` interface
(`RetrievalStrategy`, `EmbeddingProvider`, `Reranker`, `LLMProvider`) —
the pipeline composes config, not code branches. `/retrieve`'s
`strategy` field picks `dense`/`bm25`/`hybrid_rrf`/`hybrid_weighted`
without the endpoint knowing how any of them actually work internally.

## Why two-stage retrieval (dense + optional reranking)

A bi-encoder (`DenseRetriever`, Milvus) embeds the corpus once and the
query once per request — it has to generalize to a query it's never
seen, over millions of chunks, in milliseconds. A cross-encoder
(`CrossEncoderReranker`) sees the *actual* query and *actual* candidate
text together at inference time, so it can model their real interaction
— but that means it can't be precomputed, so it only ever runs on a
small top-K shortlist, never the whole corpus.

**T-M4.14 measured this tradeoff for real on this corpus, and the
reranker lost** — it edges hybrid on Recall@5 but is clearly worse on
MRR/R-Precision (the rank-*position* metrics, which is the entire point
of adding a reranking stage). Root cause and the full number table:
[`evals/results/M4_benchmark.md`](./evals/results/M4_benchmark.md),
[`evals/results/M4_failure_analysis.md`](./evals/results/M4_failure_analysis.md#failure-3-the-cross-encoder-reranker-underperformed-on-every-retrieval-metric).
The architecture keeps the reranking *stage* (it's a real, tested,
swappable component — `use_reranker: false` is one request field away)
but the current recommendation is not to enable it by default on this
corpus: a pretrained cross-encoder's training distribution (MS MARCO web
search) doesn't automatically transfer to a new domain, and this
project measured that instead of assuming the opposite.

## Why hybrid (dense + BM25 + RRF), not dense alone

Dense embeddings capture semantic similarity but are comparatively weak
on exact identifiers (policy codes like `SOP-RET-014`) — two strings
that are lexically almost identical but semantically about different
things embed close together, which is exactly backwards for a code
lookup. BM25 is the reverse: strong on exact lexical overlap, blind to
paraphrase. `RRFFusion` combines both ranked lists by reciprocal-rank
(not score — scores from different retrievers aren't on comparable
scales), with `WeightedFusion` available when scores *are* known to be
comparable and a project wants explicit control over the blend ratio.
M3's real 50-question run found hybrid+RRF won on MRR and R-Precision
overall and specifically rescued the `exact_identifier` category BM25
alone was weakest on, not strongest — see
[`evals/results/M3_retrieval.md`](./evals/results/M3_retrieval.md) for
why that result was counter to the original prediction.

## Why citations are bracket numbers, not chunk IDs

A model can only cite what it can *see* in the prompt. The context
block only ever shows a small `[n]` marker before each chunk, never the
real UUID — so `GeneratedAnswer.claims[].citation_numbers` are small
integers, resolved back to real `Citation` objects
(`resolve_claims()`) only after generation. A real bug caught by testing
against the actual model (not assumed): early on, the schema asked for
`chunk_ids` and the model dutifully cited the literal bracket number it
could see (`"2"`) instead of hallucinating a UUID it was never shown —
the fix was changing what the schema asks for, not adding validation to
reject the model's (reasonable) behavior.

## Why document version is part of the citation block

T-M4.16's failure analysis found that two chunks from different
document versions, sharing an identical section path, rendered with
*identical* headers — neither the generator nor the judge had any way
to tell which one was current. `document_version` is now part of both
`ContextSource`/`Citation` and the rendered block
(`"Loyalty Program Rules 2.0 → §4..."`), and `generate.py`'s system
prompt has an explicit rule: when two chunks disagree and carry
different version numbers, the higher one is current. Full
before/after measurement:
[`evals/results/M4_failure_analysis.md`](./evals/results/M4_failure_analysis.md#failure-1-version-conflicts-were-unresolvable-because-version-never-reached-the-prompt).

## Why an LLM judge, and its one named, unresolved limitation

Faithfulness/Correctness/Citation support (`app/evaluation/judge.py`)
are scored by the same family of model (Gemini) that generates the
answers being judged — a genuine same-provider self-preference risk the
rubric can name and instruct against but can't structurally eliminate.
T-M4.15 hand-scored 20 real answers independently, *before* reading the
judge's own score, specifically to test whether that risk shows up in
practice rather than assuming the rubric fixes it: 18/20 (90%) exact or
near-exact agreement, zero disagreement on Faithfulness or Citation
support, two real Correctness disagreements that both traced to one
concrete, now-fixed bug (see above) rather than a broken rubric. Full
writeup: [`evals/results/M4_handscore_agreement.md`](./evals/results/M4_handscore_agreement.md).

## Why every benchmark run is persisted, not just printed

`app/evaluation/experiment.py`'s `experiments` table records the
dataset version and every model version (embedding, reranker, LLM)
alongside the metrics a run measured. "Which embedding model produced
this Recall@5" is unrecoverable after the fact if it isn't captured at
run time — not a hypothetical, this project's own M3→M4 transition
changed the embedding model's effective behavior and would have made a
stored-metrics-only comparison ambiguous without this.

## Interfaces, for extension

| Interface | Implementations | Swappable via |
|---|---|---|
| `RetrievalStrategy` | `DenseRetriever`, `SparseRetriever` | `RetrieveRequest.strategy` |
| `EmbeddingProvider` | `GeminiEmbeddingProvider` | `app/embeddings/gemini.py`'s singleton |
| `Reranker` | `CrossEncoderReranker` | `QueryRequest.use_reranker` |
| `LLMProvider` | `GeminiLLMProvider` | `app/generation/gemini.py`'s singleton |

Each is a `Protocol`, not a base class — a new implementation needs to
match the shape, not inherit from anything in this codebase.
