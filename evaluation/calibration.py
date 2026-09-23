"""Development-only grouped calibration and routing-threshold selection.

This module fits the unchanged classifier on three development folds, selects
policies on one calibration fold, and confirms them on a disjoint evaluation
fold. Duplicate normalized texts never cross populations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from sklearn.model_selection import StratifiedGroupKFold

from src.classify import (
    CANONICAL_INTENTS,
    DEFAULT_TRAINING_DATA_PATH,
    RANDOM_SEED,
    build_model_bundle,
    load_training_tickets,
    predict_with_bundle,
    text_group,
    ticket_text,
    training_data_sha256,
)
from src.retrieve import DocumentationRetrievalEngine
from src.route import HIGH_RISK_INTENTS, ROUTE_AUTO_RESPOND, TicketRoutingEngine

CLASSIFICATION_GRID = (0.30, 0.40, 0.50, 0.60, 0.70, 0.80)
RETRIEVAL_GRID = (0.30, 0.40, 0.50, 0.60)
MIN_POLICY_AUTOMATIONS = 5
SCHEMA_VERSION = "1.0"


def development_three_way_split(
    tickets: Sequence[Mapping[str, Any]], random_seed: int = RANDOM_SEED
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """Return 3/1/1 grouped folds: train/calibration/evaluation."""
    texts = [ticket_text(ticket) for ticket in tickets]
    intents = [ticket["labels"]["intent"] for ticket in tickets]
    groups = [text_group(ticket) for ticket in tickets]
    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=random_seed)
    folds = [list(test_indices) for _, test_indices in splitter.split(texts, intents, groups)]
    calibration_indices, evaluation_indices = folds[0], folds[1]
    train_indices = [index for fold in folds[2:] for index in fold]
    populations = [
        [dict(tickets[index]) for index in indices]
        for indices in (train_indices, calibration_indices, evaluation_indices)
    ]
    group_sets = [{text_group(ticket) for ticket in population} for population in populations]
    overlaps = {
        "train_calibration": len(group_sets[0] & group_sets[1]),
        "train_evaluation": len(group_sets[0] & group_sets[2]),
        "calibration_evaluation": len(group_sets[1] & group_sets[2]),
    }
    if any(overlaps.values()):
        raise RuntimeError("Duplicate text groups leaked across Stage 11 populations")
    population_ids = [[ticket.get("ticket_id") for ticket in population] for population in populations]
    split_hash = hashlib.sha256(json.dumps(population_ids, sort_keys=True).encode("utf-8")).hexdigest()
    metadata = {
        "method": "shuffled StratifiedGroupKFold(n_splits=5): folds 2-4 train, fold 0 calibration, fold 1 evaluation",
        "random_seed": random_seed,
        "group_key": "normalized lowercase subject+body with collapsed whitespace",
        "train_count": len(populations[0]),
        "calibration_count": len(populations[1]),
        "evaluation_count": len(populations[2]),
        "train_group_count": len(group_sets[0]),
        "calibration_group_count": len(group_sets[1]),
        "evaluation_group_count": len(group_sets[2]),
        "group_overlap": overlaps,
        "split_assignment_sha256": split_hash,
        "all_intents_present": {
            name: set(ticket["labels"]["intent"] for ticket in population) == set(CANONICAL_INTENTS)
            for name, population in zip(("train", "calibration", "evaluation"), populations)
        },
    }
    return populations[0], populations[1], populations[2], metadata


def reliability_metrics(
    predictions: Sequence[Mapping[str, Any]], tickets: Sequence[Mapping[str, Any]], bins: int = 10
) -> Dict[str, Any]:
    """Measure confidence against correctness without modifying probabilities."""
    rows = [
        (float(prediction["confidence"]), int(prediction["intent"] == ticket["labels"]["intent"]), ticket["labels"]["intent"])
        for prediction, ticket in zip(predictions, tickets)
    ]
    buckets: Dict[int, list] = defaultdict(list)
    for confidence, correct, intent in rows:
        buckets[min(int(confidence * bins), bins - 1)].append((confidence, correct, intent))
    reliability = []
    for bucket in range(bins):
        values = buckets.get(bucket, [])
        if not values:
            reliability.append({"lower": bucket / bins, "upper": (bucket + 1) / bins,
                                "count": 0, "mean_confidence": None, "accuracy": None, "absolute_gap": None})
            continue
        mean_confidence = sum(value[0] for value in values) / len(values)
        accuracy = sum(value[1] for value in values) / len(values)
        reliability.append({"lower": bucket / bins, "upper": (bucket + 1) / bins, "count": len(values),
                            "mean_confidence": round(mean_confidence, 6), "accuracy": round(accuracy, 6),
                            "absolute_gap": round(abs(mean_confidence - accuracy), 6)})
    ece = sum(row["count"] * (row["absolute_gap"] or 0.0) for row in reliability) / len(rows) if rows else None
    per_intent = {}
    for intent in CANONICAL_INTENTS:
        values = [(confidence, correct) for confidence, correct, expected in rows if expected == intent]
        if len(values) < 5:
            continue
        per_intent[intent] = {
            "count": len(values),
            "mean_confidence": round(sum(value[0] for value in values) / len(values), 6),
            "accuracy": round(sum(value[1] for value in values) / len(values), 6),
            "mean_confidence_minus_accuracy": round(
                sum(value[0] for value in values) / len(values) - sum(value[1] for value in values) / len(values), 6
            ),
        }
    return {"eligible_count": len(rows), "expected_calibration_error": round(ece, 6) if ece is not None else None,
            "reliability_buckets": reliability, "per_intent_minimum_count": 5, "per_intent": per_intent}


def _retrieve_raw_scores(tickets: Sequence[Mapping[str, Any]]) -> List[List[Dict[str, Any]]]:
    # Expose raw cosine scores for threshold comparison. Candidate thresholds
    # never go below the unchanged production retrieval floor of 0.30.
    retriever = DocumentationRetrievalEngine(min_relevance_score=-1.0)
    results = [retriever.query_authoritative_knowledge(ticket_text(ticket), top_k=5) for ticket in tickets]
    if retriever.last_error:
        raise RuntimeError(f"Production retrieval failed during Stage 11 evidence: {retriever.last_error}")
    return results


def evaluate_policy(
    predictions: Sequence[Mapping[str, Any]], retrievals: Sequence[Sequence[Mapping[str, Any]]],
    tickets: Sequence[Mapping[str, Any]], classification_threshold: float, retrieval_threshold: float,
) -> Dict[str, Any]:
    """Evaluate one threshold pair conditional on independently verified evidence.

    This is a counterfactual development-policy simulation used to measure
    classification/retrieval threshold behavior. It does not represent the
    production release gate, which fails closed when evidence sufficiency is
    unavailable.
    """
    router = TicketRoutingEngine(
        confidence_threshold=classification_threshold,
        retrieval_threshold=retrieval_threshold,
    )
    routes = [
        router.route(
            prediction,
            retrieval,
            evidence_sufficient=True,
        )
        for prediction, retrieval in zip(predictions, retrievals)
    ]
    expected = [str(ticket["labels"]["expected_route"]).upper() for ticket in tickets]
    actual = [route["action"] for route in routes]
    auto_indices = [index for index, route in enumerate(actual) if route == ROUTE_AUTO_RESPOND]
    expected_auto = sum(route == ROUTE_AUTO_RESPOND for route in expected)
    correct_auto = sum(actual[index] == expected[index] == ROUTE_AUTO_RESPOND for index in range(len(actual)))
    false_auto = sum(actual[index] == ROUTE_AUTO_RESPOND and expected[index] != ROUTE_AUTO_RESPOND for index in range(len(actual)))
    false_escalations = sum(actual[index] != ROUTE_AUTO_RESPOND and expected[index] == ROUTE_AUTO_RESPOND for index in range(len(actual)))
    must_not = sum(bool(tickets[index]["labels"].get("must_not_auto_respond")) for index in auto_indices)
    high_risk = sum(tickets[index]["labels"].get("intent") in HIGH_RISK_INTENTS for index in auto_indices)
    auto_count = len(auto_indices); total = len(tickets)
    return {
        "classification_threshold": classification_threshold,
        "retrieval_threshold": retrieval_threshold,
        "ticket_count": total,
        "routing_accuracy": round(sum(a == e for a, e in zip(actual, expected)) / total, 6) if total else None,
        "auto_response_precision": round(correct_auto / auto_count, 6) if auto_count else None,
        "auto_response_recall": round(correct_auto / expected_auto, 6) if expected_auto else None,
        "automation_rate": round(auto_count / total, 6) if total else None,
        "escalation_rate": round((total - auto_count) / total, 6) if total else None,
        "auto_response_count": auto_count,
        "expected_auto_response_count": expected_auto,
        "false_auto_responses": false_auto,
        "false_escalations": false_escalations,
        "must_not_auto_respond_violations": must_not,
        "high_risk_violations": high_risk,
        "safety_constraints_satisfied": false_auto == must_not == high_risk == 0,
    }


def threshold_grid(predictions: Sequence[Mapping[str, Any]], retrievals: Sequence[Sequence[Mapping[str, Any]]],
                   tickets: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    return [evaluate_policy(predictions, retrievals, tickets, confidence, retrieval)
            for confidence in CLASSIFICATION_GRID for retrieval in RETRIEVAL_GRID]


def select_candidate_policies(grid: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Name three comparison policies without implying unsafe candidates pass."""
    rows = [dict(row) for row in grid]
    viable = [row for row in rows if row["auto_response_count"] >= MIN_POLICY_AUTOMATIONS]
    strictly_safe = [row for row in rows if row["safety_constraints_satisfied"]]
    safest = min(
        viable,
        key=lambda row: (
            row["false_auto_responses"], row["must_not_auto_respond_violations"],
            row["high_risk_violations"], -(row["auto_response_precision"] or 0.0),
            -row["classification_threshold"], -row["retrieval_threshold"],
        ),
    ) if viable else None
    balanced = max(
        viable,
        key=lambda row: (
            row["routing_accuracy"], row["auto_response_precision"] or 0.0,
            -row["false_auto_responses"], row["automation_rate"],
        ),
    ) if viable else None
    automated = max(
        strictly_safe,
        key=lambda row: (
            row["automation_rate"], row["routing_accuracy"],
            -row["classification_threshold"], -row["retrieval_threshold"],
        ),
    ) if strictly_safe else None
    has_safe_viable = any(row["auto_response_count"] >= MIN_POLICY_AUTOMATIONS for row in strictly_safe)
    return {
        "selection_status": "SAFE_VIABLE_POLICY_FOUND" if has_safe_viable else "NO_VIABLE_POLICY_SATISFIES_ALL_SAFETY_CONSTRAINTS",
        "minimum_automations": MIN_POLICY_AUTOMATIONS,
        "safest_viable": safest,
        "best_balanced": balanced,
        "highest_automation_safe": automated,
    }


