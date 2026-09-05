# project/

The Research Bureau codebase — a public + synthetic corpus, retrieved
with evidence, answered with citations, verified, and abstained from when
the evidence doesn't hold up. Built in three shippable tiers: V1 → V2 → V3.
See [`../Project_1_Advanced_RAG_PRD_Architecture.pdf`](../Project_1_Advanced_RAG_PRD_Architecture.pdf)
for the full plan and [`DECISIONS.md`](./DECISIONS.md) for where the build
knowingly deviates from it.

Every module in this repo plays a role in one running analogy — an internal
company research-and-answers office. See [ANALOGY.md](./ANALOGY.md) for the
full glossary before reading module docstrings; they assume it.

## Status

**Phase 0 — Foundations.** The office building exists: a FastAPI app with
typed config, structured JSON request logging, and a `/health` desk. Nothing
RAG-specific yet — that starts at M1.

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

Run the tests:

```bash
pytest -v
```

## Layout

```
app/
  main.py          — assembles the app: config, logging, error handling, routers
  core/
    config.py      — typed settings (Pydantic Settings)
    logging.py     — structured JSON logging + request-ID correlation
    middleware.py  — per-request logging middleware
    exceptions.py  — error handling policy
  api/
    health.py       — /health
tests/
  conftest.py       — shared fixtures (TestClient)
  test_health.py
```
