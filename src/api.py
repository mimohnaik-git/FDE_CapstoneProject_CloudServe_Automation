"""Minimal operational HTTP interface for the frozen support pipeline."""

from __future__ import annotations

from functools import lru_cache
import time
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.pipeline import SupportPipelineOrchestrator
from src.monitoring import observe_ticket, prometheus_payload
from src.operations import is_kill_switch_enabled, kill_switch_escalation
from src.security import require_api_access


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


@lru_cache(maxsize=1)
def get_orchestrator() -> SupportPipelineOrchestrator:
    """Construct the real production orchestrator once per application process."""

    return SupportPipelineOrchestrator()


PipelineDependency = Annotated[SupportPipelineOrchestrator, Depends(get_orchestrator)]
ApiAccessDependency = Annotated[None, Depends(require_api_access)]

app = FastAPI(
    title="CloudServe Support Pipeline API",
    version="1.0.0",
    description="Operational interface for the frozen support automation pipeline.",
)


@app.get("/health")
def health() -> dict[str, str]:
    """Report process health only; dependencies are not actively probed here."""

    return {"status": "ok", "service": "support-pipeline", "dependency_status": "not_checked"}


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
