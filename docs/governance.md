# Operational Governance — Frozen V1 and Post-Validation Pilot Controls

This document governs the operational API around frozen V1. It does not change
classifier, retrieval, routing, generation, prompt, guardrail, or evaluation behavior.

## Ownership and responsibilities

| Role | Responsibilities |
|---|---|
| System Owner | Accepts deployment risk, approves policy changes and validation claims, owns customer-impact decisions. |
| On-call Operator | Monitors alerts, activates the kill switch, contains incidents, preserves evidence, and escalates to the System Owner. |
| Support Operations Lead | Owns human escalation queues, customer communications, and backlog continuity. |
| Security Lead | Leads private-data, prompt-injection, credential, and unsafe-output incidents. |
| ML/Evaluation Owner | Investigates drift and measured quality without tuning on validation evidence. |
| Platform Owner | Owns API runtime, provider connectivity, Prometheus/Grafana, storage, backup, and recovery. |

Named individuals are evidence not available; deployment must assign people to every
role before customer traffic is enabled.

## Risk register

| Risk | Likelihood | Impact | Existing mitigation | Owner |
|---|---|---|---|---|
| Confident but wrong answer | Medium | High | Threshold routing, retrieval grounding, output guardrails, citations, kill switch | ML/Evaluation Owner |
| Private-data exposure | Low | Critical | Input/output guardrails, response allowlist, minimized logs, kill switch | Security Lead |
| Prompt injection treated as instruction | Medium | High | System/user separation, input and output injection checks, escalation | Security Lead |
| Uneven quality across groups | Medium | High | Explicit-field fairness reports and human evaluation; no inferred attributes | ML/Evaluation Owner |
| Stale documentation | Medium | High | Authoritative corpus boundary and corpus fingerprint; disable automation during corpus incidents | System Owner |
| Provider unavailability | Medium | Medium | Offline mode, bounded provider timeout, fail-closed escalation, failure metrics | Platform Owner |
| Latency degradation under load | Medium | Medium | Histogram, rolling P50/P95, failure metrics; load evidence still required | Platform Owner |
| Unexpected cost growth | Low | Medium | One generation attempt, automation-rate monitoring, provider usage review | System Owner |
| Audit-log persistence failure | Low | Critical | Response suppression and safe escalation when persistence is unavailable | Platform Owner |
| Unsafe output release | Low | Critical | Blocking guardrails, response-release allowlist, kill switch, incident procedure | Security Lead |

Likelihood and impact are governance assessments, not observed incident rates.

## API access and reviewer controls

Post-validation runtime remediation adds application-level bearer authentication
around ticket processing and a separate credential boundary for human review.

- SUPPORT_API_KEY authorizes normal ticket processing.
- SUPPORT_REVIEWER_API_KEY authorizes internal review access.
- The reviewer credential must be distinct from the processing credential.
- Reviewer identity is persisted only as a pseudonymous credential fingerprint.
- SUPPORT_API_RATE_LIMIT_PER_MINUTE provides a bounded single-process application
  rate limit.

These controls reduce accidental or unauthenticated access during a supervised
pilot. They do not establish production-grade identity federation, individual-user
RBAC, distributed rate limiting, gateway protection, or denial-of-service
resilience.

## Human-review governance

Only safe evidence-unverified escalations that have grounded generation and passing
output guardrails can produce an INTERNAL_REVIEW_ONLY draft.

The ordinary customer-processing response never exposes that draft. The draft is
held in a bounded process-local ephemeral store and is retrieved later by
decision_id through the reviewer-authenticated API. Retrieval does not rerun the
model pipeline.

A reviewer can record exactly one immutable action:

- APPROVE_DRAFT
- REJECT_DRAFT

The review action is linked to the original decision record and persisted without
the draft text. Successful review removes the ephemeral draft.

APPROVE_DRAFT is not a customer-send authorization implemented by this service.
It does not mutate the original pipeline decision, does not change
`response_released`, and does not create a customer-facing response. Any future
delivery mechanism would require a separate governed design, authorization model,
idempotency contract, delivery audit, and evaluation.

