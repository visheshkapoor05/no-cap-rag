# Changelog

Format loosely follows [Keep a Changelog](https://keepachangelog.com/) —
grouped by milestone rather than by release, since this project ships in
milestone-sized increments rather than independent versions before
`v1.0.0`. Mechanical to reconstruct because every commit followed
[D-019](./DECISIONS.md#d-019--commit-incrementally-through-a-milestone-not-in-one-batch-at-the-end):
one real commit per task, as it landed.

## [Unreleased] — M4: Reranking, Citation-Grounded Generation & Baseline Eval

### Added
- Cross-encoder reranking (`app/reranking/`, `cross-encoder/ms-marco-MiniLM-L-6-v2`), behind a `Reranker` protocol — T-M4.5.
- Context assembly: exact-text dedup, greedy token-budget fill, `[n]`-bracket citation numbering, document version in every citation header — `app/generation/context_builder.py` — T-M4.6, version field added at T-M4.16.
- `LLMProvider` protocol + Gemini generation adapter, with structured-output repair and a retry/timeout layer added after two real stalled-connection incidents — `app/generation/gemini.py` — T-M4.7.
- Citation-grounded structured generation: atomic claims, each citing real bracket numbers resolved back to chunk references, with a repair pass for out-of-range citations — `app/generation/generate.py` — T-M4.8.
- `precision_at_k()`, `r_precision()`, `ndcg()` — `app/evaluation/metrics.py` — T-M4.9.
- LLM judge on a fixed, versioned rubric (Faithfulness, Correctness, Citation support), naming position/verbosity/self-preference bias explicitly — `app/evaluation/judge.py` — T-M4.10.
- Experiment persistence: one `experiments` row per benchmark config, with dataset/model versions stored alongside metrics — `app/evaluation/experiment.py` — T-M4.11.
- `POST /query`, `POST /evaluate`, `GET /experiments/{id}`, `POST /experiments/compare` — `app/api/query.py`, `app/api/experiments.py` — T-M4.12.
- Golden set expanded 50 → 151 questions, authored against a fresh full read of the real corpus — T-M4.13.
- Full benchmark ladder (baseline dense / +hybrid / +reranker × 7 metrics) plus two ablations (contextual-prefix, context-builder) — `evals/run_m4_experiment.py`, `evals/experiment_e_contextual_prefix.py`, `evals/experiment_f_context_builder_ablation.py` — T-M4.14.
- Hand-score agreement check: 20 real answers scored independently before reading the judge's verdict — `evals/capture_handscore_sample.py` — T-M4.15.
- Failure analysis: three real failures with root cause, one with a measured before/after fix — `evals/results/M4_failure_analysis.md` — T-M4.16.
- `ARCHITECTURE.md` — the pipeline diagram and the reasoning behind each stage — T-M4.17.

### Fixed
- `GeminiLLMProvider` had no retry for transient 5xx responses, and no request timeout at all — a real transient 503 and, separately, a connection that hung for hours with zero response, both surfaced mid-benchmark-run. Added `tenacity`-based retry for `429/500/503/504` and `httpx.TimeoutException`/`ConnectError`, plus a 60s client-side timeout.
- `evals/run_m4_experiment.py`'s final metrics merge used the key `"n"` in both the retrieval and generation metric dicts, so generation's `n=36` silently overwrote retrieval's `n=127` in the saved results — renamed to `n_retrieval`/`n_generation`.
- `evals/run_m4_experiment.py` never called the migration runner — migration `0003` (the `experiments` table) had never been applied to the dev database, which is what caused experiment persistence to fail on the first otherwise-successful benchmark run.
- **Version-surfacing bug** (T-M4.16, the milestone's main fix): `build_context()` never included the source document's version in the rendered citation block, so two chunks from different document versions with the same section path were indistinguishable to both the generator and the judge. Fixed by adding `document_version` to `ContextSource`/`Citation`, propagating it through `app/api/retrieve.py`'s response model, and adding an explicit version-disambiguation rule to the generation system prompt. Bumped the judge rubric `v1` → `v2` to stop accepting an `answerable=false` premise at face value.
- A real inaccuracy in `M4_benchmark.md`'s own prose: the reranker's Recall@5 (0.919) was described as below hybrid's (0.913) when it's actually slightly above — only MRR/R-Precision regressed. Caught while writing the failure analysis's comparison table.

## M3 — Dense, BM25 & Hybrid Retrieval (merged `feat/m3-hybrid-retrieval`)

### Added
- Milvus (etcd + MinIO + standalone) added to Docker Compose; FLAT index + COSINE collection schema, chosen over HNSW at this corpus's scale ([D-006](./DECISIONS.md#d-006--milvus-index-flat-first-hnsw-at-scale)) — T-M3.5/T-M3.6.
- `EmbeddingProvider` protocol + Gemini adapter, task-type-aware (document vs. query embeddings are not the same vector) — T-M3.7.
- `RetrievalStrategy` protocol + `DenseRetriever` — T-M3.8.
- `SparseRetriever` via `rank_bm25`, in-process rather than OpenSearch ([D-005](./DECISIONS.md#d-005--bm25-engine-rank_bm25-in-process-not-opensearch)) — T-M3.9.
- `RRFFusion` and `WeightedFusion` behind one interface, config-driven pipeline assembly — T-M3.10.
- `POST /retrieve` with per-stage millisecond timings built in from the start, not retrofitted — T-M3.11.
- Real 4-config × 50-question experiment (`evals/run_m3_experiment.py`) plus a targeted chunking cross-check confirming M2's structure-aware call under the retrieval method that actually ships ([D-013](./DECISIONS.md#d-013--sequential-search-not-a-full-chunking--retrieval-grid--plus-one-targeted-cross-check)) — T-M3.12/T-M3.13.

### Fixed
- CI needed the real Milvus stack and a real `GEMINI_API_KEY` to run M3's tests — brought up from clean in `.github/workflows/ci.yml`.
- Milvus test collection wasn't isolated per test run, causing cross-test contamination — isolated per `indexed_test_corpus` run.

## M2 — Chunking & Seed Golden Set (merged `feat/m2-chunking-golden-set`)

### Added
- Structure-aware chunker with token-count size guards — T-M2.4.
- Contextual prefix (`"{title} {version} → §{section}: "`) prepended to every chunk before embedding, stored separately so it stays queryable on its own — T-M2.5.
- Disk-backed embedding cache, proven to make zero further API calls on a second pass over the same corpus — T-M2.6.
- Hand-written `recall_at_k()` / `mrr()`, implemented only after being hand-computed on a toy 5-query set first ([D-008](./DECISIONS.md#d-008--metrics-implemented-by-hand-before-reaching-for-ragas)) — T-M2.8.
- 50-question seed golden set, six categories, every reference resolved against the live corpus at build time, never a frozen UUID ([D-015](./DECISIONS.md#d-015--golden-set-references-chunks-by-natural-key-titleversionsection-never-by-postgres-uuid)) — T-M2.9 through T-M2.11.
- `EVALUATION.md` — golden-set methodology and metric definitions, written early rather than deferred ([D-010](./DECISIONS.md#d-010--recallk-and-mrr-move-earlier-m2-not-m4)) — T-M2.12.

## M1 — Corpus & Ingestion (merged `feat/the-mailroom-opens`)

### Added
- `Source` protocol + `URLSource`/`FileSource`, per-format text extraction (pdftotext/python-docx/html/text) — T-M1.5.
- Idempotent document ingestion: content-hashed, insert-or-skip, unique index on `content_hash` — T-M1.6/T-M1.7.
- `POST /documents/ingest`, `POST /documents/upload` (real file attach, distinct from the ref-based endpoint — [D-017](./DECISIONS.md#d-017--a-real-file-upload-endpoint-distinct-from-the-ref-based-ingest-endpoint)), `GET /documents/{id}` — T-M1.8.
- Reproducible ingestion CLI (`python -m app.cli ingest`) — T-M1.9.
- 44-document corpus: 28 synthetic (retail domain chosen for real identifiers, natural version conflicts, genuine multi-hop questions — [D-002](./DECISIONS.md#d-002--corpus-domain-retail)) + 16 real public retailer policy pages — T-M1.3/T-M1.4.
- Committed proof of idempotency and corpus provenance completeness — T-M1.10.
