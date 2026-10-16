"""T-M4.11: experiment recording/retrieval/comparison against the real
Postgres migrations table (0003_create_experiments_table.sql)."""
import uuid

import pytest

from app.core.db import get_pool, migrate
from app.evaluation import compare_experiments, get_experiment, list_experiments, record_experiment


def test_record_and_get_experiment_round_trips_everything():
    pool = get_pool()
    migrate(pool)
    exp = record_experiment(
        pool,
        name="dense-only baseline",
        config={"strategy": "dense", "k": 10},
        dataset_version="v1-50q",
        embedding_model="gemini-embedding-001",
        llm_model="gemini-2.5-flash",
        metrics={"recall_at_5": 0.937, "mrr": 0.917},
    )
    assert exp.reranker_model is None  # not passed, stays NULL

    fetched = get_experiment(pool, exp.id)
    assert fetched is not None
    assert fetched.name == "dense-only baseline"
    assert fetched.config == {"strategy": "dense", "k": 10}
    assert fetched.metrics["recall_at_5"] == 0.937
    assert fetched.embedding_model == "gemini-embedding-001"


def test_get_experiment_returns_none_for_an_unknown_id():
    pool = get_pool()
    assert get_experiment(pool, uuid.uuid4()) is None


def test_list_experiments_returns_most_recent_first():
    pool = get_pool()
    first = record_experiment(
        pool, name="run-a", config={}, dataset_version="v1", embedding_model="m", llm_model="l", metrics={}
    )
    second = record_experiment(
        pool, name="run-b", config={}, dataset_version="v1", embedding_model="m", llm_model="l", metrics={}
    )
    recent = list_experiments(pool, limit=2)
    ids_in_order = [e.id for e in recent]
    assert ids_in_order.index(second.id) < ids_in_order.index(first.id)


def test_compare_experiments_diffs_shared_numeric_metrics():
    pool = get_pool()
    exp_a = record_experiment(
        pool,
        name="baseline",
        config={"strategy": "dense"},
        dataset_version="v1",
        embedding_model="m",
        llm_model="l",
        metrics={"recall_at_5": 0.80, "mrr": 0.70, "note": "first pass"},
    )
    exp_b = record_experiment(
        pool,
        name="plus-reranker",
        config={"strategy": "dense", "reranker": True},
        dataset_version="v1",
        embedding_model="m",
        reranker_model="cross-encoder/ms-marco-MiniLM-L-6-v2",
        llm_model="l",
        metrics={"recall_at_5": 0.91, "mrr": 0.88, "note": "second pass"},
    )
    result = compare_experiments(pool, exp_a.id, exp_b.id)
    assert result["diff"]["recall_at_5"] == pytest.approx(0.11)
    assert result["diff"]["mrr"] == pytest.approx(0.18)
    assert "note" not in result["diff"]  # non-numeric metric excluded from the diff, not crashed on
    assert result["b"].reranker_model == "cross-encoder/ms-marco-MiniLM-L-6-v2"


def test_compare_experiments_raises_for_an_unknown_id():
    pool = get_pool()
    exp = record_experiment(
        pool, name="real", config={}, dataset_version="v1", embedding_model="m", llm_model="l", metrics={}
    )
    with pytest.raises(ValueError):
        compare_experiments(pool, exp.id, uuid.uuid4())
