"""Grounded, provider-neutral customer response generation."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Protocol, Sequence

import requests

from src.config import settings


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROMPT_PATH = PROJECT_ROOT / "prompts" / "build" / "generation_v1.txt"
PROMPT_VERSION = "generation-v1.0.0"

GEN_SOURCE_LLM = "llm"
GEN_SOURCE_OFFLINE = "offline"
GEN_SOURCE_NO_RETRIEVAL = "no_retrieval"
GEN_SOURCE_FAILURE = "failure"

FAILURE_INSUFFICIENT_DOCUMENTATION = "INSUFFICIENT_DOCUMENTATION"
FAILURE_INVALID_PROVIDER_OUTPUT = "INVALID_PROVIDER_OUTPUT"
FAILURE_UNSUPPORTED_CITATION = "UNSUPPORTED_CITATION"
FAILURE_PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
FAILURE_PROVIDER_RATE_LIMIT = "PROVIDER_RATE_LIMIT"
FAILURE_PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
FAILURE_PROVIDER_ERROR = "PROVIDER_ERROR"
FAILURE_PROMPT_DISCLOSURE = "PROMPT_DISCLOSURE"
FAILURE_UNSUPPORTED_COMMITMENT = "UNSUPPORTED_COMMITMENT"

_PROVIDER_OUTPUT_KEYS = {"answer", "citations", "supported", "uncertainty"}
GENERATION_OUTPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["answer", "citations", "supported", "uncertainty"],
    "properties": {
        "answer": {"type": ["string", "null"]},
        "citations": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["document_id", "chunk_id"],
                "properties": {
                    "document_id": {"type": "string"},
                    "chunk_id": {"type": "string"},
                },
            },
        },
        "supported": {"type": "boolean"},
        "uncertainty": {"type": ["string", "null"]},
    },
}

_COMMITMENT_PATTERNS = (
    re.compile(r"\b(?:we|i)\s+(?:will|shall)\s+(?:issue|provide|give|apply|guarantee|promise)\b", re.I),
    re.compile(r"\b(?:we|i)\s+(?:will|shall)\s+(?:refund|credit|compensate)\b", re.I),
    re.compile(r"\b(?:we|i)\s+promise\b", re.I),
    re.compile(r"\b(?:refund|credit|compensation)\s+(?:has been|will be|is)\s+(?:issued|applied|provided|guaranteed)\b", re.I),
    re.compile(r"\b(?:guaranteed?|promise[ds]?)\s+(?:refund|credit|uptime|resolution|delivery)\b", re.I),
    re.compile(r"\b(?:roadmap|feature|fix|release)\s+(?:will|shall)\s+(?:ship|launch|arrive|be available)\b", re.I),
    re.compile(r"\b(?:sla|contractual)\s+(?:guarantee|commitment|exception)\b", re.I),
    re.compile(r"\bpolicy\s+exception\b", re.I),
)

_PROMPT_DISCLOSURE_PATTERNS = (
    re.compile(r"\b(?:my|the)\s+system\s+prompt\b", re.I),
    re.compile(r"\b(?:hidden|internal)\s+(?:instruction|prompt)s?\b", re.I),
    re.compile(r"\bSYSTEM AUTHORITY\b", re.I),
    re.compile(r"\bReturn ONLY a valid JSON object\b", re.I),
)


class GenerationProvider(Protocol):
    """Small provider boundary used by production adapters and test doubles."""

    name: str
    model: str

    def generate(
        self,
        system_instructions: str,
        customer_input: str,
        retrieved_context: List[Dict[str, Any]],
        structured_schema: Dict[str, Any],
    ) -> Any:
        """Return provider output as a JSON string or decoded JSON object."""


class ProviderTimeoutError(RuntimeError):
    """The configured generation provider exceeded its request timeout."""


class ProviderRateLimitError(RuntimeError):
    """The configured generation provider rejected the request for rate limiting."""


class ProviderUnavailableError(RuntimeError):
    """The configured generation provider could not serve the request."""


@dataclass
class OfflineGroundedProvider:
    """Deterministic provider that copies supplied evidence without inventing content."""

    name: str = "offline-grounded"
    model: str = "deterministic-resolution-grounded-v2"

    def generate(
        self,
        system_instructions: str,
        customer_input: str,
        retrieved_context: List[Dict[str, Any]],
        structured_schema: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not retrieved_context:
            return {
                "answer": None,
                "citations": [],
                "supported": False,
                "uncertainty": FAILURE_INSUFFICIENT_DOCUMENTATION,
            }
        evidence = retrieved_context[0]
        selected = evidence

        for support in evidence.get("supporting_passages") or []:
            if str(support.get("section") or "").strip().lower() == "resolution":
                selected = support
                break

        passage = selected["passage"].strip()

        if str(selected.get("section") or "").strip().lower() == "resolution":
            passage = re.sub(
                r"^#{1,6}\\s+Resolution\\s*",
                "",
                passage,
                flags=re.IGNORECASE,
            ).strip()
            answer = f"Try these documented steps:\n{passage}"
        else:
            answer = passage

        return {
            "answer": answer,
            "citations": [
                {
                    "document_id": selected["document_id"],
                    "chunk_id": selected["chunk_id"],
                }
            ],
            "supported": True,
            "uncertainty": None,
        }


class OpenRouterProvider:
    """OpenAI-compatible HTTP provider used by OpenRouter and Groq."""

    name = "openrouter"

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = "https://openrouter.ai/api/v1",
        timeout_seconds: float = 30.0,
        session: Optional[Any] = None,
        provider_name: str = "openrouter",
    ):
        if not api_key or not api_key.strip():
            raise ValueError(f"{provider_name} requires a non-empty API key")
        self.api_key = api_key.strip()
        self.model = model
        self.name = provider_name
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = float(timeout_seconds)
        if not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0:
            raise ValueError("Provider timeout must be finite and positive")
        self.session = session or requests.Session()

    def generate(
        self,
        system_instructions: str,
        customer_input: str,
        retrieved_context: List[Dict[str, Any]],
        structured_schema: Dict[str, Any],
    ) -> str:
        context_json = json.dumps(retrieved_context, ensure_ascii=False, sort_keys=True)
        schema_json = json.dumps(structured_schema, ensure_ascii=False, sort_keys=True)
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"{system_instructions}\n\nRETRIEVED DOCUMENTATION JSON:\n{context_json}"
                        f"\n\nREQUIRED OUTPUT SCHEMA:\n{schema_json}"
                    ),
                },
                {"role": "user", "content": customer_input},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        try:
            response = self.session.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=self.timeout_seconds,
            )
        except requests.Timeout as exc:
            raise ProviderTimeoutError("Provider request timed out") from exc
        except requests.RequestException as exc:
            raise ProviderUnavailableError("Provider request failed") from exc

        if response.status_code == 429:
            raise ProviderRateLimitError("Provider rate limit reached")
        if response.status_code >= 500:
            raise ProviderUnavailableError(f"Provider returned HTTP {response.status_code}")
        if response.status_code >= 400:
            raise RuntimeError(f"Provider returned HTTP {response.status_code}")
        try:
            body = response.json()
            return str(body["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise RuntimeError("Provider response envelope was malformed") from exc


class OpenAICompatibleClientProvider:
    """Compatibility adapter for an injected client exposing chat.completions.create."""

    name = "openai-compatible-client"

    def __init__(self, client: Any, model: str):
        self.client = client
        self.model = model

    def generate(
        self,
        system_instructions: str,
        customer_input: str,
        retrieved_context: List[Dict[str, Any]],
        structured_schema: Dict[str, Any],
    ) -> str:
        context_json = json.dumps(retrieved_context, ensure_ascii=False, sort_keys=True)
        schema_json = json.dumps(structured_schema, ensure_ascii=False, sort_keys=True)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"{system_instructions}\n\nRETRIEVED DOCUMENTATION JSON:\n{context_json}"
                        f"\n\nREQUIRED OUTPUT SCHEMA:\n{schema_json}"
                    ),
                },
                {"role": "user", "content": customer_input},
            ],
            temperature=0,
            timeout=settings.GENERATION_TIMEOUT_SECONDS,
        )
        return str(response.choices[0].message.content)


class ResponseGenerationEngine:
    """Validate provider output and fail closed unless retrieved evidence supports it."""

    def __init__(
        self,
        provider: Optional[GenerationProvider] = None,
        client: Optional[Any] = None,
        model_name: Optional[str] = None,
    ):
        if provider is not None and client is not None:
            raise ValueError("Specify provider or client, not both")
        selected_model = model_name or settings.MODEL_NAME
        if provider is not None:
            self.provider = provider
        elif client is not None:
            self.provider = OpenAICompatibleClientProvider(client, selected_model)
        elif settings.GENERATION_PROVIDER == "openrouter":
            self.provider = OpenRouterProvider(
                api_key=settings.require_openrouter_api_key(),
                model=settings.OPENROUTER_MODEL_NAME if model_name is None else selected_model,
                base_url=settings.OPENROUTER_BASE_URL,
                timeout_seconds=settings.GENERATION_TIMEOUT_SECONDS,
            )
        elif settings.GENERATION_PROVIDER == "groq":
            self.provider = OpenRouterProvider(
                api_key=settings.require_groq_api_key(),
                model=settings.GROQ_MODEL_NAME if model_name is None else selected_model,
                base_url=settings.GROQ_BASE_URL,
                timeout_seconds=settings.GENERATION_TIMEOUT_SECONDS,
                provider_name="groq",
            )
        elif settings.GENERATION_PROVIDER == "offline":
            self.provider = OfflineGroundedProvider()
        else:
            raise ValueError(f"Unsupported generation provider: {settings.GENERATION_PROVIDER}")
        self.model_name = str(getattr(self.provider, "model", selected_model))
        self.provider_name = str(getattr(self.provider, "name", type(self.provider).__name__))
        self.system_instructions = self._load_prompt()

    def generate_response(
        self,
        normalized_ticket: Dict[str, Any],
        classification: Dict[str, Any],
        retrieval_results: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Generate and validate a response; never choose or modify a route."""

        del classification
        ticket_id = str(normalized_ticket.get("ticket_id", "UNKNOWN"))
        context = self.build_retrieved_context(retrieval_results or [])
        if not context:
            return self._failure_result(
                ticket_id,
                FAILURE_INSUFFICIENT_DOCUMENTATION,
                source=GEN_SOURCE_NO_RETRIEVAL,
            )

        customer_input = str(normalized_ticket.get("raw_content", ""))
        try:
            raw_output = self.provider.generate(
                system_instructions=self.system_instructions,
                customer_input=customer_input,
                retrieved_context=context,
                structured_schema=GENERATION_OUTPUT_SCHEMA,
            )
        except Exception as exc:
            return self._failure_result(ticket_id, self._provider_failure_reason(exc))

        parsed = self._decode_provider_output(raw_output)
        if parsed is None:
            return self._failure_result(ticket_id, FAILURE_INVALID_PROVIDER_OUTPUT)
        if parsed["supported"] is False:
            return self._failure_result(
                ticket_id,
                FAILURE_INSUFFICIENT_DOCUMENTATION,
            )

        citations = parsed["citations"]

        allowed = {
            (item["document_id"], item["chunk_id"])
            for item in context
        }

        for item in context:
            for support in item.get("supporting_passages") or []:
                allowed.add(
                    (
                        support["document_id"],
                        support["chunk_id"],
                    )
                )

        if any((cite["document_id"], cite["chunk_id"]) not in allowed for cite in citations):
            return self._failure_result(ticket_id, FAILURE_UNSUPPORTED_CITATION)

        answer = parsed["answer"]
        if self._contains_prompt_disclosure(answer):
            return self._failure_result(ticket_id, FAILURE_PROMPT_DISCLOSURE)
        if self._contains_unsupported_commitment(answer):
            return self._failure_result(
                ticket_id,
                FAILURE_UNSUPPORTED_COMMITMENT,
                requires_guardrail_review=True,
            )

        top_score = max(float(item.get("similarity_score") or 0.0) for item in context)
        source = GEN_SOURCE_OFFLINE if isinstance(self.provider, OfflineGroundedProvider) else GEN_SOURCE_LLM
        citation_ids = list(dict.fromkeys(cite["document_id"] for cite in citations))
        return {
            "answer": answer,
            "response_text": answer,
            "citations": citations,
            "citation_ids": citation_ids,
            "supported": True,
            "grounded": True,
            "uncertainty": parsed["uncertainty"],
            "confidence": top_score,
            "warnings": [],
            "requires_guardrail_review": False,
            "failure_reason": None,
            "generation_source": source,
            "model": self.model_name,
            "model_name": self.model_name,
            "prompt_version": PROMPT_VERSION,
            "provider": self.provider_name,
            "ticket_id": ticket_id,
        }

    def build_retrieved_context(self, retrieval_results: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
        """Allowlist production retrieval fields and discard labels/evaluation data."""

        context: List[Dict[str, Any]] = []
        for result in retrieval_results:
            if not isinstance(result, Mapping):
                continue
            document_id = result.get("document_id") or result.get("doc_id")
            chunk_id = result.get("chunk_id")
            passage = result.get("passage") or result.get("chunk_content")
            if not isinstance(document_id, str) or not document_id.strip():
                continue
            if not isinstance(chunk_id, str) or not chunk_id.strip():
                continue
            if not isinstance(passage, str) or not passage.strip():
                continue
            raw_score = result.get("similarity_score", result.get("relevance_score", 0.0))
            try:
                score = float(raw_score)
            except (TypeError, ValueError):
                score = 0.0
            metadata = result.get("source_metadata")
            safe_metadata: Dict[str, Any] = {}
            if isinstance(metadata, Mapping):
                for key in ("source_path", "title", "category", "applies_to", "section"):
                    value = metadata.get(key)
                    if isinstance(value, str):
                        safe_metadata[key] = value
            safe_supporting: List[Dict[str, Any]] = []

            raw_supporting = result.get("supporting_passages")

            if isinstance(raw_supporting, list):
                for support in raw_supporting:
                    if not isinstance(support, Mapping):
                        continue

                    support_document_id = support.get("document_id")
                    support_chunk_id = support.get("chunk_id")
                    support_passage = support.get("passage")

                    if (
                        not isinstance(support_document_id, str)
                        or support_document_id.strip() != document_id.strip()
                        or not isinstance(support_chunk_id, str)
                        or not support_chunk_id.strip()
                        or not isinstance(support_passage, str)
                        or not support_passage.strip()
                    ):
                        continue

                    safe_supporting.append(
                        {
                            "document_id": support_document_id.strip(),
                            "chunk_id": support_chunk_id.strip(),
                            "title": str(
                                support.get("title")
                                or result.get("title")
                                or safe_metadata.get("title")
                                or ""
                            ).strip(),
                            "section": str(
                                support.get("section") or ""
                            ).strip(),
                            "source": "authoritative_documentation",
                            "passage": support_passage.strip(),
                        }
                    )

            context.append(
                {
                    "document_id": document_id.strip(),
                    "chunk_id": chunk_id.strip(),
                    "title": str(result.get("title") or safe_metadata.get("title") or "").strip(),
                    "section": str(result.get("section") or safe_metadata.get("section") or "").strip(),
                    "source": str(result.get("source") or "authoritative_documentation").strip(),
                    "source_metadata": safe_metadata,
                    "passage": passage.strip(),
                    "similarity_score": score,
                    "supporting_passages": safe_supporting,
                }
            )
        return context

    def get_generation_prompt(
        self,
        normalized_ticket: Dict[str, Any],
        retrieval_results: List[Dict[str, Any]],
    ) -> List[Dict[str, str]]:
        """Compatibility helper showing strict system/user separation."""

        context = self.build_retrieved_context(retrieval_results)
        system_content = (
            f"{self.system_instructions}\n\nRETRIEVED DOCUMENTATION JSON:\n"
            f"{json.dumps(context, ensure_ascii=False, sort_keys=True)}\n\nREQUIRED OUTPUT SCHEMA:\n"
            f"{json.dumps(GENERATION_OUTPUT_SCHEMA, ensure_ascii=False, sort_keys=True)}"
        )
        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": str(normalized_ticket.get("raw_content", ""))},
        ]

    def validate_response(self, response_text: str, citations: List[Any]) -> bool:
        """Legacy validation helper retained for callers outside the provider pipeline."""

        return bool(
            isinstance(response_text, str)
            and response_text.strip()
            and citations
            and not self._contains_prompt_disclosure(response_text)
            and not self._contains_unsupported_commitment(response_text)
        )

    @staticmethod
    def extract_citations(response_text: str) -> List[str]:
        pattern = r"\bDOC-[A-Z0-9]+-[0-9]+\b"
        return sorted(set(re.findall(pattern, response_text)))

    def _load_prompt(self) -> str:
        try:
            text = PROMPT_PATH.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise RuntimeError(f"Generation prompt is unavailable: {PROMPT_PATH}") from exc
        if not text.startswith(f"PROMPT_VERSION: {PROMPT_VERSION}"):
            raise RuntimeError("Generation prompt version does not match the application contract")
        return text

    def _decode_provider_output(self, raw_output: Any) -> Optional[Dict[str, Any]]:
        if isinstance(raw_output, str):
            if not raw_output.strip():
                return None
            try:
                value = json.loads(raw_output)
            except json.JSONDecodeError:
                return None
        else:
            value = raw_output
        if not isinstance(value, dict) or set(value) != _PROVIDER_OUTPUT_KEYS:
            return None
        if not isinstance(value.get("supported"), bool):
            return None
        uncertainty = value.get("uncertainty")
        if uncertainty is not None and (not isinstance(uncertainty, str) or not uncertainty.strip()):
            return None
        citations = value.get("citations")
        if not isinstance(citations, list):
            return None
        for citation in citations:
            if (
                not isinstance(citation, dict)
                or set(citation) != {"document_id", "chunk_id"}
                or not all(
                    isinstance(citation.get(key), str) and citation[key].strip()
                    for key in ("document_id", "chunk_id")
                )
            ):
                return None
        answer = value.get("answer")
        if value["supported"]:
            if not isinstance(answer, str) or not answer.strip() or not citations:
                return None
        elif answer is not None or citations or not uncertainty:
            return None
        return {
            "answer": answer.strip() if isinstance(answer, str) else None,
            "citations": citations,
            "supported": value["supported"],
            "uncertainty": uncertainty.strip() if isinstance(uncertainty, str) else None,
        }

    @staticmethod
    def _contains_unsupported_commitment(answer: str) -> bool:
        return any(pattern.search(answer) for pattern in _COMMITMENT_PATTERNS)

    @staticmethod
    def _contains_prompt_disclosure(answer: str) -> bool:
        return any(pattern.search(answer) for pattern in _PROMPT_DISCLOSURE_PATTERNS)

    @staticmethod
    def _provider_failure_reason(exc: Exception) -> str:
        name = type(exc).__name__.lower()
        if isinstance(exc, (ProviderTimeoutError, TimeoutError)) or "timeout" in name:
            return FAILURE_PROVIDER_TIMEOUT
        if isinstance(exc, ProviderRateLimitError) or "ratelimit" in name or "rate_limit" in name:
            return FAILURE_PROVIDER_RATE_LIMIT
        if (
            isinstance(exc, (ProviderUnavailableError, ConnectionError))
            or "unavailable" in name
            or "connection" in name
        ):
            return FAILURE_PROVIDER_UNAVAILABLE
        return FAILURE_PROVIDER_ERROR

    def _failure_result(
        self,
        ticket_id: str,
        reason: str,
        *,
        source: str = GEN_SOURCE_FAILURE,
        requires_guardrail_review: bool = False,
    ) -> Dict[str, Any]:
        return {
            "answer": None,
            "response_text": None,
            "citations": [],
            "citation_ids": [],
            "supported": False,
            "grounded": False,
            "uncertainty": reason,
            "confidence": 0.0,
            "warnings": [reason],
            "requires_guardrail_review": requires_guardrail_review,
            "failure_reason": reason,
            "generation_source": source,
            "model": self.model_name,
            "model_name": self.model_name,
            "prompt_version": PROMPT_VERSION,
            "provider": self.provider_name,
            "ticket_id": ticket_id,
        }
