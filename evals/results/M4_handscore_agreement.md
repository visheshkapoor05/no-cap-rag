# T-M4.15: Hand-Score Agreement

**20 real question/answer/judge-score records**, real run 2026-10-16,
fixed to hybrid_rrf retrieval. Deliberately a *different* 20 questions
than T-M4.14's 36-question generation sample (skips past the questions
already used there — scoring the same answers again wouldn't test
anything new about the judge). Script: `evals/capture_handscore_sample.py`.
Raw per-question records: `evals/results/m4_handscore_sample.json`
(gitignored, regenerable).

**Method**: read each question, the real context the model saw, the
generated answer's claims, and the expected answer — and score
Faithfulness / Correctness / Citation support myself, *before* reading
the judge's own score or reasoning for that question, to avoid anchoring
on its verdict.

## Results

| ID | Category | Mine (F / C / Ci) | Judge (F / C / Ci) | Agreement |
|---|---|---|---|---|
| factual_lookup-09 | factual_lookup | 1.0 / 1.0 / 1.0 | 1.00 / 1.00 / 1.00 | exact |
| factual_lookup-10 | factual_lookup | 1.0 / 0.9 / 1.0 | 1.00 / 1.00 / 1.00 | close |
| factual_lookup-11 | factual_lookup | 1.0 / 1.0 / 1.0 | 1.00 / 1.00 / 1.00 | exact |
| factual_lookup-12 | factual_lookup | 1.0 / 1.0 / 1.0 | 1.00 / 1.00 / 1.00 | exact |
| factual_lookup-13 | factual_lookup | 1.0 / 1.0 / 1.0 | 1.00 / 1.00 / 1.00 | exact |
| factual_lookup-14 | factual_lookup | 1.0 / 1.0 / 1.0 | 1.00 / 1.00 / 1.00 | exact |
| exact_identifier-07 | exact_identifier | 1.0 / 1.0 / 1.0 | 1.00 / 1.00 / 1.00 | exact |
| exact_identifier-08 | exact_identifier | 1.0 / 0.6 / 1.0 | 1.00 / 0.50 / 1.00 | close |
| exact_identifier-09 | exact_identifier | 1.0 / 1.0 / 1.0 | 1.00 / 1.00 / 1.00 | exact |
| multi_hop-09 | multi_hop | 1.0 / 1.0 / 1.0 | 1.00 / 1.00 / 1.00 | exact |
| multi_hop-10 | multi_hop | 1.0 / 1.0 / 1.0 | 1.00 / 1.00 / 1.00 | exact |
| multi_hop-11 | multi_hop | 1.0 / 1.0 / 1.0 | 1.00 / 1.00 / 1.00 | exact |
| multi_hop-12 | multi_hop | 0.8 / 0.8 / 0.8 | 1.00 / 1.00 / 1.00 | minor gap |
| ambiguous-05 | ambiguous | 1.0 / 0.4 / 1.0 | 1.00 / 0.60 / 1.00 | close |
| ambiguous-06 | ambiguous | 1.0 / 1.0 / 1.0 | 1.00 / 1.00 / 1.00 | exact |
| **version_sensitive-05** | version_sensitive | 1.0 / **0.0** / 1.0 | 1.00 / **1.00** / 1.00 | **major** |
| version_sensitive-06 | version_sensitive | 1.0 / 0.0 / 1.0 | 1.00 / 0.00 / 1.00 | exact |
| unanswerable-07 | unanswerable | 1.0 / 1.0 / 1.0 | 1.00 / 1.00 / 1.00 | exact |
| **unanswerable-08** | unanswerable | 1.0 / **0.3** / 1.0 | 1.00 / **1.00** / 1.00 | **moderate** |
| unanswerable-09 | unanswerable | 1.0 / 1.0 / 1.0 | 1.00 / 1.00 / 1.00 | exact |

**Mean absolute difference**: Faithfulness 0.01, Correctness 0.115,
Citation support 0.01. **2/20 (10%) show a significant disagreement**
(|Δ| ≥ 0.3) — both on Correctness, both version/unanswerable edge cases,
zero on Faithfulness or Citation support.

## Verdict: the rubric is not broken, but has one specific, named gap

13/20 questions are exact three-way agreement; a further 5/20 are within
0.2 on every dimension (reasonable scorer variance, not a rubric
problem). That's the result T-M4.15 exists to confirm: Faithfulness and
Citation support were never in question across the whole sample. The two
real disagreements are both on Correctness, and both trace to the same
specific rubric gap, not a generically "weak" judge:

- **`version_sensitive-05`** (my 0.0 vs. judge's 1.0): the real context
  the model saw contains two chunks both headed identically — `Loyalty
  Program Rules → §4. Points Handling on Returns` — one saying "5
  business days," one saying "24 hours," **with no version marker
  anywhere in either chunk's visible text or document title.** The
  system abstained, citing the contradiction. The judge's rubric says an
  abstention is correct "if the context genuinely does not support an
  answer" — but the judge took that premise at face value instead of
  checking it. Given what the model actually saw, abstaining was a
  defensible call, not a clear failure — so on reflection this is less
  "the judge is wrong" and more "the judge never got a chance to be
  right," because the real bug is one step upstream: `build_context()`'s
  citation block (`app/generation/context_builder.py`) never includes
  the source document's version, so the one piece of information that
  would have resolved the contradiction (which chunk is current) never
  reaches the prompt at all.
- **`unanswerable-08`** (my 0.3 vs. judge's 1.00): the judge's own
  reasoning quotes context that plainly and explicitly answers the
  question ("doorbuster events... are not eligible for matching...").
  The judge is right that the answer is faithful and well-supported —
  my lower score reflects that the golden set labels this question
  `unanswerable`, which this real retrieval result casts doubt on. This
  looks like a golden-set labeling issue, not a judge or generation
  failure — worth a follow-up read of `evals/golden_set/build.py`'s
  `unanswerable-08` entry, not a rubric fix.

**`version_sensitive-06`** (both scored Correctness 0.0, exact
agreement) is the mirror image of `-05` and confirms the same root
cause from the opposite direction: the stale, superseded electronics
-restocking-fee chunk also carries no version marker, so it got cited
with full confidence as if current. One root cause — document version
never reaching the generation prompt — produces two opposite-looking
symptoms (wrongful confidence here, wrongful abstention in `-05`). This
becomes T-M4.16 failure case #1.

**Net finding**: judge agreement holds at 90% (18/20) with zero
disagreement on Faithfulness or Citation support, and the two real
misses both point at the same concrete, fixable upstream bug rather than
a broken rubric. No rubric rewrite needed before T-M4.16; the version
-surfacing bug is the thing to actually fix there.
