import pytest
from src.route import (
    HIGH_RISK_INTENTS,
    UNANSWERABLE_INTENTS,
    TicketRoutingEngine,
    ROUTE_AUTO_RESPOND,
    ROUTE_ESCALATE,
    REASON_LOW_CONFIDENCE,
    REASON_HIGH_RISK_INTENT,
    REASON_NO_RETRIEVAL,
    REASON_GUARDRAIL_BLOCKED,
    REASON_MISSING_CONFIDENCE,
    REASON_AUTO_RESPOND,
    REASON_INVALID_CLASSIFICATION,
    REASON_PIPELINE_FAILURE,
    REASON_UNANSWERABLE_INTENT,
    REASON_VALIDATION_FAILED,
    REASON_WEAK_RETRIEVAL,
)

DEFAULT_THRESHOLD = 0.80

@pytest.fixture
def router():
    return TicketRoutingEngine(confidence_threshold=DEFAULT_THRESHOLD)

# ---------------------------------------------------------------------------
# Happy path — AUTO_RESPOND
# ---------------------------------------------------------------------------

def test_auto_respond_when_all_criteria_met(router):
    """Technical issue above threshold with retrieval results → AUTO_RESPOND."""
    classification = {
        "intent": "authentication_failure",
        "urgency": "medium",
        "confidence": 0.92,
    }
    retrieval = [{"doc_id": "DOC-001", "chunk_content": "...", "relevance_score": 0.8, "rank": 1}]

    decision = router.route(classification, retrieval_results=retrieval)

    assert decision["action"] == ROUTE_AUTO_RESPOND
    assert decision["escalate"] is False
    assert decision["reason_code"] == REASON_AUTO_RESPOND
    assert decision["confidence"] == 0.92
    assert decision["threshold"] == DEFAULT_THRESHOLD


def test_feature_request_is_explicitly_unanswerable(router):
    """Feature requests have no authoritative documentation and must escalate."""
    classification = {"intent": "feature_request", "urgency": "low", "confidence": 0.90}
    retrieval = [{"doc_id": "DOC-002", "chunk_content": "...", "relevance_score": 0.7, "rank": 1}]

    decision = router.route(classification, retrieval_results=retrieval)

    assert decision["action"] == ROUTE_ESCALATE
    assert decision["reason_code"] == REASON_UNANSWERABLE_INTENT


# ---------------------------------------------------------------------------
# Escalation — confidence
# ---------------------------------------------------------------------------

def test_escalate_when_confidence_below_threshold(router):
    """Confidence below 0.80 → ESCALATE with correct reason."""
    classification = {"intent": "authentication_failure", "urgency": "low", "confidence": 0.65}
    retrieval = [{"doc_id": "DOC-001", "chunk_content": "...", "relevance_score": 0.8, "rank": 1}]

    decision = router.route(classification, retrieval_results=retrieval)

    assert decision["action"] == ROUTE_ESCALATE
    assert decision["escalate"] is True
    assert decision["reason_code"] == REASON_LOW_CONFIDENCE


def test_escalate_when_confidence_exactly_at_threshold(router):
    """Confidence exactly at threshold — boundary condition should AUTO_RESPOND (>= passes)."""
    classification = {"intent": "authentication_failure", "urgency": "low", "confidence": 0.80}
    retrieval = [{"doc_id": "DOC-001", "chunk_content": "...", "relevance_score": 0.8, "rank": 1}]

    decision = router.route(classification, retrieval_results=retrieval)

    # Exactly at threshold: passes (>= logic)
    assert decision["action"] == ROUTE_AUTO_RESPOND


def test_escalate_when_confidence_missing(router):
    """No confidence key in classification → ESCALATE with missing confidence reason."""
    classification = {"intent": "authentication_failure", "urgency": "medium"}

    decision = router.route(classification, retrieval_results=[{"doc_id": "D1"}])

    assert decision["action"] == ROUTE_ESCALATE
    assert decision["reason_code"] == REASON_MISSING_CONFIDENCE


def test_escalate_when_confidence_malformed(router):
    """Non-numeric confidence value → ESCALATE."""
    classification = {"intent": "authentication_failure", "urgency": "medium", "confidence": "high"}

    decision = router.route(classification, retrieval_results=[{"doc_id": "D1"}])

    assert decision["action"] == ROUTE_ESCALATE
    assert decision["reason_code"] == REASON_MISSING_CONFIDENCE


# ---------------------------------------------------------------------------
# Escalation — high-risk intent
# ---------------------------------------------------------------------------

def test_escalate_security_incident_regardless_of_confidence(router):
    """Security incidents must always escalate, even with strong evidence."""
    classification = {"intent": "security_incident", "urgency": "high", "confidence": 0.99}
    retrieval = [{"doc_id": "DOC-003", "chunk_content": "...", "relevance_score": 0.9, "rank": 1}]

    decision = router.route(classification, retrieval_results=retrieval)

    assert decision["action"] == ROUTE_ESCALATE
    assert decision["reason_code"] == REASON_HIGH_RISK_INTENT


