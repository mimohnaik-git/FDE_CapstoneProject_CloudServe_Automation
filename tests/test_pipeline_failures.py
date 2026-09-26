from dataclasses import replace
import json

import pytest

from src import generate as gen
from src.audit import AuditError, AuditStore
from src.pipeline import Pipeline
from src.schemas import Route


def test_end_to_end_logs_and_escalates(pipeline, email_ticket):
    d = pipeline.process(email_ticket, run_id="r1")
    assert d.route is Route.ESCALATE
    assert d.intent and d.urgency and d.passages and d.draft
    assert pipeline.audit.count("r1") == 1
    assert pipeline.audit.latest("T-1")["route"] == "ESCALATE"


@pytest.mark.parametrize("ch", ["email", "chat", "docs_comment", "forum"])
def test_all_four_channels(pipeline, ch):
    d = pipeline.process({"ticket_id": f"C-{ch}", "channel": ch, "body": "export data csv"})
    assert d.intent is not None and d.channel == ch


def test_malformed_ticket_is_logged_escalation(pipeline):
    d = pipeline.process({"ticket_id": "BAD", "channel": "fax", "body": "x"})
    assert d.route is Route.ESCALATE and d.reasons == ["malformed_input"]
    assert pipeline.audit.latest("BAD") is not None


def test_non_dict_ticket(pipeline):
    d = pipeline.process("garbage")
    assert d.route is Route.ESCALATE and d.ticket_id == "UNKNOWN"


def test_no_retrieval_result(pipeline):
    d = pipeline.process({"ticket_id": "NR", "channel": "email",
                          "body": "zzqx qwvv plorft"})
    assert d.route is Route.ESCALATE
    assert "no_retrieval_above_threshold" in d.reasons


def test_retriever_outage(pipeline, email_ticket, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("index offline")
    monkeypatch.setattr(pipeline.retriever, "search", boom)
    d = pipeline.process(email_ticket)
    assert d.route is Route.ESCALATE and d.reasons == ["retrieval_failure"]


class _Provider:
    def __init__(self, exc=None, out=None):
        self.exc, self.out = exc, out

    def complete(self, prompt, timeout_s):
        if self.exc:
            raise self.exc
        return self.out


@pytest.mark.parametrize("exc", [gen.ProviderTimeout("t"), gen.ProviderOutage("o"),
                                 gen.ProviderRateLimited("r"), ValueError("bug")])
def test_provider_failures_fall_back_to_grounded_draft(classifier, retriever, settings,
                                                       email_ticket, exc):
    p = Pipeline(classifier, retriever, AuditStore(":memory:"), settings, _Provider(exc))
    d = p.process(email_ticket)
    assert d.route is Route.ESCALATE
    assert d.draft.status.value == "EVIDENCE_ASSEMBLY_COMPLETE"
    assert any(r.startswith("provider_fallback") for r in d.reasons)


@pytest.mark.parametrize("out", ["", "An answer with no citations at all."])
def test_malformed_generation_falls_back(classifier, retriever, settings, email_ticket, out):
    p = Pipeline(classifier, retriever, AuditStore(":memory:"), settings, _Provider(out=out))
    d = p.process(email_ticket)
    assert "provider_fallback:MalformedGeneration" in d.reasons


def test_audit_failure_records_consistent_escalation(tmp_path, retriever, settings, auto_ticket):
    class Broken(AuditStore):
        def log_decision(self, *a, **k):
            raise AuditError("disk full")
    s = replace(settings, customer_release_authorized=True)
    from tests.conftest import AutoClassifier
    p = Pipeline(AutoClassifier(), retriever, Broken(str(tmp_path / "audit.sqlite3")), s)
    d = p.process(auto_ticket)
    assert d.route is Route.ESCALATE and "audit_store_failure" in d.reasons
    fallback = json.loads((tmp_path / "audit.sqlite3.fallback.jsonl").read_text())
    assert fallback["route"] == "ESCALATE"
    assert "audit_store_failure" in fallback["reasons"]


def test_classifier_failure_has_safe_explicit_state(pipeline, email_ticket, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("classifier offline")
    monkeypatch.setattr(pipeline.classifier, "classify_with_answerability", boom)
    d = pipeline.process(email_ticket)
    assert d.route is Route.ESCALATE
    assert d.intent.label == "UNCLASSIFIED" and d.intent.confidence == 0.0
    assert d.intent.alternatives == [] and "classification_failure" in d.reasons


def test_emergency_disable_is_one_way_for_future_tickets(auto_pipeline, auto_ticket):
    assert auto_pipeline.process(auto_ticket).route is Route.AUTO_RESPOND
    auto_pipeline.emergency_disable_auto_response()
    later = dict(auto_ticket, ticket_id="AUTO-2")
    d = auto_pipeline.process(later)
    assert d.route is Route.ESCALATE
    assert "emergency_auto_response_disabled" in d.reasons


def test_pipeline_never_sees_labels(pipeline):
    from evaluation.harness import strip_labels
    t = strip_labels({"ticket_id": "L", "channel": "email", "body": "x", "intent": "a",
                      "answerable": True, "expected_doc_ids": ["KB-1"]})
    assert set(t) == {"ticket_id", "channel", "body"}
