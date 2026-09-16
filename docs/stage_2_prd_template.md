# Stage 2 — Product Requirements Document

## 1. Document control

| Field | Value |
|---|---|
| Product | CloudServe controlled support automation system |
| Original baseline | Version 1.0, 4 September 2026 |
| Final reconciliation | Version 2.0, 12 September 2026 |
| Owner | Mimoh Naik |
| Owner review | Complete; approved 12 September 2026 |
| Deployment decision | LIMITED SUPERVISED PILOT only |
| Production status | NOT PRODUCTION-READY |
| Frozen V1 fingerprint | ddf89e82e7340a0257ee0c2ae1ce340612070545bc04f559e1e4c3ad733f59c1 |

Version 1.0 was the discovery-derived implementation baseline. Version 2.0 reconciles it with frozen V1, authoritative evaluation evidence, and completed owner review without rewriting what was known during discovery or changing V1.

## 2. Problem statement

Carried forward from the reconciled Stage 1 workbook:

> CloudServe's support team faces workload and response-delay pressure: Marcus reported more than 500 tickets a week for six agents, a two-hour response agreement, and an eight-to-twelve-hour average response, while Ravi described waits that could extend until the next day. In the supplied historical development data, only 43.8% of tickets were marked resolved on first contact even though 71.4% were labelled answerable from reviewed documentation. Sofia and Ines described a gap between having reviewed knowledge-base articles and being able to find them, with agents relying on unreviewed personal answer files; Daniel described escalations that often lacked context. CloudServe therefore needs a controlled way to help agents locate reviewed information, communicate uncertainty, and provide structured escalation context while avoiding unsupported, unsafe, or unaccountable customer communication.

These percentages are historical development-data baselines, not system results. Later evaluation findings are identified separately below.

## 3. Users and stakeholders

| User or stakeholder | Evidence-supported need |
|---|---|
| Tier 1 support agents | Faster access to reviewed documentation, explicit uncertainty, and help with repetitive answerable requests. |
| Tier 2 specialists | Escalations with enough context to avoid restarting investigation. |
| Support management | A controlled, measurable, auditable workflow and a safe automation/escalation balance. |
| Customers across the four supported channels | Timely, consistent, grounded communication without unsupported promises or protected-data disclosure. |
| Technical writing / knowledge management | Reviewed knowledge-base content as authority, with content gaps surfaced. |

Security, legal, and operations are future deployment responsibilities, not presented as interviewed personas without evidence.

## 4. Functional requirements and traceability

The original functional intent is retained. Weak outcomes are reported rather than hidden by rewriting requirements.

| ID | Original requirement | Frozen V1 mapping and acceptance evidence | Status |
|---|---|---|---|
| FR-01 | Ingest email, live chat, documentation comments, and community forum tickets into a normalized representation while preserving channel. | src/ingest.py; ingestion/pipeline tests and A2 evidence cover all four channels and malformed input. | PASS |
| FR-02 | Give every valid ticket intent, urgency, and meaningful confidence. | src/classify.py uses TF-IDF word/character logistic regression. Tests and all 80 authoritative validation records contain the fields. Urgency accuracy was 42.5% and macro F1 approximately 41.4%. | PASS functionally; urgency quality weak |
| FR-03 | Retrieve identifiable relevant passages from reviewed documentation, with ranking and a legitimate no-result outcome. Original baseline proposed MiniLM, Chroma, and BM25/hybrid retrieval. | src/retrieve.py uses MiniLM plus NumPy exact cosine; tests cover sources and no-result behavior. Authoritative validation Recall@3 was 87.7% on 53 eligible tickets. | PASS; architecture explicitly revised |
| FR-04 | Route deterministically to automatic response, manual review, or escalation using confidence, answerability, risk, retrieval, and guardrails. | src/route.py and explicit orchestration expose AUTO_RESPOND or ESCALATE; escalation is the human-review path. Tests support A5. Validation routing accuracy was 40%, automation 0%, escalation 100%. | PARTIAL versus original three-state wording; A5 two-outcome contract passes, quality target does not |
| FR-05 | Generate concise, grounded responses with claim-supporting citations and uncertainty where required. | src/generate.py and generation/citation tests support A6. The completed human citation result is DEVELOPMENT ONLY; validation semantic citation accuracy is NOT MEASURED. | PASS functionally; validation human outcome not measured |
| FR-06 | Validate grounding and block/escalate unsupported output. | src/guardrails.py; guardrail/pipeline tests demonstrate blocking and A7. | PASS |
| FR-07 | Prevent credential/private-data disclosure; block and escalate unsafe output. | Private-data guardrails and security tests. No validation customer release occurred from which to establish a zero-leakage outcome. | PASS functionally; validation outcome insufficient |
| FR-08 | Treat customer content as untrusted and resist prompt injection. | Input separation and prompt-injection guardrails with adversarial tests. | PASS |
| FR-09 | Escalate high-risk cases and prevent unsupported refunds, guarantees, promises, exceptions, and commitments. | Deterministic risk routing and commitment guardrails with tests. | PASS |
| FR-10 | Provide structured escalation context including reason, classification, confidence, and relevant sources. | Pipeline/API escalation payloads and tests. Human operator usefulness is NOT MEASURED. | PASS structurally; operator outcome not measured |
| FR-11 | Persist an auditable decision record for every processed ticket without unnecessary secrets. | src/logging_store.py with SQLite; tests and 80/80 authoritative validation log coverage. | PASS |
| FR-12 | Run unattended, arbitrary-size evaluation and emit machine- and human-readable results without validation contamination. | evaluation harness/metrics/report, tests, artifacts, and hosted CI support A9/A10. Business outcomes remain NOT MEASURED. | PASS |

