"""Production support pipeline with fail-closed, terminal decision persistence."""
from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from typing import Any, Dict, List, Mapping, Optional

from src.classify import TicketClassificationEngine
from src.config import settings
from src.generate import ResponseGenerationEngine
from src.guardrails import GuardrailEngine
from src.ingest import TicketNormalizationEngine
from src.logging_store import DecisionLoggingEngine
from src.retrieve import DocumentationRetrievalEngine
from src.route import (
    ROUTE_ESCALATE,
    ROUTING_THRESHOLD_STATUS,
    REASON_GUARDRAIL_BLOCKED,
    REASON_MESSAGES,
    TicketRoutingEngine,
)

ACTION_AUTO_RESPOND = "AUTO_RESPOND"
ACTION_ESCALATE = "ESCALATE"
ACTION_BLOCK = "BLOCK"
REASON_GENERATION_FAILED = "GENERATION_FAILED"
REASON_PIPELINE_FAILURE = "PIPELINE_INTERNAL_ERROR"
REASON_AUDIT_FAILURE = "AUDIT_PERSISTENCE_FAILED"
STAGE_FAILURES = {
    "classification": "CLASSIFICATION_FAILURE",
    "retrieval": "RETRIEVAL_FAILURE",
    "routing": "ROUTING_FAILURE",
    "generation": REASON_GENERATION_FAILED,
    "input_guardrails": "GUARDRAIL_INTERNAL_ERROR",
    "output_guardrails": "GUARDRAIL_INTERNAL_ERROR",
}


def _validate_stage(name: str, value: Any) -> Any:
    """Validate component contracts before a malformed value reaches the next stage."""
    if name == "classification":
        if (not isinstance(value, dict) or value.get("failure_code")
                or TicketRoutingEngine._classification_values(value) is None):
            raise ValueError("Invalid classification result")
        urgency_probability = value.get("urgency_confidence")
        if urgency_probability is not None and (
            isinstance(urgency_probability, bool)
            or not isinstance(urgency_probability, (int, float))
            or not math.isfinite(urgency_probability)
            or not 0 <= urgency_probability <= 1
        ):
            raise ValueError("Invalid urgency probability")
        if not isinstance(value.get("alternative_intents", []), list):
            raise ValueError("Invalid alternative classifications")
    elif name == "retrieval":
        if not isinstance(value, list):
            raise ValueError("Invalid retrieval result")
        for item in value:
            if not isinstance(item, dict):
                raise ValueError("Invalid retrieval item")
            score = item.get("relevance_score", item.get("similarity_score"))
            if (isinstance(score, bool) or not isinstance(score, (int, float))
                    or not math.isfinite(score) or not -1 <= score <= 1):
                raise ValueError("Invalid retrieval score")
    elif name == "routing":
        if (not isinstance(value, dict)
                or value.get("action") not in (ACTION_AUTO_RESPOND, ACTION_ESCALATE)
                or not isinstance(value.get("reason_code"), str)
                or not isinstance(value.get("reason"), str)):
            raise ValueError("Invalid routing result")
    elif name == "generation":
        if not isinstance(value, dict) or not isinstance(value.get("supported"), bool):
            raise ValueError("Invalid generation result")
        if not isinstance(value.get("citations", []), list):
            raise ValueError("Invalid generation citations")
    elif name in ("input_guardrails", "output_guardrails"):
        if not isinstance(value, dict) or not isinstance(value.get("passed"), bool):
            raise ValueError("Invalid guardrail result")
        if value["passed"] is False and not isinstance(value.get("primary_reason"), str):
            raise ValueError("Invalid guardrail reason")
    return value