def test_account_access_is_not_blanket_high_risk(router):
    """Dataset policy allows supported account-access questions to auto-respond."""
    classification = {"intent": "account_access", "urgency": "high", "confidence": 0.98}
    retrieval = [{"doc_id": "DOC-004", "chunk_content": "...", "relevance_score": 0.85, "rank": 1}]

    decision = router.route(classification, retrieval_results=retrieval)

    assert decision["action"] == ROUTE_AUTO_RESPOND
    assert decision["reason_code"] == REASON_AUTO_RESPOND


# ---------------------------------------------------------------------------
# Escalation — no retrieval
# ---------------------------------------------------------------------------

def test_escalate_when_no_retrieval_results(router):
    """No documentation retrieved → cannot ground a response → ESCALATE."""
    classification = {"intent": "authentication_failure", "urgency": "medium", "confidence": 0.90}

    decision = router.route(classification, retrieval_results=[])

    assert decision["action"] == ROUTE_ESCALATE
    assert decision["reason_code"] == REASON_NO_RETRIEVAL


def test_escalate_when_retrieval_results_is_none(router):
    """None retrieval_results treated same as empty list."""
    classification = {"intent": "authentication_failure", "urgency": "medium", "confidence": 0.90}

    decision = router.route(classification, retrieval_results=None)

    assert decision["action"] == ROUTE_ESCALATE
    assert decision["reason_code"] == REASON_NO_RETRIEVAL


# ---------------------------------------------------------------------------
# Escalation — guardrail
# ---------------------------------------------------------------------------

def test_escalate_when_guardrail_blocked(router):
    """Guardrail block overrides all other conditions — must ESCALATE."""
    classification = {"intent": "authentication_failure", "urgency": "low", "confidence": 0.95}
    retrieval = [{"doc_id": "DOC-001", "chunk_content": "...", "relevance_score": 0.9, "rank": 1}]

    decision = router.route(classification, retrieval_results=retrieval, guardrail_passed=False)

    assert decision["action"] == ROUTE_ESCALATE
    assert decision["reason_code"] == REASON_GUARDRAIL_BLOCKED


# ---------------------------------------------------------------------------
# Decision record schema
# ---------------------------------------------------------------------------

def test_routing_decision_contains_required_keys(router):
    """Every decision record must contain the full audit schema."""
    classification = {"intent": "authentication_failure", "urgency": "medium", "confidence": 0.90}
    retrieval = [{"doc_id": "DOC-001", "chunk_content": "...", "relevance_score": 0.8, "rank": 1}]

    decision = router.route(classification, retrieval_results=retrieval)

    required_keys = {
        "action", "reason_code", "reason", "classification_confidence",
        "retrieval_score", "retrieval_count", "risk", "answerable",
        "thresholds", "confidence", "threshold", "intent", "urgency", "escalate",
    }
    assert required_keys.issubset(decision.keys()), f"Missing keys: {required_keys - decision.keys()}"


# ---------------------------------------------------------------------------
# Configurable threshold
# ---------------------------------------------------------------------------

def test_custom_threshold_is_respected():
    """A router with a different threshold applies it correctly."""
    strict_router = TicketRoutingEngine(confidence_threshold=0.95)
    classification = {"intent": "authentication_failure", "urgency": "low", "confidence": 0.90}
    retrieval = [{"doc_id": "DOC-001", "chunk_content": "...", "relevance_score": 0.8, "rank": 1}]

    # 0.90 passes 0.80 threshold but fails 0.95 threshold
    decision = strict_router.route(classification, retrieval_results=retrieval)

    assert decision["action"] == ROUTE_ESCALATE
    assert decision["reason_code"] == REASON_LOW_CONFIDENCE
    assert decision["threshold"] == 0.95


def test_invalid_threshold_raises_on_init():
    """Threshold outside [0, 1] must raise at construction time."""
    with pytest.raises(ValueError):
        TicketRoutingEngine(confidence_threshold=1.5)

    with pytest.raises(ValueError):
        TicketRoutingEngine(confidence_threshold=-0.1)

    with pytest.raises(ValueError):
        TicketRoutingEngine(retrieval_threshold=float("nan"))


def _strong_retrieval(score=0.80):
    return [{
        "doc_id": "DOC-AUTH-001",
        "chunk_content": "Authoritative support passage.",
        "relevance_score": score,
        "rank": 1,
    }]


def _valid_classification(**overrides):
    value = {"intent": "authentication_failure", "urgency": "medium", "confidence": 0.90}
    value.update(overrides)
    return value


def test_same_signals_produce_identical_decision(router):
    first = router.route(_valid_classification(), _strong_retrieval())
    second = router.route(_valid_classification(), _strong_retrieval())
    assert first == second


