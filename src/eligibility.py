"""Evidence eligibility (diagnostic only).

Answers: 'from the ticket and retrieved docs alone, is there a
resolution-complete, plan-applicable passage?' A true `sufficient` value records
that evidence result only; it never asserts customer-release authority, which
is enforced independently by the router."""
from __future__ import annotations

import re

from .schemas import Eligibility, EvidenceAssessment, Passage, Prediction

# Requests whose resolution needs live account/operational state the KB cannot hold.
_STATEFUL = re.compile(
    r"\b(my (invoice|account|bill|charge|order|instance|cluster)|refund|charged twice|"
    r"still down|right now|currently down|since (this|yesterday)|ticket #?\d+)\b", re.I)
_RESOLUTION = re.compile(r"^(resolution|fix|steps|how to)", re.I)


def assess(ticket_text: str, tier: str, intent: Prediction, urgency: Prediction,
           passages: list[Passage], retrieval_threshold: float,
           policy: str, resolution_passages: list[Passage] | None = None,
           urgent_operational_intents: tuple = (),
           answerability: Prediction | None = None,
           answerability_threshold: float = 0.0) -> EvidenceAssessment:
    flags: list[str] = []
    if not passages or passages[0].score < retrieval_threshold:
        return EvidenceAssessment(Eligibility.UNKNOWN, None, None,
                                  ["no_relevant_evidence"], policy)

    top_doc = passages[0].doc_id
    doc_passages = [p for p in passages if p.doc_id == top_doc]
    has_resolution = bool(resolution_passages) or any(
        _RESOLUTION.match(p.section) for p in doc_passages)
    if not has_resolution:
        flags.append("symptom_only_evidence")

    plans = passages[0].plans
    plan_ok = None if not plans or tier == "unknown" else (tier in plans)
    if plan_ok is False:
        return EvidenceAssessment(Eligibility.PLAN_INAPPLICABLE, None, False,
                                  flags + ["plan_mismatch"], policy)

    if _STATEFUL.search(ticket_text):
        flags.append("requires_account_state")
    if answerability is not None and (answerability.label != "answerable" or
                                      answerability.confidence < answerability_threshold):
        flags.append("answerability_not_established")
    if (urgency.label in ("high", "critical") and
            intent.label in urgent_operational_intents):
        flags.append("urgent_operational_state")

    status = (Eligibility.SELF_SERVICE_CANDIDATE if not flags
              else Eligibility.REVIEW_REQUIRED)
    sufficient = status is Eligibility.SELF_SERVICE_CANDIDATE and has_resolution
    return EvidenceAssessment(status, sufficient, plan_ok, flags, policy)
