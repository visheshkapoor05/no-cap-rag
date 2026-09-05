# M9 — Observability, Cost/Latency & Regression Gates

**Oct 24 – Nov 2** · Reasoning: [BLUEPRINT.md §11](../../project/BLUEPRINT.md)

**Goal:** every request traced end to end with per-stage latency and cost; CI blocks a quality regression automatically.

> The PRD is explicit: *"No latency optimization before quality baselines."*
> You now have quality baselines, so you can look at cost and speed without
> risking optimizing away accuracy you hadn't measured. V2 also made the
> pipeline substantially more expensive — routing, retries, verification — so
> this is exactly when the numbers become interesting.

---

## Learn

- [ ] **T-M9.1** `[LEARN]` — OpenTelemetry: spans, traces, context propagation
  How a span tree represents a nested pipeline, and how context propagates across async boundaries so a sub-query's spans stay attached to its parent question.
- [ ] **T-M9.2** `[LEARN]` — Percentile latency, and why the mean misleads
  Compute P50/P95/P99 by hand on a synthetic heavy-tailed distribution and see how different the story is from the average.

  > A pipeline that answers in 1.2s normally but takes 14s whenever the M6 retry
  > fires has a fine mean and a terrible P99 — and the P99 is what a user
  > actually complains about. **The retry path guarantees you have a heavy tail**,
  > so the mean would actively mislead you here.
- [ ] **T-M9.3** `[LEARN]` — Regression gate design for noisy ML metrics
  The core tension: too tight and CI fails on run-to-run noise until you stop trusting it; too loose and a real regression slips through. Fixed seeds and a fixed subset are how you buy back determinism.

## Implement — observability

- [ ] **T-M9.4** `[DOCKER]` — Add a trace backend to Compose
  Jaeger or an OTel collector, in an optional profile. **Being able to *see* the span tree is most of the value** — a trace you can only read as JSON gets ignored.
- [ ] **T-M9.5** `[IMPLEMENT]` — OTel instrumentation across every pipeline stage
  Spans for route · decompose · retrieve (dense/sparse **separately**) · fuse · rerank · grade · generate · extract claims · verify.
  The retry loop must show as **repeated spans**, so a slow request is diagnosable at a glance.
- [ ] **T-M9.6** `[IMPLEMENT]` — Bridge the M9 trace ID to the P0 request ID
  The structured logs from Phase 0 and the OTel traces must share an identifier, or you have two disconnected views of the same request and neither is sufficient alone.
- [ ] **T-M9.7** `[IMPLEMENT]` — Token and cost accounting per stage
  Tokens in/out per model call, mapped to per-provider pricing in config. **Attribute cost to the stage that spent it** — routing, refinement and verification are each separately expensive, and you need to know which.
- [ ] **T-M9.8** `[IMPLEMENT]` — Caching layer (Redis) with hit-rate reporting
  Redis has been in Compose since Phase 0, unused. Cache embeddings and generation responses; **report hit rate as a first-class metric** — an uninstrumented cache is indistinguishable from a broken one.
- [ ] **T-M9.9** `[IMPLEMENT]` — Async concurrency for parallel retrieval
  Dense and sparse retrieval are independent — run them concurrently. Same for per-sub-query retrieval after decomposition. **Measure before and after rather than assuming the speedup.**

## Implement — CI gate

- [ ] **T-M9.10** `[IMPLEMENT]` — Fast CI eval subset
  ~20–30 questions spanning all categories, with fixed seeds. It has to finish in CI-acceptable time or it will be disabled within a fortnight.
- [ ] **T-M9.11** `[IMPLEMENT]` — Regression gate workflow with per-metric tolerances
  Compares against M8's baseline, fails the build on a drop beyond tolerance, and **posts the delta table to the PR** so the number is visible where the decision is made.
- [ ] **T-M9.12** `[VERIFY]` — Prove the gate catches a real regression
  **Deliberately degrade the pipeline** — disable the reranker — push, and confirm CI goes red with a sensible message. A gate never seen to fire is decoration.

## Measure & deliver

- [ ] **T-M9.13** `[MEASURE]` — Full cost/latency profile
  P50/P95/P99 **per stage** and end to end · tokens per request · estimated cost per request · cache hit rate.
  **Broken down by route taken** — a decomposed multi-hop question and a simple lookup have entirely different profiles.
- [ ] **T-M9.14** `[DOCS]` — Evaluation dashboard / results view
  A PRD deliverable. A committed static report of metrics across runs is enough — it doesn't need to be a live web app to be genuinely useful.
- [ ] **T-M9.15** `[GIT]` — Branch → PR → merge `feat/m9-observability-gates`
  Include a trace screenshot in the PR — the clearest possible evidence the instrumentation works.

---

## Exit criteria

- [ ] Every request produces a complete span tree; retries visible as repeated spans
- [ ] Per-stage P50/P95/P99, tokens and cost reported
- [ ] Log request IDs and trace IDs are the same identifier
- [ ] Cache hit rate measured and reported
- [ ] **CI gate proven to fail** on a deliberately introduced regression
