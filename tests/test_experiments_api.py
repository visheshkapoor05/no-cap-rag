"""T-M4.12: GET /experiments/{id} and POST /experiments/compare, real app + real Postgres."""
import uuid

from app.core.db import get_pool, migrate
from app.evaluation import record_experiment


def test_get_experiment_by_id_returns_the_real_record(client):
    pool = get_pool()
    migrate(pool)
    exp = record_experiment(
        pool, name="api-test", config={"strategy": "dense"}, dataset_version="v1",
        embedding_model="gemini-embedding-001", llm_model="gemini-2.5-flash",
        metrics={"recall_at_5": 0.9},
    )
    resp = client.get(f"/experiments/{exp.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "api-test"
    assert body["metrics"]["recall_at_5"] == 0.9


def test_get_experiment_by_id_404s_for_an_unknown_id(client):
    resp = client.get(f"/experiments/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_compare_endpoint_returns_a_real_numeric_diff(client):
    pool = get_pool()
    exp_a = record_experiment(
        pool, name="a", config={}, dataset_version="v1", embedding_model="m", llm_model="l",
        metrics={"recall_at_5": 0.80},
    )
    exp_b = record_experiment(
        pool, name="b", config={}, dataset_version="v1", embedding_model="m", llm_model="l",
        metrics={"recall_at_5": 0.91},
    )
    resp = client.post("/experiments/compare", json={"id_a": str(exp_a.id), "id_b": str(exp_b.id)})
    assert resp.status_code == 200
    body = resp.json()
    assert body["diff"]["recall_at_5"] == 0.11000000000000004 or abs(body["diff"]["recall_at_5"] - 0.11) < 1e-6


def test_compare_endpoint_404s_for_an_unknown_id(client):
    pool = get_pool()
    exp = record_experiment(
        pool, name="real", config={}, dataset_version="v1", embedding_model="m", llm_model="l", metrics={}
    )
    resp = client.post("/experiments/compare", json={"id_a": str(exp.id), "id_b": str(uuid.uuid4())})
    assert resp.status_code == 404
