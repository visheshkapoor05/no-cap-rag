"""Shared rehearsal props for every test in this office."""
import os

# Must happen before any app.* import below: Settings/get_pool() read this
# at first call, not at import time, but setting it here guarantees the
# whole test session -- including API tests that call get_pool() lazily
# inside route handlers -- resolves against the TEST database, never the
# one a human is using for manual exploration (DBeaver, pgAdmin, the CLI).
# See DECISIONS.md D-016: before this, tests and dev work shared one
# database, so a test's own cleanup (TRUNCATE) silently wiped out whatever
# someone had just ingested to look at.
os.environ["POSTGRES_DB"] = f"{os.environ.get('POSTGRES_DB', 'retail-rag')}-test"

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql

from app.chunking import chunk_with_context, delete_chunks_for_document, insert_chunks
from app.core.config import get_settings
from app.core.db import get_pool, migrate
from app.corpus_plan import plan_synthetic
from app.documents.hashing import compute_content_hash
from app.documents.registry import find_by_content_hash
from app.ingestion import FileSource
from app.main import create_app


def _ensure_database_exists(dbname: str) -> None:
    """Creates the test database on first run if it doesn't exist yet --
    connects to Postgres's always-present `postgres` maintenance database to
    do it, since you can't CREATE DATABASE while connected to the database
    being created. CREATE DATABASE can't run inside a transaction block,
    hence autocommit."""
    s = get_settings().postgres
    maintenance_dsn = f"postgresql://{s.user}:{s.password}@{s.host}:{s.port}/postgres"
    with psycopg.connect(maintenance_dsn, autocommit=True) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (dbname,)
        ).fetchone()
        if not exists:
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname)))


@pytest.fixture
def client() -> TestClient:
    """A visitor who can walk into the office without it actually being open for real traffic."""
    return TestClient(create_app())


@pytest.fixture(scope="session")
def pg_pool():
    """One real connection pool for the whole test session, migrated once,
    pointed at `<dbname>-test` (see the os.environ override at the top of
    this file) — never the database a human is using for manual exploration.
    Requires Postgres reachable (e.g. `docker compose up -d postgres`) —
    these are integration tests against the real schema, not a mock."""
    _ensure_database_exists(get_settings().postgres.db)
    pool = get_pool()
    migrate(pool)
    return pool


@pytest.fixture
def clean_documents(pg_pool):
    """A `documents` table guaranteed empty at the start of the test, and
    cleaned again after — so tests can assert on exact rows/counts without
    depending on run order or leftover data from a previous test."""
    with pg_pool.connection() as conn:
        conn.execute("TRUNCATE documents CASCADE")
    yield pg_pool
    with pg_pool.connection() as conn:
        conn.execute("TRUNCATE documents CASCADE")


@pytest.fixture
def full_corpus_chunks(pg_pool):
    """Ingests + chunks the full synthetic corpus immediately before the
    test runs, every time -- deliberately not session-scoped. Other tests'
    `clean_documents` fixture truncates `documents` (cascading to `chunks`)
    for their own isolation, which would otherwise silently wipe out
    whatever an earlier test populated depending on run order. Both
    ingestion and chunking are already idempotent (T-M1.7, and
    delete-then-reinsert for chunks), so re-running this before every test
    that needs it is cheap and correct rather than a workaround."""
    for plan in plan_synthetic():
        raw = FileSource().fetch(plan.ref)
        content_hash = compute_content_hash(raw.text)
        document = find_by_content_hash(pg_pool, content_hash)
        if document is None:
            from app.documents import ingest_document
            document = ingest_document(
                pg_pool, raw, type=plan.type, title=plan.title, version=plan.version,
                effective_date=plan.effective_date, metadata=plan.metadata,
            ).document
        delete_chunks_for_document(pg_pool, document.id)
        chunks = chunk_with_context(raw.text, title=plan.title, version=plan.version)
        insert_chunks(pg_pool, document.id, chunks)
    return pg_pool
