# M5 — Router & Decomposition

**Oct 4 – Oct 6** · Reasoning: [BLUEPRINT.md §8](../../project/BLUEPRINT.md#8-m5--router--decomposition)

**Goal:** questions routed by complexity; multi-part questions decomposed into sub-queries. First use of LangGraph.

> V1 sends every question down an identical path — a simple lookup and a
> multi-hop question get identical treatment, so you either overspend on the
> easy ones or underserve the hard ones.

---

## Learn & practice

- [ ] **T-M5.1** `[LEARN]` — LangGraph fundamentals
  State, nodes, edges, conditional edges, checkpointing.
  **Scope discipline:** it orchestrates. It does not retrieve, fuse, or evaluate — those stay hand-written, or the portfolio argument weakens to "wired a framework together" ([D-007](../../project/DECISIONS.md)).
- [ ] **T-M5.2** `[LEARN]` — Routing and decomposition strategies
  Classification approaches, sub-query generation, and **over-decomposition as the dominant failure mode** — splitting a simple question into four sub-queries costs 4× *and* retrieves worse, because each fragment carries less context to match against.
- [ ] **T-M5.3** `[PRACTICE]` — Toy 3-node LangGraph with one conditional edge
  Nothing RAG-related. Learn the framework in isolation so that when the real graph misbehaves you know it's your logic, not your understanding of the library.
- [ ] **T-M5.4** `[PRACTICE]` — Hand-decompose 10 multi-hop golden questions
  Worked example: *"If a Gold member returns a discounted item bought partly with points, what happens to the points?"* →
  1. Return policy for discounted items?
  2. How are points handled on returns?
  3. Do promotional purchases affect point accrual?

  Note what a single flat query would have missed — that's your target behaviour.

## Implement

- [ ] **T-M5.5** `[IMPLEMENT]` — Port the V1 pipeline into a LangGraph graph, **behaviour-identical**
  Pure refactor, zero functional change. Re-run the benchmark and confirm the numbers are unchanged. **Any movement at this step is a bug** — finding it now is far cheaper than after three more nodes are added.
- [ ] **T-M5.6** `[IMPLEMENT]` — Router node: simple vs. complex
  Start with an LLM call; optimizing to a cheap classifier before you have data is exactly what the PRD warns against. **Record the decision *and its reasoning* in the trace** — an unexplainable routing decision is worse than no routing.
- [ ] **T-M5.7** `[IMPLEMENT]` — Decomposer node + per-sub-query retrieval and merge
  Sub-queries retrieved independently, evidence merged and deduped before generation. Every sub-query traceable back to the parent question.
- [ ] **T-M5.8** `[API]` — Extend `/query` with routing metadata
  Route taken, sub-queries generated, evidence per sub-query. The API surface is how the verification story becomes visible from outside.

## Measure & deliver

- [ ] **T-M5.9** `[MEASURE]` — Experiment H: decomposition on/off
  - [ ] Multi-hop subset improves
  - [ ] **Simple questions did not regress** — the over-decomposition check, and the result people forget to look for
- [ ] **T-M5.10** `[GIT]` — Branch → PR → merge `feat/m5-router-decomposition`
  Commit `evals/results/M5_decomposition.md` alongside the code.

---

## Exit criteria

- [ ] Graph reproduces V1 benchmark numbers exactly before router/decomposer switch on
- [ ] Routing decisions visible in traces, with reasoning
- [ ] Multi-hop sub-queries traceable end to end
- [ ] Measured: decomposition helps multi-hop, doesn't hurt simple questions

---

> ⚠️ **Cut-line 1.** If V2 is at risk by Sep 27: ship the router, use flat
> retrieval for complex questions. Routing alone is a legitimate V2 feature.
