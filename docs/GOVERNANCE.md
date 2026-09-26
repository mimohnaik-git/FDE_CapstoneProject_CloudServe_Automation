# CloudServe governance controls

This document describes implemented controls and proposed operating roles. No
deployment, incident, human review, or owner approval is claimed to have
occurred. Where the supplied evidence does not establish an operational fact,
the status is `Evidence not available`.

## Deployment position

Automatic customer release is disabled by default. The mechanism is the
`CLOUDSERVE_AUTO_RESPONSE_ENABLED` environment switch. A false or missing value
forces escalation. The evaluation CLI can exercise the same auto-response policy
with `--enable-auto-policy` without changing the production default.

An enabled running process can be contained immediately through the one-way
`Pipeline.emergency_disable_auto_response()` latch. Once invoked, all subsequent
would-be automatic responses escalate. It cannot re-enable automation; restart
and the normal configuration gate are required. A production operator endpoint,
its authentication, and authorized operator assignments are `Evidence not
available` and must be established before deployment.

## Risk register

Owners below are proposed roles, not confirmed assignments.

| ID | Risk | Likelihood | Impact | Implemented mitigation | Proposed owner |
|---|---|---|---|---|---|
| R-01 | Confident incorrect answer | Medium | High | Evidence threshold, cited resolution steps, grounding and citation checks, fail-closed route | Support lead |
| R-02 | Private data or secret in outbound text | Medium | Critical | Secret/card/password patterns block and escalate; no raw customer text in trace | Security lead |
| R-03 | Ticket content redirects system instructions | Medium | High | Ticket and instruction separation; injection detection blocks | Engineering lead |
| R-04 | Unequal quality across customer groups | Medium | High | Subgroup metrics with minimum sample gate and `NOT_PROVEN` state | Support operations |
| R-05 | Stale documentation produces stale advice | Medium | High | Runtime knowledge restricted to identifiable KB documents; document ID preserved for correction | Documentation owner |
| R-06 | Provider unavailable or rate limited | Medium | Medium | Deterministic local generator; optional provider failures fall back without stopping the run | Engineering lead |
| R-07 | Latency degrades under load | Medium | Medium | Per-stage timing, p50/p95/max reporting, warm-up separated | Engineering lead |
| R-08 | Automation is enabled without adequate evidence | Low | Critical | Safe default off, explicit switch, one-way runtime disable latch, configuration fingerprint, must-not-auto evaluation gate | Support lead |
| R-09 | Audit persistence fails after an automatic route is selected | Low | Critical | Final decision is changed to escalation before fallback persistence and monitoring | Engineering lead |

Likelihood and impact are engineering assessments, not stakeholder ratings.

The frozen C1 automatic-response allowlist is API usage questions, data export,
onboarding, SSO configuration, billing queries, and quota or overage questions.
`rate_limit` remains excluded after the earlier development OOF false AUTO.
The C1 policy also fails closed when symptom evidence materially dominates
resolution evidence. This is engineering policy derived from development
evidence, not stakeholder-approved scope.

The final group-isolated C1 development OOF result produced 18 AUTO routes with
zero false AUTO and zero must-not-auto violations. The frozen C1 Validation-80
run produced eight AUTO routes with zero false AUTO and zero must-not-auto
violations. This does not establish a production-release claim: calibration and
human-review release blockers remain, and the operational release switch remains
OFF.

## Decision record

Each processed ticket produces one persistent record containing predictions,
confidence and alternatives, retrieved passages and scores, evidence status,
draft and citations, guardrail results, route and all failed gates, per-stage
latency, configuration fingerprint, policy versions, thresholds, requirements,
run ID, UTC decision timestamp, the passages supplied to generation, and a
SHA-256 fingerprint of normalized input. Raw ticket text and customer name are
not copied into the trace record. Guardrail records name both passing and
blocking controls. On primary audit failure, the same final escalation payload
is written to the fallback log where filesystem persistence remains available.

## Incident procedure

1. Detect: use decision-log reconciliation, guardrail counters, error metrics,
   and customer or agent reports.
2. Contain: invoke the one-way runtime disable latch for the affected process,
   then set `CLOUDSERVE_AUTO_RESPONSE_ENABLED=false` and restart the service.
   All subsequent decisions then escalate.
3. Assess: preserve the decision database and config fingerprint; identify the
   affected ticket IDs, document IDs, prompt version, and policy reasons.
4. Notify: the assigned incident owner informs support, engineering, security,
   documentation, and affected customers according to the established company
   incident policy. That company policy is not present in the supplied evidence.
5. Remediate: fix the relevant document, policy, model artifact, or guardrail;
   add a regression test tied to the incident.
6. Review: run the unattended evaluation, reconcile logs, obtain approval, and
   only then consider re-enabling automatic release.

The exact restart time, authorized kill-switch operators, production alerting
path, and customer notification SLA are `Evidence not available`; these must be
assigned before deployment.

## Release gate

Do not enable customer release unless a held-out run records zero
must-not-auto violations, an accepted automatic-response precision with its
denominator, complete decision-log coverage, and reviewed subgroup results.
Human hallucination review, live customer satisfaction, production availability,
and observed business impact are not supplied and must not be inferred from the
automated evaluation.

The frozen run does not satisfy the calibration release condition: maximum
confidence-band gaps exceed five percentage points for intent, urgency, and
answerability. Current-candidate human semantic citation and hallucination
review is also not available. These are release blockers even though automated
citation resolvability was 200/200. The final automated reference audit recorded
104/118 must-mention items, 52/59 fully satisfied references, zero prohibited
claims, and zero lexical-grounding failures. The seven incomplete references
comprise six retrieval misses and one reference ambiguity; they are not hidden
by the evaluator.

Historical human review is traceable at immutable commit
`65f71c3fd10603421566fb786b452fdd2aa4b57b`, but evaluates earlier development
candidates and cannot clear the current-candidate human-review gate. A controlled
local Prometheus/Grafana exercise demonstrated live movement in route, guardrail,
failure, and latency panels. It does not establish production availability,
alert delivery, or business outcomes.
