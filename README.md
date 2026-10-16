# no-cap-rag

![CI](https://github.com/visheshkapoor05/no-cap-rag/actions/workflows/ci.yml/badge.svg)

A production-oriented RAG system for retail policy Q&A — hybrid dense+BM25 retrieval, cross-encoder reranking, citation-grounded generation, claim verification, and honest abstention. Built and benchmarked end to end across V1→V2→V3.

**What this isn't:** not a chat-with-your-PDFs demo. There's no generic document upload box — the corpus, retrieval strategy, and evaluation set are all purpose-built for one domain (retail policy Q&A) so that every design choice can be measured against real numbers instead of asserted.

A public + synthetic corpus, retrieved with evidence, answered with citations, verified, and abstained from when the evidence doesn't hold up. Built in three shippable tiers: V1 → V2 → V3.
See [`Project_1_Advanced_RAG_PRD_Architecture.pdf`](./Project_1_Advanced_RAG_PRD_Architecture.pdf)
for the full plan, [`DECISIONS.md`](./DECISIONS.md) for where the build
knowingly deviates from it, [`ARCHITECTURE.md`](./ARCHITECTURE.md) for the
pipeline diagram and the reasoning behind it, and [`EVALUATION.md`](./EVALUATION.md)
for the golden-set methodology and what each metric actually measures.

## Benchmark (V1, real run, 151 questions)

| Config | Recall@5 | MRR | R-Prec | Faithfulness | Correctness | Citation support | P95 latency |
|---|---|---|---|---|---|---|---|
| Baseline (dense) | 0.928 | 0.872 | 0.672 | 1.000 | 0.986 | 1.000 | 15.8s |
| **+ Hybrid (RRF)** | 0.913 | **0.888** | **0.688** | 1.000 | 0.965 | 1.000 | 14.8s |
| + Reranker | 0.919 | 0.831 | 0.665 | 0.996 | 0.954 | 0.996 | 21.1s |

Hybrid wins on rank-quality metrics; the reranker, as currently
configured, doesn't — a real, measured result, not a bug (its training
distribution doesn't transfer to this domain). Full numbers, two
ablations, and the reasoning: [`evals/results/M4_benchmark.md`](./evals/results/M4_benchmark.md).
Three real failures found and analyzed, one fixed with before/after
numbers: [`evals/results/M4_failure_analysis.md`](./evals/results/M4_failure_analysis.md).
Judge-vs-hand-score agreement (90%, 18/20): [`evals/results/M4_handscore_agreement.md`](./evals/results/M4_handscore_agreement.md).

## Limitations (stated now, not discovered later)

- **Judge self-preference risk, named but not structurally eliminated.**
  The LLM judge is the same model family as the generator it scores.
  T-M4.15's hand-scoring is the actual test of whether this shows up in
  practice (it mostly didn't — 90% agreement), not an assumption that
  rubric wording fixes it.
- **Reranker underperforms on this corpus as currently configured.**
  See the benchmark table above — don't enable it by default without
  re-measuring after domain-specific fine-tuning.
- **Retrieval breadth vs. multi-context ambiguous questions.** A
  question whose correct answer spans 2-3 unrelated source documents can
  lose some of those contexts to the top-K window — query-specific, not
  categorically fixed by raising K. See Failure 2 in the failure
  analysis.
- **Public corpus has zero golden-set coverage.** All 151 questions
  reference the `synthetic/` half; the 16 real `public/` documents were
  ingested but never used to author evaluation questions.
- **Claim verification and abstention-on-low-confidence (V2 scope) don't
  exist yet.** Generation currently trusts its own citation-grounding;
  nothing re-checks a claim against its cited chunk after the fact.

Every module in this repo plays a role in one running analogy — an internal
company research-and-answers office. See [ANALOGY.md](./ANALOGY.md) for the
full glossary before reading module docstrings; they assume it. A separate,
growing [`GLOSSARY.md`](./GLOSSARY.md) covers general RAG/software-engineering
terminology (idempotency, connection pooling, content hashing, ...) as it
comes up in the build, each entry with a plain-English analogy and a pointer
to where it's actually used in this codebase.

## Status

**M1 — Corpus & Ingestion: done, merged to `main`.** Full ingestion
pipeline end to end: fetch/read a document (`Source` +
`URLSource`/`FileSource`), extract its text, hash it, store it idempotently
in Postgres, expose it over `POST /documents/ingest` / `POST
/documents/upload` (real file attach) / `GET /documents/{id}`, and rebuild
the whole thing from one CLI command.

**M2 — Chunking & Seed Golden Set: done, merged to `main`.**
Structure-aware chunking with a contextual prefix (`app/chunking/`), a
disk-backed embedding cache (`app/embeddings/`), hand-written Recall@K/MRR
(`app/evaluation/`), and a 50-question golden set resolved against the real,
fully-chunked corpus (`evals/golden_set/`) — see [EVALUATION.md](./EVALUATION.md)
for the methodology.

**M3 — Dense, BM25 & Hybrid Retrieval: done, on `feat/m3-hybrid-retrieval`.**
Real dense retrieval over Milvus (`app/retrieval/dense.py`, FLAT index +
COSINE, D-006), BM25 over the real corpus (`app/retrieval/sparse.py`), two
fusion strategies — RRF and weighted (`app/retrieval/fusion.py`) — behind
one `POST /retrieve` endpoint (`app/api/retrieve.py`) with per-stage timing.
Measured for real against the full 50-question golden set, 4 configs ×
Recall@1/5/10 × MRR, overall and per category, plus a chunking cross-check
confirming M2's structure-aware call under the retrieval method that
actually ships: [`evals/results/M3_retrieval.md`](./evals/results/M3_retrieval.md).
Reranking, generation, and claim verification don't exist yet — those start
at M4+.

**M4 — Reranking, Citation-Grounded Generation & Baseline Eval: done, on
`feat/m4-reranking-citations-eval`.** Cross-encoder reranking
(`app/reranking/`), an `LLMProvider` abstraction + Gemini adapter
(`app/generation/gemini.py`), citation-grounded structured generation
(`app/generation/generate.py`, bracket-number citations resolved back to
real chunks), a fixed/versioned LLM judge (`app/evaluation/judge.py`,
`judge_rubric_v2`), experiment persistence (`app/evaluation/experiment.py`),
`POST /query` / `POST /evaluate` / `GET,POST /experiments`
(`app/api/query.py`, `app/api/experiments.py`), the golden set expanded
50 → 151 questions, and the full benchmark ladder — see **Benchmark**
below and [`EVALUATION.md`](./EVALUATION.md) for the complete M4 methodology.

## Quick start

Local, without Docker:

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
curl http://127.0.0.1:8000/health
```

Full stack, with Docker Compose (API + Postgres + Redis + Milvus/etcd/MinIO
for dense retrieval, T-M3.5/T-M3.6):

```bash
docker compose up --build
curl http://127.0.0.1:8000/health
```

Needs `GEMINI_API_KEY=...` in `.env` (copy from `.env.example`) for any
embedding call — real dense retrieval, `python -m app.cli index`, and most
of the test suite all hit the real Gemini API (cached per-text, T-M2.6, so
re-running costs nothing on a second pass).

Just Postgres + Milvus, for local (non-Docker) development against the real
database/vector store (needed for the ingestion CLI, the `index` subcommand,
or running the test suite):

```bash
docker compose up -d postgres milvus   # milvus brings up etcd + MinIO + standalone too
```

Rebuild the entire corpus in Postgres from what's committed in this repo
(chunking now happens automatically as part of ingest):

```bash
python -m app.cli ingest --scope synthetic   # 28 files, offline, deterministic
python -m app.cli ingest --scope public      # 16 live URLs, hits the real internet
python -m app.cli ingest --scope all         # both
python -m app.cli index                      # embeds every chunk + upserts into Milvus
```

Run the tests (needs Postgres, Milvus, and a real `GEMINI_API_KEY` — see
above; CI brings up the same stack from clean, see `.github/workflows/ci.yml`):

```bash
pytest -v
```

## API examples

Ask a question, get a cited, structured answer (retrieve → rerank →
build context → generate, all composed by `POST /query`):

```bash
curl -s http://127.0.0.1:8000/query -X POST -H 'Content-Type: application/json' -d '{
  "question": "How long is the full-replacement warranty on general electronics?"
}' | python3 -m json.tool
```

```json
{
  "trace_id": "...",
  "question": "How long is the full-replacement warranty on general electronics?",
  "answerable": true,
  "summary": "The full replacement warranty for general electronics is 90 days, starting from the date of purchase [1].",
  "claims": [
    {
      "statement": "The full replacement warranty for general electronics lasts for 90 days.",
      "citations": [{"number": 1, "chunk_id": "...", "document_title": "Warranty Policy", "document_version": "1.0", "section_path": "1"}]
    }
  ],
  "timings_ms": {"retrieval_ms": 142.3, "rerank_ms": 38.1, "context_ms": 0.9, "generate_ms": 2104.7, "total_ms": 2286.0}
}
```

Same thing, plus a judge score against a reference answer
(`POST /evaluate`):

```bash
curl -s http://127.0.0.1:8000/evaluate -X POST -H 'Content-Type: application/json' -d '{
  "question": "How long is the full-replacement warranty on general electronics?",
  "expected_answer": "90 days from the date of purchase."
}'
```

Every benchmark run persists one row per config
(`GET /experiments/{id}`, `POST /experiments/compare`) — `config`,
`dataset_version`, and every model version are stored alongside the
metrics, so "which embedding model produced this Recall@5" is never
unrecoverable after the fact.

## Layout

```
app/
  main.py            — assembles the app: config, logging, error handling, routers
  cli.py              — reproducible ingestion CLI (python -m app.cli ingest ...)
  corpus_plan.py       — figures out what to ingest + with what metadata, from corpus/
  core/
    config.py         — typed settings (Pydantic Settings)
    db.py              — Postgres connection pool + migration runner
    logging.py         — structured JSON logging + request-ID correlation
    middleware.py       — per-request logging middleware
    exceptions.py        — error handling policy
  api/
    health.py           — /health
    documents.py          — POST /documents/ingest, GET /documents/{id}
    retrieve.py             — POST /retrieve (dense/bm25/hybrid_rrf/hybrid_weighted, T-M3.11)
    query.py                 — POST /query, POST /evaluate (T-M4.12)
    experiments.py              — GET /experiments/{id}, POST /experiments/compare (T-M4.12)
  ingestion/
    source.py             — the Source interface + RawDocument + FetchStatus
    url_source.py           — fetches a public URL
    file_source.py           — reads a local corpus file
    extract.py                — per-format text extraction (pdftotext/python-docx/html/text)
  documents/
    registry.py               — Postgres reads/writes for the documents table
    ingest.py                  — the idempotent insert-or-skip decision
    hashing.py                  — content-hash computation
    models.py                    — the Document dataclass
  chunking/
    chunker.py                   — structure-aware chunking + size guards (T-M2.4)
    contextual.py                  — contextual prefix (T-M2.5)
    registry.py                     — Postgres reads/writes for the chunks table
  embeddings/
    gemini.py                       — Gemini embedding provider (task_type-aware, T-M3.7)
    cache.py                         — disk-backed embedding cache (T-M2.6)
  retrieval/
    milvus_client.py                  — Milvus connection + FLAT/COSINE collection (T-M3.6)
    dense.py                           — DenseRetriever (T-M3.8)
    sparse.py                           — SparseRetriever, real BM25 (T-M3.9)
    fusion.py                            — RRFFusion + WeightedFusion (T-M3.10)
  reranking/
    reranker.py                          — CrossEncoderReranker, ms-marco-MiniLM (T-M4.5)
  generation/
    provider.py                          — LLMProvider protocol (T-M4.7)
    gemini.py                            — Gemini generation adapter, retry+timeout (T-M4.7)
    context_builder.py                   — dedupe, token budget, citation numbering + version (T-M4.6/T-M4.16)
    schema.py                            — GeneratedAnswer / Claim (T-M4.8)
    generate.py                          — citation-grounded generation + repair pass (T-M4.8)
  evaluation/
    metrics.py                           — Recall@K/MRR (T-M2.8) + R-Precision/NDCG (T-M4.9)
    judge.py                             — LLM judge, judge_rubric_v2 (T-M4.10/T-M4.16)
    experiment.py                        — experiment persistence (T-M4.11)
