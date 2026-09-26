"""Deterministic, evidence-driven router (A5).

Every gate is evaluated (not short-circuited) so the decision log records
*all* reasons a ticket escalated. AUTO requires every gate to pass AND
customer release to be explicitly authorised in config."""
from __future__ import annotations

import re

from .schemas import (Eligibility, EvidenceAssessment, GuardrailResult,
                      Passage, Prediction, Route)

_SAFETY = re.compile(r"\b(lawsuit|lawyer|legal action|breach|hacked|compromised|"
                     r"gdpr request|delete (all )?my data|chargeback|fraud)\b", re.I)


def route(text: str, intent: Prediction, urgency: Prediction, passages: list[Passage],
          evidence: EvidenceAssessment, guardrails: GuardrailResult | None,
          settings, retrieval_threshold: float | None = None) -> tuple[Route, list[str]]:
    reasons: list[str] = []
    thr = settings.retrieval_score_threshold if retrieval_threshold is None else retrieval_threshold
    if intent.label in settings.never_automate_intents:
        reasons.append("never_automate_intent")
    if intent.label not in settings.auto_eligible_intents:
        reasons.append("intent_not_auto_eligible")
    if intent.confidence < settings.intent_confidence_threshold:
        reasons.append("intent_below_confidence_threshold")
    if not passages or passages[0].score < thr:
        reasons.append("no_retrieval_above_threshold")
    if _SAFETY.search(text):
        reasons.append("safety_keyword")
    if (urgency.label in ("high", "critical") and
            intent.label in getattr(settings, "urgent_operational_intents", ())):
        reasons.append("urgent_operational_intent")
    if evidence.status != Eligibility.SELF_SERVICE_CANDIDATE:
        reasons.append(f"eligibility_{evidence.status.value.lower()}")
    if evidence.sufficient is not True:
        reasons.append("evidence_sufficiency_not_established")
    if guardrails is not None and not guardrails.passed:
        reasons.append("guardrail_blocked")
    if not settings.customer_release_authorized:
        reasons.append("customer_release_not_authorized")
    return (Route.ESCALATE, reasons) if reasons else (Route.AUTO_RESPOND, ["all_gates_passed"])
