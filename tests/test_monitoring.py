from src import monitoring


def test_required_operational_metrics_are_exposed():
    monitoring.observe({
        "route": "AUTO_RESPOND",
        "channel": "email",
        "total_latency_s": 0.05,
        "intent": {"label": "api_usage_question", "confidence": 0.87},
        "urgency": {"label": "medium", "confidence": 0.61},
        "answerability": {"label": "answerable", "confidence": 0.91},
        "guardrails": {"blocks": ["prompt_injection"]},
        "error": None,
    })

    body = monitoring.exposition()

    required = (
        b"cloudserve_decisions_total",
        b"cloudserve_guardrail_blocks_total",
        b"cloudserve_pipeline_seconds_bucket",
        b"cloudserve_prediction_confidence_bucket",
    )

    for metric in required:
        assert metric in body


def test_confidence_histogram_has_all_classifier_labels():
    monitoring.observe({
        "route": "ESCALATE",
        "channel": "chat",
        "total_latency_s": 0.02,
        "intent": {"confidence": 0.72},
        "urgency": {"confidence": 0.55},
        "answerability": {"confidence": 0.81},
        "guardrails": {"blocks": []},
        "error": None,
    })

    body = monitoring.exposition()

    assert b'classifier="intent"' in body
    assert b'classifier="urgency"' in body
    assert b'classifier="answerability"' in body
