"""Stage 20 development-only V1/V2 calibration and routing experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

from src.classify import build_model_bundle, load_training_tickets, predict_with_bundle, ticket_text
from src.generate import OfflineGroundedProvider, ResponseGenerationEngine
from src.retrieve import DocumentationRetrievalEngine
from src.route import HIGH_RISK_INTENTS, TicketRoutingEngine
from src.v2.calibration import (
    fit_candidate_models, grouped_development_partitions, predict_candidate,
)
from src.v2.generate import TaskOrientedGroundedProviderV2
from src.v2.retrieve import ResolutionAwareRetrievalEngineV2

CLASSIFICATION_THRESHOLDS = (0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 0.95)
RETRIEVAL_THRESHOLDS = (0.30, 0.40, 0.50)
V1_FINGERPRINT = "ddf89e82e7340a0257ee0c2ae1ce340612070545bc04f559e1e4c3ad733f59c1"
ACTION_FIXTURES = (
    ("rollback", "How do I rollback a failed release?", "rollback_request", "DOC-DEPLOY-002"),
    ("pagination", "How do I fetch the next page of API results?", "api_usage_question", "DOC-API-002"),
    ("health_check", "How do I troubleshoot a deployment health check failure?", "deployment_failure", "DOC-DEPLOY-001"),
)


def calibration_metrics(predictions: Sequence[Mapping[str, Any]],
                        tickets: Sequence[Mapping[str, Any]], bins: int = 10) -> Dict[str, Any]:
    rows = []
    ece = 0.0
    for lower_index in range(bins):
        lower, upper = lower_index / bins, (lower_index + 1) / bins
        indexes = [i for i, p in enumerate(predictions)
                   if lower <= float(p["confidence"]) <= upper
                   and (lower_index == bins - 1 or float(p["confidence"]) < upper)]
        if indexes:
            mean_confidence = sum(float(predictions[i]["confidence"]) for i in indexes) / len(indexes)
            accuracy = sum(predictions[i]["intent"] == tickets[i]["labels"]["intent"] for i in indexes) / len(indexes)
            ece += len(indexes) / len(tickets) * abs(mean_confidence - accuracy)
        else:
            mean_confidence = accuracy = None
        rows.append({"lower": lower, "upper": upper, "count": len(indexes),
                     "mean_confidence": mean_confidence, "accuracy": accuracy})
    accuracy = sum(p["intent"] == t["labels"]["intent"] for p, t in zip(predictions, tickets)) / len(tickets)
    return {"eligible_count": len(tickets), "accuracy": accuracy,
            "expected_calibration_error": ece, "reliability_buckets": rows}


def route_metrics(tickets: Sequence[Mapping[str, Any]], predictions: Sequence[Mapping[str, Any]],
                  retrieval: Sequence[Sequence[Mapping[str, Any]]], class_threshold: float,
                  retrieval_threshold: float) -> Dict[str, Any]:
    router = TicketRoutingEngine(class_threshold, retrieval_threshold)
    decisions = [router.route(
            prediction,
            evidence,
            evidence_sufficient=True,
        ) for prediction, evidence in zip(predictions, retrieval)]
    predicted_auto = [d["action"] == "AUTO_RESPOND" for d in decisions]
    expected_auto = [t["labels"]["expected_route"] == "auto_respond" for t in tickets]
    tp = sum(p and e for p, e in zip(predicted_auto, expected_auto)); fp = sum(p and not e for p, e in zip(predicted_auto, expected_auto))
    fn = sum(not p and e for p, e in zip(predicted_auto, expected_auto)); tn = len(tickets) - tp - fp - fn
    must_not = sum(p and bool(t["labels"].get("must_not_auto_respond")) for p, t in zip(predicted_auto, tickets))
    high_risk = sum(p and t["labels"]["intent"] in HIGH_RISK_INTENTS for p, t in zip(predicted_auto, tickets))
    return {"classification_threshold": class_threshold, "retrieval_threshold": retrieval_threshold,
            "eligible_count": len(tickets), "routing_accuracy": (tp + tn) / len(tickets),
            "auto_response_precision": tp / (tp + fp) if tp + fp else None,
            "auto_response_recall": tp / (tp + fn) if tp + fn else None,
            "automation_rate": (tp + fp) / len(tickets), "escalation_rate": (tn + fn) / len(tickets),
            "false_auto_responses": fp, "false_escalations": fn,
            "must_not_auto_respond_violations": must_not, "high_risk_violations": high_risk,
            # Preserve the Stage 11 safety definition: a false automatic release is
            # itself unsafe, even when it is not labelled high-risk.
            "safety_constraints_satisfied": fp == 0 and must_not == 0 and high_risk == 0}


def _predictions(bundle: Mapping[str, Any], rows: Sequence[Mapping[str, Any]], v2: bool) -> list[Dict[str, Any]]:
    function = predict_candidate if v2 else predict_with_bundle
    return [function(bundle, ticket) for ticket in rows]


def evidence_selection_fixtures(base: DocumentationRetrievalEngine) -> Dict[str, Any]:
    """Automated structural evidence only; this is not a human usefulness score."""
    v2_retriever = ResolutionAwareRetrievalEngineV2(base=base)
    v1_generator = ResponseGenerationEngine(provider=OfflineGroundedProvider())
    v2_generator = ResponseGenerationEngine(provider=TaskOrientedGroundedProviderV2())
    rows = []
    for name, query, intent, expected_doc in ACTION_FIXTURES:
        v1_evidence = base.query_authoritative_knowledge(query, top_k=5)
        v2_evidence = v2_retriever.query_authoritative_knowledge(query, top_k=5, intent=intent)
        ticket = {"ticket_id": f"development-fixture-{name}", "raw_content": query}
        classification = {"intent": intent, "urgency": "medium", "confidence": 1.0}
        v1_generation = v1_generator.generate_response(ticket, classification, v1_evidence)
        v2_generation = v2_generator.generate_response(ticket, classification, v2_evidence)
        cited = {(item["document_id"], item["chunk_id"]) for item in v2_generation.get("citations", [])}
        retrieved = {(item["document_id"], item["chunk_id"]) for item in v2_evidence}
        rows.append({"fixture": name, "expected_document_id": expected_doc,
            "v1_top_document_id": v1_evidence[0]["document_id"] if v1_evidence else None,
            "v1_top_section": v1_evidence[0]["section"] if v1_evidence else None,
            "v2_top_document_id": v2_evidence[0]["document_id"] if v2_evidence else None,
            "v2_top_section": v2_evidence[0]["section"] if v2_evidence else None,
            "v2_expected_document_retrieved": any(r["document_id"] == expected_doc for r in v2_evidence),
            "v2_exact_citations_valid": bool(cited) and cited <= retrieved,
            "v1_generation_supported": v1_generation.get("supported", False),
            "v2_generation_supported": v2_generation.get("supported", False)})
    return {"evidence_type": "automated development fixtures; not human review",
            "human_usefulness_improvement_claimed": False,
            "resolution_section_rate_v1": sum(r["v1_top_section"].lower() == "resolution" for r in rows) / len(rows),
            "resolution_section_rate_v2": sum(r["v2_top_section"].lower() == "resolution" for r in rows) / len(rows),
            "exact_citation_validity_v2": sum(r["v2_exact_citations_valid"] for r in rows) / len(rows),
            "rows": rows}


def run_stage20(dataset: Path | str) -> Dict[str, Any]:
    dataset_path = Path(dataset).resolve()
    if dataset_path.name.lower() != "development_tickets.json":
        raise ValueError("Stage 20 accepts development_tickets.json only")
    tickets = load_training_tickets(dataset_path)
    split = grouped_development_partitions(tickets)
    v1 = build_model_bundle(split.train)
    base_policy = _predictions(v1, split.policy_selection, False)
    base_eval = _predictions(v1, split.evaluation, False)
    methods: Dict[str, Any] = {}
    bundles: Dict[str, Any] = {}
    for method in ("sigmoid", "isotonic"):
        try:
            bundle = fit_candidate_models(split.train, split.calibration, method)
            policy_predictions = _predictions(bundle, split.policy_selection, True)
            methods[method] = {"status": "MEASURED", "support_count": len(split.calibration),
                               "policy_selection": calibration_metrics(policy_predictions, split.policy_selection)}
            bundles[method] = bundle
        except Exception as exc:
            methods[method] = {"status": "NOT MEASURED", "reason": type(exc).__name__}
    measured = [(name, row) for name, row in methods.items() if row["status"] == "MEASURED"]
    if not measured:
        raise RuntimeError("No calibration method could be evaluated")
    selected_method = min(measured, key=lambda item: (item[1]["policy_selection"]["expected_calibration_error"], item[0]))[0]
    v2 = bundles[selected_method]
    v2_policy = _predictions(v2, split.policy_selection, True)
    v2_eval = _predictions(v2, split.evaluation, True)

    retriever = DocumentationRetrievalEngine(min_relevance_score=-1.0)
    policy_retrieval = [retriever.query_authoritative_knowledge(ticket_text(t), top_k=5) for t in split.policy_selection]
    evaluation_retrieval = [retriever.query_authoritative_knowledge(ticket_text(t), top_k=5) for t in split.evaluation]
    if retriever.last_error:
        raise RuntimeError(f"Development retrieval unavailable: {retriever.last_error}")
    grid = [route_metrics(split.policy_selection, v2_policy, policy_retrieval, ct, rt)
            for ct in CLASSIFICATION_THRESHOLDS for rt in RETRIEVAL_THRESHOLDS]
    safe_nonzero = [row for row in grid if row["safety_constraints_satisfied"] and row["automation_rate"] > 0]
    selected = max(safe_nonzero, key=lambda row: (row["routing_accuracy"], row["auto_response_precision"] or 0,
                                                   row["automation_rate"], row["classification_threshold"],
                                                   row["retrieval_threshold"])) if safe_nonzero else None
    v1_policy_route = route_metrics(split.policy_selection, base_policy, policy_retrieval, .8, .3)
    v1_eval_route = route_metrics(split.evaluation, base_eval, evaluation_retrieval, .8, .3)
    v2_eval_route = route_metrics(split.evaluation, v2_eval, evaluation_retrieval,
                                  selected["classification_threshold"], selected["retrieval_threshold"]) if selected else None
    v1_eval_calibration = calibration_metrics(base_eval, split.evaluation)
    v2_eval_calibration = calibration_metrics(v2_eval, split.evaluation)
    fixtures = evidence_selection_fixtures(retriever)
    viable = bool(selected and v2_eval_route["automation_rate"] > 0
                  and v2_eval_route["must_not_auto_respond_violations"] == 0
                  and v2_eval_route["high_risk_violations"] == 0
                  and v2_eval_calibration["expected_calibration_error"] < v1_eval_calibration["expected_calibration_error"]
                  and v2_eval_route["routing_accuracy"] > v1_eval_route["routing_accuracy"])
    best_observed = max(grid, key=lambda row: (row["routing_accuracy"], row["auto_response_precision"] or 0))
    return {
        "stage": "Stage 20 — Development-Only V2 Remediation", "evidence_classification": "DEVELOPMENT",
        "validation_data_loaded": False, "v1_expected_fingerprint": V1_FINGERPRINT,
        "development_dataset_sha256": hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        "split": split.manifest(), "calibration_methods": methods, "selected_calibration_method": selected_method,
        "threshold_grid": grid,
        "best_observed_policy_without_strict_safety": best_observed,
        "selected_thresholds": None if not selected else {
            "classification": selected["classification_threshold"], "retrieval": selected["retrieval_threshold"],
            "selection_population": "policy_selection"},
        "v1": {"policy_calibration": calibration_metrics(base_policy, split.policy_selection),
               "evaluation_calibration": v1_eval_calibration, "policy_routing": v1_policy_route,
               "evaluation_routing": v1_eval_route},
        "v2": {"policy_calibration": calibration_metrics(v2_policy, split.policy_selection),
               "evaluation_calibration": v2_eval_calibration,
               "policy_routing": selected, "evaluation_routing": v2_eval_route},
        "candidate_decision": "V2 DEVELOPMENT CANDIDATE" if viable else "V2 REJECTED",
        "viability_checks": {"nonzero_strictly_safe_automation": bool(v2_eval_route and v2_eval_route["automation_rate"] > 0),
            "zero_false_auto_responses_on_selection": best_observed["false_auto_responses"] == 0,
            "zero_must_not_auto_violations_on_selection": best_observed["must_not_auto_respond_violations"] == 0,
            "zero_high_risk_violations_on_selection": best_observed["high_risk_violations"] == 0,
            "calibration_improved": v2_eval_calibration["expected_calibration_error"] < v1_eval_calibration["expected_calibration_error"],
            "routing_improved_only_under_unsafe_policy": best_observed["routing_accuracy"] > v1_policy_route["routing_accuracy"],
            "human_usefulness_improvement_claimed": False},
        "evidence_selection": fixtures,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="data/raw/development_tickets.json")
    parser.add_argument("--output", default="evaluation/results/stage20-v2-development.json")
    args = parser.parse_args(); result = run_stage20(args.dataset)
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"candidate_decision": result["candidate_decision"],
                      "selected_thresholds": result["selected_thresholds"]}, indent=2))


if __name__ == "__main__":
    main()