FR-01–03 and FR-05–12 have credible implementation and acceptance evidence. FR-04 remains PARTIAL against its original three-state product wording. A1–A12 nevertheless have credible PASS evidence under the engineering contract, whose route outcomes are AUTO_RESPOND and ESCALATE.

## 5. Non-functional requirements

| ID | Requirement / target | Evidence and status |
|---|---|---|
| NFR-01 | P95 pipeline latency below 3 seconds. | MEASURED + MET: approximately 0.0915 seconds on the authoritative local, sequential, provider-neutral validation rerun. Not load evidence. |
| NFR-02 | Production availability at least 99.5% (an earlier draft used 99.9%). | NOT MEASURED. /health and successful CI do not prove availability. Production-hardening requirement. |
| NFR-03 | Retrieval latency below 50 ms in the target local configuration. | DEVELOPMENT ONLY component evidence was below 50 ms P95. Frozen retrieval is NumPy exact cosine, not Chroma; production load evidence is absent. |
| NFR-04 | Protect secrets and validate credentials only when a credentialed provider is initialized. | Repository/configuration tests support placeholder-only configuration and no committed provider secret. Live-provider evidence is component-level only. |
| NFR-05 | Greater than 90% test coverage and one-command tests. | Pytest is the documented command and hosted CI succeeded; numeric coverage is NOT MEASURED. |
| NFR-06 | Complete persistent decision logging. | MEASURED + MET: 80/80 authoritative validation tickets logged with audit metadata. |
| NFR-07 | Protect private data and support applicable privacy obligations. | Blocking/escalation controls exist. Formal GDPR/CCPA compliance, retention, deletion, and access-control validation are not evidenced. PARTIAL; stale compliance claim removed. |
| NFR-08 | Fairness difference below 5 percentage points; earlier draft also proposed greater than 80% non-fluent-English intent performance. | Fairness evidence is preliminary; subgroup size/outcome coverage cannot prove the gate. NOT PROVEN. |
| NFR-09 | Reproducible local operation without a managed vector service or Codex dependency. | NumPy retrieval, SQLite, provider-neutral generation, documented setup, tests, and CI support PASS; model artifact provisioning remains a setup dependency. |
| NFR-10 | Modular, auditable workflow. | Separate ingestion, classification, retrieval, routing, generation, guardrail, logging, API, and evaluation modules/tests. PASS. |
| NFR-11 | Production authentication, authorization, and rate limiting. | Absent. Production-hardening gap, not an A1–A12 failure. |
| NFR-12 | Verified load, availability, alerts, backup, and recovery. | Monitoring/governance artifacts exist, but performance is NOT MEASURED. Production-hardening gap. |