Because the review draft store is process-local, restart or expiry can remove an
unreviewed draft. This fails safely because the ticket remains escalated. A durable
human-review queue has not been implemented or operationally measured.

## Deterministic kill switch

Mechanism: the API checks `storage/auto_response.disabled` before every ticket. The
On-call Operator, Security Lead, Platform Owner, and System Owner are authorized to
create it. Creation takes effect on the next request without a deployment or restart.
Tickets already past the check may finish; during a suspected unsafe-release event,
also remove traffic at the gateway until in-flight work drains.

Enable from the project root:

    New-Item -ItemType File -Path storage/auto_response.disabled -Force

Verify by sending a synthetic ticket: it must return `ESCALATE`, reason
`KILL_SWITCH_ENABLED`, no response/citations, and a decision ID. Prometheus should
increment the escalation counter. Disable only after owner approval by removing that
exact file, then verify a synthetic request follows normal frozen behavior. The file
is ignored by Git so operational state cannot become a deployed default accidentally.

If kill-switch audit persistence fails, the API still suppresses the response and
returns `AUDIT_PERSISTENCE_FAILED`; the operator must keep the switch enabled and
repair logging before restoring traffic.

## Incident response procedure

1. **Detect:** Alert or operator identifies unsafe output, private data, provider
   failure, elevated failures/latency, or missing audit decisions. Record time and
   dashboards without copying customer content into metrics or chat.
2. **Contain:** Activate the kill switch. For possible data disclosure, also stop
   ingress and revoke exposed credentials. Preserve logs and decision IDs.
3. **Assess:** Identify affected time window, channels, terminal actions, decision
   IDs, provider, corpus/config fingerprints, and whether any response was released.
4. **Notify:** On-call notifies System Owner and Support Operations. Notify Security
   Lead for unsafe output/private data and Platform Owner for provider/logging faults.
   Customer or regulatory notification is decided by authorized owners, not the model.
5. **Remediate:** Restore provider/cache/storage from approved configuration or roll
   back the operational deployment. Any inference-policy change invalidates the frozen
   fingerprint and requires a new governed evaluation cycle.
6. **Review:** Document cause, affected decisions, recovery proof, follow-up tests,
   owner, and due date. Do not delete or rewrite evaluation evidence.

### Incident-specific actions

- **Provider outage:** keep tickets escalated, confirm provider failure metrics, use
  offline mode only if already approved, and never silently substitute a model.
- **Audit-log failure:** suppress automation, protect the database/WAL, check capacity
  and permissions, restore from the approved backup, then prove write/read-back.
- **Unsafe output:** activate kill switch, identify released decision IDs, preserve
  cited evidence and guardrail records, involve Security Lead, and do not tune against
  validation artifacts.

## Rollback and recovery

Operational API/monitoring releases should be versioned independently of frozen V1.
Rollback restores the last known-good operational package and compatible database.
SQLite database, WAL, and SHM files must be backed up consistently while writes are
quiesced. Recovery requires a synthetic audited escalation, a disabled/enabled kill
switch test, `/health`, and `/metrics` checks before ingress is restored.

## Monitoring and alerting expectations

Prometheus scrapes `/metrics`; the Grafana dashboard uses controlled-label counters,
rates, histograms, rolling latency quantiles, guardrail blocks, failures, and confidence
buckets. Initial alert expectations are: any audit-persistence or unsafe-output event
pages the on-call operator; sustained failure-rate or P95 latency changes require
investigation; confidence-distribution shifts require evaluation-owner review.

Exact alert thresholds, availability, alert delivery, and response-time performance
are **NOT MEASURED**. They must be established by load tests and an operational
observation period before production claims are made.

## System declaration

- The system must never release an unaudited or guardrail-blocked response.
- Fail-closed routing, response suppression, persistent audit logging, and the kill
  switch enforce this boundary.
- The most likely remaining harm is a grounded but incomplete response that delays
  resolution or is accepted despite a missed semantic defect.
- Do not deploy beyond a bounded supervised setting without named owners, tested
  alerts/backups, production-grade identity and authorization, distributed/edge rate
  controls, a durable reviewer queue where required, load testing, and a rehearsed
  incident/kill-switch exercise.
