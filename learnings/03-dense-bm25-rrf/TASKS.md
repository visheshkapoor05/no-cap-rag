# M3 — Dense, BM25 & RRF

**Sep 20 – Sep 26** · Reasoning: [BLUEPRINT.md §6](../../project/BLUEPRINT.md#6-m3--dense-bm25--rrf)

**Goal:** two independent retrieval strategies plus fusion, with numbers proving whether hybrid actually beats dense.

> This is where the project stops being a pipeline and starts being an experiment.

---

## Learn & practice

- [ ] **T-M3.1** `[LEARN]` — BM25 mechanics, with a worked example on 3 toy documents
  - [ ] **IDF** — why `POS-ERR-3021` is a powerful query term and "policy" is nearly worthless
  - [ ] **TF saturation (`k1`)** — a document mentioning a term 50× isn't 50× more relevant, just repetitive
  - [ ] **Length normalization (`b`)** — long documents contain more words by accident; without this they'd dominate

  *If you can't predict which toy document wins, you don't understand it yet.*
- [ ] **T-M3.2** `[LEARN]` — RRF vs. weighted fusion; the normalization problem
  Why combining bounded cosine similarity with unbounded BM25 scores requires normalization, and what breaks when score distributions shift between queries. RRF (`Σ 1/(k + rank)`) sidesteps it entirely by using rank position only.
- [ ] **T-M3.3** `[PRACTICE]` — Implement RRF from scratch on two hardcoded lists
  Verify against reference behaviour. Vary `k` and watch the ranking shift — build intuition for what that constant controls before it's buried in the app.
- [ ] **T-M3.4** `[PRACTICE]` — Hand-run 5 queries: dense vs. BM25
  **Predict the winner before you look.** The wrong predictions are the valuable ones — write them up.

## Infrastructure

- [ ] **T-M3.5** `[DOCKER]` — Add Milvus to Docker Compose
  Milvus standalone needs **etcd and MinIO** alongside it — three new services, not one. Healthchecks on all of them; the API waits for Milvus to be healthy.
  **Budget a full day, and do this *before* the retrieval code, not alongside it.** It's the fiddliest infra step in the project.
- [ ] **T-M3.6** `[IMPLEMENT]` — Milvus collection schema + connection lifecycle
  Open the connection in the app's lifespan, not per-request. Collection with a **FLAT index** — exact search, so any recall shortfall is attributable to your logic rather than an ANN index's approximation error ([D-006](../../project/DECISIONS.md)).

## Implement

- [ ] **T-M3.7** `[IMPLEMENT]` — Embedding provider abstraction + Gemini adapter
  One interface, Gemini behind it. This is what makes Experiment G possible at M10 without rewriting callers.
  **Verify current Gemini model IDs against Google's docs — don't hardcode from memory.**
- [ ] **T-M3.8** `[IMPLEMENT]` — `RetrievalStrategy` interface + `DenseRetriever`
  The interface the PRD calls for explicitly ("interchangeable strategy interfaces").
- [ ] **T-M3.9** `[IMPLEMENT]` — `SparseRetriever` via `rank_bm25`
  Built from chunk text **plus** contextual prefix, so the section heading is searchable too. In-memory and fully inspectable — you can print per-term IDF and see exactly why a chunk scored what it did ([D-005](../../project/DECISIONS.md)).
- [ ] **T-M3.10** `[IMPLEMENT]` — `RRFFusion` and `WeightedFusion` behind one interface
  Both, so Experiment C is a config change rather than a code change. Config-driven pipeline assembly starts here.
- [ ] **T-M3.11** `[API]` — `POST /retrieve`
  Ranked chunks with scores, per-stage timings and metadata. **Build the timing breakdown in now** — retrofitting it later is much harder.

## Measure & deliver

- [ ] **T-M3.12** `[MEASURE]` — Four configs × 50 questions — Experiments A, B, C

  | Config | Recall@1 | Recall@5 | Recall@10 | MRR |
  |---|---|---|---|---|
  | Dense only | | | | |
  | BM25 only | | | | |
  | Hybrid + RRF | | | | |
  | Hybrid + weighted | | | | |

  - [ ] **Break down by question category, not just overall.** The aggregate hides the actual insight — BM25 should dominate the exact-identifier subset while losing on paraphrase. That breakdown is the chart for your README
  - [ ] Also run the chunking ablation (fixed vs. structure-aware) now that you can measure it — Experiment A
- [ ] **T-M3.13** `[DOCS]` — Commit `evals/results/M3_retrieval.md`
  A dated, diffable record of the numbers at this point in the build. Six weeks of these files is the most convincing artifact in the repo and is impossible to reconstruct later.
- [ ] **T-M3.14** `[GIT]` — Branch → PR → merge `feat/m3-hybrid-retrieval`
  Update the README quick-start — the Compose stack now needs Milvus, etcd and MinIO, so the old instructions are wrong.

---

## Exit criteria

- [ ] Four configurations run through one interface, no code duplication
- [ ] Recall@K and MRR reported **overall and per category**
- [ ] The dense-vs-hybrid question answered with numbers
- [ ] At least one surprising result written up — where your prediction was wrong, and why
- [ ] `docker compose up` brings the full stack including Milvus from clean
