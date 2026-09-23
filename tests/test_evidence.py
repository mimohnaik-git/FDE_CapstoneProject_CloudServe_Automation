import pytest

from src.evidence import (
    EVIDENCE_FEATURE_VERSION,
    EVIDENCE_POLICY_VERSION,
    REASON_DEVELOPMENT_EVIDENCE_INSUFFICIENT,
    REASON_INVALID_EVIDENCE,
    REASON_NO_EVIDENCE,
    STATUS_INSUFFICIENT,
    STATUS_INVALID,
    STATUS_UNVERIFIED,
    EvidenceSufficiencyEngine,
    extract_evidence_features,
)


def ticket():
    return {
        "ticket_id": "TEST-001",
        "subject": "Deployment health check failure",
        "body": (
            "Deployment rolls back after a health check timeout."
        ),
        "channel": "email",
    }


def retrieval():
    return [
        {
            "document_id": "DOC-DEPLOY-001",
            "chunk_id": "DOC-DEPLOY-001#resolution",
            "title": "Deployment Troubleshooting",
            "section": "Resolution",
            "passage": (
                "Check the deployment health endpoint and health "
                "check timeout configuration."
            ),
            "relevance_score": 0.78,
        },
        {
            "document_id": "DOC-DEPLOY-003",
            "chunk_id": "DOC-DEPLOY-003#health",
            "title": "Health Checks",
            "section": "Troubleshooting",
            "passage": (
                "Failed health checks can cause a deployment rollback."
            ),
            "relevance_score": 0.63,
        },
    ]


def test_extract_features_uses_only_runtime_inputs():
    features = extract_evidence_features(
        ticket(),
        retrieval(),
    )

    assert features["retrieval_count"] == 2
    assert features["distinct_document_count"] == 2

    assert features["supporting_document_ids"] == [
        "DOC-DEPLOY-001",
        "DOC-DEPLOY-003",
    ]

    assert features["top1_score"] == pytest.approx(0.78)
    assert features["top2_score"] == pytest.approx(0.63)

    assert features["top1_top2_margin"] == pytest.approx(
        0.15
    )

    assert features["resolution_section_count"] == 1


def test_protected_labels_do_not_change_features():
    baseline = ticket()

    contaminated = {
        **baseline,
        "labels": {
            "answerable_from_docs": True,
            "expected_doc_ids": ["SECRET-DOC"],
            "expected_route": "auto_respond",
            "must_not_auto_respond": False,
        },
        "answerable_from_docs": False,
        "expected_doc_ids": ["ANOTHER-SECRET-DOC"],
        "expected_route": "escalate",
        "must_not_auto_respond": True,
    }

    assert extract_evidence_features(
        baseline,
        retrieval(),
    ) == extract_evidence_features(
        contaminated,
        retrieval(),
    )


def test_current_policy_abstains_even_on_strong_retrieval():
    result = EvidenceSufficiencyEngine().assess(
        ticket(),
        retrieval(),
    )

    assert result["status"] == STATUS_UNVERIFIED

    assert result["sufficient"] is None

    assert (
        result["reason_code"]
        == REASON_DEVELOPMENT_EVIDENCE_INSUFFICIENT
    )

    assert result["confidence"] is None

    assert result["policy_version"] == EVIDENCE_POLICY_VERSION

    assert result["feature_version"] == EVIDENCE_FEATURE_VERSION


def test_empty_retrieval_is_explicitly_insufficient():
    result = EvidenceSufficiencyEngine().assess(
        ticket(),
        [],
    )

    assert result["status"] == STATUS_INSUFFICIENT
    assert result["sufficient"] is False
    assert result["reason_code"] == REASON_NO_EVIDENCE


def test_invalid_retrieval_fails_closed():
    result = EvidenceSufficiencyEngine().assess(
        ticket(),
        [
            {
                "document_id": "DOC-1",
                "passage": "text",
                "relevance_score": float("nan"),
            }
        ],
    )

    assert result["status"] == STATUS_INVALID
    assert result["sufficient"] is False
    assert result["reason_code"] == REASON_INVALID_EVIDENCE


def test_boolean_score_is_invalid():
    result = EvidenceSufficiencyEngine().assess(
        ticket(),
        [
            {
                "document_id": "DOC-1",
                "passage": "text",
                "relevance_score": True,
            }
        ],
    )

    assert result["status"] == STATUS_INVALID
    assert result["sufficient"] is False


def test_engine_never_promotes_auto_release():
    engine = EvidenceSufficiencyEngine()

    cases = [
        [],
        retrieval(),
        [
            {
                "document_id": "DOC-X",
                "passage": (
                    "Deployment rollback health timeout "
                    "resolution."
                ),
                "section": "Resolution",
                "relevance_score": 1.0,
            }
        ],
    ]

    for evidence in cases:
        result = engine.assess(
            ticket(),
            evidence,
        )

        assert result["sufficient"] is not True
