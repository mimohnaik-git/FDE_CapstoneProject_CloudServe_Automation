# Architecture Decisions

## Stage 4 retrieval stack deviation

Baseline component: Chroma local vector store

Chosen component: In-process NumPy exact cosine similarity over 170 section-aware chunks

Reason for change: The authoritative corpus has only 29 documents. Exact matrix ranking has no database lifecycle, server, telemetry, migration, or native vector-index requirement and returns the same cosine ordering needed by the application.

Evidence: The current Chroma 1.1.0 Rust backend produced a native access violation on this Windows host; legacy Chroma 0.5.4 required older HNSW/ONNX components. The selected NumPy design completed the full 500-ticket development evaluation with 16.73 ms median and 23.46 ms P95 warm-query latency.

Compatibility: NumPy 1.26.4 and PyTorch 2.2.2 were verified on Python 3.12.14 and Windows. The index is built lazily once per engine/process lifecycle from repository-relative authoritative documentation.

Evaluation impact: With MiniLM, focused chunks, and a 0.30 retrieval floor, development Recall@1/3/5 was 0.762/0.887/0.913 and MRR was 0.918, compared with lexical-baseline 0.679/0.877/0.896 and 0.867. No-result rate was 0.8% rather than the lexical baseline's forced-result 0%.

A1-A12 impact: Improves A1 installation reliability, satisfies A4 identifiable semantic passages, exposes scores for A5, preserves source data for A6, keeps arbitrary-count evaluation compatible with A9/A10, and fails closed for A11.

Baseline component: sentence-transformers 2.2.2 with all-MiniLM-L6-v2

Chosen component: sentence-transformers 5.7.0 with Transformers 4.57.6, PyTorch 2.2.2, and all-MiniLM-L6-v2

Reason for change: The legacy runtime pin is obsolete on the current Python ecosystem. The newest 6.0.1 runtime was also rejected because Transformers 5.16 disabled the declared PyTorch 2.2 floor in this environment and failed import; 5.7.0 is the smallest recent compatible runtime tested. MiniLM itself was retained because measured project performance and resource use were strongest overall.

Evidence: MiniLM Recall@3 was 0.888 with approximately 90.9 MB of parameters and 25.00 ms experiment P95. BGE-small scored 0.885/0.922 Recall@3/MRR at approximately 133.4 MB and 48.91 ms P95; E5-small scored 0.882/0.917 at approximately 133.4 MB and 47.66 ms P95.

Compatibility: Imports and inference were verified on Windows, Python 3.12.14, and CPU-only PyTorch 2.2.2. Model weights run locally after initial acquisition.

Evaluation impact: MiniLM beat both alternatives on the primary Recall@3 selection criterion, ran at roughly half their latency, and used about 32% fewer parameter bytes.

A1-A12 impact: The explicit compatible pins improve A1 reproducibility; local inference supports A4, A9, and A11 without provider cost or rate limits. A clean checkout still requires initial model acquisition unless weights are pre-provisioned.

## Post-validation runtime evidence-sufficiency stage

The current post-validation runtime adds an explicit stage between retrieval and routing:

```text
Ticket
  -> Normalize
  -> Classify
  -> Retrieve authoritative documentation
  -> EvidenceSufficiencyEngine
  -> Deterministic router
  -> Grounded generation
  -> Output guardrails
  -> Release or escalation
  -> Audit persistence
```

`EvidenceSufficiencyEngine` receives only legitimate runtime ticket and retrieval fields. Benchmark targets including `answerable_from_docs`, `expected_doc_ids`, `expected_route`, and `must_not_auto_respond` are not inference inputs.

The engine records retrieval-strength, lexical-support, document-count, section, and related diagnostics. Under the current policy it does not emit `sufficient=True`. Non-empty but unverified evidence returns an abstaining state; missing or invalid evidence fails closed.

Only the internally produced evidence result is passed directly to `TicketRoutingEngine.route(...)`. Untrusted batch/caller requests cannot promote their own evidence-sufficiency assertion. The assessment is persisted in the existing routing-signals audit JSON.

This post-validation stage does not change the historical frozen-V1 validation results or the retained 0.80 classification / 0.30 retrieval thresholds.

## Post-validation supervised-review runtime remediation

After the evidence-sufficiency remediation, engineering continued on a separate post-validation runtime-remediation branch. These changes do not alter the frozen validation evidence or promote a new automatic-release policy.

The current supervised-review path is:

```text
Authenticated ticket request
  -> Normalize
  -> Classify
  -> Retrieve authoritative documentation
  -> Evidence sufficiency
  -> Deterministic route
  -> Grounded generation when applicable
  -> Guardrails
  -> Persist terminal decision
  -> Safe public projection
       |
       +-- if evidence remains unverified and generation is grounded/safe:
             create INTERNAL_REVIEW_ONLY handoff
             -> ephemeral TTL-bounded process-local handoff store
             -> reviewer-authenticated lookup by decision_id
             -> immutable APPROVE_DRAFT / REJECT_DRAFT audit event
             -> delete ephemeral handoff after successful review action
```

The reviewer endpoint retrieves the exact handoff produced by the original ticket execution. It does not rerun classification, retrieval, generation, guardrails, or decision logging. Reviewer drafts are excluded from the canonical SQLite decision record.

The process-local handoff cache is bounded and ephemeral. If the process restarts or a handoff expires, the draft is lost and the original ticket remains safely escalated. The immutable reviewer action persists only the linked decision ID, pseudonymous reviewer identity, action, timestamp, and review-event ID.

`APPROVE_DRAFT` is an audit decision only. It does not change the original terminal action, does not set `response_released=True`, and does not send or publish a customer response. No customer-send/release endpoint exists in the review workflow.

### API operational boundaries

- `/health` is liveness only and does not initialize inference dependencies.
- `/ready` verifies successful pipeline construction and mandatory audit-store initialization without claiming provider/network availability.
- `/tickets/process` requires `SUPPORT_API_KEY`.
- reviewer endpoints require the distinct `SUPPORT_REVIEWER_API_KEY`.
- application rate limiting is process-local and bounded; it is not a distributed gateway or denial-of-service control.
- pipeline initialization failures return a sanitized HTTP 503 rather than leaking constructor/provider/storage diagnostics.

These are post-validation engineering controls for a supervised-pilot architecture. They are not production-availability, production-security, or business-outcome measurements.
