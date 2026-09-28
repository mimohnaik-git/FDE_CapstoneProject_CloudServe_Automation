import pytest
from fastapi.testclient import TestClient

from src import api


@pytest.fixture
def client(pipeline):
    api.set_pipeline(pipeline)
    yield TestClient(api.app)
    api.set_pipeline(None)


def test_health(client):
    r = client.get("/health").json()
    assert r["status"] == "ok" and r["customer_release_authorized"] is False
    assert r["release_control_precedence"] == "DISABLED overrides ENABLED"


def test_submit_and_review(client, email_ticket):
    r = client.post("/tickets", json=email_ticket).json()
    assert r["route"] == "ESCALATE" and r["intent"]["label"]
    assert "answer" not in r and "citations" not in r
    v = client.get("/review/T-1").json()
    for k in ("eligibility_status", "document_id", "customer_tier", "plan_applicable",
              "blocking_flags", "draft"):
        assert k in v
    assert v["internal_only"] is True


def test_auto_response_exposes_controlled_answer(auto_pipeline, auto_ticket):
    api.set_pipeline(auto_pipeline)
    try:
        r = TestClient(api.app).post("/tickets", json=auto_ticket).json()
    finally:
        api.set_pipeline(None)
    assert r["route"] == "AUTO_RESPOND"
    assert r["answer"] and r["citations"] and r["config_fingerprint"]


def test_approval_never_sends(client, email_ticket):
    client.post("/tickets", json=email_ticket)
    r = client.post("/review/T-1", json={"reviewer": "agent1", "action": "approve"}).json()
    assert r == {"recorded": True, "customer_message_sent": False}
    assert client.get("/review/T-1").json()["reviews"][0]["action"] == "approve"


def test_unknown_ticket_404(client):
    assert client.get("/review/nope").status_code == 404
    assert client.post("/review/nope", json={"reviewer": "a", "action": "approve"}).status_code == 404


def test_bad_review_action_rejected(client, email_ticket):
    client.post("/tickets", json=email_ticket)
    assert client.post("/review/T-1", json={"reviewer": "a", "action": "send"}).status_code == 422


def test_metrics_endpoint(client, email_ticket):
    client.post("/tickets", json=email_ticket)
    assert b"cloudserve_decisions_total" in client.get("/metrics").content


def test_run_mode_is_propagated_to_audit_and_metrics(client, email_ticket):
    response = client.post(
        "/tickets",
        json=email_ticket,
        headers={"X-CloudServe-Run-Mode": "demo", "X-CloudServe-Run-Id": "demo-test"},
    )
    assert response.status_code == 200
    decision = client.get(f"/decisions/{email_ticket['ticket_id']}").json()
    assert decision["run_mode"] == "demo"
    assert decision["run_id"] == "demo-test"
    assert b'run_mode="demo"' in client.get("/metrics").content


def test_invalid_run_mode_is_rejected(client, email_ticket):
    response = client.post(
        "/tickets", json=email_ticket,
        headers={"X-CloudServe-Run-Mode": "ticket-id-would-be-high-cardinality"},
    )
    assert response.status_code == 400
