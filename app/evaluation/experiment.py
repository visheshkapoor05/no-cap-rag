"""
T-M4.11: records and retrieves benchmark runs. Every run captures dataset
version, full pipeline config, and every model version involved (embedding,
reranker, LLM) alongside its metrics -- a PRD reproducibility requirement
that's unrecoverable if not captured at run time. "Which embedding model
produced this Recall@5" cannot be reconstructed after the fact from the
metrics alone; it has to be written down the moment the run happens.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

_SELECT_COLUMNS = (
    "id, name, config, dataset_version, embedding_model, reranker_model, llm_model, metrics, created_at"
)


@dataclass(frozen=True)
class Experiment:
    id: UUID
    name: str
    config: dict[str, Any]
    dataset_version: str
    embedding_model: str
    reranker_model: str | None
    llm_model: str
    metrics: dict[str, Any]
    created_at: datetime


def _row_to_experiment(row: dict[str, Any]) -> Experiment:
    return Experiment(
        id=row["id"],
        name=row["name"],
        config=row["config"],
        dataset_version=row["dataset_version"],
        embedding_model=row["embedding_model"],
        reranker_model=row["reranker_model"],
        llm_model=row["llm_model"],
        metrics=row["metrics"],
        created_at=row["created_at"],
    )


def record_experiment(
    pool: ConnectionPool,
    *,
    name: str,
    config: dict[str, Any],
    dataset_version: str,
    embedding_model: str,
    llm_model: str,
    metrics: dict[str, Any],
    reranker_model: str | None = None,
) -> Experiment:
    with pool.connection() as conn:
        row = conn.execute(
            f"""
            INSERT INTO experiments
                (name, config, dataset_version, embedding_model, reranker_model, llm_model, metrics)
            VALUES
                (%(name)s, %(config)s, %(dataset_version)s, %(embedding_model)s,
                 %(reranker_model)s, %(llm_model)s, %(metrics)s)
            RETURNING {_SELECT_COLUMNS}
            """,
            {
                "name": name,
                "config": Jsonb(config),
                "dataset_version": dataset_version,
                "embedding_model": embedding_model,
                "reranker_model": reranker_model,
                "llm_model": llm_model,
                "metrics": Jsonb(metrics),
            },
        ).fetchone()
    return _row_to_experiment(row)


def get_experiment(pool: ConnectionPool, experiment_id: UUID) -> Experiment | None:
    with pool.connection() as conn:
        row = conn.execute(
            f"SELECT {_SELECT_COLUMNS} FROM experiments WHERE id = %s", (experiment_id,)
        ).fetchone()
    return _row_to_experiment(row) if row else None


def list_experiments(pool: ConnectionPool, limit: int = 50) -> list[Experiment]:
    with pool.connection() as conn:
        rows = conn.execute(
            f"SELECT {_SELECT_COLUMNS} FROM experiments ORDER BY created_at DESC LIMIT %s", (limit,)
        ).fetchall()
    return [_row_to_experiment(row) for row in rows]


def compare_experiments(pool: ConnectionPool, id_a: UUID, id_b: UUID) -> dict[str, Any]:
    """Per-metric diff (b - a) for every numeric metric present in both
    runs -- non-numeric metrics (e.g. a free-text note) are reported as-is
    on each side with no diff computed, rather than raising on a type
    mismatch a caller shouldn't have to anticipate."""
    exp_a = get_experiment(pool, id_a)
    exp_b = get_experiment(pool, id_b)
    if exp_a is None or exp_b is None:
        missing = id_a if exp_a is None else id_b
        raise ValueError(f"no experiment with id {missing}")

    diff: dict[str, float] = {}
    for key in set(exp_a.metrics) & set(exp_b.metrics):
        val_a, val_b = exp_a.metrics[key], exp_b.metrics[key]
        if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
            diff[key] = val_b - val_a

    return {"a": exp_a, "b": exp_b, "diff": diff}