## 6. Scope

### In scope

- Four-channel normalization; intent/urgency/confidence classification; reviewed-document retrieval; deterministic routing; provider-neutral grounded generation; blocking guardrails; escalation context; SQLite logging; FastAPI; monitoring/governance artifacts; Pytest; arbitrary-size unattended evaluation.

### Out of scope

- Direct account/system actions; refunds, credits, guarantees, policy exceptions, or roadmap/contract promises; treating personal answer files as authority; replacing human accountability; training/tuning on validation or hidden tickets; general-purpose conversation; editing the knowledge base.

### Production exclusions

Frozen V1 lacks production auth/authz/rate limiting, proven availability/load capacity, verified alerts, verified backup/recovery, and production business-outcome evidence. A limited supervised pilot therefore requires controlled access, human oversight, conservative escalation, decision-log review, and an operable kill switch.

## 7. Assumptions and revisions

| Original assumption / hypothesis | Later evidence | Revision |
|---|---|---|
| Documentation answerability would translate into useful safe automation. | Historical answerability was 71.4%, but validation automation was 0% and escalation 100%. | Do not equate answerability with automatable volume. |
| Confidence would be adequately calibrated. | Validation ECE was approximately 42.3 percentage points. | Calibration remains a deployment limitation. |
| Urgency classification would support reliable routing. | Validation urgency accuracy 42.5%; macro F1 approximately 41.4%. | Urgency quality remains a major blocker. |
| Strong retrieval/citations would imply useful answers. | DEVELOPMENT human review: citation 98%, hallucination 2%, correctness 3.74/5, usefulness 2.87/5. | Usefulness/correctness are separate release considerations; these are not validation results. |
| Supplied data would prove the fairness gate. | Segmentation was possible but subgroup evidence was insufficient. | Fairness remains preliminary and NOT PROVEN. |
| Chroma, BM25, and LangGraph were necessary. | The simpler frozen stack met A1–A12. | Treat reference stack as baseline, with justified departures below. |
| Local functional controls implied production readiness. | Auth and operational performance evidence are absent. | Limited supervised pilot only; NOT production-ready. |

## 8. Success measures

| Measure | Historical baseline | Target | Measured system result | Classification |
|---|---:|---:|---:|---|
| FCR | 43.8% in development data | ≥60% | NOT MEASURED | NOT MEASURED |
| First-response time | Stakeholder report: about 8–12 hours; not a formal system measure | <5 minutes | NOT MEASURED | Pipeline runtime is not substituted |
| CSAT | 2.97/5 in development data | ≥4.0/5 | NOT MEASURED | NOT MEASURED |
| Escalation | 56.2% in development data | ≤30% | 100% validation | MEASURED + NOT MET |
| Classification precision | None | ≥85% | Intent per-class precision 100%; urgency evidence materially weaker | Intent MEASURED + MET; whole classification target not demonstrated |
| Hallucination | None | ≤5% | 2% DEVELOPMENT human evaluation; validation NOT MEASURED | DEVELOPMENT ONLY |
| Semantic citation accuracy | None | ≥95% | 98% DEVELOPMENT human evaluation; validation NOT MEASURED | DEVELOPMENT ONLY |
| P95 latency | None | <3 seconds | ~0.0915 seconds local sequential validation | MEASURED + MET in that environment |
| Production availability | None | ≥99.5% | NOT MEASURED | NOT MEASURED |
| Fairness difference | None | <5 percentage points | NOT PROVEN | Insufficient evidence |
| Decision-log coverage | None | 100% | 80/80 validation | MEASURED + MET |
| Calibration error | None | ≤5 percentage points | ~42.3 percentage points ECE | MEASURED + NOT MET |

The owner set 30% as a minimum worthwhile future automation target. This is an **OWNER TARGET, NOT A MEASURED RESULT** and does not authorize weakening safety controls.

## 9. Architecture and technology

