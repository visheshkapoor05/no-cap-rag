# M8 — Version-aware Retrieval, Freshness & Evaluation Harness

**Oct 13 – Oct 23** · Reasoning: [BLUEPRINT.md §11](../../project/BLUEPRINT.md)

**Goal:** answers reflect the *current* policy; sources are recrawled on a schedule; every improvement is provable against a baseline.

> **The failure this prevents is invisible without it.** A system that
> confidently quotes last year's return window looks exactly like a system
> that's working — the citation is real, the text is accurate, the document
> exists. It's simply no longer in force.
>
> Your corpus was designed in M1 with real version chains for exactly this.

---

## Learn & decide

- [ ] **T-M8.1** `[LEARN]` — Version-aware retrieval design
  Effective-date filtering, supersession chains, "as of" queries. Also: what happens when two documents are both current and contradict each other — a real retail situation (regional policy vs. national).
- [ ] **T-M8.2** `[LEARN]` — Freshness strategies for URL-sourced corpora
  Content-hash change detection, crawl scheduling, politeness/rate limits, and detecting when a page has *moved* rather than changed.
- [ ] **T-M8.3** `[LEARN]` — Airflow fundamentals: DAGs, scheduling, idempotent tasks
  Scoped tightly to one scheduled ingestion DAG. The PRD justifies Airflow as "uses DE experience where justified" — this is the justified case, not an excuse to orchestrate everything.
- [ ] **T-M8.4** `[LEARN]` — Regression and ablation harness design
  What makes a metric comparison valid across runs: fixed dataset version, fixed seed, recorded config. Why comparing two runs with different golden-set versions is meaningless.
- [ ] **T-M8.5** `[DECIDE]` — How to handle a superseded document

  | Approach | Mechanism | Trade-off |
  |---|---|---|
  | Delete on supersede | Drop the old version at ingest | Simple, but destroys history — "what was the policy in March?" becomes unanswerable, and PRD provenance breaks |
  | **Filter at query time** ✅ | Index everything; filter to `effective_date`-current unless the question is historical | **The choice.** Milvus scalar filtering handles it natively, history preserved, "as of" questions answerable |
  | Re-rank by recency | Boost newer documents in scoring | Soft signal — a strongly-matching old doc can still outrank a weakly-matching current one. Wrong for policy, where currency is binary, not a preference |

  Record as **D-009** in `DECISIONS.md`.

## Implement — version awareness

- [ ] **T-M8.6** `[IMPLEMENT]` — Metadata filters in the retrieval layer
  Milvus scalar filtering on `effective_date` and supersession status, plumbed through the `RetrievalStrategy` interface so **both dense and sparse honour the same filter**.
- [ ] **T-M8.7** `[IMPLEMENT]` — Supersession resolution
  Walk the `supersedes` chain to find the current version of a document family. Handle the broken cases: a chain with a gap, or a cycle from a data-entry error.
- [ ] **T-M8.8** `[IMPLEMENT]` — Temporal query handling
  Default to current; detect "as of \<date\>" and historical phrasing and filter accordingly. **Cite the version *and* its effective date** in the answer, so currency is visible to the reader.
- [ ] **T-M8.9** `[AUTHOR]` — Add version-sensitive golden questions
  Expand beyond M2's four: current-policy questions where the superseded version gives a **plausible but wrong** answer, plus explicit historical "as of" questions.

## Implement — freshness & harness

- [ ] **T-M8.10** `[DOCKER]` — Add Airflow to Docker Compose
  Scheduler, webserver and its metadata DB. **Keep it in an optional Compose profile** so the core stack stays lightweight for anyone just trying the project out.
- [ ] **T-M8.11** `[IMPLEMENT]` — Scheduled recrawl DAG
  Re-fetch public URLs, compare content hash, re-ingest **only on change** — creating a new version row rather than overwriting. This is T-M1.7's hash decision paying off.
- [ ] **T-M8.12** `[IMPLEMENT]` — Ablation runner
  Run N pipeline configurations over the same golden set in one command and emit a comparison table. Turns every future "does X help?" question into one command instead of a manual afternoon.
- [ ] **T-M8.13** `[IMPLEMENT]` — Baseline snapshot + regression comparison
  Store a named baseline result set; compare any run against it with per-metric deltas and a configurable tolerance. **M9's CI gate consumes this directly.**

## Measure & deliver

- [ ] **T-M8.14** `[MEASURE]` — Experiment L: version-awareness on/off
  On the version-sensitive subset. Expect a large, clean improvement — one of the most legible wins in the whole project.
- [ ] **T-M8.15** `[VERIFY]` — Freshness end to end
  Modify a locally-cached source, run the DAG, confirm a new version row appears and retrieval switches to it. Then run again unchanged and confirm it's a **no-op**.
- [ ] **T-M8.16** `[DOCS]` — Document versioning and freshness in `ARCHITECTURE.md`
  Include the three-approaches table and why query-time filtering won. Update the architecture diagram with the recrawl path.
- [ ] **T-M8.17** `[GIT]` — Branch → PR → merge `feat/m8-versioning-freshness`
  **Commit the baseline snapshot** — it's the reference every later run is judged against.

---

## Exit criteria

- [ ] Superseded policies are never returned for current-policy questions
- [ ] Answers cite the document version *and* its effective date
- [ ] Recrawl re-ingests only on content change — proven **both ways**
- [ ] Ablation runner produces a comparison table in one command
- [ ] A named baseline exists for M9's regression gate to compare against
