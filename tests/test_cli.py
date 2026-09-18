"""T-M1.9: the corpus-discovery logic (offline, deterministic) and the
full synthetic-corpus ingestion run, against real Postgres. The `public`
scope (16 live URLs) is exercised manually, not in the committed suite —
hitting real retailer websites on every test run would be slow, flaky,
and exactly the kind of test that shouldn't gate CI."""
from app.cli import ingest_plan
from app.corpus_plan import plan_public, plan_synthetic


def test_plan_synthetic_covers_all_28_documents():
    plans = plan_synthetic()

    assert len(plans) == 28
    assert all(p.type for p in plans)
    assert all(p.title for p in plans)


def test_plan_public_parses_all_16_manifest_rows():
    plans = plan_public()

    assert len(plans) == 16
    assert all(p.ref.startswith("https://") for p in plans)
    assert all(p.metadata["retailer"] for p in plans)


def test_ingesting_the_synthetic_corpus_twice_is_idempotent(clean_documents):
    plans = plan_synthetic()

    first_run = ingest_plan(clean_documents, plans)
    second_run = ingest_plan(clean_documents, plans)

    assert all(o.status == "created" for o in first_run)
    assert all(o.status == "duplicate" for o in second_run)

    with clean_documents.connection() as conn:
        count = conn.execute("SELECT COUNT(*) AS n FROM documents").fetchone()["n"]
    assert count == 28  # not 56 — the second run created nothing


def test_version_chains_resolve_across_two_passes(clean_documents):
    ingest_plan(clean_documents, plan_synthetic())

    with clean_documents.connection() as conn:
        returns_v3 = conn.execute(
            "SELECT id, supersedes FROM documents WHERE title = 'Returns Policy' AND version = '3.0'"
        ).fetchone()
        returns_v2 = conn.execute(
            "SELECT id FROM documents WHERE title = 'Returns Policy' AND version = '2.0'"
        ).fetchone()
        loyalty_v2 = conn.execute(
            "SELECT supersedes FROM documents WHERE title = 'Loyalty Program Rules' AND version = '2.0'"
        ).fetchone()
        loyalty_v1 = conn.execute(
            "SELECT id FROM documents WHERE title = 'Loyalty Program Rules' AND version = '1.0'"
        ).fetchone()
        exception_matrix = conn.execute(
            "SELECT supersedes FROM documents WHERE title = 'Returns Exception Matrix'"
        ).fetchone()

    assert returns_v3["supersedes"] == returns_v2["id"]
    assert loyalty_v2["supersedes"] == loyalty_v1["id"]
    # References an "implicit" v1.0 that was never authored as its own
    # file (see MANIFEST.md) — must resolve to nothing, not raise.
    assert exception_matrix["supersedes"] is None
