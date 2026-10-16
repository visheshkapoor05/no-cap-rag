# T-M4.16: Failure Analysis

Three real failures, found via real runs against the real corpus (T-M4.14's
benchmark ladder and T-M4.15's hand-scoring), each with what was asked,
what came back, the root cause, and — where a fix was tractable — the
measured effect of applying it.

## Failure 1: version conflicts were unresolvable because version never reached the prompt

**What was asked**: `version_sensitive-05` — "Under the current loyalty
program rules, how quickly is the points portion of a return refunded?"
**What came back**: the system declared the question unanswerable,
citing "conflicting information" between two context chunks (5 business
days vs. 24 hours). **Expected**: 24 hours, under the current Loyalty
Program Rules v2.0.

A second, opposite-direction instance of the same bug: `version_sensitive
-06` — "does a restocking fee apply to an opened electronics item
accepted outside the standard return window?" The system confidently
answered **Yes, 15%**, citing a chunk that was actually from the
superseded Returns Policy v2.0. Expected: **No** — the current v3.0
doesn't mention a restocking fee at all.

**Root cause**: `app/generation/context_builder.py`'s citation block
rendered `[n] {document_title} → §{section}: {text}` — no version. Two
chunks from different document versions, sharing the same section path,
rendered with *identical* headers. Neither the generator nor the judge
had any way to tell which chunk was current. The two failures are the
same bug in opposite directions: one case produced false uncertainty
(abstaining when a real answer existed), the other produced false
confidence (citing a stale chunk as if current).

**Fix applied**: added `document_version` to `ContextSource`/`Citation`
(`app/generation/context_builder.py`), rendered into the block header
(`"Loyalty Program Rules 2.0 → §4..."`), propagated through
`app/api/retrieve.py`'s `RetrievedChunkResponse` and every eval script's
chunk-resolution helper. Added an explicit version-disambiguation rule to
`generate.py`'s `SYSTEM_PROMPT` ("the higher version number is current").
Updated the judge rubric (`judge.py`, bumped `judge_rubric_v1` →
`judge_rubric_v2`) to stop accepting an `answerable=false` premise at
face value — it now has to check whether the chunks actually carry
distinguishing version markers before scoring an abstention as correct.

**Measured effect** (same two questions, re-run against the fixed
pipeline, hybrid_rrf, real Gemini):

| Question | Correctness before | Correctness after |
|---|---|---|
| `version_sensitive-05` | 0.0 (wrongful abstention, hand-scored — the old judge rubric had scored this 1.0, itself part of the bug) | **1.00** — now answers "24 hours" citing `[2] Loyalty Program Rules 2.0`, judge: faith=1.00, correct=1.00, cite=1.00 |
| `version_sensitive-06` | 0.0 (confidently cited stale v2.0 fee as current) | **0.50** — now correctly states v3.0 doesn't mention a restocking fee (the right fact), but still sets `answerable=false` instead of `true` with a claim, so the judge penalizes the framing even though the content is now right |

`-05` is fully fixed. `-06` is a real, measured partial fix: the
version-disambiguation problem this failure was actually about is
solved (it now reads the *current* chunk and reports its content
correctly) — what's left is a separate, narrower issue: the model treats
"the current policy doesn't mention X" as insufficient grounds to answer
rather than as itself a complete, citable answer ("no, because the
provision was removed"). That's a real residual gap, honestly reported
rather than smoothed over, and a candidate for a follow-up system-prompt
rule ("absence of a provision in the current version is itself an
answerable claim") rather than another version-surfacing fix.

## Failure 2: an ambiguous question only got answered from one of its three contexts

**What was asked**: `ambiguous-05` — "Who can authorize an override?"
**Expected**: three separate, unrelated answers depending on context —
a shift lead/store manager for most Returns Exception Matrix rows, a
regional manager specifically for disputed final-sale tagging, and the
affected employee's own agreement for a non-emergency schedule change.
**What came back**: only the first context (Returns Exception Matrix
overrides) was addressed; the regional-manager and employee-agreement
cases were never mentioned. Hand-scored correctness: 0.4; judge: 0.6
(both independently flagged this as a real, material miss — see
[`M4_handscore_agreement.md`](M4_handscore_agreement.md)).

**Root cause**: retrieval, not generation. `_run_query`'s context
window caps at the top 5 chunks after rerank/fusion (`rerank_k=5` by
default). For a genuinely ambiguous question whose correct answer spans
three unrelated source documents (Returns Exception Matrix, a
disputed-tagging escalation doc, and the Employee Handbook's scheduling
section), the top-5 window pulled back chunks dominated by one of the
three — the other two contexts simply never made it into the prompt for
the generator to even consider. This is a retrieval-breadth problem, not
a context-assembly or generation-faithfulness one: everything the model
*did* say was faithful and well-cited.

**Why no fix was applied here**: the comparable `ambiguous-06` question
("how much advance notice is required?") *did* get fully answered across
all three of its contexts in the same run — same pipeline, same k=5,
different retrieval outcome. That rules out "k=5 is categorically too
narrow for ambiguous questions" as the root cause; it's query-specific
(the phrase "authorize an override" apparently scores much more
similar to the Returns Exception Matrix content than to the scheduling
or disputed-tagging content, for this specific corpus's embeddings).
A blanket fix (e.g. raising k for the whole `ambiguous` category) would
trade a different cost (more budget pressure, more chances for the
dedup/context-builder logic Experiment F found doesn't even trigger yet
at today's scale) for an uncertain gain on this one query. Flagged as a
real, open limitation rather than patched blindly — a genuine retrieval
-breadth vs. ambiguous-question-coverage tradeoff for V2 to actually
measure, not a quick fix to claim here without evidence it generalizes.

## Failure 3: the cross-encoder reranker underperformed on every retrieval metric

**What was asked**: T-M4.14's Experiment D — does adding a reranking
stage improve retrieval quality over hybrid (RRF) alone?
**What came back**: no, not on the metrics that matter most for ranking
quality. `plus_reranker` edges out `plus_hybrid` on Recall@5 (0.919 vs.
0.913 — reranking did pull a few more relevant chunks into the top 5),
but is clearly *below* it on MRR (0.831 vs. 0.888) and R-Precision
(0.665 vs. 0.688) — and below `baseline_dense` on those same two metrics
too. MRR and R-Precision are the ones that specifically test rank
*position*, which is the entire point of adding a reranking stage — a
slight Recall@5 gain doesn't offset reordering results to be worse-
ranked on average. Full numbers: [`M4_benchmark.md`](M4_benchmark.md).

**Root cause**: the reranker (`cross-encoder/ms-marco-MiniLM-L-6-v2`) is
trained on MS MARCO, a web-search-query/passage dataset — its learned
notion of "relevant" doesn't transfer cleanly to this corpus's retail
-policy register (cross-referenced policy IDs, exception matrices,
numbered procedural steps). It also only reorders the candidates the
hybrid stage already handed it — it can't recover BM25's exact-keyword
signal for a candidate hybrid under-ranked, and reordering alone can
only hurt MRR/R-Precision if its relevance judgments disagree with the
corpus's actual structure more often than they agree.

**Why no fix was applied here**: the realistic fixes (fine-tuning the
cross-encoder on this domain, or swapping to a different pretrained
reranker) are each their own multi-day experiment with its own real
infra cost, not a same-session patch. Documented as a genuine, measured
negative result and a concrete recommendation instead: **don't enable
the reranker by default on this corpus as currently configured** —
ship `hybrid_rrf` without reranking, and treat reranker fine-tuning as
scoped future work with its own acceptance criteria, not an unverified
default "more stages = better" assumption.
