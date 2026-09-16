# Glossary

Every term here showed up for a real reason while building this project —
not a generic CS dictionary. Each entry follows the same structure:

- **Definition** — the precise technical meaning
- **In plain terms** — an analogy, no jargon
- **Why it matters (what breaks without it)** — the concrete failure this concept prevents
- **Where it showed up** — the actual line in this codebase
- **How to say it** — a ready-to-use interview/PRD/resume sentence

Living document — add to it as new terms come up.

---

### Idempotency / idempotent

**Definition:** performing an operation multiple times has the same effect as performing it once.

**In plain terms:** an elevator call button vs. a doorbell. Press the elevator button 10 times — the elevator still only comes once; the *end state* ("elevator is on its way") doesn't change no matter how many times you press it. Press a doorbell 10 times — it rings 10 times; each press has its own separate effect. Idempotent operations behave like the elevator button. `"add $10 to my balance"` behaves like the doorbell — run it 5 times, you've added $50, not $10.

**Why it matters (what breaks without it):** real systems retry things constantly, often silently — a network blip causes a client to resend a request it's not sure went through, a message queue delivers "at least once" by design, a user double-clicks submit, a CLI gets re-run because two new documents were added. If the operation underneath isn't idempotent, every one of those ordinary situations quietly corrupts your data: duplicate rows, duplicate charges, duplicate emails. Concretely in this project: without T-M1.7, re-running the ingestion CLI (T-M1.9) after adding 2 new documents wouldn't just add 2 rows — it would re-insert all 44 existing ones too, and every downstream chunk/embedding in M2/M3 would be duplicated, silently skewing retrieval and evaluation numbers in a way that would be very hard to notice until much later.

**In REST API terms (this is *why* T-M1.7 exists, not just an aside):** HTTP defines `GET`, `PUT`, `DELETE`, `HEAD`, and `OPTIONS` as idempotent by spec — calling them N times must leave the server in the same state as calling them once, and HTTP infrastructure (browsers, load balancers, client libraries) relies on this to safely auto-retry failed requests. `POST` is explicitly **not** idempotent by spec — by default, each `POST` is treated as its own new "create" action, so nothing in the HTTP layer is allowed to retry a failed `POST` for you automatically; it might not be safe. But real networks fail constantly, and sometimes you genuinely need a `POST` to be safely retryable anyway. The standard production pattern for this is an **idempotency key**: the caller (or, as here, the *content itself*) supplies a value the server checks before acting, so a retried `POST` is recognized and skipped instead of repeated. `POST /documents/ingest` (coming in T-M1.8) is exactly this situation — it's a `POST`, so HTTP gives it zero idempotency guarantees on its own. T-M1.7's content hash *is* the idempotency key, just derived from the document's content instead of supplied by the caller. (Stripe's payment API is the textbook real-world example of this exact pattern — `Idempotency-Key` header on every `POST /charges`, precisely so a retried payment request can't double-charge a customer.)

**How to say it:** *"I designed the ingestion pipeline to be idempotent — content-hash-based deduplication means re-running the full ingest is always safe. Since the ingest endpoint is a POST, which HTTP gives no idempotency guarantee for by default, I use the content hash itself as the idempotency key, the same pattern Stripe uses for payment retries."*

---

### Content hash / content-addressable identity

**Definition:** identifying a piece of data by a hash of its *content*, rather than by an external label like a filename or URL.

**In plain terms:** recognizing two photocopies as "the same page" by actually comparing what's printed on them, instead of trusting whatever someone scribbled in the corner ("copy 1", "copy 2") — labels can be wrong or misleading; the actual content can't lie about itself.

**Why it matters (what breaks without it):** external labels are untrustworthy over time — a URL can serve different content on different days, a filename tells you nothing about whether the file changed. Without content hashing, you'd have no cheap way to answer "is this the same document I already have," and M8's freshness recrawl would have no reliable way to tell "this policy genuinely changed" apart from "the page was re-served with a different session token embedded in it."

**Where it showed up:** `content_hash = sha256(extracted_text)` — proven, not assumed, with the `.docx` re-save experiment: same visible content, different raw bytes, same content hash.

**How to say it:** *"Documents are deduplicated by content hash rather than source URL, so a re-fetched page with unchanged text is never mistaken for a new version."*

---

### Provenance

**Definition:** a traceable record of where a piece of data came from and when it was obtained.

**In plain terms:** a museum placard next to an artifact — where it was found, by whom, and when — versus just "a thing" sitting on a shelf with no way to establish it's genuine or check it against the original.

