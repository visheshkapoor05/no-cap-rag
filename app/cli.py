"""
The reproducible way to rebuild the entire corpus in Postgres from nothing
but what's committed in this repo — named explicitly in the PRD's
portfolio deliverables ("reproducible ingestion CLI/config"). See
../ANALOGY.md.

    python -m app.cli ingest --scope synthetic   # 28 files, offline, deterministic
    python -m app.cli ingest --scope public      # 16 live URLs, hits the real internet
    python -m app.cli ingest --scope all         # both (default)
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from psycopg_pool import ConnectionPool

from app.core.db import get_pool, migrate
from app.corpus_plan import PlannedIngest, plan_public, plan_synthetic
from app.documents import ingest_document, update_supersedes
from app.ingestion import FetchStatus, FileSource, Source, URLSource


@dataclass(frozen=True)
class IngestOutcome:
    ref: str
    title: str
    status: Literal["created", "duplicate", "failed"]
    detail: str | None = None


def _source_for(ref: str) -> Source:
    return URLSource() if ref.startswith("http://") or ref.startswith("https://") else FileSource()


def ingest_plan(pool: ConnectionPool, plans: list[PlannedIngest]) -> list[IngestOutcome]:
    """
    Runs every planned document through T-M1.5→T-M1.7's pipeline — the
    same `ingest_document` call T-M1.8's API endpoint uses, not a second
    copy of it. `supersedes` is resolved in a second pass, after every
    document has a real Postgres id: a document can't reference another
    document's id before that id exists, and processing order in the
    corpus directory isn't something this function should have to rely on.
    """
    outcomes: list[IngestOutcome] = []
    id_by_frontmatter_id: dict[str, UUID] = {}
    pending_supersedes: list[tuple[UUID, str]] = []

    for plan in plans:
        source = _source_for(plan.ref)
        raw = source.fetch(plan.ref)

        if raw.status is not FetchStatus.OK:
            outcomes.append(IngestOutcome(plan.ref, plan.title, "failed", f"{raw.status.value}: {raw.detail}"))
            continue

        result = ingest_document(
            pool,
            raw,
            type=plan.type,
            title=plan.title,
            source_url=plan.ref if isinstance(source, URLSource) else None,
            version=plan.version,
            effective_date=plan.effective_date,
            metadata=plan.metadata,
        )

        if plan.frontmatter_id:
            id_by_frontmatter_id[plan.frontmatter_id] = result.document.id
        if plan.supersedes_frontmatter_id:
            pending_supersedes.append((result.document.id, plan.supersedes_frontmatter_id))

        outcomes.append(IngestOutcome(plan.ref, plan.title, "created" if result.created else "duplicate"))

    for document_id, target_frontmatter_id in pending_supersedes:
        target_id = id_by_frontmatter_id.get(target_frontmatter_id)
        if target_id is None:
            # Referenced a document not present in this run (e.g. the
            # returns-exception-matrix's "implicit" v1.0, which was never
            # authored as its own file) — nothing to link, not an error.
            continue
        update_supersedes(pool, document_id, target_id)

    return outcomes


def _print_summary(outcomes: list[IngestOutcome]) -> None:
    marker = {"created": "+", "duplicate": "=", "failed": "x"}
    for outcome in outcomes:
        line = f"  [{marker[outcome.status]}] {outcome.title} ({outcome.ref})"
        if outcome.detail:
            line += f" — {outcome.detail}"
        print(line)

    created = sum(1 for o in outcomes if o.status == "created")
    duplicate = sum(1 for o in outcomes if o.status == "duplicate")
    failed = sum(1 for o in outcomes if o.status == "failed")
    print(f"\n{created} ingested, {duplicate} already on file, {failed} failed (of {len(outcomes)} total)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser("ingest", help="Ingest the corpus into Postgres")
    ingest_parser.add_argument(
        "--scope",
        choices=["synthetic", "public", "all"],
        default="all",
        help="synthetic: 28 corpus files, offline. public: 16 live URLs, hits the real internet. all: both.",
    )

    args = parser.parse_args(argv)

    pool = get_pool()
    migrate(pool)

    plans: list[PlannedIngest] = []
    if args.scope in ("synthetic", "all"):
        plans += plan_synthetic()
    if args.scope in ("public", "all"):
        plans += plan_public()

    outcomes = ingest_plan(pool, plans)
    _print_summary(outcomes)
    return 1 if any(o.status == "failed" for o in outcomes) else 0


if __name__ == "__main__":
    raise SystemExit(main())
