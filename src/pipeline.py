"""Ticket -> Ingest -> Classify -> Retrieve -> Assess -> Generate ->
Guardrails -> Route -> Audit. Every failure path terminates in a logged
ESCALATE (A11)."""
from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path

from . import eligibility, generate as gen, guardrails, monitoring, router
from .audit import AuditError, AuditStore
from .classify import TicketClassifier
from .config import Settings, get_settings
from .ingest import IngestError, normalize
from .retrieve import Retriever, load_kb
from .schemas import Decision, Prediction, Route


class Pipeline:
    def __init__(self, classifier: TicketClassifier, retriever: Retriever,
                 audit: AuditStore, settings: Settings | None = None,
                 provider: gen.Provider | None = None):
        self.settings = settings or get_settings()
        self.classifier = classifier
        self.retriever = retriever
        self.audit = audit
        self.provider = provider
        self._emergency_disabled = False
        self.retrieval_threshold = self.settings.retrieval_threshold_for(
            retriever.backend_name)
        self.fingerprint = hashlib.sha256(
            f"{self.settings.fingerprint()}|{retriever.backend_name}".encode()).hexdigest()

    @classmethod
    def from_settings(cls, settings: Settings | None = None, **kw) -> "Pipeline":
        s = settings or get_settings()
        clf = TicketClassifier.load(Path(s.artifacts_dir))
        ret = Retriever(load_kb(s.kb_path), s.embedding_model, s.allow_tfidf_fallback,
                        backend=kw.pop("retrieval_backend", None) or s.retrieval_backend)
        return cls(clf, ret, AuditStore(s.db_path), s, **kw)

    @property
    def emergency_disabled(self) -> bool:
        return self._emergency_disabled

    def emergency_disable_auto_response(self) -> None:
        """One-way in-process kill switch for all subsequent tickets."""
        self._emergency_disabled = True

    def _escalate(self, tid, reason, t0, stages, err=None, **extra) -> Decision:
        return Decision(ticket_id=tid, route=Route.ESCALATE, reasons=[reason],
                        error=err, stage_latency_s=stages,
                        total_latency_s=round(time.perf_counter() - t0, 6),
                        config_fingerprint=self.fingerprint, **extra)

    def _evidence_ambiguous(self, passages) -> bool:
        """Fail closed when symptom evidence dominates resolution evidence."""
        if not passages:
            return True

        def passage_score(p) -> float:
            if isinstance(p, dict):
                value = p.get("score", 0.0)
            else:
                value = getattr(p, "score", 0.0)
            return float(value or 0.0)

        def passage_section(p) -> str:
            if isinstance(p, dict):
                value = p.get("section", "")
            else:
                value = getattr(p, "section", "")
            return str(value or "").strip().lower()

        top = max(passages, key=passage_score)

        top_score = passage_score(top)
        top_section = passage_section(top)

        best_resolution = 0.0
        best_symptoms = 0.0

        for passage in passages:
            score = passage_score(passage)
            section = passage_section(passage)

            if section == "resolution":
                best_resolution = max(
                    best_resolution,
                    score,
                )

            if section == "symptoms":
                best_symptoms = max(
                    best_symptoms,
                    score,
                )

        resolution_ratio = (
            best_resolution / top_score
            if top_score > 0
            else 0.0
        )

        symptom_margin = (
            best_symptoms - best_resolution
        )

        return (
            top_section == "symptoms"
            and resolution_ratio
            < self.settings.evidence_resolution_ratio_min
            and symptom_margin
            > self.settings.evidence_symptom_margin_max
        )

    def process(self, raw: dict, run_id: str | None = None,
                run_mode: str = "normal") -> Decision:
        t0 = time.perf_counter()
        stages: dict[str, float] = {}
        tid = str((raw or {}).get("ticket_id") or (raw or {}).get("id") or "UNKNOWN") \
            if isinstance(raw, dict) else "UNKNOWN"

        def lap(name, start):
            stages[name] = round(time.perf_counter() - start, 6)

        try:
            s = time.perf_counter()
            try:
                ticket = normalize(raw)
            except IngestError as e:
                lap("ingest", s)
                d = self._escalate(tid, "malformed_input", t0, stages, f"IngestError:{e}")
                return self._finalise(d, run_id, run_mode)
            lap("ingest", s)

            s = time.perf_counter()
            classification_failed = False
            try:
                intent, urgency, answerability = self.classifier.classify_with_answerability(
                    ticket.text)
            except Exception:
                classification_failed = True
                intent = Prediction("UNCLASSIFIED", 0.0, [])
                urgency = Prediction("UNKNOWN", 0.0, [])
                answerability = Prediction("UNKNOWN", 0.0, [])
            lap("classify", s)

            s = time.perf_counter()
            try:
                passages = self.retriever.search(ticket.text, self.settings.top_k,
                                                  self.retrieval_threshold)
            except Exception as e:
                lap("retrieve", s)
                d = self._escalate(ticket.ticket_id, "retrieval_failure", t0, stages,
                                   f"RetrievalError:{e}", intent=intent, urgency=urgency,
                                   channel=ticket.channel.value,
                                   customer_tier=ticket.customer_tier)
                return self._finalise(d, run_id, run_mode)
            lap("retrieve", s)

            s = time.perf_counter()
            resolution_passages = (self.retriever.passages_for(
                passages[0].doc_id, "resolution") if passages else [])
            context_passages = (self.retriever.passages_for(
                passages[0].doc_id, "common causes") if passages else [])
            supporting_passages = []
            seen_citations = set()
            for passage in passages + context_passages + resolution_passages:
                if passage.citation not in seen_citations:
                    supporting_passages.append(passage)
                    seen_citations.add(passage.citation)
            evidence = eligibility.assess(ticket.text, ticket.customer_tier, intent, urgency,
                                          passages, self.retrieval_threshold,
                                          self.settings.eligibility_policy,
                                          resolution_passages,
                                          self.settings.urgent_operational_intents,
                                          answerability,
                                          self.settings.answerability_confidence_threshold)
            lap("assess", s)

            s = time.perf_counter()
            draft, perr = None, None
            if passages and passages[0].score >= self.retrieval_threshold:
                draft, perr = gen.generate(ticket.text, passages, resolution_passages, self.provider,
                                           self.settings.provider_timeout_s,
                                           self.settings.prompt_version, context_passages)
            lap("generate", s)

            s = time.perf_counter()
            g = None
            if draft is not None:
                g = guardrails.check(ticket.text, draft, supporting_passages)
            lap("guardrails", s)

            decision_route, reasons = router.route(ticket.text, intent, urgency, passages,
                                                   evidence, g, self.settings,
                                                   self.retrieval_threshold)
            if perr:
                reasons.append(f"provider_fallback:{perr}")
            if classification_failed:
                reasons.append("classification_failure")
                decision_route = Route.ESCALATE
            if (
                decision_route is Route.AUTO_RESPOND
                and self._evidence_ambiguous(passages)
            ):
                decision_route = Route.ESCALATE
                reasons.append(
                    "evidence_ambiguity_review_required"
                )

            if self._emergency_disabled and decision_route is Route.AUTO_RESPOND:
                decision_route = Route.ESCALATE
                reasons.append("emergency_auto_response_disabled")
            d = Decision(ticket_id=ticket.ticket_id, route=decision_route, reasons=reasons,
                         intent=intent, urgency=urgency, answerability=answerability,
                         passages=passages, supporting_passages=supporting_passages,
                         evidence=evidence, draft=draft, guardrails=g,
                         channel=ticket.channel.value, customer_tier=ticket.customer_tier,
                         customer_region=ticket.metadata.get("customer_region"),
                         language_fluency=ticket.metadata.get("language_fluency"),
                         trace={
                             "requirement_ids": ["A2", "A3", "A4", "A5", "A6", "A7", "A8"],
                             "prompt_version": self.settings.prompt_version,
                             "eligibility_policy": self.settings.eligibility_policy,
                             "intent_threshold": self.settings.intent_confidence_threshold,
                             "answerability_threshold": self.settings.answerability_confidence_threshold,
                             "auto_eligible_intents": list(self.settings.auto_eligible_intents),
                             "evidence_resolution_ratio_min": self.settings.evidence_resolution_ratio_min,
                             "evidence_symptom_margin_max": self.settings.evidence_symptom_margin_max,
                             "retrieval_threshold": self.retrieval_threshold,
                             "retrieval_backend": self.retriever.backend_name,
                             "retrieval_configuration": self.settings.retrieval_configuration,
                             "input_sha256": hashlib.sha256(ticket.text.encode("utf-8")).hexdigest(),
                         },
                         stage_latency_s=stages,
                         total_latency_s=round(time.perf_counter() - t0, 6),
                         error=perr, config_fingerprint=self.fingerprint)
            if d.draft is not None:
                d.draft.internal_only = decision_route is not Route.AUTO_RESPOND
            return self._finalise(d, run_id, run_mode)
        except Exception as e:  # last-resort fail-closed
            d = self._escalate(tid, "unhandled_error", t0, stages,
                               f"{type(e).__name__}:{e}")
            return self._finalise(d, run_id, run_mode)

    def _finalise(self, d: Decision, run_id: str | None,
                  run_mode: str = "normal") -> Decision:
        d.run_id = run_id
        d.run_mode = run_mode if run_mode in {"normal", "demo", "evaluator"} else "normal"
        d.decision_timestamp = datetime.now(timezone.utc).isoformat()
        payload = d.to_dict()
        try:
            self.audit.log_decision(payload, run_id)
        except AuditError as e:
            d.route = Route.ESCALATE
            if "audit_store_failure" not in d.reasons:
                d.reasons.append("audit_store_failure")
            d.error = f"AuditError:{e}"
            if d.draft is not None:
                d.draft.internal_only = True
            payload = d.to_dict()
            try:
                self.audit.write_fallback(payload)
            except Exception:
                pass
        monitoring.observe(payload, d.run_mode)
        return d
