import json
import subprocess
import sys
from pathlib import Path

import pytest
from src.logging_store import DecisionLogStore

@pytest.fixture
def store():
    """In-memory SQLite store for clean testing."""
    return DecisionLogStore("sqlite:///:memory:")

@pytest.fixture
def sample_data():
    normalized_ticket = {
        "ticket_id": "T-1001",
        "channel": "email",
        "customer_tier": "enterprise",
        "raw_content": "Cannot authenticate via CLI.",
        "customer_id": "CUST-55"
    }

    classification = {
        "intent": "technical_issue",
        "urgency": "high",
        "confidence": 0.95
    }

    retrieval_results = [
        {"doc_id": "DOC-AUTH-001", "chunk_content": "CLI authentication setup...", "relevance_score": 0.90}
    ]

    routing_decision = {
        "action": "AUTO_RESPOND",
        "reason": "all_routing_criteria_satisfied",
        "confidence": 0.95,
        "threshold": 0.80,
        "intent": "technical_issue",
        "escalate": False
    }

    generated_response = {
        "response_text": "Follow steps in DOC-AUTH-001 to resolve CLI auth.",
        "citations": ["DOC-AUTH-001"],
        "grounded": True,
        "model_name": "offline",
        "ticket_id": "T-1001"
    }

    guardrail_result = {
        "passed": True,
        "action": "PROCEED",
        "blocked_by": [],
        "reasons": [],
        "checks_run": ["private_data_leakage", "grounding_failure"]
    }

    return {
        "normalized_ticket": normalized_ticket,
        "classification": classification,
        "retrieval_results": retrieval_results,
        "routing_decision": routing_decision,
        "generated_response": generated_response,
        "guardrail_result": guardrail_result
    }


def test_record_decision_creates_retrievable_record(store, sample_data):
    """Recording a decision produces a complete, persisted record."""
    d = sample_data
    record = store.record_decision(
        ticket_id="T-1001",
        routing_action="AUTO_RESPOND",
        routing_reason="all_routing_criteria_satisfied",
        normalized_ticket=d["normalized_ticket"],
        classification=d["classification"],
        retrieval_results=d["retrieval_results"],
        routing_decision=d["routing_decision"],
        generated_response=d["generated_response"],
        guardrail_result=d["guardrail_result"]
    )

    assert record["decision_id"] is not None
    assert record["ticket_id"] == "T-1001"
    assert record["channel"] == "email"
    assert record["customer_tier"] == "enterprise"
    assert record["intent"] == "technical_issue"
    assert record["confidence"] == 0.95
    assert record["retrieved_source_ids"] == ["DOC-AUTH-001"]
    assert record["routing_action"] == "AUTO_RESPOND"
    assert record["citations"] == ["DOC-AUTH-001"]
    assert record["is_grounded"] is True
    assert record["guardrail_passed"] is True


def test_get_decision_by_id(store, sample_data):
    """Retrieving by decision_id returns the exact stored record."""
    d = sample_data
    created = store.record_decision(
        ticket_id="T-1001",
        routing_action="AUTO_RESPOND",
        routing_reason="all_routing_criteria_satisfied",
        normalized_ticket=d["normalized_ticket"],
        classification=d["classification"]
    )

    fetched = store.get_decision_by_id(created["decision_id"])

    assert fetched is not None
    assert fetched["decision_id"] == created["decision_id"]
    assert fetched["ticket_id"] == "T-1001"


def test_get_decisions_by_ticket_id(store, sample_data):
    """Multiple decisions for the same ticket_id are all retrieved."""
    d = sample_data
    store.record_decision(ticket_id="T-2002", routing_action="ESCALATE", routing_reason="low_confidence")
    store.record_decision(ticket_id="T-2002", routing_action="AUTO_RESPOND", routing_reason="retry_passed")

    records = store.get_decisions_by_ticket_id("T-2002")

    assert len(records) == 2
    assert {r["routing_action"] for r in records} == {"ESCALATE", "AUTO_RESPOND"}


def test_list_all_decisions(store):
    """list_all_decisions returns every record across tickets."""
    store.record_decision(ticket_id="T-1", routing_action="AUTO_RESPOND", routing_reason="ok")
    store.record_decision(ticket_id="T-2", routing_action="ESCALATE", routing_reason="risk")
    store.record_decision(ticket_id="T-3", routing_action="AUTO_RESPOND", routing_reason="ok")

    all_records = store.list_all_decisions()

    assert len(all_records) == 3


def test_get_decisions_by_outcome(store):
    """Filter decisions by routing outcome (AUTO_RESPOND or ESCALATE)."""
    store.record_decision(ticket_id="T-1", routing_action="AUTO_RESPOND", routing_reason="ok")
    store.record_decision(ticket_id="T-2", routing_action="ESCALATE", routing_reason="risk")
    store.record_decision(ticket_id="T-3", routing_action="AUTO_RESPOND", routing_reason="ok")

    auto_records = store.get_decisions_by_outcome("AUTO_RESPOND")
    esc_records = store.get_decisions_by_outcome("ESCALATE")

    assert len(auto_records) == 2
    assert len(esc_records) == 1
    assert auto_records[0]["ticket_id"] == "T-1"


