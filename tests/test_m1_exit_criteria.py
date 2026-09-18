"""T-M1.10: the actual proof behind two of M1's exit criteria, not an
assumption that they hold. Runs against the full synthetic corpus (28
documents, offline, deterministic) — `public` stays out of the committed
suite for the same reason it's excluded in test_cli.py: hitting real
retailer sites on every CI run is slow, flaky, and not something a test
suite should depend on to stay green."""
from app.cli import ingest_plan
from app.corpus_plan import plan_synthetic


def test_reingesting_the_full_corpus_twice_creates_no_duplicates(clean_documents):
    plans = plan_synthetic()

    ingest_plan(clean_documents, plans)
    with clean_documents.connection() as conn:
        first_count = conn.execute("SELECT COUNT(*) AS n FROM documents").fetchone()["n"]

    ingest_plan(clean_documents, plans)
    with clean_documents.connection() as conn:
        second_count = conn.execute("SELECT COUNT(*) AS n FROM documents").fetchone()["n"]

    assert first_count == len(plans)
    assert second_count == first_count


def test_every_ingested_document_has_complete_core_provenance(clean_documents):
    """content_hash/title/type are always required — populated by
    corpus_plan.py for every document, never left to a default. `version`
    is deliberately not checked here: it's legitimately null for postmortems,
    ADRs, and runbooks (see T-M1.10's correction note in TASKS.md) — a
    document without a meaningful version isn't a provenance gap."""
    ingest_plan(clean_documents, plan_synthetic())

    with clean_documents.connection() as conn:
        incomplete = conn.execute(
            "SELECT id, title FROM documents "
            "WHERE content_hash IS NULL OR title IS NULL OR type IS NULL"
        ).fetchall()

    assert incomplete == []
