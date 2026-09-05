# The Research Office — analogy glossary

This project is built around one running analogy: **an internal company
research-and-answers department.** Someone asks a question; the office finds
the right source material and writes back a cited answer — or says "we can't
back that up" instead of guessing. Every module in this codebase plays one
role in that office. This file is the single source of truth for the mapping
— module/class docstrings reference it instead of re-explaining it inline,
and `learnings/` notes are written against it.

Source of truth for the system itself: `../Project_1_Advanced_RAG_PRD_Architecture.pdf`
(V1 → V2 → V3 roadmap) — that file is never edited directly; deviations from
it are logged in [DECISIONS.md](./DECISIONS.md) instead (e.g. Milvus in
place of the PRD's suggested Qdrant/LanceDB). Update this file whenever a
new concept is introduced, before writing the code for it.

## Tiers

The office doesn't open all at once — it's built in three stages, each a
shippable version of the business:

- **V1 — Strong Baseline.** The office can find source material and write a
  cited memo. No judgment calls yet.
- **V2 — Retrieve, Constrain, Verify, Abstain.** The office adds a quality
  desk: it checks its own evidence before writing, fact-checks its own memo
  after writing, and is allowed to say "we don't have enough to answer this"
  instead of making something up.
- **V3 — Production-oriented.** The office adds the operational layer: a
  paper trail on everything, tracking which policy version is current,
  re-checking sources for updates, and a standing benchmark that proves any
  process change actually helped.

## Infrastructure — the building itself (Phase 0)

Before the office can see a single visitor, the building has to exist. These
aren't RAG concepts, they're what makes the office openable at all:

| Office role | Codebase location | Concept |
|---|---|---|
| The operating manual — every setting checked against the rulebook before the office is allowed to open | `app/core/config.py` | Typed config (Pydantic Settings) |
| A ticket number stamped on every piece of paperwork for a visit, so the whole trail can be pulled back out later | `app/core/logging.py`, `app/core/middleware.py` | Structured JSON logging + request-ID correlation |
| Office policy for when something goes wrong: a recognized problem gets explained plainly; a genuine bug never leaks its internals to the visitor | `app/core/exceptions.py` | Exception handling |
| The building and utilities — mailroom, archive room, phone lines — switched on together, each checked ready before the front door unlocks | `docker-compose.yml` | Docker Compose, service healthchecks |
| The daily inspection that certifies the office before it's allowed to open | `.github/workflows/ci.yml` | CI |
| Closed-door rehearsals of standard procedures before real visitors show up | `tests/` | pytest |

## The cast

| Office role | Codebase location | RAG concept | Tier |
|---|---|---|---|
| Mailroom clerk | `app/ingestion` | Ingestion — logs each document in, stamps it with a receipt (content hash/version) so it's never filed twice | V1 |
| Two kinds of incoming mail: real letters from public sources, and practice cases the office writes itself, clearly stamped "PRACTICE — not a real client" | `corpus/` (public URLs/PDFs + synthetic enterprise docs) | Corpus strategy — public sources + explicitly-labelled synthetic enterprise documents | V1 |
| Clerk stripping envelopes & staples | `app/ingestion` (parsers/cleaner) | Cleaning/parsing — removes formatting noise, keeps the letterhead | V1 |
| Clerk filing a report under the right department/section instead of cutting blindly every N words | `app/ingestion` (chunker) | Structure-aware chunking — splits along the document's own headings/sections, not arbitrary boundaries | V1 |
| Clerk stapling a receipt with the document's edition number and effective date to every card | `app/ingestion` (metadata) | Metadata + stable IDs + versions — needed for citations and, later, "which policy is current" | V1 (fields) / V3 (used for freshness) |
| Clerk writing a "topic scent" tag on each card | `app/embeddings` | Embeddings | V1 |
| The scent-sorted filing cabinet | Milvus | Dense / vector index | V1 |
| The alphabetical keyword card catalog | BM25 index | Sparse / lexical index | V1 |
| Two research assistants — one searches by "this feels related," one by "these exact words appear" — and the office manager merges their two shortlists into one ranked list | `app/retrieval` (dense + sparse + fusion) | Dense retrieval + BM25 + RRF fusion | V1 |
| Senior analyst double-checking and reordering the shortlist | `app/retrieval` (reranker) | Reranking — cross-encoder | V1 |
| Staff writer drafting a memo, citing which card backs each line | `app/generation` | Cited generation | V1 |
| **Front-desk triage** — "is this a simple lookup, or a multi-part question that needs splitting up?" | `app/orchestration` (router) | Query routing | V2 |
| **Case splitter** — breaks a multi-part question into separate research tickets, each worked independently | `app/orchestration` (decomposer) | Query decomposition | V2 |
| **Evidence reviewer** — before anyone writes a word, checks whether what was found is actually strong enough to answer from | `app/orchestration` (evidence grading) | Retrieval/evidence grading (weak vs. strong) | V2 |
| Reviewer sending a ticket back for a better search — but only a limited number of times before the office has to work with what it has | `app/orchestration` (bounded refine loop) | Bounded query refinement / retry | V2 |
| A proofreader who goes through the finished memo sentence by sentence and lists out each individual factual claim it makes | `app/evaluation` / `app/orchestration` (claim extraction) | Claim extraction | V2 |
| **Fact-checker** — checks each listed claim against the cited evidence, one by one | `app/evaluation` (claim verifier) | Claim/faithfulness verification | V2 |
| Office policy: if even one claim can't be backed up, that line gets rewritten, cut, or the whole memo says "insufficient evidence" instead of guessing — and the report always names the *weakest* claim, not just an average confidence score | `app/generation` (revise/abstain) | Abstention + weakest-claim reporting | V2 |
| **The office manager's routing rulebook on the wall** — decides which desk a ticket goes to next, handles the retry loop, and knows when to stop and escalate | `app/orchestration` (LangGraph graph) | Orchestration state graph (LangGraph, used from V2 on) | V2 |
| Standing test cases with known correct answers — including cases the office should correctly refuse to answer | `evals/golden_set` | Golden evaluation set (`answerable` flag included) | V1 (created) / V2 (used to test abstention) |
| Grading how good the assistants were at pulling the *right* cards, and how good the writer was at only saying supportable things | `app/evaluation` (metrics) | Recall@K/Precision@K/MRR/NDCG, answer correctness, faithfulness, citation support rate | V1 |
| Filing cabinet label that says "this policy replaces the one from March" and a clerk who periodically re-checks public source pages for edits | `app/ingestion` (version-aware retrieval + freshness recrawl) | Version-aware retrieval (`effective_date`, `supersedes`) + scheduled recrawl via content hash | V3 |
| The office's own internal regression test suite — re-running the standard cases and comparing against last version | `app/evaluation` (regression + ablations) | Evaluation harness — golden set + regression + ablations | V3 |
| Timestamped paper trail on every memo — who touched it, how long each step took, what it cost | `app/observability` | End-to-end tracing (OpenTelemetry), cost/latency telemetry | V3 |
| Staffing agency contract instead of one in-house specialist — any assistant/writer/reviewer role can be swapped for a different vendor without changing how the rest of the office works | `app/core` (provider interfaces) | Pluggable LLM/embedding/reranker abstraction | V3 |
| A stress-test day where the archive is stuffed with far more filings than usual, just to prove the system doesn't fall over | benchmarking scripts | Optional scale benchmark (1M+ chunks) | V3 |
| The mailroom scheduling a standing pickup route instead of waiting for mail to arrive | Airflow DAG | Scheduled ingestion pipeline | V3 |
| Mailroom rejecting oversized/suspicious incoming mail; never letting a note planted *inside* submitted evidence give orders to the office | `app/core` (upload validation) | Upload validation / prompt-injection defense | V1/V3 |

## How the analogy is used in code

- **Module/class docstrings** get one short line tying the module to its
  office role.
- **Any function with genuine multi-step internal logic** gets the workflow
  narrated step by step as the office's actual process (see `learnings/`
  for the calibration example) — not just a one-line tag.
- **Trivial functions stay comment-free.** Forcing a story onto a one-line
  getter is noise, not teaching.
- **`learnings/NN-topic/`** notes and the top-level `README.md` use the
  analogy at full depth, including for parameters and config values as
  they're introduced milestone by milestone.

## Extending it

New concept in a later milestone → add a row here first, tagged with its
tier (V1/V2/V3), before writing the module docstring or the learnings note.
If nothing in the office naturally fits, that's a signal to sanity-check
whether the concept is really needed, or just find the closest honest fit
and note it rather than forcing a stretch.
