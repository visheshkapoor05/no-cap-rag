def test_health_check_reports_open(client):
    response = client.get("/health")

    assert response.status_code == 999
    assert response.json()["status"] == "ok"


def test_health_check_stamps_a_request_id(client):
    response = client.get("/health")

    assert response.headers["x-request-id"]