class SupportAutomationOrchestrator:
    """Run every ticket to exactly one terminal outcome and one audit event."""

    def __init__(
        self, ingester: Optional[TicketNormalizationEngine] = None,
        classifier: Optional[TicketClassificationEngine] = None,
        retriever: Optional[DocumentationRetrievalEngine] = None,
        router: Optional[TicketRoutingEngine] = None,
        generator: Optional[ResponseGenerationEngine] = None,
        guardrails: Optional[GuardrailEngine] = None,
        logger: Optional[DecisionLoggingEngine] = None,
        confidence_threshold: Optional[float] = None,
        retrieval_routing_threshold: Optional[float] = None,
        db_url: Optional[str] = None,
    ):
        threshold = confidence_threshold if confidence_threshold is not None else (
            router.confidence_threshold if router is not None else settings.CLASSIFICATION_CONFIDENCE_THRESHOLD
        )
        self.ingester = ingester or TicketNormalizationEngine()
        self.classifier = classifier or TicketClassificationEngine()
        self.retriever = retriever or DocumentationRetrievalEngine()
        self.retrieval_top_k = settings.RETRIEVAL_TOP_K
        self.router = router or TicketRoutingEngine(
            confidence_threshold=threshold, retrieval_threshold=retrieval_routing_threshold
        )
        self.generator = generator or ResponseGenerationEngine()
        self.guardrails = guardrails or GuardrailEngine(confidence_threshold=threshold)
        self.logger_initialization_error = None
        try:
            self.logger = logger if logger is not None else DecisionLoggingEngine(db_url=db_url)
        except Exception as exc:
            self.logger = None
            self.logger_initialization_error = type(exc).__name__
        self.logging_store = self.logger

    def process_ticket(self, raw_ticket: Dict[str, Any], *, run_id: Optional[str] = None) -> Dict[str, Any]:
        started = time.perf_counter()
        stage_latencies: Dict[str, float] = {}
        normalized: Dict[str, Any] = {}
        classification: Dict[str, Any] = {}
        retrieval: List[Dict[str, Any]] = []
        routing: Dict[str, Any] = {}
        generation: Dict[str, Any] = {}
        guardrails: Dict[str, Any] = {}
        active_stage = None

        def run_stage(name: str, operation: Any) -> Any:
            nonlocal active_stage
            active_stage = name
            stage_start = time.perf_counter()
            try:
                value = operation()
                if name == "retrieval" and getattr(self.retriever, "last_error", None):
                    raise RuntimeError("Retrieval backend failed")
                return _validate_stage(name, value)
            finally:
                stage_latencies[name] = round((time.perf_counter() - stage_start) * 1000, 6)

        try:
            try:
                normalized = run_stage("ingestion", lambda: self.ingester.normalize_ticket(raw_ticket))
            except Exception as exc:
                ticket_id = raw_ticket.get("ticket_id", "MALFORMED") if isinstance(raw_ticket, dict) else "MALFORMED"
                return self._finish(
                    ticket_id=ticket_id, ticket={"ticket_id": ticket_id}, classification={}, retrieval=[], routing={}, generation={},
                    guardrails={}, action=ACTION_ESCALATE, reason="ingestion_failure: Ticket ingestion failed safely.",
                    reason_code="INGESTION_FAILURE", run_id=run_id, started=started,
                    stage_latencies=stage_latencies, failure_state="INGESTION_FAILURE",
                    error_type=type(exc).__name__, error_category="MALFORMED_INPUT",
                )

            ticket_id = normalized["ticket_id"]
            content = normalized["raw_content"]
            classification = run_stage("classification", lambda: self.classifier.process_classification(normalized))
            try:
                guardrails = run_stage("input_guardrails", lambda: self.guardrails.check_input(normalized))
            except Exception as exc:
                guardrails = GuardrailEngine.internal_error_result(exc)

            if not guardrails["passed"]:
                routing = {
                    "action": ACTION_BLOCK, "reason_code": REASON_GUARDRAIL_BLOCKED,
                    "reason": REASON_MESSAGES[REASON_GUARDRAIL_BLOCKED],
                    "thresholds": {
                        "classification_confidence": self.router.confidence_threshold,
                        "retrieval_routing": self.router.retrieval_threshold,
                        "status": ROUTING_THRESHOLD_STATUS,
                    },
                }
                return self._finish(
                    ticket_id=ticket_id, ticket=normalized, classification=classification,
                    retrieval=[], routing=routing, generation={}, guardrails=guardrails,
                    action=ACTION_ESCALATE, reason=guardrails["reason"],
                    reason_code=guardrails["primary_reason"], run_id=run_id, started=started,
                    stage_latencies=stage_latencies,
                    failure_state="GUARDRAIL_INTERNAL_ERROR" if guardrails["primary_reason"] == "GUARDRAIL_INTERNAL_ERROR" else None,
                )

            retrieval = run_stage(
                "retrieval", lambda: self.retriever.query_authoritative_knowledge(
                    content, top_k=self.retrieval_top_k
                )
            )
            routing = run_stage("routing", lambda: self.router.route(classification, retrieval))
            if routing["action"] == ROUTE_ESCALATE:
                return self._finish(
                    ticket_id=ticket_id, ticket=normalized, classification=classification,
                    retrieval=retrieval, routing=routing, generation={}, guardrails=guardrails,
                    action=ACTION_ESCALATE, reason=routing["reason"], reason_code=routing["reason_code"],
                    run_id=run_id, started=started, stage_latencies=stage_latencies,
                )

            generation = run_stage(
                "generation", lambda: self.generator.generate_response(normalized, classification, retrieval)
            )
            if not generation.get("supported"):
                guardrails = {
                    "passed": None, "action": "NOT_RUN", "blocked": False, "blocked_by": [],
                    "reason_codes": [], "reasons": [], "checks": {}, "checks_run": [],
                }
                return self._finish(
                    ticket_id=ticket_id, ticket=normalized, classification=classification,
                    retrieval=retrieval, routing=routing, generation=generation, guardrails=guardrails,
                    action=ACTION_ESCALATE, reason="Generation failed safely.",
                    reason_code=REASON_GENERATION_FAILED, run_id=run_id, started=started,
                    stage_latencies=stage_latencies,
                    failure_state=generation.get("failure_reason") or "GENERATION_FAILURE",
                    error_category="GENERATION_FAILURE",
                )

            try:
                guardrails = run_stage(
                    "output_guardrails",
                    lambda: self.guardrails.check(generation, classification, normalized, retrieval),
                )
            except Exception as exc:
                guardrails = GuardrailEngine.internal_error_result(exc)
            if not guardrails["passed"]:
                blocked_route = dict(routing)
                blocked_route["post_route_guardrail_action"] = ACTION_BLOCK
                return self._finish(
                    ticket_id=ticket_id, ticket=normalized, classification=classification,
                    retrieval=retrieval, routing=blocked_route, generation=generation, guardrails=guardrails,
                    action=ACTION_ESCALATE, reason=guardrails["reason"],
                    reason_code=guardrails["primary_reason"], run_id=run_id, started=started,
                    stage_latencies=stage_latencies,
                    failure_state="GUARDRAIL_INTERNAL_ERROR" if guardrails["primary_reason"] == "GUARDRAIL_INTERNAL_ERROR" else None,
                )

            return self._finish(
                ticket_id=ticket_id, ticket=normalized, classification=classification,
                retrieval=retrieval, routing=routing, generation=generation, guardrails=guardrails,
                action=ACTION_AUTO_RESPOND, reason=routing["reason"], reason_code=routing["reason_code"],
                run_id=run_id, started=started, stage_latencies=stage_latencies,
            )
        except Exception as exc:
            failure_code = STAGE_FAILURES.get(active_stage, REASON_PIPELINE_FAILURE)
            ticket_id = normalized.get("ticket_id") or (
                raw_ticket.get("ticket_id", "UNKNOWN") if isinstance(raw_ticket, dict) else "UNKNOWN"
            )
            return self._finish(
                ticket_id=ticket_id, ticket=normalized, classification=classification,
                retrieval=retrieval, routing=routing, generation=generation, guardrails=guardrails,
                action=ACTION_ESCALATE, reason="Unexpected pipeline failure; escalated safely.",
                reason_code=failure_code, run_id=run_id, started=started,
                stage_latencies=stage_latencies, failure_state=failure_code,
                error_type=type(exc).__name__, error_category=failure_code,
            )

    def _finish(
        self, *, ticket_id: str, ticket: Dict[str, Any], classification: Dict[str, Any],
        retrieval: List[Dict[str, Any]], routing: Dict[str, Any], generation: Dict[str, Any],
        guardrails: Dict[str, Any], action: str, reason: str, reason_code: str,
        run_id: Optional[str], started: float, stage_latencies: Dict[str, float],
        failure_state: Optional[str] = None, error_type: Optional[str] = None,
        error_category: Optional[str] = None,
    ) -> Dict[str, Any]:
        total_ms = round((time.perf_counter() - started) * 1000, 6)
        if failure_state == "GUARDRAIL_INTERNAL_ERROR":
            error_category = failure_state
        # Preserve malformed input IDs and suppress all blocked/failed answer text
        # even in the diagnostic result. No customer content is needed in fallback logs.
        ticket = {**ticket, "ticket_id": ticket_id}
        generation = dict(generation) if isinstance(generation, Mapping) else {}
        if generation and action != ACTION_AUTO_RESPOND:
            for field in ("response_text", "answer"):
                generation[field] = None
        decision = self._build_decision_record(
            ticket, classification, retrieval, routing, generation, guardrails, action, reason,
            reason_code, run_id, total_ms, stage_latencies, failure_state, error_type, error_category,
        )
        try:
            decision_id = self.logger.log_decision(decision)
            stored = self.logger.get_decision_by_id(decision_id)
            if not stored:
                raise RuntimeError("Persisted decision could not be read back")
        except Exception as exc:
            fallback = {
                "event": "audit_persistence_failure", "ticket_id": str(ticket_id),
                "run_id": run_id, "terminal_action": ACTION_ESCALATE,
                "reason_code": REASON_AUDIT_FAILURE, "error_type": type(exc).__name__,
            }
            fallback.pop("ticket_id", None)
            fallback["ticket_fingerprint"] = hashlib.sha256(str(ticket_id).encode()).hexdigest()
            try:
                print(json.dumps(fallback, sort_keys=True), file=sys.stderr)
            except Exception:
                pass  # Broken stderr must not trigger a second database write.
            return {
                "decision_id": None, "action": ACTION_ESCALATE, "status": ACTION_ESCALATE,
                "ticket_id": ticket_id, "response_text": None,
                "reason": "Automated response suppressed because the required audit record was unavailable.",
                "reason_code": REASON_AUDIT_FAILURE, "decision_record": None,
                "audit_record": None, "response": None, "classification": classification,
                "routing": routing, "guardrails": guardrails, "response_released": False,
                "failure_state": REASON_AUDIT_FAILURE,
                "run_id": run_id, "confidence": None,
                "error_type": type(exc).__name__, "error_category": REASON_AUDIT_FAILURE,
                "processing_status": "FAILED", "total_latency_ms": total_ms,
            }

        response_released = action == ACTION_AUTO_RESPOND
        return {
            "decision_id": decision_id, "action": action, "status": action, "ticket_id": ticket_id,
            "response_text": generation.get("response_text") if response_released else None,
            "confidence": generation.get("confidence") if response_released else None,
            "reason": reason, "reason_code": reason_code, "decision_record": decision,
            "audit_record": stored,
            "response": generation if generation and (response_released or generation.get("supported") is False) else None,
            "classification": classification, "routing": routing, "guardrails": guardrails,
            "response_released": response_released, "failure_state": failure_state,
            "run_id": run_id, "error_type": error_type, "error_category": error_category,
            "processing_status": "FAILED" if failure_state or error_type else "COMPLETED",
            "total_latency_ms": round((time.perf_counter() - started) * 1000, 6),
        }

    def _build_decision_record(
        self, ticket: Dict[str, Any], classification: Dict[str, Any],
        retrieval: List[Dict[str, Any]], routing: Dict[str, Any],
        generation: Dict[str, Any], guardrails: Dict[str, Any],
        action: str, reason: str, reason_code: str, run_id: Optional[str],
        total_latency_ms: float, stage_latencies: Dict[str, float],
        failure_state: Optional[str], error_type: Optional[str], error_category: Optional[str],
    ) -> Dict[str, Any]:
        raw = ticket.get("raw_content")
        return {
            "ticket_id": ticket.get("ticket_id", "UNKNOWN"), "run_id": run_id,
            "channel": ticket.get("channel"), "original_channel": ticket.get("original_channel") or ticket.get("channel"),
            "customer_tier": ticket.get("customer_tier"),
            "input_fingerprint": hashlib.sha256(raw.encode()).hexdigest() if isinstance(raw, str) and raw else None,
            "classification": classification or {}, "retrieval": retrieval or [],
            "routing": routing or {}, "generation": generation or {}, "guardrails": guardrails or {},
            "selected_action": action, "prediction": action, "reason": reason, "reason_code": reason_code,
            "response_released": action == ACTION_AUTO_RESPOND, "failure_state": failure_state,
            "total_latency_ms": total_latency_ms, "stage_latencies": stage_latencies,
            "processing_status": "FAILED" if failure_state or error_type else "COMPLETED",
            "error_type": error_type, "error_category": error_category,
            "retriever_model": getattr(self.retriever, "model_name", None),
            "requirement_ids": ["A8", "A11"],
        }


SupportPipelineOrchestrator = SupportAutomationOrchestrator
