# M6 — Evidence Grading & Refinement

**Oct 7 – Oct 9** · Reasoning: [BLUEPRINT.md §9](../../project/BLUEPRINT.md#9-m6--evidence-grading--refinement)

**Goal:** evidence graded before generation; weak evidence triggers a bounded retry.

> Everything so far assumes retrieval succeeded. This milestone stops assuming.
>
> The system usually has enough information to know its retrieval was poor
> *before* it generates anything. Generating from weak evidence is how
> confident, well-cited, wrong answers get produced — the worst failure mode,
> because the citations make it look trustworthy.

---

## Learn & practice

- [ ] **T-M6.1** `[LEARN]` — Evidence-grading approaches and weak-retrieval signals
  - Top reranker score below threshold
  - Large gap between the top score and the rest
  - No agreement across retrieved chunks
  - Chunks don't collectively cover the question's sub-parts

  **Start with a reranker-score threshold** — simple, explainable, tunable against your golden set. A simple explainable signal beats a clever opaque one when you have to debug it at 11pm.
- [ ] **T-M6.2** `[LEARN]` — Bounded-loop design in state graphs
  Termination guarantees, give-up paths, budget guards. **"Bounded" is load-bearing** — an unbounded refine loop on a genuinely unanswerable question runs forever and burns your API budget. The failure you're designing against is a loop that spends $40 discovering a question is unanswerable.
- [ ] **T-M6.3** `[PRACTICE]` — Hand-label 20 retrieval results weak/strong
  Compare against reranker scores to find your threshold **empirically rather than by intuition**. Include several unanswerable questions — they should cluster at the weak end.

  > This is where your `answerable: false` golden questions finally pay off:
  > they give you ground truth to calibrate against.

## Implement

- [ ] **T-M6.4** `[IMPLEMENT]` — Evidence grader node with a calibrated threshold
  Configurable, not hardcoded — the threshold is a tuning knob you'll revisit, and it belongs in the experiment config so runs stay reproducible.
- [ ] **T-M6.5** `[IMPLEMENT]` — Query refinement node + bounded retry loop
  Hard cap on attempts, plus an **explicit give-up path** that hands off to abstention rather than accepting weak evidence on the final try.
- [ ] **T-M6.6** `[IMPLEMENT]` — Budget guard: max retries, max tokens per request
  A hard ceiling independent of the retry cap. Belt and braces — the loop and the budget can fail independently.
- [ ] **T-M6.7** `[API]` — Surface grading decisions in `/query` and traces
  Grade, score, whether a retry fired, and the refined query. A PRD acceptance criterion: *"verification decisions are visible in traces."*

## Measure & deliver

- [ ] **T-M6.8** `[VERIFY]` — Prove the loop terminates
  Test with an adversarial unanswerable question. **A committed test, not a manual check** — this is the failure that costs real money if it regresses.
- [ ] **T-M6.9** `[MEASURE]` — Experiment I: grading + retry on/off
  - [ ] Grader agreement with your 20 hand labels
  - [ ] Retry-triggered rate
  - [ ] Unanswerable questions reliably grade weak
  - [ ] Latency cost of the retry path
- [ ] **T-M6.10** `[GIT]` — Branch → PR → merge `feat/m6-evidence-grading`
  Commit the results file **and the hand labels** — they're reusable ground truth.

---

## Exit criteria

- [ ] Weak retrieval triggers exactly one bounded retry cycle
- [ ] **Loop provably terminates** — proven by a committed adversarial test
- [ ] Grader agreement with hand labels measured and reported
- [ ] Grading decisions visible in traces

---

> ⚠️ **Cut-line 2.** If V2 is at risk by Sep 29: keep evidence *grading*, drop
> the retry. Grading plus abstention is still a complete, defensible story.
