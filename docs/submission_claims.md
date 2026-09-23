# Submission Claim Register

This register is the submission-facing source of truth as of 11 September 2026. Every
performance statement must name its evidence class and denominator. Historical
discovery measurements are not system outcomes, local technical tests are not
operational evidence, and missing evidence must remain NOT MEASURED.

## Claim classifications

| Classification | Meaning |
|---|---|
| MEASURED | Directly calculated from the named evidence; not necessarily validation or production evidence. |
| VALIDATION | Measured on the frozen V1 authorized technical validation rerun. |
| DEVELOPMENT ONLY | Measured using development data or development response candidates; not validation or production. |
| OPERATIONAL | An implemented operational control or observation. Configuration alone does not prove service performance. |
| NOT MEASURED | No eligible evidence supports a numeric result. |
| LIMITATION | A material constraint, failure, missing deliverable, or scope boundary. |

## Reconciled claims

| Topic | Submission-safe claim | Classification | Evidence and denominator |
|---|---|---|---|
| Frozen V1 | V1 fingerprint is `ddf89e82e7340a0257ee0c2ae1ce340612070545bc04f559e1e4c3ad733f59c1`; thresholds are 0.80/0.30. | MEASURED | Stage 12/15 freeze manifests and current fingerprint calculation. |
| Validation attempt disclosure | Attempt 1 failed because of embedding-cache infrastructure. Attempt 2 was the single owner-authorized technical rerun; no tuning occurred between attempts. | VALIDATION | Stage 13 failure evidence, Stage 14 adjudication, Stage 15 manifest, Stage 16 artifacts. |
| Validation reconciliation | 80 source, 80 evaluated, 80 terminal, and 80 decision records reconciled. | VALIDATION | `validation-technical-rerun.json`; n=80. |
| Intent classification | Accuracy, macro precision, macro recall, and macro F1 were each 100%. | VALIDATION | 80 validation tickets. |
| Urgency classification | Accuracy was 42.5% and macro F1 was 41.4%; both failed their formal targets. | VALIDATION | 80 validation tickets. |
| Retrieval | Recall@1/3/5 was 76.4%/87.7%/88.7%; Precision@1/3/5 was 90.6%/36.8%/25.6%; MRR was 92.8%. | VALIDATION | 53 validation tickets with expected-document labels. |
| Routing | Routing accuracy was 40%. | VALIDATION | 80 validation tickets; FAIL. |
| V1 automation | Automation was 0%; escalation was 100%. Auto-response recall was 0%, and precision was NOT MEASURED because there were no predicted automatic responses. | VALIDATION | 80 validation tickets. Escalation target <=30% failed. |
| Reliability | Processing failure rate was 0% and decision-log coverage was 100%. | VALIDATION | 80 validation tickets/terminal decisions. |
| Latency | Local sequential pipeline P50/P95 was 0.0502s/0.0915s. | VALIDATION | 80 validation tickets. This is not first-response time, load, or availability evidence. |
| Calibration | Expected calibration error was 42.3%. | VALIDATION | 80 validation tickets; FAIL. |
| Validation hallucination | Hallucination rate was NOT MEASURED because validation released zero responses. | NOT MEASURED | No eligible validation response population. |
| Validation semantic citation accuracy | Semantic citation accuracy was NOT MEASURED because validation released zero responses. | NOT MEASURED | No eligible validation response population. Automated citation-ID validity must not be called citation accuracy. |
| Human-development hallucination | Hallucination rate was 2% (1/50) and passed the <=5% target. | DEVELOPMENT ONLY | 50 HUMAN DEVELOPMENT EVALUATION candidates, two independent reviewers. |
| Human-development semantic citations | Semantic citation accuracy was 98% (49/50) and passed the >=95% target. | DEVELOPMENT ONLY | 50 HUMAN DEVELOPMENT EVALUATION candidates, two independent reviewers. |
| Response quality | Correctness was 3.74/5 and usefulness was 2.87/5, with no formal targets. | DEVELOPMENT ONLY | 100 reviewer ratings over 50 candidates; not validation auto-response performance. |
| Fairness | Only explicit tier/fluency fields and a deterministic text-length grouping were used. Validation enterprise n=8 and non-fluent n=19 were below minimum n=20. | LIMITATION | Stage 18 fairness report. Underpowered groups and cross-group human quality are NOT MEASURED. |
| V2 | V2 was a rejected development experiment, not a candidate for production or validation. | DEVELOPMENT ONLY | Stage 20: calibration improved, but no policy met zero-false-auto safety; best observed policy had 18 false auto-responses. |
| API and supervised-review controls | FastAPI implements `/health`, `/ready`, authenticated `/tickets/process`, `/metrics`, exact reviewer handoff retrieval by `decision_id`, and immutable reviewer action recording. Processing and reviewer credentials are distinct, and bounded single-process application rate limiting is regression tested. | POST-VALIDATION ENGINEERING | Local regression tests only. `/health` is liveness, `/ready` verifies pipeline/audit initialization only, reviewer approval is audit-only, and these controls do not establish production IAM/RBAC, distributed rate limiting, gateway protection, provider availability, or production readiness. |
| Kill switch | The deterministic kill switch suppresses AUTO_RESPOND, escalates with an explicit reason, and keeps decision logging active. | OPERATIONAL | Local synthetic tests; fleet propagation and operator response time are not measured. |
| Monitoring | Prometheus-compatible metrics and Grafana-ready configuration exist. | OPERATIONAL | Local tests/configuration only; scrape retention, alert delivery, and response performance are NOT MEASURED. |
| CI | GitHub Actions CI was observed passing on `main` commit `b97f40bd308127fc7569b79e97ed5a297f226c1b` (run `34617707232`). Checkout, Python 3.12 setup, dependency installation, `pip check`, offline clean-checkout smoke, and the complete pytest suite all succeeded. | OPERATIONAL | GitHub Actions workflow `CI`, run `34617707232`, conclusion `success`. This is hosted CI evidence, not production availability evidence. |
| Historical FCR/CSAT | Development discovery recorded historical FCR 43.8% and mean historical CSAT 2.97/5. These are dataset baselines, not outcomes of V1. | DEVELOPMENT ONLY | 500 supplied development tickets. |
| System FCR | System-attributable FCR is NOT MEASURED. | NOT MEASURED | No linked resolution/follow-up outcomes. |
| System CSAT | System-attributable CSAT is NOT MEASURED. | NOT MEASURED | No attributable customer ratings. |
| Availability | Service availability is NOT MEASURED. | NOT MEASURED | No deployed observation window. |
| First-response time | Customer first-response time is NOT MEASURED. | NOT MEASURED | Local pipeline latency is not this metric. |
| Load behavior | Concurrent/load performance is NOT MEASURED. | NOT MEASURED | No representative load test. |
| Alerting performance | Alert delivery, acknowledgement, and response performance are NOT MEASURED. | NOT MEASURED | Configuration and unit tests only. |
| Business outcomes | Cost, ticket deflection, resolution, satisfaction improvement, and other V1 business outcomes are NOT MEASURED. | NOT MEASURED | No production or controlled-pilot outcome study. |

