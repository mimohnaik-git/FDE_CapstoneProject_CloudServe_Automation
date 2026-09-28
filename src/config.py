"""Central configuration. Every threshold and policy version lives here so a
run can be fingerprinted and reproduced."""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _customer_release_authorized_from_env() -> bool:
    """Enable requests AUTO release; the explicit disable switch always wins."""
    enabled = _env_bool("CLOUDSERVE_AUTO_RESPONSE_ENABLED", False)
    disabled = _env_bool("CLOUDSERVE_AUTO_RESPONSE_DISABLED", False)
    return enabled and not disabled


@dataclass(frozen=True)
class Settings:
    # Classification
    intent_confidence_threshold: float = 0.60
    answerability_confidence_threshold: float = 0.75
    # Retrieval
    retrieval_score_threshold: float = 0.30
    tfidf_retrieval_score_threshold: float = 0.10
    top_k: int = 5
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    retrieval_backend: str = "tfidf"
    retrieval_configuration: str = "field-weighted-word-char-unique-docs-v1"
    allow_tfidf_fallback: bool = True
    # Policy versions
    prompt_version: str = "generation-v1.0.0"
    eligibility_policy: str = "evidence-sufficiency-v1-fail-closed"
    # Customer release is fail-closed. AUTO release requires ENABLED=true and
    # DISABLE not true. The explicit disable switch wins if both are true.
    customer_release_authorized: bool = field(
        default_factory=_customer_release_authorized_from_env
    )
    never_automate_intents: tuple = (
        "security_incident", "compliance_request", "feature_request",
        "unclear_request", "billing_dispute", "legal_request",
        "account_deletion", "outage_report", "data_breach",
    )
    auto_eligible_intents: tuple = (
        "api_usage_question",
        "data_export",
        "onboarding",
        "sso_configuration",
        "billing_query",
        "quota_or_overage",
    )

    evidence_resolution_ratio_min: float = 0.40
    evidence_symptom_margin_max: float = 0.30
    urgent_operational_intents: tuple = (
        "database_issue", "performance_degradation", "outage_report",
    )
    provider_timeout_s: float = 8.0
    db_path: str = field(default_factory=lambda: os.environ.get(
        "CLOUDSERVE_DB", str(ROOT / "var" / "decisions.sqlite3")))
    artifacts_dir: str = field(default_factory=lambda: os.environ.get(
        "CLOUDSERVE_ARTIFACTS", str(ROOT / "artifacts")))
    kb_path: str = field(default_factory=lambda: os.environ.get(
        "CLOUDSERVE_KB", str(ROOT / "data" / "cloudserve" / "documentation.json")))

    def retrieval_threshold_for(self, backend: str) -> float:
        return (self.tfidf_retrieval_score_threshold if backend == "tfidf"
                else self.retrieval_score_threshold)

    def fingerprint(self) -> str:
        config = asdict(self)
        for key in ("db_path", "artifacts_dir", "kb_path"):
            config.pop(key, None)
        blob = json.dumps(
            config,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def get_settings(**overrides) -> Settings:
    return Settings(**overrides) if overrides else Settings()
