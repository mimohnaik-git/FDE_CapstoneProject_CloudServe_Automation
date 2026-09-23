"""Deterministic blocking guardrails for generated customer responses."""

from __future__ import annotations

import math
import re
from collections import OrderedDict
from typing import Any, Dict, List, Mapping, Optional, Sequence


GUARDRAIL_GENERATION = "GenerationValidityGuardrail"
GUARDRAIL_PRIVATE_DATA = "PrivateDataGuardrail"
GUARDRAIL_GROUNDING = "GroundingGuardrail"
GUARDRAIL_CITATION = "CitationIntegrityGuardrail"
GUARDRAIL_PROMPT_INJECTION = "PromptInjectionGuardrail"
GUARDRAIL_UNSUPPORTED_COMMITMENT = "UnsupportedCommitmentsGuardrail"
GUARDRAIL_CONFIDENCE = "ConfidenceGuardrail"

ACTION_PROCEED = "PROCEED"
ACTION_BLOCK = "BLOCK"

REASON_PRIVATE_DATA_LEAK = "PRIVATE_DATA_LEAK"
REASON_SECRET_DISCLOSURE = "SECRET_DISCLOSURE"
REASON_GROUNDING_FAILURE = "GROUNDING_FAILURE"
REASON_UNSUPPORTED_CITATION = "UNSUPPORTED_CITATION"
REASON_PROMPT_INJECTION = "PROMPT_INJECTION"
REASON_SYSTEM_PROMPT_DISCLOSURE = "SYSTEM_PROMPT_DISCLOSURE"
REASON_UNSUPPORTED_COMMITMENT = "UNSUPPORTED_COMMITMENT"
REASON_INVALID_GENERATION = "INVALID_GENERATION"
REASON_MISSING_EVIDENCE = "MISSING_EVIDENCE"
REASON_CONFIDENCE_FAILURE = "CONFIDENCE_FAILURE"
REASON_GUARDRAIL_INTERNAL_ERROR = "GUARDRAIL_INTERNAL_ERROR"

REASON_MESSAGES = {
    REASON_PRIVATE_DATA_LEAK: "Response contains likely protected customer or payment data.",
    REASON_SECRET_DISCLOSURE: "Response contains a likely credential, token, or secret.",
    REASON_GROUNDING_FAILURE: "Response grounding could not be established from cited evidence.",
    REASON_UNSUPPORTED_CITATION: "A response citation or external source does not resolve to retrieved evidence.",
    REASON_PROMPT_INJECTION: "Untrusted customer instructions attempt to override application authority.",
    REASON_SYSTEM_PROMPT_DISCLOSURE: "Response appears to expose protected instructions or internal control metadata.",
    REASON_UNSUPPORTED_COMMITMENT: "Response makes an unsupported customer commitment.",
    REASON_INVALID_GENERATION: "Generation result is malformed or not releasable.",
    REASON_MISSING_EVIDENCE: "No valid retrieved evidence is available for grounding validation.",
    REASON_CONFIDENCE_FAILURE: "Required confidence state is missing, invalid, or below the configured floor.",
    REASON_GUARDRAIL_INTERNAL_ERROR: "The guardrail subsystem failed internally and blocked the response.",
}

