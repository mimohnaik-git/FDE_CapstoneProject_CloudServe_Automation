"""Prometheus metrics. No-ops cleanly if prometheus_client is absent."""
from __future__ import annotations

import math

try:
    from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest

    REGISTRY = CollectorRegistry()

    DECISIONS = Counter(
        "cloudserve_decisions_total",
        "Routing decisions",
        ["route", "channel", "run_mode"],
        registry=REGISTRY,
    )

    BLOCKS = Counter(
        "cloudserve_guardrail_blocks_total",
        "Guardrail blocks",
        ["guardrail", "run_mode"],
        registry=REGISTRY,
    )

    FAILURES = Counter(
        "cloudserve_failures_total",
        "Handled failures",
        ["kind", "run_mode"],
        registry=REGISTRY,
    )

    LATENCY = Histogram(
        "cloudserve_pipeline_seconds",
        "Pipeline latency",
        ["run_mode"],
        registry=REGISTRY,
        buckets=(.01, .025, .05, .1, .2, .5, 1, 2, 5),
    )

    CONFIDENCE = Histogram(
        "cloudserve_prediction_confidence",
        "Prediction confidence by classifier",
        ["classifier", "run_mode"],
        registry=REGISTRY,
        buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
    )

    ENABLED = True

except ImportError:  # pragma: no cover
    ENABLED = False
    generate_latest = None


def _observe_confidence(decision: dict, classifier: str, run_mode: str) -> None:
    prediction = decision.get(classifier) or {}
    value = prediction.get("confidence")

    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return

    value = float(value)

    if not math.isfinite(value):
        return

    value = min(1.0, max(0.0, value))
    CONFIDENCE.labels(classifier, run_mode).observe(value)


def observe(decision: dict, run_mode: str = "normal") -> None:
    if not ENABLED:
        return

    run_mode = run_mode if run_mode in {"normal", "demo", "evaluator"} else "normal"
    DECISIONS.labels(
        decision["route"],
        decision.get("channel") or "unknown",
        run_mode,
    ).inc()

    LATENCY.labels(run_mode).observe(decision.get("total_latency_s", 0.0))

    for classifier in ("intent", "urgency", "answerability"):
        _observe_confidence(decision, classifier, run_mode)

    guardrails = decision.get("guardrails") or {}
    for block in guardrails.get("blocks", []):
        BLOCKS.labels(block, run_mode).inc()

    if decision.get("error"):
        FAILURES.labels(decision["error"].split(":")[0], run_mode).inc()


def exposition() -> bytes:
    if not ENABLED:
        return b""

    assert generate_latest is not None
    return generate_latest(REGISTRY)
