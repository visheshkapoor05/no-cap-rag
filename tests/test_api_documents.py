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


def test_upload_a_real_file_ingests_it(client, clean_documents):
    """The actual "attach a document" path — distinct from POST /ingest,
    which only ever points at a ref the server already has on disk or can
    fetch. This one sends real file bytes in the request body, the way any
    other web upload form would."""
    with open(SHIFT_POLICY, "rb") as f:
        response = client.post(
            "/documents/upload",
            files={"file": ("shift-policy.md", f, "text/markdown")},
            data={"type": "staff", "title": "Shift Policy", "version": "1.0"},
        )

    assert response.status_code == 201
    body = response.json()
    assert body["created"] is True
    assert body["version"] == "1.0"
    assert body["content_hash"]


def test_uploading_the_same_file_twice_returns_200_not_201(client, clean_documents):
    with open(SHIFT_POLICY, "rb") as f:
        first = client.post(
            "/documents/upload",
            files={"file": ("shift-policy.md", f, "text/markdown")},
            data={"type": "staff", "title": "Shift Policy"},
        )
    with open(SHIFT_POLICY, "rb") as f:
        second = client.post(
            "/documents/upload",
            files={"file": ("shift-policy.md", f, "text/markdown")},
            data={"type": "staff", "title": "Shift Policy"},
        )

    assert first.status_code == 201
    assert second.status_code == 200  # identical content, T-M1.7's idempotency check
    assert second.json()["created"] is False
    assert second.json()["id"] == first.json()["id"]


def test_upload_accepts_a_real_pdf_from_the_mixed_corpus(client, clean_documents):
    """Proves the upload path shares T-M1.5's real format extraction
    (pdftotext -layout) — not just markdown, the same four formats the
    Source abstraction already handles."""
    pdf_path = CORPUS / "synthetic" / "mixed" / "pos-outage-postmortem.pdf"
    with open(pdf_path, "rb") as f:
        response = client.post(
            "/documents/upload",
            files={"file": ("pos-outage-postmortem.pdf", f, "application/pdf")},
            data={"type": "incident", "title": "POS Outage Postmortem"},
        )

    assert response.status_code == 201
    assert response.json()["created"] is True


def test_upload_with_no_extractable_text_is_422(client, clean_documents):
    response = client.post(
        "/documents/upload",
        files={"file": ("empty.bin", b"", "application/octet-stream")},
        data={"type": "staff", "title": "Empty"},
    )

    assert response.status_code == 422
    assert "could not extract text" in response.json()["detail"]


def test_upload_with_malformed_metadata_json_is_422(client, clean_documents):
    with open(SHIFT_POLICY, "rb") as f:
        response = client.post(
            "/documents/upload",
            files={"file": ("shift-policy.md", f, "text/markdown")},
            data={"type": "staff", "title": "Shift Policy", "metadata": "{not valid json"},
        )

    assert response.status_code == 422
    assert "not valid JSON" in response.json()["detail"]


def test_upload_without_effective_date_auto_detects_it_from_the_document_text(client, clean_documents):
    """shift-policy.md's own header says "Effective: January 1, 2026" --
    omitting effective_date in the form should still populate it."""
    with open(SHIFT_POLICY, "rb") as f:
        response = client.post(
            "/documents/upload",
            files={"file": ("shift-policy.md", f, "text/markdown")},
            data={"type": "staff", "title": "Shift Policy"},  # no effective_date
        )

    assert response.status_code == 201
    fetched = client.get(f"/documents/{response.json()['id']}")
    assert fetched.json()["effective_date"] == "2026-01-01"


def test_upload_with_explicit_effective_date_overrides_the_auto_detected_one(client, clean_documents):
    with open(SHIFT_POLICY, "rb") as f:
        response = client.post(
            "/documents/upload",
            files={"file": ("shift-policy.md", f, "text/markdown")},
            data={"type": "staff", "title": "Shift Policy", "effective_date": "2030-05-05"},
        )

    assert response.status_code == 201
    fetched = client.get(f"/documents/{response.json()['id']}")
    assert fetched.json()["effective_date"] == "2030-05-05"


def test_upload_parses_metadata_json_correctly(client, clean_documents):
    with open(SHIFT_POLICY, "rb") as f:
        response = client.post(
            "/documents/upload",
            files={"file": ("shift-policy.md", f, "text/markdown")},
            data={"type": "staff", "title": "Shift Policy", "metadata": '{"source": "manual upload"}'},
        )

    assert response.status_code == 201
    fetched = client.get(f"/documents/{response.json()['id']}")
    assert fetched.json()["metadata"] == {"source": "manual upload"}