@pytest.mark.parametrize("intent", ["security_incident", "compliance_request"])
def test_authoritative_high_risk_intents_escalate(router, intent):
    decision = router.route(_valid_classification(intent=intent), _strong_retrieval())
    assert decision["action"] == ROUTE_ESCALATE
    assert decision["reason_code"] == REASON_HIGH_RISK_INTENT
    assert decision["risk"] == "high"


@pytest.mark.parametrize("confidence", [-0.01, 1.01, float("nan"), float("inf"), True])
def test_out_of_bounds_or_nonfinite_confidence_is_invalid(router, confidence):
    decision = router.route(_valid_classification(confidence=confidence), _strong_retrieval())
    assert decision["action"] == ROUTE_ESCALATE
    assert decision["reason_code"] == REASON_INVALID_CLASSIFICATION


@pytest.mark.parametrize(
    "retrieval",
    [
        _strong_retrieval(0.29),
        [{"doc_id": "DOC-AUTH-001", "rank": 1}],
        [{"relevance_score": 0.90, "rank": 1}],
        "not-a-result-list",
    ],
)
def test_weak_or_malformed_retrieval_escalates(router, retrieval):
    decision = router.route(_valid_classification(), retrieval)
    assert decision["action"] == ROUTE_ESCALATE
    assert decision["reason_code"] == REASON_WEAK_RETRIEVAL
    assert decision["answerable"] is False


def test_retrieval_routing_threshold_is_independently_configurable():
    router = TicketRoutingEngine(confidence_threshold=0.50, retrieval_threshold=0.75)
    decision = router.route(_valid_classification(confidence=0.80), _strong_retrieval(0.70))
    assert decision["reason_code"] == REASON_WEAK_RETRIEVAL
    assert decision["thresholds"]["classification_confidence"] == 0.50
    assert decision["thresholds"]["retrieval_routing"] == 0.75


@pytest.mark.parametrize(
    "classification",
    [
        None,
        {},
        {"intent": "billing_dispute", "urgency": "high", "confidence": 0.99},
        {"intent": "authentication_failure", "urgency": "critical", "confidence": 0.99},
    ],
)
def test_invalid_or_legacy_classification_escalates(router, classification):
    decision = router.route(classification, _strong_retrieval())
    assert decision["action"] == ROUTE_ESCALATE
    assert decision["reason_code"] == REASON_INVALID_CLASSIFICATION


def test_legacy_nonexistent_intents_are_not_risk_policy_entries():
    assert "billing_dispute" not in HIGH_RISK_INTENTS
    assert "account_access" not in HIGH_RISK_INTENTS
    assert UNANSWERABLE_INTENTS == {"feature_request", "unclear_request"}


def test_available_guardrail_validation_and_failure_states_fail_closed(router):
    classification = _valid_classification()
    retrieval = _strong_retrieval()
    assert router.route(classification, retrieval, guardrail_passed=False)["reason_code"] == REASON_GUARDRAIL_BLOCKED
    assert router.route(classification, retrieval, validation_passed=False)["reason_code"] == REASON_VALIDATION_FAILED
    assert router.route(classification, retrieval, validation_passed="unknown")["reason_code"] == REASON_VALIDATION_FAILED
    assert router.route(classification, retrieval, failure_state="retriever_timeout")["reason_code"] == REASON_PIPELINE_FAILURE


def test_target_labels_do_not_affect_inference_route(router):
    classification = _valid_classification()
    retrieval = _strong_retrieval()
    baseline = router.route(classification, retrieval)
    classification_with_targets = {
        **classification,
        "expected_route": "escalate",
        "must_not_auto_respond": True,
        "expected_doc_ids": ["WRONG"],
    }
    retrieval_with_targets = [
        {**retrieval[0], "labels": {"expected_route": "escalate"}}
    ]
    assert router.route(classification_with_targets, retrieval_with_targets) == baseline


def test_router_is_direct_python_and_requires_no_llm_client(router):
    assert not hasattr(router, "client")
    assert router.route(_valid_classification(), _strong_retrieval())["action"] == ROUTE_AUTO_RESPOND


def test_route_batch_contains_one_route_failure():
    class FailingOnceRouter(TicketRoutingEngine):
        def __init__(self):
            super().__init__(confidence_threshold=0.80, retrieval_threshold=0.30)
            self.calls = 0

        def route(self, *args, **kwargs):
            self.calls += 1
            if self.calls == 2:
                raise RuntimeError("isolated route failure")
            return super().route(*args, **kwargs)

    requests = [
        {"classification": _valid_classification(), "retrieval_results": _strong_retrieval()}
        for _ in range(3)
    ]
    decisions = FailingOnceRouter().route_batch(requests)
    assert [decision["reason_code"] for decision in decisions] == [
        REASON_AUTO_RESPOND,
        REASON_PIPELINE_FAILURE,
        REASON_AUTO_RESPOND,
    ]

def test_routing_metadata_reports_selected_stage11_baseline(router):
    decision = router.route(_valid_classification(), _strong_retrieval())
    assert decision["thresholds"]["status"] == "SELECTED_STAGE_11_BASELINE"
