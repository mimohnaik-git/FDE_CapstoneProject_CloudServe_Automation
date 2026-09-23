"""Operational API contract tests using controlled pipeline outcomes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import src.api as api_module
from src.ingest import TicketNormalizationEngine
from src.logging_store import DecisionLoggingEngine
from src.security import api_rate_limiter


TEST_API_KEY = "synthetic-test-api-key"
AUTH_HEADERS = {"Authorization": f"Bearer {TEST_API_KEY}"}


def _ticket(channel: str = "email") -> dict:
    return {
        "ticket_id": f"API-{channel}", "channel": channel, "customer_tier": "standard",
        "subject": "Login help", "body": "My login fails with an invalid credentials error.",
        "customer_id": "CUST-API-1",
    }


def _result(*, action: str = "ESCALATE", reason_code: str = "LOW_CONFIDENCE") -> dict:
    released = action == "AUTO_RESPOND"
    response = {
        "response_text": "Use the documented login recovery procedure.",
        "citations": [{"document_id": "DOC-AUTH-001", "chunk_id": "DOC-AUTH-001-1"}],
    } if released else None
    return {
        "ticket_id": "API-email", "status": action, "response_released": released,
        "response_text": response["response_text"] if response else None, "response": response,
        "classification": {"intent": "authentication_failure", "urgency": "medium", "confidence": 0.95},
        "reason": "Controlled routing outcome.", "reason_code": reason_code,
        "decision_id": "DECISION-API-1", "processing_status": "COMPLETED",
        "audit_record": {"private": "metadata"}, "decision_record": {"system_prompt": "hidden"},
        "error_type": "InternalSyntheticError", "expected_route": "hidden-evaluation-field",
    }


class StubOrchestrator:
    def __init__(self, result=None, error: Exception | None = None):
        self.result = result or _result()
        self.error = error
        self.calls: list[dict] = []

    def process_ticket(self, ticket):
        self.calls.append(ticket)
        if self.error:
            raise self.error
        result = dict(self.result)
        result["ticket_id"] = ticket["ticket_id"]
        return result


@pytest.fixture(autouse=True)
def api_security_defaults(monkeypatch):
    monkeypatch.setenv("SUPPORT_API_KEY", TEST_API_KEY)
    monkeypatch.setenv("SUPPORT_API_RATE_LIMIT_PER_MINUTE", "60")
    api_rate_limiter.reset()

    yield

    api_rate_limiter.reset()


@pytest.fixture
def stub():
    return StubOrchestrator()


@pytest.fixture
def client(stub):
    api_module.app.dependency_overrides[api_module.get_orchestrator] = lambda: stub
    with TestClient(api_module.app) as test_client:
        test_client.headers.update(AUTH_HEADERS)
        yield test_client
    api_module.app.dependency_overrides.clear()


def test_health_reports_application_health_without_dependency_claims(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "support-pipeline", "dependency_status": "not_checked"}


def test_valid_ticket_returns_safe_escalation_and_decision_id(client, stub):
    response = client.post("/tickets/process", json=_ticket())
    assert response.status_code == 200
    assert response.json()["terminal_action"] == "ESCALATE"
    assert response.json()["decision_id"] == "DECISION-API-1"
    assert response.json()["processing_status"] == "COMPLETED"
    assert stub.calls == [_ticket()]


@pytest.mark.parametrize("channel", ["email", "chat", "docs_comment", "forum"])
def test_all_four_channels_are_accepted(client, stub, channel):
    response = client.post("/tickets/process", json=_ticket(channel))
    assert response.status_code == 200
    assert stub.calls[-1]["channel"] == channel


def test_health_remains_available_without_api_credential():
    with TestClient(api_module.app) as public_client:
        response = public_client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_processing_fails_closed_when_server_authentication_is_not_configured(
    client,
    stub,
    monkeypatch,
):
    monkeypatch.delenv("SUPPORT_API_KEY", raising=False)

    response = client.post("/tickets/process", json=_ticket())

    assert response.status_code == 503
    assert response.json()["detail"] == "API authentication is not configured."
    assert stub.calls == []


@pytest.mark.parametrize(
    "authorization",
    [
        "",
        "Basic synthetic-test-api-key",
        "Bearer wrong-api-key",
    ],
)
def test_processing_rejects_missing_or_invalid_api_credentials(
    client,
    stub,
    authorization,
):
    response = client.post(
        "/tickets/process",
        json=_ticket(),
        headers={"Authorization": authorization},
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["detail"] == "Invalid or missing API credential."
    assert stub.calls == []


def test_failed_authentication_does_not_resolve_pipeline_dependency(
    monkeypatch,
):
    dependency_calls = []

    def forbidden_orchestrator_resolution():
        dependency_calls.append("resolved")
        return StubOrchestrator()

    api_module.app.dependency_overrides[
        api_module.get_orchestrator
    ] = forbidden_orchestrator_resolution

    try:
        with TestClient(api_module.app) as test_client:
            response = test_client.post(
                "/tickets/process",
                json=_ticket(),
                headers={"Authorization": "Bearer wrong-api-key"},
            )
    finally:
        api_module.app.dependency_overrides.clear()

    assert response.status_code == 401
    assert dependency_calls == []


def test_api_secret_is_never_exposed_by_http_surfaces(
    monkeypatch,
):
    secret = "SYNTHETIC-PRIVATE-API-KEY-DO-NOT-EXPOSE"
    monkeypatch.setenv("SUPPORT_API_KEY", secret)
    api_rate_limiter.reset()

    with TestClient(api_module.app) as test_client:
        unauthorized = test_client.post(
            "/tickets/process",
            json=_ticket(),
            headers={"Authorization": "Bearer wrong-api-key"},
        )
        metrics = test_client.get("/metrics")
        openapi = test_client.get("/openapi.json")

    combined = (
        unauthorized.text
        + metrics.text
        + openapi.text
    )

    assert unauthorized.status_code == 401
    assert secret not in combined
    assert "SYNTHETIC-PRIVATE-API-KEY" not in combined


def test_processing_rate_limit_is_enforced_per_authenticated_identity(
    client,
    stub,
    monkeypatch,
):
    monkeypatch.setenv("SUPPORT_API_RATE_LIMIT_PER_MINUTE", "2")
    api_rate_limiter.reset()

    first = client.post("/tickets/process", json=_ticket())
    second = client.post("/tickets/process", json=_ticket())
    third = client.post("/tickets/process", json=_ticket())

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.json()["detail"] == "API rate limit exceeded."
    assert len(stub.calls) == 2


def test_invalid_server_rate_limit_configuration_fails_closed(
    client,
    stub,
    monkeypatch,
):
    monkeypatch.setenv(
        "SUPPORT_API_RATE_LIMIT_PER_MINUTE",
        "not-an-integer",
    )
    api_rate_limiter.reset()

    response = client.post("/tickets/process", json=_ticket())

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "API rate limiting is not configured correctly."
    )
    assert stub.calls == []


@pytest.mark.parametrize("payload", [
    {},
    {"ticket_id": "X", "channel": "slack", "customer_tier": "standard", "body": "help"},
    {"ticket_id": "X", "channel": "email", "customer_tier": "standard", "body": "   "},
    {**_ticket(), "unknown_internal_field": "not allowed"},
])
def test_malformed_ticket_is_controlled_422_and_never_calls_pipeline(client, stub, payload):
    response = client.post("/tickets/process", json=payload)
    assert response.status_code == 422
    assert stub.calls == []


def test_controlled_auto_response_exposes_only_released_answer_and_citations(client, stub):
    stub.result = _result(action="AUTO_RESPOND", reason_code="SAFE_TO_AUTO_RESPOND")
    body = client.post("/tickets/process", json=_ticket()).json()
    assert body["terminal_action"] == "AUTO_RESPOND"
    assert body["response_text"].startswith("Use the documented")
    assert body["citations"] == [{"document_id": "DOC-AUTH-001", "chunk_id": "DOC-AUTH-001-1"}]


def test_guardrail_blocked_result_is_safe_escalation(client, stub):
    stub.result = _result(reason_code="PROMPT_INJECTION_DETECTED")
    body = client.post("/tickets/process", json=_ticket()).json()
    assert body["terminal_action"] == "ESCALATE"
    assert body["routing_reason_code"] == "PROMPT_INJECTION_DETECTED"
    assert body["response_text"] is None
    assert body["citations"] == []


def test_internal_escalation_handoff_is_not_exposed_by_public_api(client, stub):
    stub.result = {
        **_result(reason_code="EVIDENCE_SUFFICIENCY_UNVERIFIED"),
        "escalation_context": {
            "visibility": "INTERNAL_REVIEW_ONLY",
            "review_draft": "PRIVATE REVIEW DRAFT - DO NOT RELEASE",
            "citations": [
                {
                    "document_id": "DOC-AUTH-001",
                    "chunk_id": "DOC-AUTH-001-1",
                }
            ],
        },
    }

    response = client.post("/tickets/process", json=_ticket())
    body = response.json()

    assert response.status_code == 200
    assert body["terminal_action"] == "ESCALATE"
    assert body["response_text"] is None
    assert body["citations"] == []
    assert "escalation_context" not in body
    assert "PRIVATE REVIEW DRAFT" not in response.text


def test_pipeline_exception_is_suppressed_and_cannot_crash_api(client, stub):
    secret = "sk-secret-provider-key"
    stub.error = RuntimeError(f"database failed; key={secret}; system prompt=private")
    response = client.post("/tickets/process", json=_ticket())
    serialized = response.text
    assert response.status_code == 200
    assert response.json()["terminal_action"] == "ESCALATE"
    assert response.json()["processing_status"] == "FAILED"
    assert response.json()["decision_id"] is None
    assert secret not in serialized
    assert "database failed" not in serialized
    assert "system prompt" not in serialized.lower()


def test_private_and_evaluation_fields_are_not_in_response(client):
    body = client.post("/tickets/process", json=_ticket()).json()
    assert set(body) == {
        "ticket_id", "terminal_action", "intent", "urgency", "confidence", "routing_reason",
        "routing_reason_code", "response_text", "citations", "decision_id", "processing_status",
    }
    serialized = str(body).lower()
    for private_name in ("audit_record", "system_prompt", "expected_route", "internalsyntheticerror"):
        assert private_name not in serialized


def test_production_support_pipeline_orchestrator_entry_point_is_called(monkeypatch):
    calls = []
    monkeypatch.setattr(api_module.SupportPipelineOrchestrator, "__init__", lambda self: None)
    monkeypatch.setattr(api_module.SupportPipelineOrchestrator, "process_ticket", lambda self, ticket: calls.append(ticket) or _result())
    api_module.app.dependency_overrides.clear()
    api_module.get_orchestrator.cache_clear()
    with TestClient(api_module.app) as production_client:
        response = production_client.post(
            "/tickets/process",
            json=_ticket(),
            headers=AUTH_HEADERS,
        )
    api_module.get_orchestrator.cache_clear()
    assert response.status_code == 200
    assert len(calls) == 1
    assert calls[0]["ticket_id"] == "API-email"


def test_metrics_endpoint_is_prometheus_compatible_and_has_required_series(client):
    client.post("/tickets/process", json=_ticket("chat"))
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    text = response.text
    for name in (
        "support_tickets_processed_total", "support_processing_latency_seconds_bucket",
        "support_processing_latency_seconds_p50", "support_processing_latency_seconds_p95",
        "support_auto_response_rate", "support_escalation_rate",
        "support_classification_confidence_bucket",
    ):
        assert name in text
    assert 'channel="live_chat"' in text
    assert 'terminal_action="ESCALATE"' in text


def test_metrics_never_expose_ticket_content_customer_id_or_secret_labels(client, stub):
    secret = "sk-super-secret-metric-value"
    payload = _ticket()
    payload["body"] = f"My token is {secret}"
    payload["customer_id"] = "PRIVATE-CUSTOMER-987"
    stub.result = {**_result(), "processing_status": "FAILED", "error_category": secret, "failure_state": secret}
    client.post("/tickets/process", json=payload)
    text = client.get("/metrics").text
    assert secret not in text
    assert payload["body"] not in text
    assert payload["customer_id"] not in text
    assert 'category="OTHER"' in text


def test_guardrail_block_reason_is_counted_with_bounded_label(client, stub):
    stub.result = {
        **_result(reason_code="PROMPT_INJECTION"),
        "guardrails": {"passed": False, "blocked": True, "reason_codes": ["PROMPT_INJECTION"]},
    }
    client.post("/tickets/process", json=_ticket())
    text = client.get("/metrics").text
    assert 'support_guardrail_blocks_total{reason="PROMPT_INJECTION"}' in text


class KillSwitchOrchestrator:
    def __init__(self):
        self.ingester = TicketNormalizationEngine()
        self.logger = DecisionLoggingEngine(db_url="sqlite:///:memory:")
        self.calls = []

    def process_ticket(self, payload):
        self.calls.append(payload)
        result = _result(action="AUTO_RESPOND", reason_code="SAFE_TO_AUTO_RESPOND")
        result["ticket_id"] = payload["ticket_id"]
        return result


def test_kill_switch_suppresses_auto_response_escalates_and_persists_audit(monkeypatch, tmp_path):
    switch = tmp_path / "auto_response.disabled"
    switch.touch()
    monkeypatch.setenv("SUPPORT_KILL_SWITCH_FILE", str(switch))
    monkeypatch.delenv("SUPPORT_KILL_SWITCH", raising=False)
    orchestrator = KillSwitchOrchestrator()
    api_module.app.dependency_overrides[api_module.get_orchestrator] = lambda: orchestrator
    try:
        with TestClient(api_module.app) as test_client:
            body = test_client.post(
                "/tickets/process",
                json=_ticket(),
                headers=AUTH_HEADERS,
            ).json()
    finally:
        api_module.app.dependency_overrides.clear()
    assert orchestrator.calls == []
    assert body["terminal_action"] == "ESCALATE"
    assert body["routing_reason_code"] == "KILL_SWITCH_ENABLED"
    assert body["response_text"] is None and body["citations"] == []
    assert body["decision_id"]
    stored = orchestrator.logger.get_decision_by_id(body["decision_id"])
    assert stored["terminal_action"] == "ESCALATE"
    assert stored["terminal_reason_code"] == "KILL_SWITCH_ENABLED"
    assert stored["response_released"] is False


def test_normal_behavior_is_preserved_when_kill_switch_disabled(monkeypatch, tmp_path):
    monkeypatch.setenv("SUPPORT_KILL_SWITCH_FILE", str(tmp_path / "absent"))
    monkeypatch.delenv("SUPPORT_KILL_SWITCH", raising=False)
    orchestrator = KillSwitchOrchestrator()
    api_module.app.dependency_overrides[api_module.get_orchestrator] = lambda: orchestrator
    try:
        with TestClient(api_module.app) as test_client:
            body = test_client.post(
                "/tickets/process",
                json=_ticket(),
                headers=AUTH_HEADERS,
            ).json()
    finally:
        api_module.app.dependency_overrides.clear()
    assert len(orchestrator.calls) == 1
    assert body["terminal_action"] == "AUTO_RESPOND"
