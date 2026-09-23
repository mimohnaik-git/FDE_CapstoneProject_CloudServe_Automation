"""Deterministic routing from measurable classification and retrieval signals."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Optional, Sequence

from src.classify import CANONICAL_INTENTS, CANONICAL_URGENCIES
from src.config import settings

ROUTE_AUTO_RESPOND = "AUTO_RESPOND"
ROUTE_ESCALATE = "ESCALATE"
ROUTING_THRESHOLD_STATUS = "DEFAULTS_RETAINED_INSUFFICIENT_EVIDENCE"

# The development policy labels mark every ticket in these canonical intents as
# must-not-auto-respond. Feature requests and unclear requests are handled as
# unsupported rather than being misclassified as security risks.
HIGH_RISK_INTENTS = frozenset({"security_incident", "compliance_request"})
UNANSWERABLE_INTENTS = frozenset({"feature_request", "unclear_request"})
HIGH_URGENCY_OPERATIONAL_INTENTS = frozenset(
    {"database_issue", "performance_degradation"}
)

# Stable reason codes. The legacy constant names remain import-compatible.
REASON_INVALID_CLASSIFICATION = "INVALID_CLASSIFICATION"
REASON_LOW_CONFIDENCE = "LOW_CLASSIFICATION_CONFIDENCE"
REASON_HIGH_RISK_INTENT = "HIGH_RISK_INTENT"
REASON_UNANSWERABLE_INTENT = "UNANSWERABLE_INTENT"
REASON_HIGH_URGENCY_OPERATIONAL = "HIGH_URGENCY_OPERATIONAL"
REASON_NO_RETRIEVAL = "NO_RETRIEVAL"
REASON_WEAK_RETRIEVAL = "WEAK_RETRIEVAL"
REASON_EVIDENCE_SUFFICIENCY_UNVERIFIED = "EVIDENCE_SUFFICIENCY_UNVERIFIED"
REASON_GUARDRAIL_BLOCKED = "GUARDRAIL_BLOCKED"
REASON_VALIDATION_FAILED = "VALIDATION_FAILED"
REASON_PIPELINE_FAILURE = "PIPELINE_FAILURE"
REASON_AUTO_RESPOND = "SAFE_TO_AUTO_RESPOND"
REASON_MISSING_CONFIDENCE = REASON_INVALID_CLASSIFICATION

REASON_MESSAGES = {
    REASON_INVALID_CLASSIFICATION: "Classification output is missing or invalid.",
    REASON_LOW_CONFIDENCE: "Classification confidence is below the selected routing threshold.",
    REASON_HIGH_RISK_INTENT: "The predicted intent requires human review under the risk policy.",
    REASON_UNANSWERABLE_INTENT: "The predicted intent is not answerable from the authoritative corpus.",
    REASON_HIGH_URGENCY_OPERATIONAL: (
        "High-urgency database or performance incidents require human review."
    ),
    REASON_NO_RETRIEVAL: "No authoritative documentation was retrieved.",
    REASON_WEAK_RETRIEVAL: "Retrieved evidence is below the selected routing evidence threshold.",
    REASON_EVIDENCE_SUFFICIENCY_UNVERIFIED: (
        "Retrieved evidence has not been independently verified as sufficient "
        "to answer this specific customer request."
    ),
    REASON_GUARDRAIL_BLOCKED: "A guardrail blocked automated handling.",
    REASON_VALIDATION_FAILED: "Available validation state did not pass.",
    REASON_PIPELINE_FAILURE: "An upstream pipeline failure prevents safe automated handling.",
    REASON_AUTO_RESPOND: "All currently available routing safety conditions are satisfied.",
}


class TicketRoutingEngine:
    """
    Deterministic routing engine for CloudServe support tickets.

    Routing is DETERMINISTIC and AUDITABLE. No LLM call is made here.
    Every decision is based on explicit, configurable thresholds and
    structured signals from upstream pipeline stages.

    Routing considers classification validity/confidence, intent risk and
    answerability, identifiable retrieval evidence, and any available failure,
    guardrail, or validation state. The current baseline thresholds were selected
    in Stage 11 and remain explicit, auditable configuration values.
    """

    def __init__(
        self,
        confidence_threshold: Optional[float] = None,
        retrieval_threshold: Optional[float] = None,
        min_retrieval_results: int = 1,
    ):
        self.confidence_threshold = self._validated_threshold(
            settings.CLASSIFICATION_CONFIDENCE_THRESHOLD
            if confidence_threshold is None
            else confidence_threshold,
            "confidence_threshold",
        )
        self.retrieval_threshold = self._validated_threshold(
            settings.RETRIEVAL_ROUTING_THRESHOLD
            if retrieval_threshold is None
            else retrieval_threshold,
            "retrieval_threshold",
        )
        if isinstance(min_retrieval_results, bool) or not isinstance(min_retrieval_results, int):
            raise ValueError("ROUTING CONFIG ERROR: min_retrieval_results must be an integer.")
        if min_retrieval_results < 1:
            raise ValueError("ROUTING CONFIG ERROR: min_retrieval_results must be at least 1.")
        self.min_retrieval_results = min_retrieval_results

    @staticmethod
    def _validated_threshold(value: Any, name: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"ROUTING CONFIG ERROR: {name} must be numeric.")
        number = float(value)
        if not math.isfinite(number) or not 0.0 <= number <= 1.0:
            raise ValueError(f"ROUTING CONFIG ERROR: {name} must be finite and between 0.0 and 1.0.")
        return number

    def route(
        self,
        classification: Mapping[str, Any],
        retrieval_results: Optional[Sequence[Mapping[str, Any]]] = None,
        guardrail_passed: bool = True,
        validation_passed: Optional[bool] = None,
        failure_state: Optional[Any] = None,
        evidence_sufficient: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Return a deterministic route from structured production signals."""
        if failure_state:
            return self._decision(REASON_PIPELINE_FAILURE, classification)
        if guardrail_passed is not True:
            return self._decision(REASON_GUARDRAIL_BLOCKED, classification)
        if validation_passed is not None and validation_passed is not True:
            return self._decision(REASON_VALIDATION_FAILED, classification)

        classification_values = self._classification_values(classification)
        if classification_values is None:
            return self._decision(REASON_INVALID_CLASSIFICATION, classification)
        intent, urgency, confidence = classification_values

        if intent in HIGH_RISK_INTENTS:
            return self._decision(
                REASON_HIGH_RISK_INTENT, classification, confidence=confidence, urgency=urgency,
                risk="high", answerable=False,
            )
        if intent in UNANSWERABLE_INTENTS:
            return self._decision(
                REASON_UNANSWERABLE_INTENT, classification, confidence=confidence, urgency=urgency,
                risk="standard", answerable=False,
            )
        if (
            intent in HIGH_URGENCY_OPERATIONAL_INTENTS
            and urgency == "high"
        ):
            return self._decision(
                REASON_HIGH_URGENCY_OPERATIONAL,
                classification,
                confidence=confidence,
                urgency=urgency,
                risk="high",
                answerable=False,
            )

        if confidence < self.confidence_threshold:
            return self._decision(
                REASON_LOW_CONFIDENCE, classification, confidence=confidence, urgency=urgency,
                risk="standard", answerable=False,
            )

        evidence = self._retrieval_evidence(retrieval_results)
        if evidence["result_count"] == 0:
            return self._decision(
                REASON_NO_RETRIEVAL, classification, confidence=confidence, urgency=urgency,
                risk="standard", answerable=False, **evidence,
            )
        if (
            evidence["valid_evidence_count"] < self.min_retrieval_results
            or evidence["top_score"] is None
            or evidence["top_score"] < self.retrieval_threshold
        ):
            return self._decision(
                REASON_WEAK_RETRIEVAL, classification, confidence=confidence, urgency=urgency,
                risk="standard", answerable=False, **evidence,
            )
        if evidence_sufficient is not True:
            return self._decision(
                REASON_EVIDENCE_SUFFICIENCY_UNVERIFIED,
                classification,
                confidence=confidence,
                urgency=urgency,
                risk="standard",
                answerable=False,
                **evidence,
            )

        return self._decision(
            REASON_AUTO_RESPOND, classification, confidence=confidence, urgency=urgency,
            risk="standard", answerable=True, **evidence,
        )

    @staticmethod
    def _classification_values(
        classification: Any,
    ) -> Optional[tuple[str, str, float]]:
        if not isinstance(classification, Mapping):
            return None
        intent = classification.get("intent")
        urgency = classification.get("urgency")
        confidence = classification.get("confidence")
        if intent not in CANONICAL_INTENTS or urgency not in CANONICAL_URGENCIES:
            return None
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            return None
        confidence = float(confidence)
        if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
            return None
        return intent, urgency, confidence

    @staticmethod
    def _retrieval_evidence(
        retrieval_results: Optional[Sequence[Mapping[str, Any]]],
    ) -> Dict[str, Any]:
        if retrieval_results is None:
            results: List[Any] = []
        elif isinstance(retrieval_results, Sequence) and not isinstance(
            retrieval_results, (str, bytes)
        ):
            results = list(retrieval_results)
        else:
            return {"result_count": 1, "valid_evidence_count": 0, "top_score": None}

        valid_scores: List[float] = []
        for result in results:
            if not isinstance(result, Mapping):
                continue
            source_id = result.get("doc_id") or result.get("document_id")
            score = result.get("relevance_score", result.get("similarity_score"))
            if not isinstance(source_id, str) or not source_id.strip():
                continue
            if isinstance(score, bool) or not isinstance(score, (int, float)):
                continue
            score = float(score)
            if math.isfinite(score) and -1.0 <= score <= 1.0:
                valid_scores.append(score)
        return {
            "result_count": len(results),
            "valid_evidence_count": len(valid_scores),
            "top_score": max(valid_scores) if valid_scores else None,
        }

    def _decision(
        self,
        reason_code: str,
        classification: Any,
        *,
        confidence: Optional[float] = None,
        urgency: Optional[str] = None,
        risk: str = "unknown",
        answerable: bool = False,
        result_count: int = 0,
        valid_evidence_count: int = 0,
        top_score: Optional[float] = None,
    ) -> Dict[str, Any]:
        action = ROUTE_AUTO_RESPOND if reason_code == REASON_AUTO_RESPOND else ROUTE_ESCALATE
        intent = classification.get("intent") if isinstance(classification, Mapping) else None
        return {
            "action": action,
            "reason_code": reason_code,
            "reason": REASON_MESSAGES[reason_code],
            "classification_confidence": confidence,
            "retrieval_score": top_score,
            "retrieval_count": result_count,
            "valid_retrieval_count": valid_evidence_count,
            "intent": intent,
            "urgency": urgency,
            "risk": risk,
            "answerable": answerable,
            "thresholds": {
                "classification_confidence": self.confidence_threshold,
                "retrieval_routing": self.retrieval_threshold,
                "minimum_retrieval_results": self.min_retrieval_results,
                "status": ROUTING_THRESHOLD_STATUS,
            },
            # Compatibility fields consumed by the existing decision store.
            "confidence": confidence,
            "threshold": self.confidence_threshold,
            "escalate": action == ROUTE_ESCALATE,
        }

    def route_batch(self, requests: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        """Route every request independently; one failure cannot end the batch."""
        decisions: List[Dict[str, Any]] = []
        for request in requests:
            try:
                decisions.append(
                    self.route(
                        request.get("classification"),
                        request.get("retrieval_results"),
                        guardrail_passed=request.get("guardrail_passed", True),
                        validation_passed=request.get("validation_passed"),
                        failure_state=request.get("failure_state"),
                        evidence_sufficient=request.get("evidence_sufficient"),
                    )
                )
            except Exception:
                classification = request.get("classification") if isinstance(request, Mapping) else None
                decisions.append(self._decision(REASON_PIPELINE_FAILURE, classification))
        return decisions
