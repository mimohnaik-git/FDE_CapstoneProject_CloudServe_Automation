"""Inference-time evidence sufficiency assessment.

The current release policy intentionally abstains from declaring retrieved
documentation sufficient for automatic customer response.

Development-only experiments did not establish a defensible high-precision
operating region with meaningful coverage. This module therefore computes
legitimate inference-time evidence diagnostics but fails closed until an
independently justified release policy is approved.

Protected benchmark labels such as ``answerable_from_docs``,
``expected_doc_ids``, ``expected_route``, and ``must_not_auto_respond`` are
never consumed here.
"""
from __future__ import annotations

import math
import re
from typing import Any, Dict, Mapping, Sequence

from src.classify import ticket_text


EVIDENCE_POLICY_VERSION = "evidence-sufficiency-v1-fail-closed"
EVIDENCE_FEATURE_VERSION = "evidence-features-v1"

STATUS_INSUFFICIENT = "INSUFFICIENT"
STATUS_UNVERIFIED = "UNVERIFIED"
STATUS_INVALID = "INVALID"

REASON_NO_EVIDENCE = "NO_EVIDENCE"
REASON_INVALID_EVIDENCE = "INVALID_EVIDENCE"
REASON_DEVELOPMENT_EVIDENCE_INSUFFICIENT = (
    "DEVELOPMENT_EVIDENCE_INSUFFICIENT_FOR_RELEASE"
)

PROTECTED_TARGET_FIELDS = frozenset(
    {
        "answerable_from_docs",
        "expected_doc_ids",
        "expected_route",
        "must_not_auto_respond",
    }
)


def _tokens(value: Any) -> set[str]:
    """Return deterministic lowercase alphanumeric tokens."""
    return set(
        re.findall(
            r"[a-z0-9]+",
            str(value or "").lower(),
        )
    )


def _score(item: Mapping[str, Any]) -> float:
    """Read and validate one retrieval score."""
    value = item.get(
        "relevance_score",
        item.get("similarity_score"),
    )

    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or not -1.0 <= float(value) <= 1.0
    ):
        raise ValueError("Invalid retrieval score")

    return float(value)


def _passage(item: Mapping[str, Any]) -> str:
    return str(
        item.get("passage")
        or item.get("chunk_content")
        or ""
    )


def _document_id(item: Mapping[str, Any]) -> str:
    return str(
        item.get("document_id")
        or item.get("doc_id")
        or ""
    ).strip()


def extract_evidence_features(
    ticket: Mapping[str, Any],
    retrieval_results: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Compute legitimate inference-time evidence diagnostics.

    The function intentionally does not inspect ticket labels, expected
    documents, expected routes, or any other benchmark ground truth.
    """
    if not isinstance(ticket, Mapping):
        raise ValueError("Ticket must be a mapping")

    if (
        isinstance(retrieval_results, (str, bytes))
        or not isinstance(retrieval_results, Sequence)
    ):
        raise ValueError("Retrieval results must be a sequence")

    query = ticket_text(ticket)
    query_tokens = _tokens(query)

    scores: list[float] = []
    coverages: list[float] = []
    jaccards: list[float] = []
    document_ids: list[str] = []
    resolution_count = 0

    for item in retrieval_results:
        if not isinstance(item, Mapping):
            raise ValueError("Retrieval item must be a mapping")

        score = _score(item)
        scores.append(score)

        document_id = _document_id(item)
        if document_id:
            document_ids.append(document_id)

        passage_tokens = _tokens(_passage(item))

        intersection = query_tokens & passage_tokens
        union = query_tokens | passage_tokens

        coverage = (
            len(intersection) / len(query_tokens)
            if query_tokens
            else 0.0
        )

        jaccard = (
            len(intersection) / len(union)
            if union
            else 0.0
        )

        coverages.append(float(coverage))
        jaccards.append(float(jaccard))

        section = str(
            item.get("section", "")
        ).lower()

        if "resolution" in section:
            resolution_count += 1

    sorted_scores = list(scores)

    top1 = (
        sorted_scores[0]
        if len(sorted_scores) >= 1
        else None
    )

    top2 = (
        sorted_scores[1]
        if len(sorted_scores) >= 2
        else None
    )

    top3 = sorted_scores[:3]

    return {
        "retrieval_count": len(retrieval_results),
        "distinct_document_count": len(set(document_ids)),
        "supporting_document_ids": list(dict.fromkeys(document_ids)),
        "top1_score": top1,
        "top2_score": top2,
        "top1_top2_margin": (
            top1 - top2
            if top1 is not None and top2 is not None
            else None
        ),
        "top3_mean_score": (
            sum(top3) / len(top3)
            if top3
            else None
        ),
        "mean_score": (
            sum(scores) / len(scores)
            if scores
            else None
        ),
        "resolution_section_count": resolution_count,
        "max_query_token_coverage": (
            max(coverages)
            if coverages
            else 0.0
        ),
        "top3_mean_query_token_coverage": (
            sum(coverages[:3]) / len(coverages[:3])
            if coverages[:3]
            else 0.0
        ),
        "max_query_passage_jaccard": (
            max(jaccards)
            if jaccards
            else 0.0
        ),
        "top3_mean_query_passage_jaccard": (
            sum(jaccards[:3]) / len(jaccards[:3])
            if jaccards[:3]
            else 0.0
        ),
        "score_count_ge_050": sum(
            score >= 0.50
            for score in scores
        ),
        "score_count_ge_060": sum(
            score >= 0.60
            for score in scores
        ),
        "score_count_ge_070": sum(
            score >= 0.70
            for score in scores
        ),
    }


class EvidenceSufficiencyEngine:
    """Fail-closed evidence assessor for the current production candidate."""

    policy_version = EVIDENCE_POLICY_VERSION
    feature_version = EVIDENCE_FEATURE_VERSION

    def assess(
        self,
        ticket: Mapping[str, Any],
        retrieval_results: Sequence[Mapping[str, Any]],
    ) -> Dict[str, Any]:
        """Return an auditable evidence-sufficiency assessment.

        ``sufficient=True`` is intentionally impossible under the current
        policy because development evidence has not justified a production
        release threshold.
        """
        try:
            features = extract_evidence_features(
                ticket,
                retrieval_results,
            )
        except Exception as exc:
            return {
                "status": STATUS_INVALID,
                "sufficient": False,
                "confidence": None,
                "reason_code": REASON_INVALID_EVIDENCE,
                "reason": (
                    "Evidence diagnostics were invalid; "
                    "automatic release is disabled."
                ),
                "policy_version": self.policy_version,
                "feature_version": self.feature_version,
                "features": {},
                "error_type": type(exc).__name__,
            }

        if features["retrieval_count"] == 0:
            return {
                "status": STATUS_INSUFFICIENT,
                "sufficient": False,
                "confidence": None,
                "reason_code": REASON_NO_EVIDENCE,
                "reason": (
                    "No authoritative retrieval evidence is available."
                ),
                "policy_version": self.policy_version,
                "feature_version": self.feature_version,
                "features": features,
                "error_type": None,
            }

        return {
            "status": STATUS_UNVERIFIED,
            "sufficient": None,
            "confidence": None,
            "reason_code": REASON_DEVELOPMENT_EVIDENCE_INSUFFICIENT,
            "reason": (
                "Retrieved documentation has inference-time support signals, "
                "but development evidence does not justify declaring it "
                "sufficient for automatic release."
            ),
            "policy_version": self.policy_version,
            "feature_version": self.feature_version,
            "features": features,
            "error_type": None,
        }
