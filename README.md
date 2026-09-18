# no-cap-rag

![CI](https://github.com/visheshkapoor05/no-cap-rag/actions/workflows/ci.yml/badge.svg)

A production-oriented RAG system for retail policy Q&A — hybrid dense+BM25 retrieval, cross-encoder reranking, citation-grounded generation, claim verification, and honest abstention. Built and benchmarked end to end across V1→V2→V3.

**What this isn't:** not a chat-with-your-PDFs demo. There's no generic document upload box — the corpus, retrieval strategy, and evaluation set are all purpose-built for one domain (retail policy Q&A) so that every design choice can be measured against real numbers instead of asserted.

A public + synthetic corpus, retrieved with evidence, answered with citations, verified, and abstained from when the evidence doesn't hold up. Built in three shippable tiers: V1 → V2 → V3.
See [`Project_1_Advanced_RAG_PRD_Architecture.pdf`](./Project_1_Advanced_RAG_PRD_Architecture.pdf)
for the full plan and [`DECISIONS.md`](./DECISIONS.md) for where the build
knowingly deviates from it.

Every module in this repo plays a role in one running analogy — an internal
company research-and-answers office. See [ANALOGY.md](./ANALOGY.md) for the
full glossary before reading module docstrings; they assume it. A separate,
growing [`GLOSSARY.md`](./GLOSSARY.md) covers general RAG/software-engineering
terminology (idempotency, connection pooling, content hashing, ...) as it
comes up in the build, each entry with a plain-English analogy and a pointer
to where it's actually used in this codebase.

## Status

**M1 — Corpus & Ingestion, in progress on `feat/the-mailroom-opens`.** The
corpus is fully authored (see [Corpus](#corpus) below), and there's now a
working ingestion pipeline end to end: fetch/read a document (`Source` +
`URLSource`/`FileSource`), extract its text, hash it, store it idempotently
in Postgres, expose it over `POST /documents/ingest` / `GET /documents/{id}`,
and rebuild the whole thing from one CLI command. Chunking, embeddings, and
the vector DB don't exist yet — those start at M2/M3.

## Quick start

Local, without Docker:

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
curl http://127.0.0.1:8000/health
```

Full stack, with Docker Compose (API + Postgres + Redis):

```bash
docker compose up --build
curl http://127.0.0.1:8000/health
```

Just Postgres, for local (non-Docker) development against the real database
(needed for the ingestion CLI, or running the test suite):

```bash
docker compose up -d postgres
```

Rebuild the entire corpus in Postgres from what's committed in this repo:

```bash
python -m app.cli ingest --scope synthetic   # 28 files, offline, deterministic
python -m app.cli ingest --scope public      # 16 live URLs, hits the real internet
python -m app.cli ingest --scope all         # both
```

Run the tests (needs Postgres running — see above):

```bash
pytest -v
```

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
migrations/
  0001_create_documents_table.sql
corpus/
  MANIFEST.md          — every source, its licence status, and fetch outcome
  synthetic/            — 28 fictional documents (see Corpus below)
  public/                — 16 real retailer policy pages (see Corpus below)
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
