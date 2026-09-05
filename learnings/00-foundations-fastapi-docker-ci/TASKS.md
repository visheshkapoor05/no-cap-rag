# P0 — Foundations & Repository Setup

**Aug 18 – Aug 24** (app skeleton, complete) **· Sep 5** (repo & GitHub setup, starting today) · Reasoning: [BLUEPRINT.md §3](../../project/BLUEPRINT.md)

**Goal:** a FastAPI service that boots via Docker Compose with typed config and structured logging — under version control, on GitHub, with CI green.

> **Code is complete. The git side is not.** The repo sat as a plain
> directory for 12 days after the code was finished — a whole build's worth
> of work one power-cut away from gone. T-P0.8 is the immediate next action
> in the whole project, and it's what today (5 Sep) is for. The rest of the
> schedule (M1 onward) has been rebased to start tomorrow — see
> [BLUEPRINT.md §3](../../project/BLUEPRINT.md#3-schedule-at-a-glance).

---

## Application skeleton — complete

- [x] **T-P0.1** — FastAPI app factory + lifespan
  `create_app()` with an `asynccontextmanager` lifespan. Later milestones open Milvus/Postgres connections here, once at startup rather than per-request.
- [x] **T-P0.2** — Typed config via Pydantic Settings
  Nested sub-settings for Postgres and Redis; `@lru_cache` singleton. Invalid config fails at startup, not mid-request.
- [x] **T-P0.3** — Structured JSON logging + request-ID correlation
  `ContextVar`-based request ID stamped on every log line. The cheap precursor to M9's real tracing.
- [x] **T-P0.4** — Exception handlers + structured errors
  Named `AppError`s explain themselves; unexpected exceptions log fully but never leak internals to the caller.
- [x] **T-P0.5** — Docker Compose: api + postgres + redis
  Healthchecks on all three; `depends_on: condition: service_healthy` so the API can't start against a Postgres that isn't accepting connections yet.
- [x] **T-P0.6** — Dockerfile with layer-cache-aware ordering
  Dependencies copied and installed before app code, so a code edit doesn't trigger a full reinstall.
- [x] **T-P0.7** — pytest harness + `/health` tests
  `conftest.py` with a `TestClient` fixture. Verified live that request IDs round-trip into response headers.

## Repository & GitHub — outstanding

- [ ] **T-P0.8** — `git init`, verify `.gitignore`, first commit
  **Before the first `git add`:** run `git status` and confirm `.env`, `.venv/` and `__pycache__` are all ignored. A secret committed once stays in the object history even after deletion.
- [ ] **T-P0.9** — Create the GitHub repo and push `main`
  Public. Repo description + topics (`rag`, `retrieval`, `evaluation`, `llm`) — these are how the project gets found.
- [ ] **T-P0.10** — Branch protection + PR workflow
  Protect `main`, require CI to pass. Forces the per-milestone branch → PR → merge loop instead of committing straight to main.
- [ ] **T-P0.11** — Confirm CI runs green on GitHub
  Then deliberately break a test, push, and watch it go red. A CI badge that has never actually failed proves nothing.
- [ ] **T-P0.12** — LICENSE + README skeleton + CI badge
  MIT or Apache-2.0. README states what this is and what it deliberately isn't ("not a chat-with-your-PDFs demo") from day one.
- [ ] **T-P0.13** — Commit the planning documents
  `BLUEPRINT.md`, `DECISIONS.md`, `ANALOGY.md`, the PRD PDF and `docs/architecture.jpg`. The PRD names "Architecture + PRD" as a portfolio deliverable.

---

## Exit criteria

- [ ] Repo is on GitHub, `main` protected, CI green — and proven to go red when broken
- [ ] `git log` shows no secrets, no `.venv`, no `__pycache__`
- [ ] A stranger can clone, `docker compose up`, and hit `/health` from the README alone