migrations/
  0001_create_documents_table.sql
  0002_create_chunks_table.sql
  0003_create_experiments_table.sql
corpus/
  MANIFEST.md          — every source, its licence status, and fetch outcome
  synthetic/            — 28 fictional documents (see Corpus below)
  public/                — 16 real retailer policy pages (see Corpus below)
evals/
  golden_set/            — 151-question golden set + loader/resolver (see EVALUATION.md)
  results/                — dated, diffable results per milestone (M3_retrieval.md, M4_benchmark.md, M4_failure_analysis.md, M4_handscore_agreement.md)
  run_m3_experiment.py     — the real T-M3.12 experiment (4 configs x 50 questions)
  run_m4_experiment.py      — the real T-M4.14 benchmark ladder (3 configs x 151/36 questions)
  experiment_e_contextual_prefix.py — T-M4.14 Experiment E
  experiment_f_context_builder_ablation.py — T-M4.14 Experiment F
  capture_handscore_sample.py        — T-M4.15's 20-question capture
tests/
  conftest.py            — shared fixtures (TestClient, real-Postgres pool + cleanup)
  test_*.py
```

Planning docs — `BLUEPRINT.md` (build plan + reasoning), `DECISIONS.md`
(where this build knowingly deviates from the PRD, and every mid-build
correction made along the way), `ANALOGY.md` (the office analogy referenced
throughout the code) — live at the repo root alongside the code they
describe.

The `learnings/` and `practice/` companion directories (concept notes and
throwaway technique scripts) live one level up, outside this repo — they're
personal working notes, not part of the shipped project.

## Corpus

44 documents, split into two halves that are never treated the same way.
The PRD calls for "public corporate sources + synthetic enterprise
corpus" without specifying a domain — retail was the specific choice, and
[D-002](./DECISIONS.md#d-002--corpus-domain-retail) covers why (real
identifiers, natural version conflicts, genuine multi-hop questions).

- **`corpus/synthetic/`** — 28 fictional retail documents, written for this
  project. Every one carries a visible `SYNTHETIC — illustrative, not from
  any real company` banner in-document *and* `is_synthetic: true` in
  metadata — never ambiguous which half a retrieved chunk came from. Split
  further into two directories with different jobs
  ([D-011](./DECISIONS.md#d-011--synthetic-corpus-split-clean-md-vs-mixed-pdfdocxtxt)):
  - `clean/` — 15 `.md` files, format held constant on purpose. This is the
    only set M2/M3's chunking and retrieval experiments run against, so a
    bad result is attributable to the logic being tested, not to PDF/DOCX
    extraction noise.
  - `mixed/` — 13 `.pdf`/`.docx`/`.txt` files with real extraction failure
    modes deliberately built in (broken tables, scrambled multi-column
    text, diagrams that degrade to disconnected fragments). Exercises the
    ingestion parser, kept out of the chunking ablation so its format noise
    can't contaminate that measurement.
  - Full per-document breakdown, why each sibling document exists, and the
    cross-document dependency map: [`corpus/synthetic/INDEX.md`](./corpus/synthetic/INDEX.md).
- **`corpus/public/`** — 16 real, currently-live retailer policy pages
  (Target, IKEA, Best Buy, Kohl's, Walmart, Nordstrom), stored as a short
  paraphrased summary plus `source_url`/`fetched_at` provenance, not a
  verbatim copy — see [`corpus/MANIFEST.md`](./corpus/MANIFEST.md) for the
  licence rationale. Real fetches hit real bot detection, geo-redirects,
  CAPTCHAs, and at least one page a plain HTTP client can't get past at
  all — documented rather than smoothed over in
  [`corpus/public/README.md`](./corpus/public/README.md), because a
  synthetic-only corpus can never produce that kind of unpredictable
  failure, and the ingestion pipeline needs to handle it for real.

Rebuild it from scratch: see [Quick start](#quick-start) above.
