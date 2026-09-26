"""Prometheus metrics. No-ops cleanly if prometheus_client is absent."""
from __future__ import annotations

try:
    from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest
    REGISTRY = CollectorRegistry()
    DECISIONS = Counter("cloudserve_decisions_total", "Routing decisions",
                        ["route", "channel"], registry=REGISTRY)
    BLOCKS = Counter("cloudserve_guardrail_blocks_total", "Guardrail blocks",
                     ["guardrail"], registry=REGISTRY)
    FAILURES = Counter("cloudserve_failures_total", "Handled failures",
                       ["kind"], registry=REGISTRY)
    LATENCY = Histogram("cloudserve_pipeline_seconds", "Pipeline latency",
                        registry=REGISTRY,
                        buckets=(.01, .025, .05, .1, .2, .5, 1, 2, 5))
    ENABLED = True
except ImportError:  # pragma: no cover
    ENABLED = False
    generate_latest = None


def observe(decision: dict) -> None:
    if not ENABLED:
        return
    DECISIONS.labels(decision["route"], decision.get("channel") or "unknown").inc()
    LATENCY.observe(decision.get("total_latency_s", 0.0))
    g = decision.get("guardrails") or {}
    for b in g.get("blocks", []):
        BLOCKS.labels(b).inc()
    if decision.get("error"):
        FAILURES.labels(decision["error"].split(":")[0]).inc()


def exposition() -> bytes:
    if not ENABLED:
        return b""
    assert generate_latest is not None
    return generate_latest(REGISTRY)
