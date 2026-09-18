"""
The archive room's plumbing: one connection pool opened lazily and shared
by every request, plus the migration runner that keeps the archive room's
shelving (schema) in sync with whatever's checked into migrations/. See
../../ANALOGY.md.
"""
from __future__ import annotations

from pathlib import Path

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.core.config import get_settings

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent.parent / "migrations"

_pool: ConnectionPool | None = None


def get_pool() -> ConnectionPool:
    """Opens the pool once, lazily, and hands out the same one after that —
    the same singleton pattern as `get_settings()`."""
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = ConnectionPool(
            settings.postgres.dsn,
            min_size=1,
            max_size=5,
            kwargs={"row_factory": dict_row},
            open=True,
        )
    return _pool


def close_pool() -> None:
    """Closes the office at shutdown; mainly here so tests can reset state
    between runs against different settings."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def migrate(pool: ConnectionPool | None = None) -> list[str]:
    """
    Applies every migrations/*.sql file not already recorded in
    schema_migrations, in filename order, each in its own transaction.
    Running this twice is a no-op the second time — the same idempotency
    principle T-M1.7 applies to document ingestion, applied here to schema
    changes instead. Returns the filenames actually applied this call.
    """
    pool = pool or get_pool()
    applied: list[str] = []
    with pool.connection() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "filename TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        already = {
            row["filename"]
            for row in conn.execute("SELECT filename FROM schema_migrations").fetchall()
        }
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if path.name in already:
                continue
            with conn.transaction():
                conn.execute(path.read_text())
                conn.execute(
                    "INSERT INTO schema_migrations (filename) VALUES (%s)", (path.name,)
                )
            applied.append(path.name)
    return applied
