"""Persistent, minimized decision records for the production pipeline."""
from __future__ import annotations

import hashlib
import json
import math
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, String, Text, create_engine, event, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from src.config import settings

DECISION_SCHEMA_VERSION = "1.0"
Base = declarative_base()
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_SECRET_PATTERNS = (
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)\b(?:api[_ -]?key|password|passwd|token|secret)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
)


class DecisionRecordModel(Base):
    """Versioned audit event; ticket IDs are deliberately not unique."""
    __tablename__ = "decision_records"

    decision_id = Column(String(36), primary_key=True)
    decision_schema_version = Column(String(16), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    run_id = Column(String(100), nullable=True, index=True)
    ticket_id = Column(String(100), nullable=False, index=True)
    channel = Column(String(50))
    original_channel = Column(String(50))
    customer_tier = Column(String(50))
    input_fingerprint = Column(String(64))
    intent = Column(String(100))
    urgency = Column(String(50))
    intent_confidence = Column(Float)
    urgency_confidence = Column(Float)
    classification_metadata = Column(Text, nullable=False)
    retrieval_status = Column(String(50), nullable=False)
    retrieval_items = Column(Text, nullable=False)
    top_retrieval_score = Column(Float)
    retriever_model = Column(String(200))
    original_route_action = Column(String(50))
    routing_reason_code = Column(String(100))
    routing_reason = Column(String(500), nullable=False)
    routing_signals = Column(Text, nullable=False)
    classification_threshold = Column(Float)
    retrieval_threshold = Column(Float)
    risk = Column(String(50))
    generation_attempted = Column(Boolean, nullable=False)
    generation_supported = Column(Boolean)
    generation_grounded = Column(Boolean)
    generation_provider = Column(String(100))
    generation_model = Column(String(200))
    prompt_version = Column(String(100))
    citation_ids = Column(Text, nullable=False)
    generation_failure_code = Column(String(100))
    guardrail_passed = Column(Boolean)
    guardrail_blocked = Column(Boolean, nullable=False)
    guardrail_reason_codes = Column(Text, nullable=False)
    guardrail_action = Column(String(50))
    guardrail_checks = Column(Text, nullable=False)
    guardrail_internal_error = Column(Boolean, nullable=False)
    terminal_action = Column(String(50), nullable=False, index=True)
    terminal_reason_code = Column(String(100), nullable=False)
    response_released = Column(Boolean, nullable=False)
    failure_state = Column(String(100))
    total_latency_ms = Column(Float)
    stage_latencies = Column(Text, nullable=False)
    processing_status = Column(String(50), nullable=False)
    error_type = Column(String(100))
    error_category = Column(String(100))
    requirement_ids = Column(Text, nullable=False)


class ReviewActionModel(Base):
    """Immutable human-review decision linked to one pipeline decision."""

    __tablename__ = "review_actions"

    review_id = Column(String(36), primary_key=True)
    decision_id = Column(
        String(36),
        ForeignKey("decision_records.decision_id"),
        nullable=False,
        unique=True,
        index=True,
    )
    timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    reviewer_identity = Column(
        String(64),
        nullable=False,
        index=True,
    )
    action = Column(
        String(32),
        nullable=False,
    )


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _clean(value: Any, limit: int = 500) -> Optional[str]:
    if value is None:
        return None
    text = str(value)
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text[:limit]


def _number(value: Any) -> Optional[float]:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def _sqlite_url(url: str) -> str:
    if url == "sqlite:///:memory:" or not url.startswith("sqlite:///"):
        return url
    path = Path(url.removeprefix("sqlite:///"))
    if not path.is_absolute():
        path = (_PROJECT_ROOT / path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path.as_posix()}"


def _retrieval(results: Sequence[Any]) -> List[Dict[str, Any]]:
    items = []
    for rank, value in enumerate(results, 1):
        if not isinstance(value, Mapping):
            continue
        doc = value.get("document_id") or value.get("doc_id")
        chunk = value.get("chunk_id")
        score = _number(value.get("similarity_score", value.get("relevance_score")))
        if doc is not None or chunk is not None or score is not None:
            items.append({"rank": rank, "document_id": _clean(doc, 200), "chunk_id": _clean(chunk, 200), "score": score})
    return items


def _classification(value: Mapping[str, Any]) -> Dict[str, Any]:
    alternatives = [
        {"intent": _clean(item.get("intent"), 100), "confidence": _number(item.get("confidence"))}
        for item in value.get("alternative_intents") or [] if isinstance(item, Mapping)
    ]
    return {
        "alternatives": alternatives,
        "model_name": _clean(value.get("model_name"), 200),
        "model_version": _clean(value.get("model_version"), 100),
        "data_fingerprint": _clean(value.get("training_data_sha256"), 100),
    }


def _checks(value: Mapping[str, Any]) -> List[Dict[str, Any]]:
    raw = value.get("checks")
    if not isinstance(raw, Mapping):
        return []
    return [
        {
            "key": _clean(key, 100), "name": _clean(check.get("name"), 100),
            "passed": check.get("passed") if isinstance(check.get("passed"), bool) else None,
            "blocked": bool(check.get("blocked")), "reason_code": _clean(check.get("reason_code"), 100),
        }
        for key, check in raw.items() if isinstance(check, Mapping)
    ]


class DecisionLogStore:
    """Transactional SQLite decision store with minimized, queryable records."""

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = _sqlite_url(db_url or settings.DATABASE_URL)
        args: Dict[str, Any] = {"echo": False}
        if self.db_url.startswith("sqlite"):
            args["connect_args"] = {"check_same_thread": False, "timeout": 5}
        if self.db_url == "sqlite:///:memory:":
            args["poolclass"] = StaticPool
        self.engine = create_engine(self.db_url, **args)
        if self.db_url.startswith("sqlite"):
            event.listen(self.engine, "connect", self._configure_sqlite)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.initialize()

    @staticmethod
    def _configure_sqlite(connection: Any, _record: Any) -> None:
        cursor = connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.execute("PRAGMA journal_mode=WAL")
        finally:
            cursor.close()

    def initialize(self) -> None:
        Base.metadata.create_all(self.engine)

    def record_decision(
        self, ticket_id: str, routing_action: str, routing_reason: str,
        normalized_ticket: Optional[Dict[str, Any]] = None,
        classification: Optional[Dict[str, Any]] = None,
        retrieval_results: Optional[List[Dict[str, Any]]] = None,
        routing_decision: Optional[Dict[str, Any]] = None,
        generated_response: Optional[Dict[str, Any]] = None,
        guardrail_result: Optional[Dict[str, Any]] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
        *, run_id: Optional[str] = None, terminal_reason_code: Optional[str] = None,
        response_released: Optional[bool] = None, total_latency_ms: Optional[float] = None,
        stage_latencies: Optional[Mapping[str, Any]] = None,
        processing_status: Optional[str] = None, error_type: Optional[str] = None,
        error_category: Optional[str] = None, failure_state: Optional[str] = None,
        requirement_ids: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        ticket, cls, results = normalized_ticket or {}, classification or {}, retrieval_results or []
        route, generation, guardrails, extra = routing_decision or {}, generated_response or {}, guardrail_result or {}, extra_metadata or {}
        items = _retrieval(results)
        scores = [item["score"] for item in items if item["score"] is not None]
        thresholds = route.get("thresholds") if isinstance(route.get("thresholds"), Mapping) else {}
        reason_codes = list(guardrails.get("reason_codes") or [])
        if not reason_codes and guardrails.get("primary_reason"):
            reason_codes = [guardrails["primary_reason"]]
        checks = _checks(guardrails)
        citations = generation.get("citations") or generation.get("citation_ids") or []
        citation_ids: List[str] = []
        for citation in citations:
            value = citation.get("document_id") if isinstance(citation, Mapping) else citation
            if value is not None and str(value) not in citation_ids:
                citation_ids.append(str(value))
        released = routing_action == "AUTO_RESPOND" if response_released is None else bool(response_released)
        released = released and routing_action == "AUTO_RESPOND"
        input_text = ticket.get("raw_content")
        fingerprint = extra.get("input_fingerprint")
        if not fingerprint and isinstance(input_text, str) and input_text:
            fingerprint = hashlib.sha256(input_text.encode()).hexdigest()
        signals = {
            key: route[key]
            for key in (
                "classification_confidence",
                "retrieval_score",
                "retrieval_count",
                "valid_retrieval_count",
                "answerable",
            )
            if route.get(key) is not None
        }

        evidence_sufficiency = route.get(
            "evidence_sufficiency"
        )

        if isinstance(evidence_sufficiency, Mapping):
            signals["evidence_sufficiency"] = dict(
                evidence_sufficiency
            )
        record = DecisionRecordModel(
            decision_id=str(uuid.uuid4()), decision_schema_version=DECISION_SCHEMA_VERSION,
            timestamp=datetime.now(timezone.utc), run_id=_clean(run_id or extra.get("run_id"), 100),
            ticket_id=_clean(ticket_id, 100) or "UNKNOWN",
            channel=_clean(ticket.get("channel") or extra.get("channel"), 50),
            original_channel=_clean(ticket.get("original_channel") or ticket.get("channel") or extra.get("channel"), 50),
            customer_tier=_clean(ticket.get("customer_tier") or extra.get("customer_tier"), 50),
            input_fingerprint=_clean(fingerprint, 64), intent=_clean(cls.get("intent"), 100), urgency=_clean(cls.get("urgency"), 50),
            intent_confidence=_number(cls.get("confidence")), urgency_confidence=_number(cls.get("urgency_confidence")),
            classification_metadata=_json(_classification(cls)),
            retrieval_status=(
                "FAILED" if extra.get("error_category") == "RETRIEVAL_FAILURE" else
                "NOT_RUN" if "stage_latencies" in extra and "retrieval" not in extra["stage_latencies"] else
                "NO_RESULT" if not items else "RETRIEVED"
            ), retrieval_items=_json(items),
            top_retrieval_score=max(scores) if scores else None, retriever_model=_clean(extra.get("retriever_model"), 200),
            original_route_action=_clean(route.get("action"), 50), routing_reason_code=_clean(route.get("reason_code"), 100),
            routing_reason=_clean(routing_reason) or "unspecified", routing_signals=_json(signals),
            classification_threshold=_number(thresholds.get("classification_confidence", route.get("threshold"))),
            retrieval_threshold=_number(thresholds.get("retrieval_routing")), risk=_clean(route.get("risk"), 50),
            generation_attempted=bool(generation),
            generation_supported=generation.get("supported") if isinstance(generation.get("supported"), bool) else None,
            generation_grounded=generation.get("grounded") if isinstance(generation.get("grounded"), bool) else None,
            generation_provider=_clean(generation.get("provider"), 100),
            generation_model=_clean(generation.get("model_name") or generation.get("model"), 200),
            prompt_version=_clean(generation.get("prompt_version"), 100), citation_ids=_json(citation_ids),
            generation_failure_code=_clean(generation.get("failure_reason"), 100),
            guardrail_passed=guardrails.get("passed") if isinstance(guardrails.get("passed"), bool) else None,
            guardrail_blocked=bool(guardrails.get("blocked") or guardrails.get("blocked_by")),
            guardrail_reason_codes=_json([_clean(code, 100) for code in reason_codes]),
            guardrail_action=_clean(guardrails.get("action"), 50), guardrail_checks=_json(checks),
            guardrail_internal_error=("GUARDRAIL_INTERNAL_ERROR" in reason_codes),
            terminal_action=_clean(routing_action, 50) or "ESCALATE",
            terminal_reason_code=_clean(terminal_reason_code or extra.get("reason_code") or route.get("reason_code") or "UNSPECIFIED", 100) or "UNSPECIFIED",
            response_released=released, failure_state=_clean(failure_state or extra.get("failure_state"), 100),
            total_latency_ms=_number(total_latency_ms if total_latency_ms is not None else extra.get("total_latency_ms")),
            stage_latencies=_json(dict(stage_latencies or extra.get("stage_latencies") or {})),
            processing_status=_clean(processing_status or extra.get("processing_status") or "COMPLETED", 50) or "COMPLETED",
            error_type=_clean(error_type or extra.get("error_type"), 100),
            error_category=_clean(error_category or extra.get("error_category"), 100),
            requirement_ids=_json(list(requirement_ids or extra.get("requirement_ids") or ["A8"])),
        )
        session = self.Session()
        try:
            session.add(record)
            session.commit()
            return self._record_to_dict(record)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def log_decision(self, decision: Dict[str, Any]) -> str:
        action = decision.get("selected_action") or decision.get("prediction") or decision.get("routing_action") or "ESCALATE"
        ticket = decision.get("ticket") or {
            "channel": decision.get("channel"), "original_channel": decision.get("original_channel"),
            "customer_tier": decision.get("customer_tier"), "raw_content": decision.get("input_content_for_fingerprint"),
        }
        stored = self.record_decision(
            decision.get("ticket_id", "UNKNOWN"), action, decision.get("reason", "unspecified"),
            ticket, decision.get("classification"), decision.get("retrieval"), decision.get("routing"),
            decision.get("generation"), decision.get("guardrails"), decision,
            run_id=decision.get("run_id"), terminal_reason_code=decision.get("reason_code"),
            response_released=decision.get("response_released"), total_latency_ms=decision.get("total_latency_ms"),
            stage_latencies=decision.get("stage_latencies"), processing_status=decision.get("processing_status"),
            error_type=decision.get("error_type"), error_category=decision.get("error_category"),
            failure_state=decision.get("failure_state"), requirement_ids=decision.get("requirement_ids"),
        )
        return stored["decision_id"]

    def _query(self, **filters: Any) -> List[Dict[str, Any]]:
        session = self.Session()
        try:
            query = session.query(DecisionRecordModel)
            for key, value in filters.items():
                query = query.filter(getattr(DecisionRecordModel, key) == value)
            return [self._record_to_dict(row) for row in query.order_by(DecisionRecordModel.timestamp).all()]
        finally:
            session.close()

    def get_decision_by_id(self, decision_id: str) -> Optional[Dict[str, Any]]:
        rows = self._query(decision_id=decision_id)
        return rows[0] if rows else None

    get_decision = get_decision_by_id
    retrieve_decision = get_decision_by_id

    def get_review_action(
        self,
        decision_id: str,
    ) -> Optional[Dict[str, Any]]:
        session = self.Session()
        try:
            row = (
                session.query(ReviewActionModel)
                .filter(
                    ReviewActionModel.decision_id
                    == str(decision_id)
                )
                .first()
            )

            if row is None:
                return None

            return {
                "review_id": row.review_id,
                "decision_id": row.decision_id,
                "timestamp": row.timestamp.isoformat(),
                "reviewer_identity": row.reviewer_identity,
                "action": row.action,
            }
        finally:
            session.close()

    def record_review_action(
        self,
        decision_id: str,
        reviewer_identity: str,
        action: str,
    ) -> Dict[str, Any]:
        decision_id = str(decision_id).strip()
        reviewer_identity = str(reviewer_identity).strip()
        action = str(action).strip().upper()

        if action not in {
            "APPROVE_DRAFT",
            "REJECT_DRAFT",
        }:
            raise ValueError(
                "Unsupported review action"
            )

        if not decision_id:
            raise ValueError(
                "decision_id is required"
            )

        if not reviewer_identity:
            raise ValueError(
                "reviewer_identity is required"
            )

        if self.get_decision_by_id(decision_id) is None:
            raise ValueError(
                "Pipeline decision does not exist"
            )

        if self.get_review_action(decision_id) is not None:
            raise ValueError(
                "Review action already recorded"
            )

        session = self.Session()

        try:
            row = ReviewActionModel(
                review_id=str(uuid.uuid4()),
                decision_id=decision_id,
                timestamp=datetime.now(timezone.utc),
                reviewer_identity=reviewer_identity[:64],
                action=action,
            )

            session.add(row)

            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise ValueError(
                    "Review action already recorded"
                ) from exc

            session.refresh(row)

            return {
                "review_id": row.review_id,
                "decision_id": row.decision_id,
                "timestamp": row.timestamp.isoformat(),
                "reviewer_identity": row.reviewer_identity,
                "action": row.action,
            }
        finally:
            session.close()

    def get_decisions_by_ticket_id(self, ticket_id: str) -> List[Dict[str, Any]]:
        return self._query(ticket_id=ticket_id)

    get_decisions_for_ticket = get_decisions_by_ticket_id

    def get_decisions_for_run(self, run_id: str) -> List[Dict[str, Any]]:
        return self._query(run_id=run_id)

    def get_decisions_by_outcome(self, outcome: str, limit: int = 100) -> List[Dict[str, Any]]:
        return self._query(terminal_action=outcome)[:limit]

    def list_all_decisions(self) -> List[Dict[str, Any]]:
        return self._query()

    def count_decisions(self, *, run_id: Optional[str] = None, terminal_action: Optional[str] = None) -> int:
        session = self.Session()
        try:
            query = session.query(func.count(DecisionRecordModel.decision_id))
            if run_id is not None:
                query = query.filter(DecisionRecordModel.run_id == run_id)
            if terminal_action is not None:
                query = query.filter(DecisionRecordModel.terminal_action == terminal_action)
            return int(query.scalar() or 0)
        finally:
            session.close()

    def terminal_action_counts(self, *, run_id: Optional[str] = None) -> Dict[str, int]:
        session = self.Session()
        try:
            query = session.query(DecisionRecordModel.terminal_action, func.count(DecisionRecordModel.decision_id))
            if run_id is not None:
                query = query.filter(DecisionRecordModel.run_id == run_id)
            return {str(action): int(count) for action, count in query.group_by(DecisionRecordModel.terminal_action).all()}
        finally:
            session.close()

    def get_summary_stats(self) -> Dict[str, Any]:
        total, counts = self.count_decisions(), self.terminal_action_counts()
        auto, escalated = counts.get("AUTO_RESPOND", 0), counts.get("ESCALATE", 0) + counts.get("BLOCK", 0)
        blocked = sum(row["guardrail_blocked"] for row in self.list_all_decisions())
        return {"total_decisions": total, "auto_responded": auto, "escalated": escalated,
                "blocked_by_guardrail": blocked, "auto_response_rate": auto / total if total else 0.0,
                "escalation_rate": escalated / total if total else 0.0}

    @staticmethod
    def _record_to_dict(row: DecisionRecordModel) -> Dict[str, Any]:
        items, cls_meta = json.loads(row.retrieval_items), json.loads(row.classification_metadata)
        codes, checks, citations = json.loads(row.guardrail_reason_codes), json.loads(row.guardrail_checks), json.loads(row.citation_ids)
        generation = {"attempted": row.generation_attempted, "supported": row.generation_supported,
                      "provider": row.generation_provider, "model_name": row.generation_model,
                      "prompt_version": row.prompt_version, "citation_ids": citations,
                      "failure_reason": row.generation_failure_code}
        guardrails = {"passed": row.guardrail_passed, "blocked": row.guardrail_blocked,
                      "action": row.guardrail_action, "reason_codes": codes,
                      "primary_reason": codes[0] if codes else None, "checks": checks}
        return {
            "decision_id": row.decision_id, "decision_schema_version": row.decision_schema_version,
            "timestamp": row.timestamp.isoformat(), "run_id": row.run_id, "ticket_id": row.ticket_id,
            "channel": row.channel, "original_channel": row.original_channel, "customer_tier": row.customer_tier,
            "input_fingerprint": row.input_fingerprint, "intent": row.intent, "urgency": row.urgency,
            "confidence": row.intent_confidence, "intent_confidence": row.intent_confidence,
            "urgency_confidence": row.urgency_confidence, "classification_metadata": cls_meta,
            "retrieval_status": row.retrieval_status, "retrieval": items,
            "retrieved_source_ids": [i["document_id"] for i in items if i.get("document_id")],
            "retrieved_chunk_ids": [i["chunk_id"] for i in items if i.get("chunk_id")],
            "retrieval_scores": [i["score"] for i in items if i.get("score") is not None],
            "top_retrieval_score": row.top_retrieval_score, "retriever_model": row.retriever_model,
            "original_route_action": row.original_route_action, "routing_action": row.terminal_action,
            "terminal_action": row.terminal_action, "routing_reason_code": row.routing_reason_code,
            "routing_reason": row.routing_reason, "routing_signals": json.loads(row.routing_signals),
            "classification_threshold": row.classification_threshold, "retrieval_threshold": row.retrieval_threshold,
            "risk": row.risk, "generation": generation, "generated_response": None, "citations": citations,
            "is_grounded": row.generation_grounded, "model_name": row.generation_model,
            "prompt_version": row.prompt_version, "guardrail_passed": row.guardrail_passed,
            "guardrail_blocked": row.guardrail_blocked,
            "guardrail_blocked_by": [c.get("name") for c in checks if c.get("blocked")],
            "guardrail_reasons": codes, "guardrail_internal_error": row.guardrail_internal_error,
            "terminal_reason_code": row.terminal_reason_code, "response_released": row.response_released,
            "failure_state": row.failure_state, "total_latency_ms": row.total_latency_ms,
            "stage_latencies": json.loads(row.stage_latencies), "processing_stage": row.processing_status,
            "processing_status": row.processing_status, "error_type": row.error_type,
            "error_category": row.error_category, "requirement_ids": json.loads(row.requirement_ids),
            "metadata": {
                "classification": {"intent": row.intent, "urgency": row.urgency,
                                   "confidence": row.intent_confidence, "urgency_confidence": row.urgency_confidence, **cls_meta},
                "retrieval": items,
                "routing": {"action": row.original_route_action, "reason_code": row.routing_reason_code,
                            "signals": json.loads(row.routing_signals)},
                "generation": generation, "guardrails": guardrails,
            },
        }


DecisionLoggingEngine = DecisionLogStore