| Capability | Baseline | Frozen V1 | Justified departure / status |
|---|---|---|---|
| Classification | Provider/model examples | TF-IDF word/char logistic regression | Local, deterministic, reproducible; urgency limitation reported. |
| Embeddings | MiniLM | MiniLM | Retained. |
| Retrieval store/search | Chroma; earlier BM25 option | NumPy exact cosine | Simpler for small corpus while retaining ranking, source IDs, no-result behavior, and evaluation evidence. |
| Orchestration | LangChain/LangGraph | Explicit Python | Directly inspectable fail-closed decisions without unnecessary dependency. |
| Generation | OpenRouter/Groq examples | Provider-neutral grounded interface with offline, OpenRouter, and Groq implementations | Avoids single-provider coupling. Post-freeze hardening added provider-specific model resolution and first-class Groq credential/model/base-URL configuration; live-provider evidence remains synthetic development component evidence only. |
| API / log / tests | FastAPI / SQLite / Pytest | FastAPI / SQLite / Pytest | Baseline retained. |

## 10. API and operations

FastAPI provides structured contracts, error handling, health information, and metrics exposure. /health shows process state, not 99.5% availability. Prometheus/Grafana configuration, governance procedures, and a tested kill switch support supervision; auth/authz/rate limiting, load testing, alert validation, and backup/recovery validation remain production gaps.

## 11. Validation and evaluation boundary

- Supplied validation evidence contains 80 tickets.
- The failed initial validation attempt is preserved; the explicitly authorized 80-ticket technical rerun is authoritative.
- The unattended harness accepts arbitrary sizes and hard-codes neither 80, 100, nor 120.
- The Build Specification expects a final hidden assessment of up to 120 tickets; it was not inspected or used for tuning.
- The completed 50-response, two-reviewer human evaluation is DEVELOPMENT ONLY.
- The rejected V2 experiment remains development evidence and did not replace V1. No V3 is authorized here.

## 12. Open questions

| Question | Why | Owner | Resolve by | State |
|---|---|---|---|---|
| What sources, customer population, volume, and duration are permitted in the pilot? | Defines exposure, oversight, sampling, and rollback. | Owner with Support Operations | Before pilot authorization | Unresolved |
| What urgency and calibration evidence must a successor meet before automation? | Prevents unsafe reliance on weak predictions. | Owner with Evaluation/ML lead | Before successor release criteria | Unresolved |
| What identity provider, roles, permissions, and rate limits protect external access? | Required for controlled access. | Security/Operations owner to be named | Before external pilot access | Unresolved |
| What retention, deletion, backup, RPO, and RTO apply to logs? | Determines privacy and resilience controls. | Owner with Security/Operations | Before production design approval | Unresolved |
| What alert thresholds, named owners, and response rota apply? | Dashboards alone do not establish readiness. | Operations owner to be named | Before production review | Unresolved |
| What independent validation/human-review plan follows future model, threshold, or route changes? | Preserves evaluation separation. | Owner with Evaluation lead | Before successor validation | Unresolved |

## 13. Release and deployment

The completed owner decision is **LIMITED SUPERVISED PILOT** and **NOT PRODUCTION-READY**. Safety takes priority over automation. Production is not approved because urgency and calibration are weak; safe automation is unproven and measured at 0%; DEVELOPMENT usefulness is 2.87/5; fairness is preliminary; auth/authz/rate limiting are absent; load, availability, alerts, and backup/recovery are untested; and live-provider evidence is component-level only. No production release date is asserted.

## 14. Approval and version history

| Version | Date | Meaning | Approval |
|---|---|---|---|
| 1.0 | 4 September 2026 | Original discovery-derived implementation baseline. | Historical baseline. |
| 2.0 | 12 September 2026 | Reconciled with Stage 1, frozen V1, authoritative validation, DEVELOPMENT human evaluation, governance/monitoring, hosted CI, and final owner decision. | Owner review/sign-off complete — Mimoh Naik. |

Historical frozen CI evidence: GitHub Actions run 34773077234, commit
6a80e91a3b7a82504f04afa98cdb8265f7617234, result SUCCESS. Current post-freeze
implementation-hardening evidence: run 34889316386, commit
7062f683e41a178e644713acee81478731dc9adc, result SUCCESS, with 355 tests and
zero warnings. This hardening changed no product requirement, threshold, prompt,
guardrail policy, or validation result. CI is reproducibility evidence, not
availability evidence.
