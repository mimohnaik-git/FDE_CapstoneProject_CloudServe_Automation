import json
from pathlib import Path

import pytest

from src.classify import (
    CANONICAL_INTENTS,
    CANONICAL_URGENCIES,
    FEATURE_FIELDS,
    MODEL_VERSION,
    CALIBRATION_METHOD,
    CALIBRATION_FOLDS,
    TicketClassificationEngine,
    grouped_calibration_splits,
    load_training_tickets,
    stratified_group_holdout,
    text_group,
)


@pytest.fixture(scope="module")
def classifier():
    return TicketClassificationEngine()


@pytest.fixture(scope="module")
def development_tickets():
    return load_training_tickets()


def normalized_ticket(body, subject=""):
    return {
        "ticket_id": "TEST-CLASSIFY",
        "channel": "email",
        "customer_tier": "standard",
        "raw_content": body,
        "metadata": {"original_subject": subject},
    }


def test_exact_canonical_taxonomy_has_all_22_authoritative_intents():
    assert len(CANONICAL_INTENTS) == 22
    assert set(CANONICAL_INTENTS) == {
        "account_access", "api_key_issue", "api_usage_question", "authentication_failure",
        "billing_query", "compliance_request", "configuration_help", "data_export",
        "data_residency", "database_issue", "deployment_failure", "feature_request",
        "integration_help", "onboarding", "performance_degradation", "quota_or_overage",
        "rate_limit", "rollback_request", "security_incident", "sso_configuration",
        "unclear_request", "webhook_issue",
    }
    assert set(CANONICAL_URGENCIES) == {"low", "medium", "high"}


def test_fitted_model_supports_every_canonical_intent(classifier):
    bundle = classifier._get_bundle()
    classes = set(bundle["intent_model"].classes_)
    assert classes == set(CANONICAL_INTENTS)


def test_lazy_model_bundle_is_reused_processwide(classifier):
    second_classifier = TicketClassificationEngine()
    assert classifier._get_bundle() is second_classifier._get_bundle()


@pytest.mark.parametrize(
    "body",
    [
        "Our deployment fails while resolving dependencies.",
        "How do I configure an SSO identity provider?",
        "Webhook delivery retries are not arriving.",
        "Please add dark mode to the dashboard.",
    ],
)
def test_output_always_uses_canonical_labels_and_probability_confidence(classifier, body):
    result = classifier.process_classification(normalized_ticket(body))
    assert result["intent"] in CANONICAL_INTENTS
    assert result["urgency"] in CANONICAL_URGENCIES
    assert isinstance(result["confidence"], float)
    assert 0.0 <= result["confidence"] <= 1.0
    assert isinstance(result["urgency_confidence"], float)
    assert 0.0 <= result["urgency_confidence"] <= 1.0
    assert result["model_version"] == MODEL_VERSION


def test_same_model_and_input_are_deterministic(classifier):
    ticket = normalized_ticket("The API returns 429 responses during traffic spikes.")
    assert classifier.process_classification(ticket) == classifier.process_classification(ticket)


@pytest.mark.parametrize("malformed", [None, "not a mapping", [], 17])
def test_malformed_input_fails_safely(classifier, malformed):
    result = classifier.process_classification(malformed)
    assert result["intent"] == "unclear_request"
    assert result["urgency"] == "medium"
    assert result["confidence"] == 0.0


def test_empty_text_fails_safely_without_fabricated_confidence(classifier):
    result = classifier.process_classification(normalized_ticket("", ""))
    assert result["intent"] == "unclear_request"
    assert result["confidence"] == 0.0
    assert result["alternative_intents"] == []


def test_minimal_ambiguous_text_has_valid_non_certain_result(classifier):
    result = classifier.process_classification(normalized_ticket("help"))
    assert result["intent"] in CANONICAL_INTENTS
    assert 0.0 <= result["confidence"] < 1.0
    assert len(result["alternative_intents"]) == 3
    assert all(0.0 <= item["confidence"] <= 1.0 for item in result["alternative_intents"])


def test_classifier_uses_only_subject_and_body_not_targets_or_history(classifier):
    assert FEATURE_FIELDS == ("subject", "body")
    base = normalized_ticket("We need to export our account data.", "Data export")
    poisoned = dict(base)
    poisoned["labels"] = {"intent": "security_incident", "urgency": "high"}
    poisoned["history"] = {"csat_rating": 1, "escalated": True}
    poisoned["expected_doc_ids"] = ["LEAKED-TARGET"]
    assert classifier.process_classification(base) == classifier.process_classification(poisoned)


