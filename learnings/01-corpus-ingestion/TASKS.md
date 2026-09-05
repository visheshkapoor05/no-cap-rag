# M1 — Corpus & Ingestion

**Sep 6 – Sep 12** · Reasoning: [BLUEPRINT.md §4](../../project/BLUEPRINT.md#4-m1--corpus--ingestion)

**Goal:** a reproducible retail corpus, ingested with stable IDs and content hashes, queryable from Postgres.

> The critical path runs through here. Every metric from M3 onward is measured
> against this data, and a weak corpus produces meaningless numbers for six
> weeks without ever looking broken.

---

## Learn & decide

- [ ] **T-M1.1** `[LEARN]` — Corpus and evaluation-set design
  What makes a corpus good for *evaluation* specifically, not just retrieval; why an unrepresentative corpus silently invalidates every downstream metric. Write to `notes.md`.
- [ ] **T-M1.2** `[DECIDE]` — Write `corpus/MANIFEST.md`
  Exact public URLs with licence/terms status for each · synthetic inventory by category · the three planned version pairs · the five planned cross-document dependencies. **Plan the relationships before writing, or they won't exist.**

## Build

- [ ] **T-M1.3** `[AUTHOR]` — Write the synthetic corpus (25–35 documents)
  **Largest single cost in M1 — time-box to 2–3 days.** Markdown with genuine heading structure (M2's chunker depends on it). Visible `SYNTHETIC — illustrative, not from any real company` banner in each, plus `is_synthetic: true` in metadata.

  Coverage:
  - [ ] Customer policy — Returns **v2.0 and v3.0**, Shipping, Warranty, Gift Cards, Price Match
  - [ ] Loyalty — Program Rules **v1.0 and v2.0** (changed tier thresholds), Points Expiry
  - [ ] Promotions — Discount Stacking, Markdown Policy, Campaign Brief
  - [ ] Store SOPs — Opening/Closing, Cash Handling, Stock Take, Returns Exception Matrix
  - [ ] Incidents — POS Outage, Payment Gateway Failure, Inventory Sync, Loyalty Double-Credit
  - [ ] Runbooks — Failed Refund, Delivery Dispute, Chargeback
  - [ ] ADRs — OMS choice, Loyalty Platform choice
  - [ ] Staff — Shift, Employee Discount, Leave *(adjacent-domain distractors that test precision)*

  Build in deliberately:
  - [ ] **Exact identifiers throughout** — `SOP-RET-014`, `POS-ERR-3021`, `GOLD_TIER`, `SKU-88213`. Without these the dense-vs-hybrid ablation shows noise
  - [ ] **≥3 version pairs** that contradict each other on a substantive point
  - [ ] **≥5 real cross-document dependencies** — the genuine multi-hop material

- [ ] **T-M1.4** `[BUILD]` — Collect the public documents (15–25)
  Fetch and store locally with source URL and fetch timestamp. Record each source's terms status — a corpus you can't legally redistribute isn't reproducible.

## Implement

- [ ] **T-M1.5** `[IMPLEMENT]` — `Source` interface + URL and file adapters
  One interface, two implementations. The abstraction earns itself at M8 when scheduled recrawl reuses the URL adapter.
- [ ] **T-M1.6** `[IMPLEMENT]` — Document registry in Postgres
  Per the PRD data model: `id, source_url, type, title, version, effective_date, fetched_at, content_hash, supersedes, metadata`. Populate `version`/`supersedes` now even though nothing reads them until V3.
- [ ] **T-M1.7** `[IMPLEMENT]` — Content-hash idempotency
  **Hash the extracted text, not the raw bytes.** A PDF re-exported with a new timestamp has different bytes but identical content — hashing bytes triggers a spurious re-ingest and a false version bump. M8's freshness recrawl depends on this being right.
- [ ] **T-M1.8** `[API]` — `POST /documents/ingest` and `GET /documents/{id}`
  Upload/index a document; return document, version and index status. First real endpoints beyond `/health`.
- [ ] **T-M1.9** `[IMPLEMENT]` — Ingestion CLI
  Named explicitly in the PRD's portfolio deliverables: "reproducible ingestion CLI/config." One command rebuilds the entire corpus from scratch.

## Verify & deliver

- [ ] **T-M1.10** `[MEASURE]` — Prove idempotency and provenance completeness
  Run full ingestion twice; assert zero duplicate rows. Assert no null `content_hash`, `title`, `type` or `version`. **Write it as a committed test, not a one-off script.**
- [ ] **T-M1.11** `[DOCS]` — README corpus section
  What the corpus is, the public/synthetic split, why synthetic documents are labelled, and how to rebuild it from the CLI.
- [ ] **T-M1.12** `[GIT]` — Branch → PR → merge `feat/m1-corpus-ingestion`
  Read the full diff before merging. Confirm the corpus **is** committed and no fetched HTML junk or API keys came along with it.

---

## Exit criteria

- [ ] 40+ documents ingested; every synthetic one visibly labelled in-document *and* in metadata
- [ ] Re-running ingestion produces zero duplicates — proven by a committed test
- [ ] ≥3 version pairs with `supersedes` populated; ≥5 cross-document dependencies present
- [ ] `corpus/MANIFEST.md` covers every source and its licence status
- [ ] Merged to `main` via PR, CI green
