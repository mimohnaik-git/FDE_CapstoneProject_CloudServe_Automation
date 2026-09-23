import json

import pytest

from evaluation.calibration import (
    development_three_way_split,
    evaluate_policy,
    build_markdown,
    run_stage11,
    select_candidate_policies,
)
from src.classify import load_training_tickets, text_group


def _prediction(intent="account_access", confidence=0.9):
    return {"intent": intent, "urgency": "medium", "confidence": confidence}


def _retrieval(score=0.9):
    return [{"document_id": "DOC-1", "relevance_score": score}]


def _ticket(expected="auto_respond", intent="account_access", must_not=False):
    return {"labels": {"intent": intent, "expected_route": expected, "must_not_auto_respond": must_not}}


def test_calibration_split_has_no_grouped_text_leakage():
    train, calibration, evaluation, metadata = development_three_way_split(load_training_tickets())
    groups = [{text_group(ticket) for ticket in population} for population in (train, calibration, evaluation)]
    assert not groups[0] & groups[1]
    assert not groups[0] & groups[2]
    assert not groups[1] & groups[2]
    assert set(metadata["group_overlap"].values()) == {0}


def test_true_high_risk_and_must_not_cases_cannot_qualify_as_safe_policy():
    predictions = [_prediction("account_access"), _prediction("account_access")]
    tickets = [_ticket("escalate", "security_incident", True), _ticket()]
    result = evaluate_policy(predictions, [_retrieval(), _retrieval()], tickets, 0.5, 0.3)
    assert result["must_not_auto_respond_violations"] == 1
    assert result["high_risk_violations"] == 1
    assert result["safety_constraints_satisfied"] is False


def test_predicted_high_risk_is_always_escalated():
    result = evaluate_policy([_prediction("security_incident")], [_retrieval()],
                             [_ticket("escalate", "security_incident", True)], 0.3, 0.3)
    assert result["automation_rate"] == 0.0
    assert result["high_risk_violations"] == 0


def test_threshold_configuration_is_deterministic():
    args = ([_prediction()], [_retrieval()], [_ticket()], 0.5, 0.4)
    assert evaluate_policy(*args) == evaluate_policy(*args)


def test_selected_thresholds_reproduce_measured_policy_behavior():
    rows = []
    for confidence in (0.5, 0.6):
        rows.append({"classification_threshold": confidence, "retrieval_threshold": 0.4,
                     "ticket_count": 10, "routing_accuracy": 0.9, "auto_response_precision": 1.0,
                     "auto_response_recall": 0.8, "automation_rate": 0.5, "escalation_rate": 0.5,
                     "auto_response_count": 5, "expected_auto_response_count": 6,
                     "false_auto_responses": 0, "false_escalations": 1,
                     "must_not_auto_respond_violations": 0, "high_risk_violations": 0,
                     "safety_constraints_satisfied": True})
    selected = select_candidate_policies(rows)["safest_viable"]
    measured = evaluate_policy([_prediction( confidence=0.9)] * 5, [_retrieval()] * 5, [_ticket()] * 5,
                               selected["classification_threshold"], selected["retrieval_threshold"])
    reproduced = evaluate_policy([_prediction(confidence=0.9)] * 5, [_retrieval()] * 5, [_ticket()] * 5,
                                 selected["classification_threshold"], selected["retrieval_threshold"])
    assert measured == reproduced


def test_retained_defaults_reproduce_recorded_policy_behavior():
    predictions = [_prediction(confidence=0.7), _prediction(confidence=0.9)]
    retrievals = [_retrieval(), _retrieval()]
    tickets = [_ticket(), _ticket()]
    recorded = evaluate_policy(predictions, retrievals, tickets, 0.80, 0.30)
    reproduced = evaluate_policy(predictions, retrievals, tickets, 0.80, 0.30)
    assert recorded == reproduced


def test_stage11_rejects_validation_path_before_loading(monkeypatch, tmp_path):
    called = False
    def forbidden(_path):
        nonlocal called
        called = True
        raise AssertionError("must not load")
    monkeypatch.setattr("evaluation.calibration.load_training_tickets", forbidden)
    with pytest.raises(ValueError, match="development dataset"):
        run_stage11(tmp_path / "validation_tickets.json")
    assert called is False



def test_stage11_reports_current_calibration_and_policy_scope(monkeypatch):
    # Reporting-contract coverage must not depend on the semantic embedding
    # runtime, model cache, network state, or vector-store availability.
    def deterministic_retrieval(tickets):
        return [
            [
                {
                    "document_id": "TEST-DOC",
                    "doc_id": "TEST-DOC",
                    "relevance_score": 0.0,
                }
            ]
            for _ in tickets
        ]

    monkeypatch.setattr(
        "evaluation.calibration._retrieve_raw_scores",
        deterministic_retrieval,
    )

    result = run_stage11()

    assert result["validation_or_final_data_loaded"] is False

    model = result["model"]

    assert model["intent_calibration_method"] == "sigmoid"
    assert model["intent_calibration_folds"] == 3
    assert model["urgency_calibration_method"] == "none"
    assert model["feature_fields"] == ["subject", "body"]

    simulation = result["policy_simulation"]

    assert simulation["scope"] == "counterfactual_threshold_analysis"
    assert simulation["evidence_sufficient_assumption"] is True
    assert simulation["production_automation_claim"] is False

    assert (
        result["selected_thresholds"]["new_thresholds"]
        is None
    )

    assert (
        result["selected_thresholds"]["production_config_changed"]
        is False
    )

    markdown = build_markdown(result)

    assert "counterfactual policy simulations" in markdown
    assert "Production remains fail-closed" in markdown
    assert "Probabilities were measured, not transformed" not in markdown
    assert "Urgency remains weak but is not a routing input" not in markdown