**Why it matters (what breaks without it):** when a RAG system answers a question, "where did that come from, and is it still accurate" needs a real answer — without provenance, you can't audit a wrong answer back to its source, can't tell a user which policy version they're reading, and can't know which sources are stale enough to need re-checking. This is a genuine trust/compliance requirement in real enterprise RAG (legal, healthcare, finance), not an academic nicety.

**Where it showed up:** `source_url`, `fetched_at`, and `fetch_method` (direct vs. search-recovered) recorded on every one of the 16 public corpus documents.

**How to say it:** *"Every ingested document carries full provenance — source URL, fetch timestamp, fetch method — so any answer the system gives can be traced back to a specific, dated source."*

---

### Connection pooling

**Definition:** reusing a small set of already-open database connections across many requests, instead of opening a brand-new connection every time.

**In plain terms:** a taxi rank with a few cars already idling, versus calling a taxi company from scratch and waiting for a car to be dispatched every single time you need a ride. Opening a fresh DB connection is expensive — TCP handshake, authentication, session setup — a pool keeps a few connections "idling" so a request just grabs one that's ready.

**Why it matters (what breaks without it):** without pooling, every request pays the full connection-setup cost (often tens of milliseconds of pure overhead), and under real traffic you can exhaust Postgres's maximum connection limit entirely — at which point the database starts refusing connections outright, and the whole app goes down even though it could easily have handled the actual query load.

**Where it showed up:** `app/core/db.py`'s `get_pool()` — one `psycopg_pool.ConnectionPool`, opened once, shared by every caller (mirrors the same singleton pattern `get_settings()` already used for config).

**How to say it:** *"Database access goes through a connection pool rather than a fresh connection per request, both for latency and to avoid exhausting Postgres's connection limit under load."*

---

### Schema migration

**Definition:** a versioned, repeatable, tracked change to a database's structure, applied in order and recorded so it's never silently skipped or re-applied.

**In plain terms:** a shared building's renovation logbook — everyone who renovates writes down exactly what they changed, in order, and signs off, so nobody redoes a renovation that's already done, and anyone can reconstruct the building's exact history by reading the log.

**Why it matters (what breaks without it):** without migrations, "make my local/staging/production database's schema match what the code expects" becomes tribal knowledge — manual SQL someone runs by hand, might mistype, might forget to run on one environment. This is a very real, common cause of production incidents: someone manually changes a column in production, forgets to do the same in staging, and the two environments silently diverge until something breaks in a way that only reproduces in one of them.

**Where it showed up:** `migrations/0001_create_documents_table.sql` + `app/core/db.py`'s `migrate()`, which tracks applied files in a `schema_migrations` table — proven idempotent by calling it twice and confirming the second call applies nothing.

**How to say it:** *"Schema changes are tracked as numbered, idempotent migrations rather than applied by hand, so the schema is fully reproducible from source control alone."*

---

### ORM vs. raw SQL

**Definition:** an ORM (Object-Relational Mapper, e.g. SQLAlchemy) automatically maps database rows to language objects; raw SQL means writing the SQL yourself and mapping results by hand.

**In plain terms:** automatic vs. manual transmission. An ORM mostly hides the gear-shifting (SQL) from you; raw SQL gives direct control over every query, at the cost of writing more by hand.

**Why it matters (what breaks without discipline either way):** leaning on an ORM without watching what it generates is a classic trap — the "N+1 query problem," where code that looks like one clean loop silently fires hundreds of individual queries against the database. Leaning on raw SQL everywhere without care risks hand-written boilerplate and, if parameters aren't handled correctly, SQL injection. The interview-relevant point isn't "which is better" — it's being able to name *why* you picked one for a given situation.

**Where it showed up:** this project deliberately used raw SQL (`psycopg`) for the one-table `documents` schema — an ORM would be more machinery than a single table currently justifies; worth revisiting if the schema grows past a handful of tables.

**How to say it:** *"I used raw SQL over an ORM for the initial schema — a deliberate scope call given the table count at this stage, not a default I didn't think about."*

---

### Foreign key / referential integrity

**Definition:** a column whose value must match an existing row in another (or the same) table, enforced by the database itself.

**In plain terms:** a college registrar's system that actually *enforces* prerequisites — you cannot enroll in "Advanced X" unless "Intro X" exists in the catalog and is recorded as completed. The rule isn't just a sentence in the course description; the system itself blocks the invalid case.

**Why it matters (what breaks without it):** without a DB-enforced foreign key, "orphaned" references creep in silently over time — a row claiming to reference an ID that was deleted, or never existed. Code reading that reference later breaks or silently returns nothing, often far away from and long after the actual mistake, making the root cause much harder to trace.

**Where it showed up:** `documents.supersedes UUID REFERENCES documents(id)` — a document can only claim to supersede a document that genuinely exists; proven with a test that inserts a real superseding pair and checks the reference resolves.