_SECRET_PATTERNS = (
    ("openai_style_key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("bearer_token", re.compile(r"\bBearer\s+[A-Za-z0-9._~-]{16,}\b", re.I)),
    ("api_key_assignment", re.compile(r"\bapi[_ -]?key\s*[:=]\s*[\"']?[^\s\"']{8,}", re.I)),
    ("password_assignment", re.compile(r"\bpassword\s*[:=]\s*[\"']?[^\s\"']{6,}", re.I)),
    ("secret_assignment", re.compile(r"\bsecret(?:_key)?\s*[:=]\s*[\"']?[^\s\"']{8,}", re.I)),
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", re.I)),
)

_PRIVATE_DATA_PATTERNS = (
    ("payment_card", re.compile(r"\b(?:\d[ -]?){15,16}\b")),
    ("customer_identifier", re.compile(r"\bCUST-[A-Z0-9-]{3,}\b", re.I)),
    (
        "account_identifier",
        re.compile(r"\baccount\s+(?:id|number)\s*[:#=]\s*[A-Z0-9-]{4,}\b", re.I),
    ),
    (
        "other_customer_marker",
        re.compile(r"\b(?:another|other)\s+customer(?:'s)?\s+(?:data|email|address|account|name|identifier)\b", re.I),
    ),
)

_INPUT_INJECTION_PATTERNS = (
    re.compile(r"\bignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions?\b", re.I),
    re.compile(r"\bdisregard\s+(?:all\s+)?(?:instructions?|rules?)\b", re.I),
    re.compile(r"\breveal\s+(?:your\s+|the\s+)?(?:system\s+)?prompt\b", re.I),
    re.compile(r"\banswer\s+from\s+(?:memory|your\s+training)\b", re.I),
    re.compile(r"\bpretend\s+(?:the\s+)?documentation\s+says\b", re.I),
    re.compile(r"\bcite\s+(?:a\s+)?document\s+(?:that\s+was\s+not|not)\s+retrieved\b", re.I),
    re.compile(r"\b(?:jailbreak|DAN\s+mode)\b", re.I),
)

_OUTPUT_INSTRUCTION_PATTERNS = (
    re.compile(r"\bignore\s+(?:all\s+)?(?:previous|prior|system)\s+instructions?\b", re.I),
    re.compile(r"\bcustomer\s+instructions?\s+(?:override|outrank)\b", re.I),
)

_SYSTEM_DISCLOSURE_PATTERNS = (
    re.compile(r"\b(?:my|the)\s+system\s+prompt\b", re.I),
    re.compile(r"\b(?:hidden|internal)\s+(?:instructions?|prompt|policy\s+text)\b", re.I),
    re.compile(r"\b(?:chain[- ]of[- ]thought|developer\s+message)\b", re.I),
    re.compile(r"\b(?:routing\s+threshold|guardrail\s+configuration|SYSTEM AUTHORITY)\b", re.I),
)

_COMMITMENT_PATTERNS = (
    re.compile(r"\b(?:we|i)\s+(?:will|shall)\s+(?:refund|credit|compensate|reimburse)\b", re.I),
    re.compile(r"\b(?:we|i)\s+(?:will|shall)\s+(?:issue|provide|apply|guarantee|promise)\s+(?:a\s+)?(?:refund|credit|compensation|exception)\b", re.I),
    re.compile(r"\b(?:refund|credit|compensation)\s+(?:has been|will be|is)\s+(?:issued|applied|provided|guaranteed)\b", re.I),
    re.compile(r"\b(?:we|i)\s+(?:guarantee|promise)\b", re.I),
    re.compile(r"\b(?:guaranteed?|promise[ds]?)\s+(?:uptime|resolution|delivery|refund|credit)\b", re.I),
    re.compile(r"\b(?:roadmap|feature|fix|release)\s+(?:will|shall)\s+(?:ship|launch|arrive|be available)\b", re.I),
    re.compile(r"\bwill\s+be\s+available\s+by\b", re.I),
    re.compile(r"\b(?:policy|SLA|contractual)\s+exception\s+(?:is|has been|will be)\s+(?:approved|granted|made)\b", re.I),
)

_DOC_ID_PATTERN = re.compile(r"\bDOC-[A-Z0-9]+-[0-9]+\b")
_URL_PATTERN = re.compile(r"https?://[^\s<>\"]+|www\.[^\s<>\"]+", re.I)
_WORD_PATTERN = re.compile(r"[a-z0-9]{3,}", re.I)
_STOP_WORDS = frozenset(
    {
        "and", "are", "based", "can", "for", "from", "has", "have", "here", "into",
        "our", "that", "the", "their", "this", "was", "were", "will", "with", "you", "your",
    }
)


def _check_result(
    *,
    name: str,
    key: str,
    reason_code: Optional[str] = None,
    detail: str = "",
    evidence: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    blocked = reason_code is not None
    return {
        "name": name,
        "key": key,
        "passed": not blocked,
        "blocked": blocked,
        "reason_code": reason_code,
        "detail": detail,
        "evidence": evidence or [],
    }


def _response_text(payload: Mapping[str, Any]) -> str:
    value = payload.get("response_text", payload.get("answer", ""))
    return value if isinstance(value, str) else ""


def _retrieval_pairs(retrieval_results: Any) -> Dict[tuple[str, str], str]:
    """Return every authoritative passage that generation is allowed to cite."""
    pairs: Dict[tuple[str, str], str] = {}

    if (
        not isinstance(retrieval_results, Sequence)
        or isinstance(retrieval_results, (str, bytes))
    ):
        return pairs

    for item in retrieval_results:
        if not isinstance(item, Mapping):
            continue

        document_id = item.get("document_id") or item.get("doc_id")
        chunk_id = item.get("chunk_id")
        passage = item.get("passage") or item.get("chunk_content")

        if all(
            isinstance(value, str) and value.strip()
            for value in (document_id, chunk_id, passage)
        ):
            document_id = document_id.strip()
            pairs[(document_id, chunk_id.strip())] = passage.strip()
        else:
            document_id = None

        supporting = item.get("supporting_passages")

        if not isinstance(supporting, list) or not document_id:
            continue

        for support in supporting:
            if not isinstance(support, Mapping):
                continue

            support_document_id = support.get("document_id")
            support_chunk_id = support.get("chunk_id")
            support_passage = (
                support.get("passage")
                or support.get("chunk_content")
            )

            if not all(
                isinstance(value, str) and value.strip()
                for value in (
                    support_document_id,
                    support_chunk_id,
                    support_passage,
                )
            ):
                continue

            # Supporting evidence is valid only inside its parent
            # authoritative document.
            if support_document_id.strip() != document_id:
                continue

            pairs[
                (
                    support_document_id.strip(),
                    support_chunk_id.strip(),
                )
            ] = support_passage.strip()

    return pairs

def _cited_passages(
    payload: Mapping[str, Any],
    retrieval_results: Any,
) -> List[str]:
    pairs = _retrieval_pairs(retrieval_results)
    citations = payload.get("citations")
    if not isinstance(citations, list):
        return []
    passages: List[str] = []
    for citation in citations:
        if not isinstance(citation, Mapping):
            continue
        pair = (citation.get("document_id"), citation.get("chunk_id"))
        if pair in pairs:
            passages.append(pairs[pair])
    return passages


class BaseGuardrail:
    name = "BaseGuardrail"
    key = "base"

    def check(
        self,
        payload: Mapping[str, Any],
        retrieval_results: Optional[Sequence[Mapping[str, Any]]] = None,
    ) -> Dict[str, Any]:
        raise NotImplementedError


class GenerationValidityGuardrail(BaseGuardrail):
    name = GUARDRAIL_GENERATION
    key = "generation_validity"

    def check(self, payload, retrieval_results=None):
        if payload.get("_generation_is_mapping") is not True:
            return _check_result(
                name=self.name, key=self.key, reason_code=REASON_INVALID_GENERATION,
                detail="Generation result is not a mapping.",
            )
        text = payload.get("response_text", payload.get("answer"))
        citations = payload.get("citations")
        if (
            payload.get("supported") is not True
            or payload.get("grounded") is not True
            or not isinstance(text, str)
            or not text.strip()
            or not isinstance(citations, list)
        ):
            return _check_result(
                name=self.name, key=self.key, reason_code=REASON_INVALID_GENERATION,
                detail="Generation must be supported, grounded, non-empty, and contain a citation list.",
            )
        return _check_result(name=self.name, key=self.key)


class PrivateDataGuardrail(BaseGuardrail):
    name = GUARDRAIL_PRIVATE_DATA
    key = "private_data"

    def check(self, payload, retrieval_results=None):
        text = _response_text(payload)
        for label, pattern in _SECRET_PATTERNS:
            if pattern.search(text):
                return _check_result(
                    name=self.name, key=self.key, reason_code=REASON_SECRET_DISCLOSURE,
                    detail=REASON_MESSAGES[REASON_SECRET_DISCLOSURE],
                    evidence=[{"detector": label}],
                )
        for label, pattern in _PRIVATE_DATA_PATTERNS:
            if pattern.search(text):
                return _check_result(
                    name=self.name, key=self.key, reason_code=REASON_PRIVATE_DATA_LEAK,
                    detail=REASON_MESSAGES[REASON_PRIVATE_DATA_LEAK],
                    evidence=[{"detector": label}],
                )
        return _check_result(name=self.name, key=self.key)


class GroundingGuardrail(BaseGuardrail):
    name = GUARDRAIL_GROUNDING
    key = "grounding"

    def check(self, payload, retrieval_results=None):
        pairs = _retrieval_pairs(retrieval_results)
        if not pairs:
            return _check_result(
                name=self.name, key=self.key, reason_code=REASON_MISSING_EVIDENCE,
                detail=REASON_MESSAGES[REASON_MISSING_EVIDENCE],
            )
        if payload.get("supported") is not True or payload.get("grounded") is not True:
            return _check_result(
                name=self.name, key=self.key, reason_code=REASON_GROUNDING_FAILURE,
                detail=REASON_MESSAGES[REASON_GROUNDING_FAILURE],
            )

        text = _response_text(payload)
        answer_tokens = {
            token.lower() for token in _WORD_PATTERN.findall(text)
            if token.lower() not in _STOP_WORDS
        }
        cited_passages = _cited_passages(payload, retrieval_results)
        evidence_tokens = {
            token.lower() for passage in cited_passages for token in _WORD_PATTERN.findall(passage)
            if token.lower() not in _STOP_WORDS
        }
        overlap = len(answer_tokens & evidence_tokens) / len(answer_tokens) if answer_tokens else 0.0
        if len(answer_tokens) >= 4 and overlap < 0.20:
            return _check_result(
                name=self.name, key=self.key, reason_code=REASON_GROUNDING_FAILURE,
                detail="Response has insufficient lexical support in retrieved passages.",
                evidence=[{"token_overlap_ratio": round(overlap, 6), "minimum": 0.20}],
            )
        return _check_result(
            name=self.name,
            key=self.key,
            evidence=[{"token_overlap_ratio": round(overlap, 6), "minimum": 0.20}],
        )


class CitationIntegrityGuardrail(BaseGuardrail):
    name = GUARDRAIL_CITATION
    key = "citation_integrity"

    def check(self, payload, retrieval_results=None):
        pairs = _retrieval_pairs(retrieval_results)
        citations = payload.get("citations")
        if not pairs:
            return _check_result(
                name=self.name, key=self.key, reason_code=REASON_MISSING_EVIDENCE,
                detail=REASON_MESSAGES[REASON_MISSING_EVIDENCE],
            )
        if not isinstance(citations, list) or not citations:
            return _check_result(
                name=self.name, key=self.key, reason_code=REASON_UNSUPPORTED_CITATION,
                detail="Supported response has no structured citation.",
            )

        cited_pairs: List[tuple[str, str]] = []
        for citation in citations:
            if not isinstance(citation, Mapping):
                return _check_result(
                    name=self.name, key=self.key, reason_code=REASON_UNSUPPORTED_CITATION,
                    detail="Citation is not a structured document/chunk pair.",
                )
            document_id = citation.get("document_id")
            chunk_id = citation.get("chunk_id")
            if not isinstance(document_id, str) or not isinstance(chunk_id, str):
                return _check_result(
                    name=self.name, key=self.key, reason_code=REASON_UNSUPPORTED_CITATION,
                    detail="Citation has missing or invalid identity fields.",
                )
            pair = (document_id.strip(), chunk_id.strip())
            if pair not in pairs:
                return _check_result(
                    name=self.name, key=self.key, reason_code=REASON_UNSUPPORTED_CITATION,
                    detail="Citation pair does not exist in retrieved evidence.",
                    evidence=[{"document_id": pair[0], "chunk_id": pair[1]}],
                )
            cited_pairs.append(pair)

        text = _response_text(payload)
        allowed_document_ids = {document_id for document_id, _ in pairs}
        unsupported_ids = sorted(set(_DOC_ID_PATTERN.findall(text)) - allowed_document_ids)
        if unsupported_ids:
            return _check_result(
                name=self.name, key=self.key, reason_code=REASON_UNSUPPORTED_CITATION,
                detail="Response text references a document that was not retrieved.",
                evidence=[{"unsupported_document_ids": unsupported_ids}],
            )

        evidence_text = "\n".join(pairs.values())
        unsupported_urls = sorted(
            {
                url.rstrip(".,);]")
                for url in _URL_PATTERN.findall(text)
                if url.rstrip(".,);]") not in evidence_text
            }
        )
        if unsupported_urls:
            return _check_result(
                name=self.name, key=self.key, reason_code=REASON_UNSUPPORTED_CITATION,
                detail="Response contains an external source URL absent from retrieved evidence.",
                evidence=[{"unsupported_url_count": len(unsupported_urls)}],
            )
        return _check_result(
            name=self.name,
            key=self.key,
            evidence=[{"validated_citation_count": len(cited_pairs)}],
        )


class PromptInjectionGuardrail(BaseGuardrail):
    name = GUARDRAIL_PROMPT_INJECTION
    key = "instruction_integrity"

    def check(self, payload, retrieval_results=None):
        ticket_content = payload.get("_ticket_content", "")
        if isinstance(ticket_content, str):
            for pattern in _INPUT_INJECTION_PATTERNS:
                if pattern.search(ticket_content):
                    return _check_result(
                        name=self.name, key=self.key, reason_code=REASON_PROMPT_INJECTION,
                        detail=REASON_MESSAGES[REASON_PROMPT_INJECTION],
                        evidence=[{"source": "customer_input"}],
                    )

        text = _response_text(payload)
        for pattern in _SYSTEM_DISCLOSURE_PATTERNS:
            if pattern.search(text):
                return _check_result(
                    name=self.name, key=self.key, reason_code=REASON_SYSTEM_PROMPT_DISCLOSURE,
                    detail=REASON_MESSAGES[REASON_SYSTEM_PROMPT_DISCLOSURE],
                    evidence=[{"source": "generated_response"}],
                )
        for pattern in _OUTPUT_INSTRUCTION_PATTERNS:
            if pattern.search(text):
                return _check_result(
                    name=self.name, key=self.key, reason_code=REASON_PROMPT_INJECTION,
                    detail="Response appears to comply with an instruction override.",
                    evidence=[{"source": "generated_response"}],
                )
        return _check_result(name=self.name, key=self.key)


class UnsupportedCommitmentsGuardrail(BaseGuardrail):
    name = GUARDRAIL_UNSUPPORTED_COMMITMENT
    key = "unsupported_commitment"

    def check(self, payload, retrieval_results=None):
        text = _response_text(payload)
        evidence_text = "\n".join(_cited_passages(payload, retrieval_results))
        for pattern in _COMMITMENT_PATTERNS:
            match = pattern.search(text)
            if not match:
                continue
            sentence = self._containing_sentence(text, match.start(), match.end())
            if sentence and self._normalise(sentence) in self._normalise(evidence_text):
                continue
            return _check_result(
                name=self.name, key=self.key, reason_code=REASON_UNSUPPORTED_COMMITMENT,
                detail=REASON_MESSAGES[REASON_UNSUPPORTED_COMMITMENT],
                evidence=[{"detector": pattern.pattern}],
            )
        return _check_result(name=self.name, key=self.key)

    @staticmethod
    def _containing_sentence(text: str, start: int, end: int) -> str:
        left = max(text.rfind(".", 0, start), text.rfind("\n", 0, start))
        right_candidates = [position for position in (text.find(".", end), text.find("\n", end)) if position >= 0]
        right = min(right_candidates) if right_candidates else len(text)
        return text[left + 1:right + 1].strip()

    @staticmethod
    def _normalise(text: str) -> str:
        return " ".join(text.lower().split())


class ConfidenceGuardrail(BaseGuardrail):
    name = GUARDRAIL_CONFIDENCE
    key = "confidence"

    def __init__(self, confidence_threshold: float):
        self.confidence_threshold = confidence_threshold

    def check(self, payload, retrieval_results=None):
        classification_confidence = payload.get("_classification_confidence")
        generation_confidence = payload.get("confidence")
        values = {
            "classification_confidence": classification_confidence,
            "generation_confidence": generation_confidence,
        }
        for label, value in values.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return _check_result(
                    name=self.name, key=self.key, reason_code=REASON_CONFIDENCE_FAILURE,
                    detail=f"{label} is missing or non-numeric.",
                    evidence=[{"field": label}],
                )
            numeric = float(value)
            if not math.isfinite(numeric) or not 0.0 <= numeric <= 1.0:
                return _check_result(
                    name=self.name, key=self.key, reason_code=REASON_CONFIDENCE_FAILURE,
                    detail=f"{label} is outside the valid probability range.",
                    evidence=[{"field": label}],
                )
        if float(classification_confidence) < self.confidence_threshold:
            return _check_result(
                name=self.name, key=self.key, reason_code=REASON_CONFIDENCE_FAILURE,
                detail="Classification confidence is below the configured downstream safety floor.",
                evidence=[
                    {
                        "classification_confidence": float(classification_confidence),
                        "threshold": self.confidence_threshold,
                    }
                ],
            )
        return _check_result(
            name=self.name,
            key=self.key,
            evidence=[
                {
                    "classification_confidence": float(classification_confidence),
                    "generation_confidence": float(generation_confidence),
                    "threshold": self.confidence_threshold,
                }
            ],
        )


class GuardrailEngine:
    """Run every guardrail deterministically and fail closed on internal errors."""

    def __init__(
        self,
        confidence_threshold: float = 0.80,
        guardrails: Optional[List[BaseGuardrail]] = None,
    ):
        if (
            isinstance(confidence_threshold, bool)
            or not isinstance(confidence_threshold, (int, float))
            or not math.isfinite(float(confidence_threshold))
            or not 0.0 <= float(confidence_threshold) <= 1.0
        ):
            raise ValueError(
                "GUARDRAIL CONFIG ERROR: confidence_threshold must be finite and in [0.0, 1.0]."
            )
        self.confidence_threshold = float(confidence_threshold)
        self.guardrails = guardrails or [
            GenerationValidityGuardrail(),
            PrivateDataGuardrail(),
            GroundingGuardrail(),
            CitationIntegrityGuardrail(),
            PromptInjectionGuardrail(),
            UnsupportedCommitmentsGuardrail(),
            ConfidenceGuardrail(self.confidence_threshold),
        ]

    def check_input(self, normalized_ticket: Mapping[str, Any]) -> Dict[str, Any]:
        """Validate untrusted ticket instructions before retrieval or generation."""

        ticket_content = (
            normalized_ticket.get("raw_content", "")
            if isinstance(normalized_ticket, Mapping)
            else ""
        )
        payload = {"_ticket_content": ticket_content}
        return self._run_checks(payload, [], [PromptInjectionGuardrail()])

    def check(
        self,
        generated_response: Any,
        classification: Mapping[str, Any],
        normalized_ticket: Mapping[str, Any],
        retrieval_results: Optional[Sequence[Mapping[str, Any]]] = None,
    ) -> Dict[str, Any]:
        payload = dict(generated_response) if isinstance(generated_response, Mapping) else {}
        payload["_generation_is_mapping"] = isinstance(generated_response, Mapping)
        payload["_classification_confidence"] = (
            classification.get("confidence") if isinstance(classification, Mapping) else None
        )
        payload["_ticket_content"] = (
            normalized_ticket.get("raw_content", "")
            if isinstance(normalized_ticket, Mapping)
            else ""
        )
        return self._run_checks(payload, retrieval_results or [], self.guardrails)

    def validate_response(
        self,
        response: Any,
        retrieval_results: Optional[Sequence[Mapping[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Compatibility interface using response confidence as prerequisite confidence."""

        payload = dict(response) if isinstance(response, Mapping) else {}
        payload["_generation_is_mapping"] = isinstance(response, Mapping)
        payload["_classification_confidence"] = payload.get("confidence")
        payload["_ticket_content"] = payload.get("raw_content", payload.get("ticket_content", ""))
        return self._run_checks(payload, retrieval_results or [], self.guardrails)

    def _run_checks(
        self,
        payload: Mapping[str, Any],
        retrieval_results: Sequence[Mapping[str, Any]],
        guardrails: Sequence[BaseGuardrail],
    ) -> Dict[str, Any]:
        checks: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
        for index, guardrail in enumerate(guardrails):
            key = guardrail.key
            if key in checks:
                key = f"{key}_{index}"
            try:
                result = guardrail.check(payload, retrieval_results)
                if (
                    not isinstance(result, Mapping)
                    or result.get("blocked") not in (True, False)
                    or result.get("passed") is result.get("blocked")
                ):
                    raise ValueError("Guardrail returned an invalid result")
                checks[key] = dict(result)
            except Exception as exc:
                checks[key] = _check_result(
                    name=getattr(guardrail, "name", type(guardrail).__name__),
                    key=key,
                    reason_code=REASON_GUARDRAIL_INTERNAL_ERROR,
                    detail=REASON_MESSAGES[REASON_GUARDRAIL_INTERNAL_ERROR],
                    evidence=[{"error_type": type(exc).__name__}],
                )
        return self._aggregate(checks)

    @classmethod
    def internal_error_result(cls, exc: Exception) -> Dict[str, Any]:
        """Build a safe block result when the engine boundary itself raises."""

        check = _check_result(
            name="GuardrailEngine",
            key="guardrail_internal_error",
            reason_code=REASON_GUARDRAIL_INTERNAL_ERROR,
            detail=REASON_MESSAGES[REASON_GUARDRAIL_INTERNAL_ERROR],
            evidence=[{"error_type": type(exc).__name__}],
        )
        return cls._aggregate(OrderedDict([("guardrail_internal_error", check)]))

    @staticmethod
    def _aggregate(checks: "OrderedDict[str, Dict[str, Any]]") -> Dict[str, Any]:
        blocked_checks = [check for check in checks.values() if check["blocked"]]
        reason_codes = list(
            dict.fromkeys(
                check["reason_code"] for check in blocked_checks if check.get("reason_code")
            )
        )
        details = [
            {
                "check": check["key"],
                "guardrail": check["name"],
                "reason_code": check["reason_code"],
                "detail": check["detail"],
                "evidence": check["evidence"],
            }
            for check in blocked_checks
        ]
        blocked = bool(blocked_checks)
        primary_reason = reason_codes[0] if reason_codes else None
        primary_detail = details[0]["detail"] if details else ""
        return {
            "passed": not blocked,
            "blocked": blocked,
            "action": ACTION_BLOCK if blocked else ACTION_PROCEED,
            "checks": dict(checks),
            "reason_codes": reason_codes,
            "primary_reason": primary_reason,
            "details": details,
            # Compatibility fields for the existing orchestrator and decision store.
            "blocked_by": [check["name"] for check in blocked_checks],
            "reasons": [detail["detail"] for detail in details],
            "checks_run": [check["name"] for check in checks.values()],
            "reason": primary_detail,
            "guardrail_triggered": [check["name"] for check in blocked_checks],
        }
