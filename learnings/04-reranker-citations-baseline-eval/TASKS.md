# M4 — Reranking, Citations & Evaluation → **V1**

**Sep 27 – Oct 3** · Reasoning: [BLUEPRINT.md §7](../../project/BLUEPRINT.md#7-m4--reranking-citations--evaluation--v1)

**Goal:** cross-encoder reranking, citation-grounded generation, the full golden set, and the metrics that make V1 shippable.

> **First-stage retrieval optimizes recall. Reranking optimizes precision.**
> Recall lost at stage one is unrecoverable — a reranker cannot retrieve a
> document that was never returned. That asymmetry is why Recall@K is the
> primary first-stage metric even though answer quality is what you care about.

---

## Learn & practice

- [ ] **T-M4.1** `[LEARN]` — Bi-encoder vs. cross-encoder

  | | Bi-encoder (retrieval) | Cross-encoder (reranking) |
  |---|---|---|
  | How | Query and doc embedded *separately* | Fed through the model *together* |
  | Precompute | Yes — embed once, reuse forever | No — nothing precomputable |
  | Scale | Millions | ~50 candidates |
  | Accuracy | Lower — they never "see" each other | Higher — models their interaction |

  That contrast *is* why two-stage architectures exist: cheap-and-broad, then expensive-and-narrow.
- [ ] **T-M4.2** `[LEARN]` — Recall@K, Precision@K, MRR, NDCG
  **Hand-compute all four on a toy 5-query set before writing any code.** Know what each is *blind* to — that's how you avoid optimizing the wrong metric for a week.
- [ ] **T-M4.3** `[LEARN]` — LLM-judge rubric design and its failure modes
  Position bias, verbosity bias, self-preference. Design the rubric to resist each rather than hoping they don't apply.
- [ ] **T-M4.4** `[PRACTICE]` — Run a local cross-encoder on a fixed candidate set
  Inspect what moved up, what moved down, **and whether you agree with it.** If the reordering looks wrong to you, find out why before wiring it in.

## Implement

- [ ] **T-M4.5** `[IMPLEMENT]` — `Reranker` interface + local cross-encoder
  Runs on CPU for a top-50 candidate set. Local rather than an API — free to iterate on, reproducible, and you learn more from running the model than calling an endpoint.
- [ ] **T-M4.6** `[IMPLEMENT]` — Context builder: dedupe, token budget, citation mapping
  Overlapping chunks from two retrievers must be deduped; assembled context must fit a token budget; every surviving chunk keeps its ID so the citation can point back at it.
- [ ] **T-M4.7** `[IMPLEMENT]` — LLM provider abstraction + Gemini generation adapter
  Mirrors the embedding abstraction from T-M3.7. Both are what the PRD means by "pluggable LLM/embedding/reranker".
- [ ] **T-M4.8** `[IMPLEMENT]` — Citation-grounded **structured** generation + malformed-output recovery
  Pydantic-validated claims with chunk IDs. Structured-output requests *do* fail — retry with a repair prompt, then a structured error.

  > **Forward-looking decision:** M7 must verify claims individually. Free text
  > means M7 begins by parsing claims back out of prose; structured claims here
  > make M7's extraction nearly free.
- [ ] **T-M4.9** `[IMPLEMENT]` — Metrics module — all four, hand-written
  ~20 lines each ([D-008](../../project/DECISIONS.md)). Optionally cross-check against Ragas *afterwards* as validation — but write them yourself first, or you can't debug a number that looks wrong.
- [ ] **T-M4.10** `[IMPLEMENT]` — LLM judge with a fixed rubric
  Temperature 0, versioned rubric text. Faithfulness, answer correctness, citation support rate.
- [ ] **T-M4.11** `[IMPLEMENT]` — Experiment runner + persistence
  Every run records dataset version, pipeline config, embedding model, reranker model and LLM version. Reproducibility is a PRD requirement and is unrecoverable if not captured at run time.
- [ ] **T-M4.12** `[API]` — `POST /query`, `POST /evaluate`, `GET /experiments/{id}`, `POST /experiments/compare`
  The full API surface the PRD specifies. `/query` returns answer, citations, trace ID and a timing breakdown.

## Author & measure

- [ ] **T-M4.13** `[AUTHOR]` — Expand the golden set to 150–200 questions
  **Write the adversarial cases now, not at M2.** You've watched the system fail for three weeks — those observed failure modes make far better adversarial questions than anything you'd have invented up front.
- [ ] **T-M4.14** `[MEASURE]` — Full benchmark ladder — Experiments D, E, F

  | Config | Recall@5 | MRR | Faithfulness | Correctness | Citation support | P95 latency |
  |---|---|---|---|---|---|---|
  | Baseline (dense) | | | | | | |
  | + hybrid | | | | | | |
  | + reranker | | | | | | |

  Plus the context-builder ablation (F) and the contextual-prefix comparison (E).
- [ ] **T-M4.15** `[VERIFY]` — Hand-score 20 answers; measure judge agreement
  **The gate on everything downstream.** If the judge disagrees with you on 8 of 20, the rubric is broken and every generation metric is noise — fix it *before* V2 is built on it.
- [ ] **T-M4.16** `[MEASURE]` — Failure analysis: document three real failures
  A PRD acceptance criterion. For each: what was asked, what came back, the root cause, and the measured effect of the fix. These are the most-read paragraphs in any portfolio README.

## Ship V1

- [ ] **T-M4.17** `[DOCS]` — Write `ARCHITECTURE.md`
  The diagram plus the reasoning: why two-stage retrieval, why hybrid, why these interfaces. Link out to `DECISIONS.md` rather than repeating it.
- [ ] **T-M4.18** `[DOCS]` — Complete `EVALUATION.md` and the full README
  README: architecture diagram · quick start · API examples · **the benchmark table** · failure analysis · limitations. Lead with the numbers.
- [ ] **T-M4.19** `[DOCS]` — Start `CHANGELOG.md`
  Mechanical if you've used conventional commits; archaeology if you haven't.
- [ ] **T-M4.20** `[GIT]` — Tag `v1.0.0` and publish the GitHub Release
  Release notes lead with the benchmark table and the dense-vs-hybrid result. First of the three PRD-mandated releases.
- [ ] **T-M4.21** `[VERIFY]` — Clean-clone reproducibility check
  Clone into a fresh directory, follow **only** the README, confirm the stack comes up and `/query` answers. Anything you had to know from memory is a documentation bug.

---

## V1 exit criteria *(from the PRD)*

- [ ] Every answer has traceable evidence linked to document/chunk IDs
- [ ] Dense-only vs. hybrid benchmarked, with numbers
- [ ] Answerable *and* unanswerable questions in the set
- [ ] Every document has stable provenance metadata
- [ ] Judge/human agreement measured on ≥20 answers
- [ ] Three failure cases documented with root causes and measured fixes
- [ ] `v1.0.0` tagged, GitHub Release published, clean clone reproduces the benchmark