**How to say it:** *"Version chains are enforced with a self-referencing foreign key, so the database guarantees a document can't claim to supersede a row that doesn't exist — that's not left to application-code discipline."*

---

### Unique constraint

**Definition:** a database-enforced rule that no two rows may share the same value in a given column.

**In plain terms:** a nightclub bouncer checking names against a guest list at the door, in addition to whatever the front desk already checked — even if the front desk (application code) makes a mistake, the bouncer (the database) is a second, independent check that still catches it.

**Why it matters (what breaks without it):** relying only on application-level dedupe logic is fragile — a bug, a race condition (two requests both check "does this exist" before either has finished inserting), or a completely different piece of code bypassing your Python entirely (a raw script, another service) can all slip a duplicate past application logic alone. A DB-level constraint doesn't care how the write was attempted.

**Where it showed up:** the unique index on `documents.content_hash` — a schema-level backstop for T-M1.7's idempotency logic, proven with a test that expects `psycopg.errors.UniqueViolation` on a duplicate insert.

**How to say it:** *"Deduplication is enforced at two independent layers — application-level idempotency logic, and a unique constraint as a database-level backstop in case that logic is ever bypassed."*

---

### Interface / abstraction (dependency inversion)

**Definition:** a contract that multiple concrete implementations agree to honor, so calling code doesn't need to know which implementation it's actually talking to.

**In plain terms:** a wall power socket. Any appliance with a standard plug works in it — the socket doesn't care whether you plug in a lamp or a laptop charger, as long as the plug shape matches. You can swap appliances without rewiring the wall.

**Why it matters (what breaks without it):** without a shared interface, every place in the code that needs "a document" ends up with its own separate copy of "if it's a URL do X, if it's a file do Y" logic. Every new source type later (a Slack export, a Confluence page) then means hunting down and editing every one of those copies, instead of writing one new adapter and plugging it into what already exists.

**Where it showed up:** the `Source` ABC with `URLSource`/`FileSource` — both return the same `RawDocument` shape, which is exactly what lets M8's freshness recrawl reuse `URLSource` without touching anything else in the pipeline.

**How to say it:** *"I built a common `Source` interface so the ingestion pipeline is agnostic to where a document came from — this is a plain-language description of the dependency inversion principle, one of the SOLID principles, and it's what lets a later feature reuse the URL adapter without touching the rest of the pipeline."*

---

### Dataclass / value object

**Definition:** a class whose entire purpose is holding a fixed set of related fields, with equality/representation handled automatically — no behavior beyond carrying data.

**In plain terms:** a printed form with fixed, labeled boxes (Name, Date, Amount) vs. a blank sheet of paper where anyone can write anything anywhere. A plain dict is the blank paper — nothing stops a typo like `"tittle"` instead of `"title"` from silently creating a new field instead of raising an error.

**Why it matters (what breaks without it):** with a plain dict, a typo'd key fails silently — you get a confusing `KeyError` somewhere far downstream, or worse, quietly missing data with no error at all. A dataclass with typed fields fails immediately, at the exact line that's actually wrong.

**Where it showed up:** `RawDocument`, `Document`, `IngestResult` — all `@dataclass(frozen=True)`, immutable value objects passed between modules instead of dicts.

**How to say it:** *"Data crossing a module boundary is passed as an immutable dataclass rather than a dict, so the shape is enforced at the type level instead of by convention alone."*

---

### Integration test vs. unit test

**Definition:** a unit test verifies one piece of logic in isolation, often with its dependencies mocked out; an integration test verifies that multiple real components actually work together correctly.

**In plain terms:** unit-testing a single car part on a bench (does the engine turn over by itself, disconnected from everything else) vs. actually driving the assembled car around the block (do the engine, transmission, and wheels all work together for real, wired up the way they'll really be used).

**Why it matters (what breaks without it):** some bugs only exist in how two real pieces talk to each other — e.g. a SQL query that's syntactically fine on its own but references a column name that doesn't actually exist in the real, migrated schema. A unit test with the database mocked out would never catch that; only running against a real Postgres does.

**Where it showed up:** `URLSource` tests mock the HTTP transport (unit-style — testing classification branches in isolation); every `app/documents/*` test runs against a real Postgres container via `docker compose up -d postgres` (integration-style — proving the SQL and the Python actually agree with each other).

**How to say it:** *"I use mocked unit tests for branching logic and real-database integration tests for anything touching persistence — a unit test passing doesn't prove the SQL itself is even valid."*

---

*Next terms likely to land here: dense retrieval, sparse retrieval (BM25), embedding, Reciprocal Rank Fusion (RRF), reranking, hybrid retrieval, cross-encoder, recall@k, MRR, NDCG — once M2/M3 start.*
