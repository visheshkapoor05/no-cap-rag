# M7 — Claim Verification & Abstention → **V2**

**Oct 10 – Oct 12** · Reasoning: [BLUEPRINT.md §10](../../project/BLUEPRINT.md#10-m7--claim-verification--abstention--v2)

**Goal:** answers decomposed into claims, each verified against cited evidence; unsupported claims revised or triggering abstention.

> The milestone the whole project builds toward. M6 checks the evidence
> *before* generating; M7 checks the answer *after* — because a model can
> produce an unsupported claim even from strong evidence.

---

## Learn & practice

- [ ] **T-M7.1** `[LEARN]` — Claim extraction: atomicity and edge cases
  What counts as one claim · compound sentences · hedged statements ("typically 30 days" — is that verifiable at all?) · claims that are implied rather than stated.
- [ ] **T-M7.2** `[LEARN]` — NLI-style verification, **three outcomes not two**
  `supported` · `contradicted` · `not_addressed`
  Collapsing the last two loses real information — "the policy says the opposite" and "the policy is silent on this" call for genuinely different responses.
- [ ] **T-M7.3** `[LEARN]` — Abstention and calibration
  When refusing beats answering · over-abstention as its own failure mode · how to present a refusal usefully rather than as a dead end.

  > The hardest idea here to internalize, because every instinct says answering
  > beats refusing. In retail, a confidently wrong refund-policy answer costs
  > far more than "I can't determine this from the available policies."
- [ ] **T-M7.4** `[PRACTICE]` — Hand-extract and verify claims from 10 answers
  **This is the ground truth your automated verifier gets measured against.** Do it *before* building the verifier, so your labels aren't anchored by what the machine produced.

## Implement

- [ ] **T-M7.5** `[IMPLEMENT]` — Claim extractor
  Leans on T-M4.8's structured output — this is the payoff for that decision. If generation already emits claim-level data, extraction is mostly validation rather than parsing.
- [ ] **T-M7.6** `[IMPLEMENT]` — Claim verifier with three-way outcomes
  Each claim checked against **its own cited chunks**, not the whole context — verifying against everything retrieved would let an uncited chunk rescue a fabricated citation.
- [ ] **T-M7.7** `[IMPLEMENT]` — Revise-or-abstain + weakest-claim reporting
  **Report the minimum claim score, never the mean.** Bounded revision — one attempt, then abstain.

  > PRD: *"Avoids hiding one bad claim behind an average score."* An answer with
  > four solid claims and one fabricated one averages to "pretty good" — and
  > ships the fabrication.
- [ ] **T-M7.8** `[IMPLEMENT]` — Abstention response format
  What the user sees · what evidence *was* found · why it was judged insufficient · what would need to exist to answer. **A useful refusal, not a shrug.**
- [ ] **T-M7.9** `[API]` — Surface per-claim verification in `/query`
  Each claim with its outcome, its supporting chunk IDs, and the weakest-claim score for the answer as a whole.

## Measure & ship V2

- [ ] **T-M7.10** `[MEASURE]` — Experiment J: V1 vs. V2
  - [ ] Verifier agreement with hand labels
  - [ ] Abstention rate on unanswerable questions — **should be high**
  - [ ] Abstention rate on answerable questions — **should be low; over-abstention is its own failure**
  - [ ] Faithfulness delta V1 → V2
  - [ ] Latency and cost delta
- [ ] **T-M7.11** `[DOCS]` — README: the verification and abstention story
  The V1→V2 comparison table, the weakest-claim reasoning, and an honest note on what was traded — some correctness given up in exchange for far fewer confident fabrications.
- [ ] **T-M7.12** `[GIT]` — Tag `v2.0.0` and publish the GitHub Release
  Release notes lead with the faithfulness improvement and the abstention numbers. Second of the three PRD-mandated releases.

---

## V2 exit criteria *(from the PRD)*

- [ ] Complex questions produce traceable sub-queries
- [ ] Weak retrieval triggers a bounded retry
- [ ] Unsupported claims are revised, removed, or cause abstention
- [ ] Verification decisions visible in traces
- [ ] Abstention rate measured on **both** answerable and unanswerable sets
- [ ] Faithfulness improvement V1 → V2 quantified
- [ ] `v2.0.0` tagged and released

---

> ⚠️ **Cut-line 3.** If time is short: abstain on unsupported claims rather than
> attempting a rewrite. Simpler, and arguably more defensible anyway.
>
> **Never cut:** claim verification itself, or the measurement of abstention.
> Those *are* V2. A V2 that verifies and abstains but doesn't decompose is a
> coherent release. A V2 that decomposes but doesn't verify is just V1 with
> extra API calls.