def test_development_dataset_taxonomy_is_complete_and_valid(development_tickets):
    assert len(development_tickets) == 500
    assert {ticket["labels"]["intent"] for ticket in development_tickets} == set(CANONICAL_INTENTS)
    assert {ticket["labels"]["urgency"] for ticket in development_tickets} == set(CANONICAL_URGENCIES)


def test_grouped_holdout_is_reproducible_stratified_and_duplicate_safe(development_tickets):
    train_a, holdout_a = stratified_group_holdout(development_tickets)
    train_b, holdout_b = stratified_group_holdout(development_tickets)
    assert [ticket["ticket_id"] for ticket in train_a] == [ticket["ticket_id"] for ticket in train_b]
    assert [ticket["ticket_id"] for ticket in holdout_a] == [ticket["ticket_id"] for ticket in holdout_b]
    assert not ({text_group(ticket) for ticket in train_a} & {text_group(ticket) for ticket in holdout_a})
    assert {ticket["labels"]["intent"] for ticket in train_a} == set(CANONICAL_INTENTS)
    assert {ticket["labels"]["intent"] for ticket in holdout_a} == set(CANONICAL_INTENTS)


def test_training_loader_rejects_noncanonical_target(tmp_path):
    bad_path = tmp_path / "bad.json"
    bad_path.write_text(json.dumps([{
        "subject": "x", "body": "y",
        "labels": {"intent": "technical_issue", "urgency": "medium"},
    }]), encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported intent"):
        load_training_tickets(bad_path)



def test_group_safe_calibration_splits_are_deterministic(
    development_tickets,
):
    labels = [
        ticket["labels"]["intent"]
        for ticket in development_tickets
    ]

    first = grouped_calibration_splits(
        development_tickets,
        labels,
    )

    second = grouped_calibration_splits(
        development_tickets,
        labels,
    )

    assert len(first) == CALIBRATION_FOLDS
    assert len(second) == CALIBRATION_FOLDS

    first_normalized = [
        (
            train.tolist(),
            calibration.tolist(),
        )
        for train, calibration in first
    ]

    second_normalized = [
        (
            train.tolist(),
            calibration.tolist(),
        )
        for train, calibration in second
    ]

    assert first_normalized == second_normalized


def test_group_safe_calibration_splits_do_not_leak_duplicate_text(
    development_tickets,
):
    labels = [
        ticket["labels"]["intent"]
        for ticket in development_tickets
    ]

    groups = [
        text_group(ticket)
        for ticket in development_tickets
    ]

    for train, calibration in grouped_calibration_splits(
        development_tickets,
        labels,
    ):
        train_groups = {
            groups[int(index)]
            for index in train
        }

        calibration_groups = {
            groups[int(index)]
            for index in calibration
        }

        assert not (
            train_groups
            & calibration_groups
        )


def test_model_bundle_reports_calibration_metadata(
    classifier,
):
    bundle = classifier._get_bundle()

    assert (
        bundle["intent_calibration_method"]
        == CALIBRATION_METHOD
    )

    assert (
        bundle["intent_calibration_folds"]
        == CALIBRATION_FOLDS
    )

    assert (
        bundle["urgency_calibration_method"]
        == "none"
    )

    assert bundle["training_data_sha256"]
    assert bundle["model_fingerprint"]

    assert len(
        bundle["model_fingerprint"]
    ) == 64

def test_prediction_reports_calibration_provenance(
    classifier,
):
    result = classifier.process_classification(
        normalized_ticket(
            "How do I configure SSO for our organization?"
        )
    )

    assert result["intent"] in CANONICAL_INTENTS
    assert result["urgency"] in CANONICAL_URGENCIES

    assert (
        result["intent_calibration_method"]
        == CALIBRATION_METHOD
    )

    assert (
        result["intent_calibration_folds"]
        == CALIBRATION_FOLDS
    )

    assert (
        result["urgency_calibration_method"]
        == "none"
    )

    assert result["model_version"] == MODEL_VERSION
    assert result["training_data_sha256"]
    assert result["model_fingerprint"]

    assert 0.0 <= result["confidence"] <= 1.0
    assert 0.0 <= result["urgency_confidence"] <= 1.0
