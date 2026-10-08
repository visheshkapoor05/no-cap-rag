"""
T-M2.10: chunk statistics over the real, fully-chunked corpus -- token-count
distribution, orphans under 50 tokens, chunks over the MAX cap, and % with a
resolved section_path. Exists to catch a bad MIN/MAX threshold or a chunker
regression on the real population, not the 3-document sample T-M2.3's
guesses were originally set from. See ../../ANALOGY.md.

    python -m evals.chunk_stats
"""
from __future__ import annotations

import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import get_pool  # noqa: E402

MIN_CHUNK_TOKENS = 40
MAX_CHUNK_TOKENS = 350
ORPHAN_CEILING = 50  # "orphans under 50 tokens" per the task spec -- a wider
                      # net than the MIN=40 guard itself, to catch chunks that
                      # only just squeaked past it.


def compute_stats(pool) -> dict:
    with pool.connection() as conn:
        rows = conn.execute(
            "SELECT c.token_count, c.section_path, d.title "
            "FROM chunks c JOIN documents d ON d.id = c.document_id"
        ).fetchall()

    token_counts = [r["token_count"] for r in rows]
    total = len(token_counts)

    orphans = [r for r in rows if r["token_count"] < ORPHAN_CEILING]
    over_cap = [r for r in rows if r["token_count"] > MAX_CHUNK_TOKENS]
    with_section = [r for r in rows if r["section_path"]]

    buckets = {
        "0-49": 0, "50-99": 0, "100-149": 0, "150-199": 0, "200-249": 0,
        "250-299": 0, "300-349": 0, "350+": 0,
    }
    for tc in token_counts:
        if tc > 349:
            buckets["350+"] += 1
        else:
            lo = (tc // 50) * 50
            buckets[f"{lo}-{lo+49}"] += 1

    return {
        "total_chunks": total,
        "min": min(token_counts),
        "max": max(token_counts),
        "mean": round(statistics.mean(token_counts), 1),
        "median": statistics.median(token_counts),
        "stdev": round(statistics.stdev(token_counts), 1),
        "buckets": buckets,
        "orphans_under_50": orphans,
        "orphan_rate_pct": round(100 * len(orphans) / total, 1),
        "over_cap": over_cap,
        "with_section_path": len(with_section),
        "section_path_resolution_pct": round(100 * len(with_section) / total, 1),
    }


def main() -> None:
    stats = compute_stats(get_pool())

    print(f"Total chunks: {stats['total_chunks']}")
    print(f"Token count: min={stats['min']} max={stats['max']} mean={stats['mean']} "
          f"median={stats['median']} stdev={stats['stdev']}")
    print("\nDistribution:")
    for bucket, count in stats["buckets"].items():
        bar = "#" * count
        print(f"  {bucket:>8} tok | {count:3d} {bar}")

    print(f"\nOrphans (<{ORPHAN_CEILING} tok): {len(stats['orphans_under_50'])} "
          f"({stats['orphan_rate_pct']}%) -- exit criterion: under 5%")
    for r in stats["orphans_under_50"]:
        print(f"    {r['token_count']:3d} tok | {r['title']} | {r['section_path']!r}")

    print(f"\nOver MAX cap ({MAX_CHUNK_TOKENS} tok): {len(stats['over_cap'])} -- should always be 0")
    for r in stats["over_cap"]:
        print(f"    {r['token_count']:3d} tok | {r['title']} | {r['section_path']!r}")

    print(f"\nResolved section_path: {stats['with_section_path']}/{stats['total_chunks']} "
          f"({stats['section_path_resolution_pct']}%)")


if __name__ == "__main__":
    main()
