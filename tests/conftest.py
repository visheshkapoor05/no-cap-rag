"""Shared rehearsal props for every test in this office."""
import pytest
from fastapi.testclient import TestClient

from app.core.db import get_pool, migrate
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    """A visitor who can walk into the office without it actually being open for real traffic."""
    return TestClient(create_app())


@pytest.fixture(scope="session")
def pg_pool():
    """One real connection pool for the whole test session, migrated once.
    Requires Postgres reachable (e.g. `docker compose up -d postgres`) —
    these are integration tests against the real schema, not a mock."""
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
