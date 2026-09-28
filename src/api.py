"""FastAPI service. Drafts are internal; approval is recorded but NEVER
sends anything to a customer.

Run: uvicorn src.api:app --port 8000"""
from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from . import monitoring
from .pipeline import Pipeline

app = FastAPI(title="CloudServe Supervised Support API", version="1.0.0")
_pipeline: Pipeline | None = None


def get_pipeline() -> Pipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = Pipeline.from_settings()
    return _pipeline


def set_pipeline(p: Pipeline) -> None:  # used by tests
    global _pipeline
    _pipeline = p


class TicketIn(BaseModel):
    ticket_id: str
    channel: str
    subject: str = ""
    body: str = ""
    customer_tier: str = "unknown"
    messages: list | None = None


class ReviewIn(BaseModel):
    reviewer: str = Field(min_length=1)
    action: str = Field(pattern="^(approve|reject|edit)$")
    note: str = ""


@app.get("/health")
def health():
    p = get_pipeline()
    return {"status": "ok", "retrieval_backend": p.retriever.backend_name,
            "customer_release_authorized": p.settings.customer_release_authorized,
            "emergency_auto_response_disabled": p.emergency_disabled,
            "release_control_precedence": "DISABLED overrides ENABLED",
            "config_fingerprint": p.fingerprint}


@app.post("/tickets")
def submit(ticket: TicketIn,
           run_mode: str = Header("normal", alias="X-CloudServe-Run-Mode"),
           run_id: str | None = Header(None, alias="X-CloudServe-Run-Id")):
    if run_mode not in {"normal", "demo", "evaluator"}:
        raise HTTPException(400, "run mode must be normal, demo, or evaluator")
    d = get_pipeline().process(
        ticket.model_dump(exclude_none=True), run_id=run_id, run_mode=run_mode
    ).to_dict()
    response = {"ticket_id": d["ticket_id"], "route": d["route"],
                "reasons": d["reasons"], "intent": d["intent"],
                "urgency": d["urgency"], "answerability": d["answerability"],
                "config_fingerprint": d["config_fingerprint"]}
    if d["route"] == "AUTO_RESPOND":
        draft_text = (d.get("draft") or {}).get("text") or ""
        # The stored draft retains its internal-review heading for auditability;
        # the customer-facing contract returns only the controlled answer body.
        response["answer"] = draft_text.split("\n\n", 1)[-1]
        response["citations"] = (d.get("draft") or {}).get("citations", [])
    return response


@app.get("/decisions/{ticket_id}")
def decision(ticket_id: str):
    d = get_pipeline().audit.latest(ticket_id)
    if not d:
        raise HTTPException(404, "no decision for ticket")
    return d


@app.get("/review/{ticket_id}")
def review_view(ticket_id: str):
    p = get_pipeline()
    d = p.audit.latest(ticket_id)
    if not d:
        raise HTTPException(404, "no decision for ticket")
    ev = d.get("evidence") or {}
    g = d.get("guardrails") or {}
    return {
        "ticket_id": ticket_id,
        "route": d["route"],
        "eligibility_status": ev.get("status"),
        "document_id": (d.get("draft") or {}).get("doc_id"),
        "customer_tier": d.get("customer_tier"),
        "plan_applicable": ev.get("plan_applicable"),
        "blocking_flags": sorted(set(ev.get("flags", []) + g.get("blocks", []))),
        "escalation_reasons": d["reasons"],
        "draft": d.get("draft"),
        "internal_only": True,
        "reviews": p.audit.reviews(ticket_id),
    }


@app.post("/review/{ticket_id}")
def review_action(ticket_id: str, body: ReviewIn):
    p = get_pipeline()
    if not p.audit.latest(ticket_id):
        raise HTTPException(404, "no decision for ticket")
    p.audit.record_review(ticket_id, body.reviewer, body.action, body.note)
    return {"recorded": True, "customer_message_sent": False}


@app.get("/metrics")
def metrics():
    return Response(monitoring.exposition(), media_type="text/plain; version=0.0.4")
