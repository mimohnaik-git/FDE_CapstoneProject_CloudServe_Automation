"""Development-only component smoke test for frozen V1 generation.

This does not use validation data, construct the orchestrator, alter routing, or
write frozen evaluation artifacts. It invokes the existing V1 generation and
guardrail components directly after the frozen classifier/retriever produce
evidence. Secrets and raw provider exceptions are intentionally never persisted.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
# ``src.config`` deliberately calls ``load_dotenv()`` without a path.  Make the
# repository root the process working directory before importing it, so that
# the normal project configuration path consistently discovers the root .env
# even when this script is launched by absolute path from another directory.
os.chdir(PROJECT_ROOT)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
# Stage 15 established this exact workspace-local cache as the offline, readable
# MiniLM runtime source. Set it before importing the frozen retriever so the
# existing SentenceTransformer initialization follows the documented path.
_HF_HOME = PROJECT_ROOT / ".cache" / "huggingface"
os.environ["HF_HOME"] = str(_HF_HOME)
os.environ["HF_HUB_CACHE"] = str(_HF_HOME / "hub")
os.environ["HF_TOKEN_PATH"] = str(_HF_HOME / "no-token")
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

# Importing src.config is the normal project configuration path. It calls
# load_dotenv() and validates the OpenRouter key only if a live provider is used.
from src.classify import TicketClassificationEngine
from src.config import settings
from src.generate import OfflineGroundedProvider, OpenRouterProvider, ResponseGenerationEngine
from src.guardrails import GuardrailEngine
from src.ingest import TicketNormalizationEngine
from src.retrieve import DocumentationRetrievalEngine
from src.route import TicketRoutingEngine


DEVELOPMENT_PATH = PROJECT_ROOT / "data" / "raw" / "development_tickets.json"
DEFAULT_OUTPUT_DIRECTORY = PROJECT_ROOT / "tmp" / "live_provider_generation_smoke"
HISTORICAL_OUTPUT_PATHS = {
    (PROJECT_ROOT / "artifacts" / "live_provider_generation_smoke" / name).resolve()
    for name in ("groq-positive-control.json", "groq-result.json", "openrouter-result.json")
}
LABEL = "Live Provider Generation Component Smoke Test - development-only evidence. This does not change frozen V1 routing or validation results."
SYNTHETIC_TICKET = {
    "ticket_id": "SYNTHETIC-PROVIDER-001",
    "channel": "chat",
    "body": "What should an API client do when it reaches a documented rate limit?",
    "customer_tier": "standard",
}


def _live_provider_configuration(provider_name: str) -> tuple[str, str, str, str | None]:
    """Return a development-only live-provider configuration without serializing credentials."""

    if provider_name == "openrouter":
        return (
            "openrouter",
            settings.OPENROUTER_MODEL_NAME,
            settings.OPENROUTER_BASE_URL,
            settings.OPENROUTER_API_KEY,
        )
    if provider_name == "groq":
        return (
            "groq",
            settings.GROQ_MODEL_NAME,
            settings.GROQ_BASE_URL,
            settings.GROQ_API_KEY,
        )
    raise ValueError(f"Unsupported smoke-test live provider: {provider_name}")


_SECRET_PATTERNS = (
    re.compile(r"(?i)\bBearer\s+[^\s,;]+"),
    re.compile(r"(?i)\b(?:api[_ -]?key|access[_ -]?token|token|secret|password)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"(?i)([?&](?:api[_-]?key|access[_-]?token|token|key)=)[^&#\s]+"),
    re.compile(r"(?i)\b(?:sk|gsk|pk|rk)[-_][A-Za-z0-9._-]{8,}\b"),
)


def _sanitize_error_text(value: Any) -> str | None:
    """Keep a short provider diagnostic without retaining secret-like material."""

    if not isinstance(value, str):
        return None
    compact = " ".join(value.split())[:500]
    if not compact:
        return None
    for known_secret in (settings.OPENROUTER_API_KEY, settings.GROQ_API_KEY):
        if known_secret:
            compact = compact.replace(known_secret, "[REDACTED]")
    for pattern in _SECRET_PATTERNS:
        compact = pattern.sub(
            lambda match: (
                f"{match.group(1)}[REDACTED]" if match.lastindex else "[REDACTED]"
            ),
            compact,
        )
    return compact


def _validated_output_path(path: Path) -> Path:
    resolved = path.resolve()
    if resolved in HISTORICAL_OUTPUT_PATHS:
        raise ValueError("Refusing to overwrite a preserved historical provider-smoke artifact")
    return resolved


def _execution_failed(result: Mapping[str, Any]) -> bool:
    """Treat transport/parsing blockers as failure, not safe guardrail rejection."""
    if result.get("blockers"):
        return True
    provider_name = result.get("live_provider")
    for case in result.get("cases", []):
        if not isinstance(case, Mapping):
            return True
        providers = case.get("providers")
        record = providers.get(provider_name) if isinstance(providers, Mapping) else None
        if not isinstance(record, Mapping) or record.get("failure_reason") is not None:
            return True
    return False


class ProviderDiagnosticSession:
    """Capture a minimal, sanitized HTTP diagnostic for this smoke harness."""

    def __init__(self, provider_name: str, base_url: str) -> None:
        self._session = requests.Session()
        self.diagnostic: dict[str, Any] = {
            "provider": provider_name,
            "request_url": f"{base_url.rstrip('/')}/chat/completions",
            "model": None,
            "response_format": None,
            "http_status": None,
            "provider_error_type": None,
            "provider_error_code": None,
            "provider_error_message": None,
            "failure_category": None,
        }

    def post(self, url: str, *, headers: Any = None, json: Any = None, timeout: Any = None) -> Any:
        # Deliberately do not inspect or retain ``headers`` or customer/context
        # payload fields. Only the non-sensitive routing-compatible fields are
        # retained for this provider diagnostic.
        self.diagnostic["request_url"] = _sanitize_error_text(str(url))
        if isinstance(json, Mapping):
            self.diagnostic["model"] = json.get("model")
            response_format = json.get("response_format")
            self.diagnostic["response_format"] = (
                {"type": response_format.get("type")}
                if isinstance(response_format, Mapping) else None
            )
        try:
            response = self._session.post(url, headers=headers, json=json, timeout=timeout)
        except requests.Timeout:
            self.diagnostic["failure_category"] = "TIMEOUT"
            raise
        except requests.RequestException:
            self.diagnostic["failure_category"] = "NETWORK_UNAVAILABLE"
            raise

        self.diagnostic["http_status"] = response.status_code
        if response.status_code >= 400:
            try:
                body = response.json()
            except ValueError:
                body = {}
            error = body.get("error") if isinstance(body, Mapping) else {}
            if isinstance(error, Mapping):
                self.diagnostic["provider_error_type"] = _sanitize_error_text(error.get("type"))
                self.diagnostic["provider_error_code"] = _sanitize_error_text(error.get("code"))
                self.diagnostic["provider_error_message"] = _sanitize_error_text(error.get("message"))
            self.diagnostic["failure_category"] = {
                400: "BAD_REQUEST",
                401: "AUTHENTICATION_FAILED",
                403: "MODEL_ACCESS_DENIED",
                429: "RATE_LIMITED",
            }.get(response.status_code, "SERVER_FAILURE" if response.status_code >= 500 else "HTTP_FAILURE")
        return response


def _provider_request_assessment(diagnostic: Mapping[str, Any]) -> dict[str, Any]:
    """State only what the HTTP status establishes; do not infer unaudited causes."""

    status = diagnostic.get("http_status")
    category = diagnostic.get("failure_category")
    return {
        "authentication_succeeded": True if isinstance(status, int) and 200 <= status < 400 else (
            False if category == "AUTHENTICATION_FAILED" else None
        ),
        "model_access_succeeded": True if isinstance(status, int) and 200 <= status < 400 else (
            False if category == "MODEL_ACCESS_DENIED" else None
        ),
        "payload_accepted": True if isinstance(status, int) and 200 <= status < 300 else (
            False if category == "BAD_REQUEST" else None
        ),
    }


def _unwrap_development(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list) and len(raw) == 1 and isinstance(raw[0], list):
        raw = raw[0]
    if not isinstance(raw, list) or not all(isinstance(item, dict) for item in raw):
        raise ValueError("Development ticket data must be a list of ticket objects")
    return raw


def _safe_generation_record(
    result: Mapping[str, Any], guardrails: Mapping[str, Any], retrieval: list[dict[str, Any]], latency_ms: float
) -> dict[str, Any]:
    citations = result.get("citations") if isinstance(result.get("citations"), list) else []
    retrieved_pairs = {
        (item.get("document_id"), item.get("chunk_id")) for item in retrieval
        if isinstance(item.get("document_id"), str) and isinstance(item.get("chunk_id"), str)
    }
    cited_pairs = {
        (item.get("document_id"), item.get("chunk_id")) for item in citations
        if isinstance(item, Mapping)
    }
    raw_generation_success = result.get("failure_reason") is None
    accepted = bool(result.get("supported") is True and guardrails.get("passed") is True)
    # Preserve a candidate for comparison when the guardrail result is solely a
    # routing/calibration rejection. Never persist a candidate flagged for
    # sensitive-data or internal-instruction disclosure.
    reason_codes = set(guardrails.get("reason_codes") or [])
    disclosure_blocks = {"PRIVATE_DATA_LEAK", "SECRET_DISCLOSURE", "SYSTEM_PROMPT_DISCLOSURE"}
    answer = (
        result.get("answer")
        if not (reason_codes & disclosure_blocks) and isinstance(result.get("answer"), str)
        else None
    )
    return {
        "provider": result.get("provider"),
        "model": result.get("model_name") or result.get("model"),
        "raw_generation_success": raw_generation_success,
        "structured_output_valid": raw_generation_success and result.get("failure_reason") != "INVALID_PROVIDER_OUTPUT",
        "generated_answer": answer,
        "citations": citations,
        "supported": result.get("supported"),
        "guardrail_result": {
            "passed": guardrails.get("passed"),
            "blocked": guardrails.get("blocked"),
            "primary_reason": guardrails.get("primary_reason"),
            "reason_codes": guardrails.get("reason_codes"),
        },
        "final_generation_acceptance": "ACCEPTED" if accepted else "REJECTED",
        "provider_latency_ms": round(latency_ms, 3),
        "failure_reason": result.get("failure_reason"),
        "exact_cited_ids_exist_in_retrieval": bool(cited_pairs) and cited_pairs.issubset(retrieved_pairs),
    }


def _run_provider(
    provider: Any, ticket: dict[str, Any], classification: dict[str, Any], retrieval: list[dict[str, Any]],
    guardrails: GuardrailEngine,
) -> dict[str, Any]:
    engine = ResponseGenerationEngine(provider=provider, model_name=settings.MODEL_NAME)
    started = time.perf_counter()
    result = engine.generate_response(ticket, classification, retrieval)
    latency_ms = (time.perf_counter() - started) * 1000
    checked = guardrails.check(result, classification, ticket, retrieval)
    return _safe_generation_record(result, checked, retrieval, latency_ms)


def run(
    output_path: Path,
    requested_ids: list[str],
    live_provider_name: str,
    *,
    synthetic: bool = False,
) -> dict[str, Any]:
    if synthetic:
        selected_raw = [SYNTHETIC_TICKET]
        dataset_role = "SYNTHETIC_DEVELOPMENT_COMPONENT"
    else:
        raw = json.loads(DEVELOPMENT_PATH.read_text(encoding="utf-8"))
        development = _unwrap_development(raw)
        requested = set(requested_ids)
        selected_raw = [row for row in development if not requested or row.get("ticket_id") in requested]
        if requested and len(selected_raw) != len(requested):
            missing = sorted(requested - {row.get("ticket_id") for row in selected_raw})
            raise ValueError(f"Unknown development ticket IDs: {missing}")
        dataset_role = "DEVELOPMENT_ONLY"

    ingester = TicketNormalizationEngine()
    classifier = TicketClassificationEngine()
    retriever = DocumentationRetrievalEngine()
    router = TicketRoutingEngine()
    guardrails = GuardrailEngine(confidence_threshold=settings.CLASSIFICATION_CONFIDENCE_THRESHOLD)
    live_name, live_model, live_base_url, live_api_key = _live_provider_configuration(live_provider_name)
    cases: list[dict[str, Any]] = []
    blockers: list[str] = []

    for raw_ticket in selected_raw:
        ticket = ingester.normalize_ticket(raw_ticket)
        classification = classifier.process_classification(ticket)
        retrieval = retriever.query_authoritative_knowledge(
            ticket["raw_content"], top_k=settings.RETRIEVAL_TOP_K
        )
        original_routing = router.route(classification, retrieval)
        top_score = max((float(item["relevance_score"]) for item in retrieval), default=None)
        case: dict[str, Any] = {
            "ticket_id": ticket["ticket_id"],
            "predicted_intent": classification.get("intent"),
            "classification_confidence": classification.get("confidence"),
            "retrieval_score": top_score,
            "retrieved_evidence": [
                {"document_id": item["document_id"], "chunk_id": item["chunk_id"], "passage": item["passage"]}
                for item in retrieval
            ],
            "original_routing": {
                "action": original_routing.get("action"),
                "reason_code": original_routing.get("reason_code"),
            },
            "original_routing_overridden": False,
            "providers": {},
        }
        if not retrieval:
            case["selection_status"] = "SKIPPED_NO_RETRIEVAL"
            case["failure_reason"] = f"RETRIEVAL_UNAVAILABLE:{retriever.last_error or 'NO_RESULT'}"
            blockers.append(case["failure_reason"])
            cases.append(case)
            continue

        case["selection_status"] = "RETRIEVAL_EVIDENCE_AVAILABLE"
        case["providers"]["offline-grounded"] = _run_provider(
            OfflineGroundedProvider(), ticket, classification, retrieval, guardrails
        )
        if not live_api_key:
            case["providers"][live_name] = {
                "provider": live_name, "model": live_model,
                "raw_generation_success": False, "structured_output_valid": False,
                "generated_answer": None, "citations": [], "supported": False,
                "guardrail_result": None, "final_generation_acceptance": "NOT_RUN",
                "provider_latency_ms": None, "failure_reason": f"{live_name.upper()}_API_KEY_NOT_CONFIGURED",
                "exact_cited_ids_exist_in_retrieval": None,
            }
            blockers.append(f"{live_name.upper()}_API_KEY_NOT_CONFIGURED")
        else:
            diagnostic_session = ProviderDiagnosticSession(live_name, live_base_url)
            provider = OpenRouterProvider(
                api_key=live_api_key, model=live_model,
                base_url=live_base_url, timeout_seconds=settings.GENERATION_TIMEOUT_SECONDS,
                session=diagnostic_session,
                provider_name=live_name,
            )
            live_record = _run_provider(
                provider, ticket, classification, retrieval, guardrails
            )
            live_record["provider_http_diagnostic"] = {
                **diagnostic_session.diagnostic,
                **_provider_request_assessment(diagnostic_session.diagnostic),
            }
            case["providers"][live_name] = live_record
        cases.append(case)

    result = {
        "label": LABEL,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_role": dataset_role,
        "validation_data_accessed": False,
        "frozen_v1_artifacts_modified": False,
        "routing_not_overridden": True,
        "prompt_version": "generation-v1.0.0",
        "live_provider": live_name,
        "configured_model": live_model,
        "live_key_configured": bool(live_api_key),
        "runtime_embedding_cache": ".cache/huggingface",
        "cases": cases,
        "blockers": sorted(set(blockers)),
    }
    output_path = _validated_output_path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--ticket-id", action="append", default=None, help="Development ticket ID; repeatable")
    parser.add_argument("--live-provider", choices=("openrouter", "groq"), default="openrouter")
    parser.add_argument(
        "--synthetic", action="store_true",
        help="Use a built-in non-customer synthetic development component fixture.",
    )
    args = parser.parse_args()
    output_path = _validated_output_path(
        args.output or DEFAULT_OUTPUT_DIRECTORY / f"{args.live_provider}-result.json"
    )
    result = run(
        output_path, args.ticket_id or ["DEV-0009"], args.live_provider,
        synthetic=args.synthetic,
    )
    failed = _execution_failed(result)
    print(json.dumps({
        "status": "FAIL" if failed else "PASS",
        "output": str(output_path),
        "cases": len(result["cases"]),
        "blockers": result["blockers"],
    }))
    raise SystemExit(1 if failed else 0)
