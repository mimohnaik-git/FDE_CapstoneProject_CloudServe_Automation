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


@dataclass(frozen=True)
class Settings:
    # Classification
    intent_confidence_threshold: float = 0.60
    answerability_confidence_threshold: float = 0.75
    # Retrieval
    retrieval_score_threshold: float = 0.30          # calibrated for MiniLM cosine
    # TF-IDF cosine lives on a different scale; never reuse the MiniLM threshold.
    tfidf_retrieval_score_threshold: float = 0.10
    top_k: int = 5
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    # Explicit validated backend. Installed packages never change selection.
    retrieval_backend: str = "tfidf"
    retrieval_configuration: str = "field-weighted-word-char-unique-docs-v1"
    # Retained for configuration compatibility; explicit backend selection does
    # not silently fall back.
    allow_tfidf_fallback: bool = True
    # Policy versions
    prompt_version: str = "generation-v1.0.0"
    eligibility_policy: str = "evidence-sufficiency-v1-fail-closed"
    # Customer release. Kept False: no evidence has authorised automatic
    # release. The AUTO path exists but cannot fire unless this is flipped
    # by an explicit, reviewed configuration change.
    # Operational kill switch. False is the safe default; enabling it requires
    # an explicit environment/config change and is captured in the fingerprint.
    customer_release_authorized: bool = field(default_factory=lambda: _env_bool(
        "CLOUDSERVE_AUTO_RESPONSE_ENABLED", False))
    # Intents that must never be auto-answered, regardless of confidence.
    never_automate_intents: tuple = (
        "security_incident", "compliance_request", "feature_request",
        "unclear_request", "billing_dispute", "legal_request",
        "account_deletion", "outage_report", "data_breach",
    )
    # Conservative first release. The group-isolated development replay found
    # a false AUTO for `rate_limit`; it is therefore intentionally excluded.
    # Expansion requires a reviewed held-out evaluation and a versioned
    # configuration change.
    auto_eligible_intents: tuple = (
        "api_usage_question",
        "data_export",
        "onboarding",
        "sso_configuration",
        "billing_query",
        "quota_or_overage",
    )

    # Evidence-ambiguity safeguard selected from group-isolated
    # development OOF policy evaluation.
    evidence_resolution_ratio_min: float = 0.40
    evidence_symptom_margin_max: float = 0.30
    # Discovery evidence and development labels show these require live
    # operational state when urgent, even when a related article exists.
    urgent_operational_intents: tuple = (
        "database_issue", "performance_degradation", "outage_report",
    )
    # Provider (optional LLM). Deterministic assembler is the default.
    provider_timeout_s: float = 8.0
    # Storage
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

        # Runtime/storage locations are deployment-specific and must not
        # change the identity of an otherwise identical decision policy.
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
