"""Typed records passed between pipeline stages."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, cast


class Channel(str, Enum):
    EMAIL = "email"
    CHAT = "chat"
    DOCS_COMMENT = "docs_comment"
    FORUM = "forum"


class Route(str, Enum):
    AUTO_RESPOND = "AUTO_RESPOND"
    ESCALATE = "ESCALATE"


class Eligibility(str, Enum):
    SELF_SERVICE_CANDIDATE = "SELF_SERVICE_CANDIDATE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    PLAN_INAPPLICABLE = "PLAN_INAPPLICABLE"
    UNKNOWN = "UNKNOWN"


class DraftStatus(str, Enum):
    EVIDENCE_ASSEMBLY_COMPLETE = "EVIDENCE_ASSEMBLY_COMPLETE"
    NO_EVIDENCE = "NO_EVIDENCE"
    BLOCKED = "BLOCKED"


@dataclass
class Ticket:
    ticket_id: str
    channel: Channel
    subject: str
    body: str
    original_text: str = ""
    customer_tier: str = "unknown"
    metadata: dict = field(default_factory=dict)

    @property
    def text(self) -> str:
        return f"{self.subject}\n{self.body}".strip()


@dataclass
class Prediction:
    label: str
    confidence: float
    alternatives: list  # [(label, prob), ...] excluding top


@dataclass
class Passage:
    doc_id: str
    title: str
    section: str
    text: str
    score: float
    plans: list = field(default_factory=list)

    @property
    def citation(self) -> str:
        return f"{self.doc_id}#{self.section}"


@dataclass
class EvidenceAssessment:
    status: Eligibility
    # Never True: release authority has not been proven. None = "not established".
    sufficient: Any = None
    plan_applicable: Any = None
    flags: list = field(default_factory=list)
    policy: str = ""


@dataclass
class Draft:
    status: DraftStatus
    text: str = ""
    citations: list = field(default_factory=list)
    doc_id: str | None = None
    internal_only: bool = True


@dataclass
class GuardrailResult:
    passed: bool
    blocks: list = field(default_factory=list)   # guardrail names that blocked
    details: dict = field(default_factory=dict)
    checks: dict = field(default_factory=dict)


@dataclass
class Decision:
    ticket_id: str
    route: Route
    reasons: list
    intent: Prediction | None = None
    urgency: Prediction | None = None
    answerability: Prediction | None = None
    passages: list = field(default_factory=list)
    supporting_passages: list = field(default_factory=list)
    evidence: EvidenceAssessment | None = None
    draft: Draft | None = None
    guardrails: GuardrailResult | None = None
    channel: str | None = None
    customer_tier: str | None = None
    customer_region: str | None = None
    language_fluency: str | None = None
    trace: dict = field(default_factory=dict)
    stage_latency_s: dict = field(default_factory=dict)
    total_latency_s: float = 0.0
    error: str | None = None
    config_fingerprint: str = ""
    run_id: str | None = None
    decision_timestamp: str | None = None

    def to_dict(self) -> dict:
        def conv(o):
            if isinstance(o, Enum):
                return o.value
            if isinstance(o, dict):
                return {k: conv(v) for k, v in o.items()}
            if isinstance(o, (list, tuple)):
                return [conv(v) for v in o]
            return o
        return cast(dict[str, Any], conv(asdict(self)))
