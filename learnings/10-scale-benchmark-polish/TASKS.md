# M10 — Scale Benchmark, Provider Swap & Polish → **V3**

**Nov 3 – Nov 12** · Reasoning: [BLUEPRINT.md §11](../../project/BLUEPRINT.md)

**Goal:** prove the system holds under scale, prove the provider abstraction is real, and make the repo genuinely readable by a stranger.

> Everything measurable is now measured, so the two remaining claims — "it
> scales" and "providers are pluggable" — can be **demonstrated** rather than
> asserted. The PRD is pointed about this: no 10M fake documents, and no
> "near-zero hallucination" claim without your own benchmark.

---

## Scale

- [ ] **T-M10.1** `[LEARN]` — ANN index types and their trade-offs
  HNSW (`M`, `efConstruction`, `ef`) vs. IVF variants: build time, memory, query speed, recall. Enough to choose parameters deliberately rather than copying a tutorial.
- [ ] **T-M10.2** `[BUILD]` — Generate a scale corpus
  Programmatic expansion to a few hundred thousand chunks — **clearly marked synthetic, never presented as real data**.
  **Benchmark at 10k first** to validate the methodology before spending hours on the large run.
- [ ] **T-M10.3** `[IMPLEMENT]` — HNSW index + parameter sweep
  Index build time, memory, query latency and recall across several `ef` values, all against the FLAT ground truth.
- [ ] **T-M10.4** `[MEASURE]` — Experiment K: FLAT vs. HNSW
  The recall/latency curve, with your chosen operating point marked and justified.
  Also confirm whether `rank_bm25` is still viable at this scale or has become the bottleneck (per [D-005](../../project/DECISIONS.md)'s revisit trigger).

  > **This is the point of the scale benchmark, not a side-effect.** Every number
  > so far ran on exact search, so you have genuine ground-truth recall.
  > Measuring *exactly how much recall you trade for the speed you gain* is a far
  > better artifact than "I used HNSW because everyone uses HNSW." Almost nobody
  > can quote that number for their own system.

## Provider swap

- [ ] **T-M10.5** `[IMPLEMENT]` — Local embedding provider (BGE-M3 or equivalent)
  Added as a **second** provider, not a replacement. If this requires touching anything outside the adapter, the abstraction was leaky — and **finding that out is itself a valuable result worth writing up honestly**.
- [ ] **T-M10.6** `[MEASURE]` — Experiment G: Gemini vs. local embeddings
  Retrieval quality, latency, and cost per 1000 chunks. The interesting question isn't which wins — it's whether local is *good enough* to buy full reproducibility and zero marginal cost.
- [ ] **T-M10.7** `[VERIFY]` — Confirm the embedding cache is provider-aware
  T-M2.6 keyed the cache on `hash(text + model_id)` for exactly this moment — verify switching providers doesn't silently serve Gemini vectors to the local model's index.

## Security & hardening

- [ ] **T-M10.8** `[LEARN]` — Prompt injection via retrieved content
  Your corpus is partly fetched from the public web. A page containing "ignore previous instructions" becomes model input — **retrieved content is data, not instructions**, and the prompt architecture has to enforce that.
- [ ] **T-M10.9** `[IMPLEMENT]` — Upload validation and parsing isolation
  File size and type limits, content-type verification, resource limits on parsing. A malicious PDF shouldn't be able to exhaust memory during ingestion.
- [ ] **T-M10.10** `[VERIFY]` — Injection test, with a documented result
  Ingest a document containing embedded instructions, query so it's retrieved, confirm the pipeline treats it as content.
  **Report the outcome honestly, including partial mitigation** — an overstated security claim is worse than a scoped one.
- [ ] **T-M10.11** `[DOCS]` — Write `SECURITY.md`
  Threat model, what's mitigated, what explicitly isn't, and how to report an issue. **Naming your own gaps reads as competence, not weakness.**

## Ship V3

- [ ] **T-M10.12** `[DOCS]` — Final README with the full V1→V2→V3 benchmark ladder
  One table showing every configuration and what each stage bought. The single most-read artifact in the repo — readable in 30 seconds, defensible for 30 minutes.
- [ ] **T-M10.13** `[DOCS]` — The quality / latency / cost operating point
  The PRD's closing requirement: state which configuration you'd actually run in production **and why it isn't simply the highest-scoring one**. Naming what you gave up is the whole point.
- [ ] **T-M10.14** `[DOCS]` — Expanded failure analysis and limitations
  Beyond M4's three cases: what still fails at V3, what a self-authored evaluation set can't tell you, and where the LLM judge remains a weak instrument.
- [ ] **T-M10.15** `[DOCS]` — Record the demo
  A PRD deliverable. Show evidence, citations, verification, and — most importantly — **a question the system correctly refuses to answer**. That refusal is the most distinctive thing this project does.
- [ ] **T-M10.16** `[VERIFY]` — Final clean-clone reproducibility pass
  Fresh clone, README only, full stack up, benchmark reproduced. Anything requiring knowledge you didn't write down is a documentation bug.
- [ ] **T-M10.17** `[GIT]` — Tag `v3.0.0` and publish the final GitHub Release
  Third of the three PRD-mandated releases. Notes cover the scale results, the provider comparison, and the operating-point decision.

---

## V3 exit criteria

- [ ] Scale benchmark run, with the FLAT→HNSW recall/latency trade-off **quantified**
- [ ] A second embedding provider works without changes outside its adapter
- [ ] `SECURITY.md` published with an honest, scoped threat model
- [ ] README ends with a **defended** quality/latency/cost operating point
- [ ] Demo shows evidence, citations, verification *and* a correct refusal
- [ ] All three releases tagged; clean clone reproduces the benchmark