## Prohibited shorthand

Do not use any of these statements in submission materials:

- “Validation hallucination was 0%.”
- “Guardrails achieved 0% hallucination across all evaluation runs.”
- “Citation-ID validity proves citation accuracy.”
- “V2 is a development candidate” or “V2 improved production.”
- “V1 achieved automation” or omit its 100% escalation rate.
- “CI passes” as a general production-reliability claim; one observed hosted CI run does not prove production availability or ongoing service performance.
- “The system improved FCR/CSAT/availability/response time.”
- “Local P95 latency proves load capacity, availability, or customer first-response time.”

## Source-of-truth precedence

For Stage 13/16 validation, the immutable evaluation JSON and Markdown artifacts take
precedence over narrative documents. For human metrics, the Stage 18 aggregate takes
precedence. For V2, the Stage 20 JSON decision takes precedence. Historical artifacts
may retain the state known when generated and must not be rewritten; submission-facing
documents must explain later evidence explicitly.

## Post-validation evidence-sufficiency claim reconciliation

The repository now contains an explicit inference-time evidence-sufficiency stage.
This is a post-validation engineering remediation and is not a new validation result.

Permitted current claim:

> The current runtime computes evidence-sufficiency diagnostics internally and records
> them in the audit trail, but it intentionally fails closed because development-only
> experiments did not establish a defensible high-precision automatic-release policy
> with meaningful independent coverage.

Claims that remain unsupported:

- that safe non-zero automation has been proven;
- that the evidence-sufficiency stage has been validated on a fresh independent
  validation population;
- that the current branch improves the historical 0% validation automation result;
- that validation hallucination, citation quality, FCR, CSAT, production reliability,
  or other previously unmeasured outcomes are now measured;
- that the hidden/final assessment has been accessed.

Historical frozen-V1 validation remains 0% automation and 100% escalation. The
deployment recommendation remains **LIMITED SUPERVISED PILOT - NOT PRODUCTION-READY**.

Post-validation runtime remediation added safe internal escalation handoffs,
same-document Resolution support for grounded generation, application-level bearer
authentication, a separate reviewer credential, bounded single-process rate limiting,
fail-closed readiness checks, exact ephemeral handoff retrieval, and immutable
`APPROVE_DRAFT` / `REJECT_DRAFT` review auditing. The local regression suite reached
425 passing tests. These are post-validation engineering results only: validation was
not rerun, the hidden/final assessment was not accessed, no automatic-release threshold
was promoted, reviewer approval does not send a customer response, and no new
validation-quality, availability, business-outcome, or production-readiness claim is
created.