def _confirmed_candidate(candidate: Mapping[str, Any], predictions: Sequence[Mapping[str, Any]],
                         retrievals: Sequence[Sequence[Mapping[str, Any]]], tickets: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    return evaluate_policy(predictions, retrievals, tickets, candidate["classification_threshold"], candidate["retrieval_threshold"])


def run_stage11(dataset_path: Path | str = DEFAULT_TRAINING_DATA_PATH) -> Dict[str, Any]:
    path = Path(dataset_path).resolve()
    if path != DEFAULT_TRAINING_DATA_PATH.resolve():
        raise ValueError("Stage 11 is restricted to the configured development dataset")
    tickets = load_training_tickets(path)
    train, calibration, evaluation, split = development_three_way_split(tickets)
    bundle = build_model_bundle(train)
    calibration_predictions = [predict_with_bundle(bundle, ticket) for ticket in calibration]
    evaluation_predictions = [predict_with_bundle(bundle, ticket) for ticket in evaluation]
    calibration_retrievals = _retrieve_raw_scores(calibration)
    evaluation_retrievals = _retrieve_raw_scores(evaluation)
    calibration_grid = threshold_grid(calibration_predictions, calibration_retrievals, calibration)
    candidates = select_candidate_policies(calibration_grid)
    confirmations = {}
    for name in ("safest_viable", "best_balanced", "highest_automation_safe"):
        candidate = candidates.get(name)
        confirmations[name] = _confirmed_candidate(candidate, evaluation_predictions, evaluation_retrievals, evaluation) if candidate else None
    selected_name = "highest_automation_safe"
    selected_calibration = candidates.get(selected_name)
    selected_evaluation = confirmations.get(selected_name)
    sufficient = bool(
        candidates["selection_status"] == "SAFE_VIABLE_POLICY_FOUND"
        and selected_calibration and selected_evaluation
        and selected_evaluation["safety_constraints_satisfied"]
        and selected_evaluation["auto_response_count"] >= MIN_POLICY_AUTOMATIONS
    )
    selected = {
        "policy": selected_name if sufficient else None,
        "old_thresholds": {"classification_confidence": 0.80, "retrieval_routing": 0.30},
        "new_thresholds": ({"classification_confidence": selected_calibration["classification_threshold"],
                            "retrieval_routing": selected_calibration["retrieval_threshold"]} if sufficient else None),
        "status": "PROVISIONAL_DEVELOPMENT" if sufficient else "CURRENT_DEFAULTS_RETAINED_INSUFFICIENT_EVIDENCE",
        "evidence_used": "Calibration-fold selection and disjoint development evaluation-fold confirmation.",
        "expected_trade_off": "Safety constraints are mandatory; higher escalation is accepted rather than unsafe automation.",
        "production_config_changed": False,
        "current_default_behavior": {
            "calibration": next(row for row in calibration_grid if row["classification_threshold"] == 0.80 and row["retrieval_threshold"] == 0.30),
            "evaluation": evaluate_policy(evaluation_predictions, evaluation_retrievals, evaluation, 0.80, 0.30),
        },
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_classification": "DEVELOPMENT",
        "dataset_sha256": training_data_sha256(path),
        "validation_or_final_data_loaded": False,
        "split": split,
        "model": {
            "architecture": (
                "TF-IDF logistic regression with group-safe sigmoid-calibrated "
                "intent confidence and an uncalibrated urgency head"
            ),
            "model_version": bundle.get("model_version"),
            "feature_fields": list(bundle.get("feature_fields", ())),
            "intent_calibration_method": bundle.get(
                "intent_calibration_method"
            ),
            "intent_calibration_folds": bundle.get(
                "intent_calibration_folds"
            ),
            "urgency_calibration_method": bundle.get(
                "urgency_calibration_method"
            ),
            "fit_population": "train only",
            "training_count": len(train),
        },
        "calibration_metrics": reliability_metrics(calibration_predictions, calibration),
        "evaluation_metrics": reliability_metrics(evaluation_predictions, evaluation),
        "threshold_grid": {"classification_thresholds": list(CLASSIFICATION_GRID), "retrieval_thresholds": list(RETRIEVAL_GRID),
                           "selection_population": "calibration", "rows": calibration_grid},
        "candidate_policies": candidates,
        "candidate_evaluation_confirmation": confirmations,
        "selected_thresholds": selected,
        "policy_simulation": {
            "scope": "counterfactual_threshold_analysis",
            "evidence_sufficient_assumption": True,
            "production_release_gate": (
                "fail closed when evidence sufficiency is unverified"
            ),
            "production_automation_claim": False,
        },
        "urgency_note": (
            "The urgency head remains uncalibrated. Predicted high urgency is "
            "a routing input for database_issue and performance_degradation. "
            "Threshold-grid results are conditional on independently verified "
            "evidence sufficiency."
        ),
    }


def build_markdown(result: Mapping[str, Any]) -> str:
    split = result["split"]; selected = result["selected_thresholds"]
    calibration = result["calibration_metrics"]; evaluation = result["evaluation_metrics"]
    grid_lines = []
    for row in result["threshold_grid"]["rows"]:
        precision = "-" if row["auto_response_precision"] is None else f"{row['auto_response_precision']:.1%}"
        grid_lines.append(
            f"| {row['classification_threshold']:.2f} | {row['retrieval_threshold']:.2f} | {row['routing_accuracy']:.1%} | "
            f"{precision} | {row['auto_response_recall']:.1%} | {row['automation_rate']:.1%} | {row['escalation_rate']:.1%} | "
            f"{row['false_auto_responses']} | {row['false_escalations']} | {row['must_not_auto_respond_violations']} | "
            f"{row['high_risk_violations']} | {row['safety_constraints_satisfied']} |"
        )
    grid_rows = "\n".join(grid_lines)
    candidate_rows = []
    for name, label in (("safest_viable", "Safest viable candidate (fails strict safety if False below)"), ("best_balanced", "Best balanced candidate"), ("highest_automation_safe", "Highest automation satisfying strict safety")):
        chosen = result["candidate_policies"].get(name); confirmed = result["candidate_evaluation_confirmation"].get(name)
        if not chosen:
            candidate_rows.append(f"| {label} | Not identified | - | - | - |")
        else:
            candidate_rows.append(f"| {label} | {chosen['classification_threshold']:.2f} / {chosen['retrieval_threshold']:.2f} | {chosen['automation_rate']:.1%} | {confirmed['automation_rate']:.1%} | {confirmed['safety_constraints_satisfied']} |")
    return f"""# Stage 11 Confidence Calibration and Routing Threshold Selection

## Calibration Method

Evidence class: **DEVELOPMENT**. The classifier was fit on {split['train_count']} tickets. Intent confidence uses group-safe sigmoid calibration; the urgency head remains uncalibrated. Policy selection used {split['calibration_count']} disjoint calibration tickets; confirmation used {split['evaluation_count']} disjoint evaluation tickets.

## Leakage Check

- Group key: {split['group_key']}
- Train/calibration overlap: {split['group_overlap']['train_calibration']}
- Train/evaluation overlap: {split['group_overlap']['train_evaluation']}
- Calibration/evaluation overlap: {split['group_overlap']['calibration_evaluation']}
- Split assignment SHA-256: `{split['split_assignment_sha256']}`
- Validation or final data loaded: `{result['validation_or_final_data_loaded']}`

## Calibration Metrics

| Population | Tickets | Expected calibration error |
| :--- | ---: | ---: |
| Calibration | {calibration['eligible_count']} | {calibration['expected_calibration_error']:.1%} |
| Evaluation | {evaluation['eligible_count']} | {evaluation['expected_calibration_error']:.1%} |

Reliability buckets and per-intent confidence behavior (minimum five examples) are recorded in the machine-readable result.

## Threshold Grid

These routing rows are **counterfactual policy simulations** with `evidence_sufficient=True`. They measure classification/retrieval threshold behavior after an independent evidence-sufficiency gate has hypothetically passed. They are not observed production automation rates.

| Class threshold | Retrieval threshold | Route accuracy | Auto precision | Auto recall | Automation | Escalation | False auto | False escalation | Must-not violations | High-risk violations | Safety satisfied |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
{grid_rows}

## Candidate Policies

| Policy | Class / retrieval | Calibration automation | Evaluation automation | Evaluation safety |
| :--- | :--- | ---: | ---: | :---: |
{chr(10).join(candidate_rows)}

## Selected Thresholds

- Status: **{selected['status']}**
- Old thresholds: classification 0.80; retrieval 0.30
- New thresholds: {selected['new_thresholds'] or 'none'}
- Production configuration changed: `{selected['production_config_changed']}`
- Evidence: {selected['evidence_used']}
- Trade-off: {selected['expected_trade_off']}

## Safety Results

Safety-constrained candidates require zero false auto-responses, zero must-not-auto-respond violations, and zero true high-risk violations. The escalation target is not used as a selection constraint.

## Conditional Routing Metrics After Intent Calibration

Under the counterfactual `evidence_sufficient=True` assumption, the currently configured 0.80 / 0.30 thresholds produce the following behavior. Production remains fail-closed when evidence sufficiency is unverified:

| Population | Route accuracy | Auto precision | Auto recall | Automation | Escalation | False auto | False escalation | Must-not violations | High-risk violations |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Calibration | {selected['current_default_behavior']['calibration']['routing_accuracy']:.1%} | - | {selected['current_default_behavior']['calibration']['auto_response_recall']:.1%} | {selected['current_default_behavior']['calibration']['automation_rate']:.1%} | {selected['current_default_behavior']['calibration']['escalation_rate']:.1%} | {selected['current_default_behavior']['calibration']['false_auto_responses']} | {selected['current_default_behavior']['calibration']['false_escalations']} | {selected['current_default_behavior']['calibration']['must_not_auto_respond_violations']} | {selected['current_default_behavior']['calibration']['high_risk_violations']} |
| Evaluation | {selected['current_default_behavior']['evaluation']['routing_accuracy']:.1%} | - | {selected['current_default_behavior']['evaluation']['auto_response_recall']:.1%} | {selected['current_default_behavior']['evaluation']['automation_rate']:.1%} | {selected['current_default_behavior']['evaluation']['escalation_rate']:.1%} | {selected['current_default_behavior']['evaluation']['false_auto_responses']} | {selected['current_default_behavior']['evaluation']['false_escalations']} | {selected['current_default_behavior']['evaluation']['must_not_auto_respond_violations']} | {selected['current_default_behavior']['evaluation']['high_risk_violations']} |

## Remaining Risks

- This is development evidence, not validation or final evidence.
- Small per-intent populations limit intent-specific calibration conclusions.
- The urgency head remains weak and uncalibrated; high predicted urgency is nevertheless a routing input for database and performance incidents.
- No tested threshold pair satisfied the zero-false-auto safety requirement with viable automation.
- Production does not obtain `evidence_sufficient=True` from retrieval score or generated-response support.
"""


def write_outputs(result: Mapping[str, Any], json_path: Path | str, markdown_path: Path | str) -> None:
    json_output, markdown_output = Path(json_path), Path(markdown_path)
    json_output.parent.mkdir(parents=True, exist_ok=True); markdown_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    markdown_output.write_text(build_markdown(result), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default=str(DEFAULT_TRAINING_DATA_PATH))
    parser.add_argument("--output", default="evaluation/results/stage11-calibration.json")
    parser.add_argument("--markdown", default="evaluation/results/stage11-calibration.md")
    args = parser.parse_args()
    result = run_stage11(args.dataset); write_outputs(result, args.output, args.markdown)
    print(json.dumps({"evidence_classification": result["evidence_classification"],
                      "selected_thresholds": result["selected_thresholds"]}, indent=2))


if __name__ == "__main__":
    main()
