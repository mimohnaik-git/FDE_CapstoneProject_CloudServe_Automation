"""Minimal operational HTTP interface for the frozen support pipeline."""

from __future__ import annotations

from functools import lru_cache
import time
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.pipeline import SupportPipelineOrchestrator
from src.monitoring import observe_ticket, prometheus_payload
from src.operations import is_kill_switch_enabled, kill_switch_escalation
from src.security import require_api_access, require_reviewer_access
from src.review import review_handoff_store


class TicketRequest(BaseModel):
    """Public inbound contract accepted for every supported source channel."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    ticket_id: str = Field(min_length=1)
    channel: Literal[
        "email", "chat", "live_chat", "docs_comment",
        "documentation_comments", "forum", "community_forum",
    ]
    customer_tier: Literal["free", "standard", "business", "enterprise"]
    body: str | None = None
    content: str | None = None
    subject: str | None = None
    customer_id: str | None = None
    customer_name: str | None = None
    customer_region: str | None = None
    language_fluency: Literal["fluent", "non_fluent"] | None = None
    sender: str | None = None
    received_at: str | None = None
    timestamp: str | None = None

    @model_validator(mode="after")
    def require_ticket_text(self) -> "TicketRequest":
        if not ((self.content and self.content.strip()) or (self.body and self.body.strip())):
            raise ValueError("Either content or body must be a non-empty string")
        return self


class CitationResponse(BaseModel):
    document_id: str
    chunk_id: str


class TicketResponse(BaseModel):
    ticket_id: str
    terminal_action: Literal["AUTO_RESPOND", "ESCALATE"]
    intent: str | None
    urgency: str | None
    confidence: float | None
    routing_reason: str
    routing_reason_code: str
    response_text: str | None
    citations: list[CitationResponse]
    decision_id: str | None
    processing_status: Literal["COMPLETED", "FAILED"]


class ReviewActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal[
        "APPROVE_DRAFT",
        "REJECT_DRAFT",
    ]


class ReviewActionResponse(BaseModel):
    review_id: str
    decision_id: str
    action: Literal[
        "APPROVE_DRAFT",
        "REJECT_DRAFT",
    ]
    status: Literal["RECORDED"]


class ResolutionEligibilityResponse(BaseModel):
    status: str
    document_id: str | None = None
    customer_tier: str | None = None
    applies_to: str | None = None
    plan_applicable: bool | None = None
    blocking_flags: list[str]


class ReviewerTicketResponse(BaseModel):
    """Strict internal projection for supervised human review."""

    ticket_id: str
    terminal_action: Literal["AUTO_RESPOND", "ESCALATE"]
    intent: str | None
    urgency: str | None
    routing_reason: str
    routing_reason_code: str
    decision_id: str | None
    processing_status: Literal["COMPLETED", "FAILED"]
    approval_required: bool
    review_draft: str | None
    citations: list[CitationResponse]
    evidence_status: str | None
    evidence_reason_code: str | None
    resolution_eligibility: ResolutionEligibilityResponse | None = None


@lru_cache(maxsize=1)
def get_orchestrator() -> SupportPipelineOrchestrator:
    """Construct one ready orchestrator without leaking initialization errors."""

    try:
        orchestrator = SupportPipelineOrchestrator()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pipeline dependencies are unavailable.",
        ) from exc

    # Audit persistence is a mandatory safety dependency. Do not cache or
    # serve a newly initialized pipeline that could not initialize its logger.
    if getattr(orchestrator, "logger", None) is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pipeline dependencies are unavailable.",
        )

    return orchestrator


PipelineDependency = Annotated[SupportPipelineOrchestrator, Depends(get_orchestrator)]
ApiAccessDependency = Annotated[None, Depends(require_api_access)]
ReviewerAccessDependency = Annotated[str, Depends(require_reviewer_access)]

app = FastAPI(
    title="CloudServe Support Pipeline API",
    version="1.0.0",
    description="Operational interface for the frozen support automation pipeline.",
)


@app.get("/health")
def health() -> dict[str, str]:
    """Report process health only; dependencies are not actively probed here."""

    return {"status": "ok", "service": "support-pipeline", "dependency_status": "not_checked"}


@app.get("/ready")
def readiness(
    orchestrator: PipelineDependency,
) -> dict[str, str]:
    """Report initialization readiness without probing external networks."""

    # Dependency resolution has already verified that the pipeline and
    # mandatory audit store initialized successfully.
    del orchestrator

    return {
        "status": "ready",
        "service": "support-pipeline",
        "dependency_status": "initialized",
    }


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    """Expose Prometheus text format without ticket/customer content."""
    return Response(prometheus_payload(), media_type="text/plain; version=0.0.4; charset=utf-8")


@app.post("/tickets/process", response_model=TicketResponse)
def process_ticket(
    ticket: TicketRequest,
    _api_access: ApiAccessDependency,
    orchestrator: PipelineDependency,
) -> TicketResponse:
    """Process one ticket and return only the safe public result projection."""

    payload = ticket.model_dump(exclude_none=True)
    started = time.perf_counter()
    try:
        result = (
            kill_switch_escalation(orchestrator, payload)
            if is_kill_switch_enabled()
            else orchestrator.process_ticket(payload)
        )
    except Exception:
        # This boundary protects the service even if a replacement/injected
        # orchestrator violates the production entry point's fail-closed contract.
        result = {
            "ticket_id": ticket.ticket_id,
            "status": "ESCALATE",
            "reason": "Ticket processing failed safely and requires human review.",
            "reason_code": "PIPELINE_INTERNAL_ERROR",
            "processing_status": "FAILED",
            "decision_id": None,
            "classification": {},
            "response_released": False,
        }
    observe_ticket(ticket.channel, result, time.perf_counter() - started)

    handoff = (
        result.get("escalation_context")
        if isinstance(result.get("escalation_context"), dict)
        else None
    )
    decision_id = result.get("decision_id")

    if (
        isinstance(decision_id, str)
        and decision_id.strip()
        and handoff is not None
        and handoff.get("visibility") == "INTERNAL_REVIEW_ONLY"
        and handoff.get("approval_required") is True
    ):
        review_handoff_store.put(
            decision_id,
            {
                "ticket_id": str(
                    result.get("ticket_id") or ticket.ticket_id
                ),
                "terminal_action": "ESCALATE",
                "classification": (
                    result.get("classification")
                    if isinstance(
                        result.get("classification"),
                        dict,
                    )
                    else {}
                ),
                "routing_reason": str(
                    result.get("reason")
                    or "Human review required."
                ),
                "routing_reason_code": str(
                    result.get("reason_code")
                    or "UNSPECIFIED_ESCALATION"
                ),
                "decision_id": decision_id,
                "processing_status": (
                    "FAILED"
                    if result.get("processing_status") == "FAILED"
                    else "COMPLETED"
                ),
                "escalation_context": handoff,
            },
            audit_store=getattr(orchestrator, "logger", None),
        )

    classification = result.get("classification") if isinstance(result.get("classification"), dict) else {}
    released = result.get("response_released") is True and result.get("status") == "AUTO_RESPOND"
    response = result.get("response") if released and isinstance(result.get("response"), dict) else {}
    raw_citations = response.get("citations", []) if released else []
    citations = [
        CitationResponse(document_id=item["document_id"], chunk_id=item["chunk_id"])
        for item in raw_citations
        if isinstance(item, dict)
        and isinstance(item.get("document_id"), str)
        and isinstance(item.get("chunk_id"), str)
    ]
    terminal_action = "AUTO_RESPOND" if released else "ESCALATE"
    return TicketResponse(
        ticket_id=str(result.get("ticket_id") or ticket.ticket_id),
        terminal_action=terminal_action,
        intent=classification.get("intent"),
        urgency=classification.get("urgency"),
        confidence=classification.get("confidence"),
        routing_reason=str(result.get("reason") or "Human review required."),
        routing_reason_code=str(result.get("reason_code") or "UNSPECIFIED_ESCALATION"),
        response_text=result.get("response_text") if released else None,
        citations=citations,
        decision_id=result.get("decision_id"),
        processing_status="FAILED" if result.get("processing_status") == "FAILED" else "COMPLETED",
    )

@app.get(
    "/review/decisions/{decision_id}",
    response_model=ReviewerTicketResponse,
)
def get_review_handoff(
    decision_id: str,
    _reviewer_access: ReviewerAccessDependency,
) -> ReviewerTicketResponse:
    """Return the exact original internal handoff without reprocessing."""

    stored = review_handoff_store.get(decision_id)

    if stored is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review handoff not found.",
        )

    classification = (
        stored.get("classification")
        if isinstance(stored.get("classification"), dict)
        else {}
    )

    handoff = (
        stored.get("escalation_context")
        if isinstance(stored.get("escalation_context"), dict)
        else {}
    )

    raw_citations = handoff.get("citations", [])

    citations = [
        CitationResponse(
            document_id=item["document_id"],
            chunk_id=item["chunk_id"],
        )
        for item in raw_citations
        if isinstance(item, dict)
        and isinstance(item.get("document_id"), str)
        and isinstance(item.get("chunk_id"), str)
    ]

    return ReviewerTicketResponse(
        ticket_id=str(stored["ticket_id"]),
        terminal_action="ESCALATE",
        intent=classification.get("intent"),
        urgency=classification.get("urgency"),
        routing_reason=str(stored["routing_reason"]),
        routing_reason_code=str(
            stored["routing_reason_code"]
        ),
        decision_id=str(stored["decision_id"]),
        processing_status=str(
            stored["processing_status"]
        ),
        approval_required=True,
        review_draft=str(
            handoff["review_draft"]
        ).strip(),
        citations=citations,
        evidence_status=handoff.get("evidence_status"),
        evidence_reason_code=handoff.get(
            "evidence_reason_code"
        ),
        resolution_eligibility=(
            handoff.get("resolution_eligibility")
            if isinstance(
                handoff.get("resolution_eligibility"),
                dict,
            )
            else None
        ),
    )

@app.post(
    "/review/decisions/{decision_id}/action",
    response_model=ReviewActionResponse,
)
def record_review_action(
    decision_id: str,
    request: ReviewActionRequest,
    reviewer_identity: ReviewerAccessDependency,
) -> ReviewActionResponse:
    """Record one immutable human decision; never sends a customer response."""

    stored = review_handoff_store.get_for_action(decision_id)

    if stored is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review handoff not found.",
        )

    _, audit_store = stored

    if audit_store is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Review audit dependency is unavailable.",
        )

    try:
        review = audit_store.record_review_action(
            decision_id,
            reviewer_identity,
            request.action,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Review action could not be recorded.",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Review audit dependency is unavailable.",
        ) from exc

    # Remove the draft only after the immutable audit event commits.
    review_handoff_store.delete(decision_id)

    return ReviewActionResponse(
        review_id=str(review["review_id"]),
        decision_id=str(review["decision_id"]),
        action=review["action"],
        status="RECORDED",
    )
