"""T-M1.8: the first real end-to-end proof that Source (T-M1.5) → idempotent
ingest (T-M1.6/T-M1.7) → Postgres actually work together over real HTTP,
not just when called directly from a script."""
from pathlib import Path
from uuid import uuid4

CORPUS = Path(__file__).resolve().parent.parent / "corpus"
SHIFT_POLICY = str(CORPUS / "synthetic" / "clean" / "shift-policy.md")


def test_ingest_then_get_round_trips_over_http(client, clean_documents):
    response = client.post(
        "/documents/ingest",
        json={"ref": SHIFT_POLICY, "type": "staff", "title": "Shift Policy", "version": "1.0"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["created"] is True
    assert body["version"] == "1.0"
    assert body["content_hash"]

    fetched = client.get(f"/documents/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "Shift Policy"
    assert fetched.json()["source_url"] is None  # file-sourced, not a public URL


def test_ingesting_twice_returns_200_not_201_the_second_time(client, clean_documents):
    first = client.post(
        "/documents/ingest",
        json={"ref": SHIFT_POLICY, "type": "staff", "title": "Shift Policy"},
    )
    second = client.post(
        "/documents/ingest",
        json={"ref": SHIFT_POLICY, "type": "staff", "title": "Shift Policy"},
    )

    assert first.status_code == 201
    assert second.status_code == 200  # same content already on file — no new row
    assert second.json()["created"] is False
    assert second.json()["id"] == first.json()["id"]


def test_get_unknown_document_is_404(client, clean_documents):
    response = client.get(f"/documents/{uuid4()}")

    assert response.status_code == 404


def test_ingest_with_unreadable_ref_is_422(client, clean_documents):
    response = client.post(
        "/documents/ingest",
        json={"ref": str(CORPUS / "synthetic" / "clean" / "does-not-exist.md"), "type": "staff", "title": "Nope"},
    )

    assert response.status_code == 422
    assert "not_found" in response.json()["detail"]