def test_log_decision_dict_interface(store):
    """log_decision accepts a complete decision record dict and returns decision_id."""
    decision_dict = {
        "ticket_id": "T-DICT-1",
        "selected_action": "AUTO_RESPOND",
        "reason": "all_checks_passed"
    }

    dec_id = store.log_decision(decision_dict)
    assert dec_id is not None

    retrieved = store.retrieve_decision(dec_id)
    assert retrieved is not None
    assert retrieved["ticket_id"] == "T-DICT-1"


def test_summary_stats_computation(store):
    """get_summary_stats correctly aggregates totals and rates."""
    store.record_decision(ticket_id="T-1", routing_action="AUTO_RESPOND", routing_reason="ok")
    store.record_decision(ticket_id="T-2", routing_action="AUTO_RESPOND", routing_reason="ok")
    store.record_decision(ticket_id="T-3", routing_action="ESCALATE", routing_reason="risk")
    store.record_decision(
        ticket_id="T-4",
        routing_action="ESCALATE",
        routing_reason="guardrail_blocked",
        guardrail_result={"passed": False, "blocked_by": ["private_data"]}
    )

    stats = store.get_summary_stats()

    assert stats["total_decisions"] == 4
    assert stats["auto_responded"] == 2
    assert stats["escalated"] == 2
    assert stats["blocked_by_guardrail"] == 1
    assert stats["auto_response_rate"] == 0.5
    assert stats["escalation_rate"] == 0.5


def test_record_decision_handles_empty_optional_fields(store):
    """record_decision works safely with minimal inputs."""
    record = store.record_decision(
        ticket_id="T-MINIMAL",
        routing_action="ESCALATE",
        routing_reason="missing_data"
    )

    assert record["ticket_id"] == "T-MINIMAL"
    assert record["routing_action"] == "ESCALATE"
    assert record["retrieved_source_ids"] == []
    assert record["citations"] == []
    assert record["is_grounded"] is None
    assert record["guardrail_passed"] is None


def test_canonical_record_preserves_run_and_stage_metadata(store, sample_data):
    d = sample_data
    d["classification"].update({"urgency_confidence": 0.88, "alternative_intents": [{"intent": "account_access", "confidence": 0.04}], "model_version": "classifier-v1", "training_data_sha256": "abc123"})
    d["retrieval_results"][0]["chunk_id"] = "DOC-AUTH-001-c1"
    d["routing_decision"].update({"reason_code": "AUTO_RESPOND_CRITERIA_MET", "risk": "standard", "thresholds": {"classification_confidence": 0.8, "retrieval_routing": 0.3}})
    d["generated_response"].update({"supported": True, "provider": "offline", "prompt_version": "generation-v1"})
    d["guardrail_result"].update({"blocked": False, "reason_codes": [], "action": "PROCEED", "checks": {"grounding": {"name": "Grounding", "passed": True, "blocked": False, "reason_code": None}}})
    record = store.record_decision(
        "T-1001", "AUTO_RESPOND", "criteria met", d["normalized_ticket"], d["classification"],
        d["retrieval_results"], d["routing_decision"], d["generated_response"], d["guardrail_result"],
        run_id="RUN-1", terminal_reason_code="AUTO_RESPOND_CRITERIA_MET", response_released=True,
        total_latency_ms=12.5, stage_latencies={"retrieval": 2.5},
    )
    assert record["decision_schema_version"] == "1.0"
    assert record["run_id"] == "RUN-1"
    assert record["urgency_confidence"] == 0.88
    assert record["classification_metadata"]["alternatives"][0]["intent"] == "account_access"
    assert record["retrieved_chunk_ids"] == ["DOC-AUTH-001-c1"]
    assert record["retrieval_scores"] == [0.9]
    assert record["classification_threshold"] == 0.8
    assert record["retrieval_threshold"] == 0.3
    assert record["generation"]["provider"] == "offline"
    assert record["prompt_version"] == "generation-v1"
    assert record["terminal_reason_code"] == "AUTO_RESPOND_CRITERIA_MET"
    assert record["response_released"] is True
    assert record["total_latency_ms"] == 12.5
    assert record["stage_latencies"] == {"retrieval": 2.5}


def test_run_queries_counts_and_repeated_ticket_events(store):
    first = store.record_decision("T-RETRY", "ESCALATE", "first", run_id="RUN-A")
    second = store.record_decision("T-RETRY", "AUTO_RESPOND", "second", run_id="RUN-B")
    assert first["decision_id"] != second["decision_id"]
    assert len(store.get_decisions_for_ticket("T-RETRY")) == 2
    assert len(store.get_decisions_for_run("RUN-A")) == 1
    assert store.count_decisions(run_id="RUN-B") == 1
    assert store.terminal_action_counts() == {"AUTO_RESPOND": 1, "ESCALATE": 1}


def test_secret_bearing_content_is_not_persisted(tmp_path):
    db_path = tmp_path / "audit.sqlite"
    store = DecisionLogStore(f"sqlite:///{db_path.as_posix()}")
    secrets = ["sk-SYNTHETIC123456", "Bearer SYNTHETIC.token", "password=FakePass123"]
    record = store.record_decision(
        "T-SECRET", "ESCALATE", "provider error: api_key=DO_NOT_STORE",
        normalized_ticket={"channel": "email", "raw_content": " ".join(secrets)},
        retrieval_results=[{"doc_id": "DOC-1", "chunk_content": "Bearer PRIVATE_DOC_TOKEN", "relevance_score": 0.8}],
        generated_response={"response_text": " ".join(secrets), "supported": False},
        extra_metadata={"provider_credential": "sk-PROVIDER123456", "system_prompt": "FULL SYSTEM PROMPT TEXT"},
    )
    assert "[REDACTED]" in record["routing_reason"]
    store.engine.dispose()
    raw = b"".join(path.read_bytes() for path in tmp_path.glob("audit.sqlite*"))
    for secret in [*secrets, "Bearer PRIVATE_DOC_TOKEN", "sk-PROVIDER123456", "FULL SYSTEM PROMPT TEXT"]:
        assert secret.encode() not in raw


def test_failed_transaction_rolls_back(store, monkeypatch):
    real_factory = store.Session
    session = real_factory()
    monkeypatch.setattr(session, "commit", lambda: (_ for _ in ()).throw(RuntimeError("synthetic commit failure")))
    monkeypatch.setattr(store, "Session", lambda: session)
    with pytest.raises(RuntimeError, match="synthetic commit failure"):
        store.record_decision("T-ROLLBACK", "ESCALATE", "failure")
    monkeypatch.setattr(store, "Session", real_factory)
    assert store.count_decisions() == 0


def test_import_does_not_create_configured_database(tmp_path):
    db_path = tmp_path / "import-only.sqlite"
    code = "import os; os.environ['DATABASE_URL']=r'sqlite:///{}'; import src.logging_store".format(db_path.as_posix())
    subprocess.run([sys.executable, "-c", code], check=True, cwd=str(Path(__file__).resolve().parents[1]))
    assert not db_path.exists()

def test_review_action_is_persisted_without_draft_content(store):
    decision = store.record_decision(
        ticket_id="T-REVIEW-1",
        routing_action="ESCALATE",
        routing_reason="Human review required",
    )

    review = store.record_review_action(
        decision["decision_id"],
        "reviewer-key-fingerprint",
        "APPROVE_DRAFT",
    )

    assert review["decision_id"] == decision["decision_id"]
    assert review["action"] == "APPROVE_DRAFT"
    assert review["reviewer_identity"] == "reviewer-key-fingerprint"

    stored = store.get_review_action(
        decision["decision_id"]
    )

    assert stored == review

    assert set(stored) == {
        "review_id",
        "decision_id",
        "timestamp",
        "reviewer_identity",
        "action",
    }

    assert "review_draft" not in stored
    assert "response_text" not in stored
    assert "escalation_context" not in stored


def test_review_action_requires_existing_pipeline_decision(store):
    with pytest.raises(
        ValueError,
        match="Pipeline decision does not exist",
    ):
        store.record_review_action(
            "DECISION-NOT-FOUND",
            "reviewer-key-fingerprint",
            "REJECT_DRAFT",
        )


def test_review_action_is_immutable_per_pipeline_decision(store):
    decision = store.record_decision(
        ticket_id="T-REVIEW-2",
        routing_action="ESCALATE",
        routing_reason="Human review required",
    )

    store.record_review_action(
        decision["decision_id"],
        "reviewer-key-fingerprint",
        "REJECT_DRAFT",
    )

    with pytest.raises(
        ValueError,
        match="already recorded",
    ):
        store.record_review_action(
            decision["decision_id"],
            "reviewer-key-fingerprint",
            "APPROVE_DRAFT",
        )


@pytest.mark.parametrize(
    "action",
    [
        "",
        "APPROVE",
        "REJECT",
        "AUTO_RESPOND",
    ],
)
def test_review_action_rejects_unsupported_actions(
    store,
    action,
):
    decision = store.record_decision(
        ticket_id=f"T-REVIEW-{action or 'EMPTY'}",
        routing_action="ESCALATE",
        routing_reason="Human review required",
    )

    with pytest.raises(
        ValueError,
        match="Unsupported review action",
    ):
        store.record_review_action(
            decision["decision_id"],
            "reviewer-key-fingerprint",
            action,
        )
