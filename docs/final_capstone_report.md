# CloudServe Support Automation Capstone Report

**Owner:** Mimoh Naik
**Client:** CloudServe Solutions
**Evidence cut-off:** 12 September 2026
**Frozen V1 fingerprint:** `ddf89e82e7340a0257ee0c2ae1ce340612070545bc04f559e1e4c3ad733f59c1`
**Owner-approved decision:** **LIMITED SUPERVISED PILOT — NOT PRODUCTION-READY**

## 1. Executive summary

CloudServe's supplied discovery materials described delayed support, difficulty locating reviewed documentation, and context-poor escalations. The brief's reported business baselines were FCR 42%, mean first response 8–12 hours, CSAT 3.2/5, and escalation 58%; repeat contacts were not measured. Separately, the supplied 500-ticket development dataset contains descriptive fields: 71.4% documentation answerability, 43.8% FCR-labelled tickets, and mean CSAT 2.97/5. Neither source is a system outcome.

Frozen V1 is a controlled, documentation-grounded support pipeline. It normalizes four channels; classifies intent and urgency; retrieves reviewed passages; routes deterministically; generates provider-neutral grounded candidates; blocks unsafe output; creates structured escalations; and persists auditable decisions. FastAPI, SQLite, Prometheus-compatible monitoring, governance controls, and GitHub Actions CI accompany the pipeline.

The authoritative usable validation evidence is the owner-authorized 80-ticket technical rerun. It reconciled 80 source tickets, terminal outcomes, and audit records. Intent macro precision was 100.0%, P95 local sequential pipeline latency was 0.0915 seconds, and decision-log coverage was 100.0%. However, urgency accuracy was 42.5%, urgency macro F1 was 41.417%, calibration ECE was about 42.3 percentage points, V1 automation was 0%, and escalation was 100%.

The owner-approved recommendation is **LIMITED SUPERVISED PILOT**. V1 is **NOT PRODUCTION-READY** and safety takes priority over automation. The owner's 30% future automation target is an **OWNER FUTURE TARGET — NOT MEASURED RESULT**. FCR, CSAT, first-response time, production availability, load/alert performance, backup/recovery, and validation human response-quality measures are **NOT MEASURED**.

The report separates three questions that should not be answered by the same number. First, the engineering acceptance question asks whether the implemented workflow, tests, failure handling, logging, and unattended harness provide credible A1–A12 evidence. Second, the evaluation question asks what the frozen V1 did on the permitted technical validation population. Third, the deployment question asks what level of real-world use the owner is prepared to authorize given the remaining gaps. The first question has credible PASS evidence; the second contains both strong and weak results; the third is answered by the owner's limited supervised pilot decision. This separation prevents a passing test suite, a fast local latency result, or a strong intent result from being presented as a production outcome.

The central design choice is therefore controlled escalation rather than maximum automation. V1 records enough context for a reviewer to understand the route, retains a fail-closed path when evidence or validation is inadequate, and treats generation as a candidate response rather than the final authority. That design accounts for the 0% validation automation result without recasting it as a successful automation outcome. It also explains why the report retains explicit boundaries around validation human quality, privacy outcomes, fairness, and operational business results.

## 2. Discovery and problem framing

### Discovery evidence

The supplied discovery materials contain five stakeholder perspectives. The Stage 1 workbook consolidates and reconciles these findings rather than asserting a day-by-day authorship sequence. Marcus, Head of Support, identified workload and response-delay pressure. Sofia, a Tier 1 agent, described effort spent locating knowledge and reliance on personal answer files. Daniel, a Tier 2 engineer, described escalations that lacked usable context. Ines, the technical writer, described reviewed articles that were difficult to locate through symptom language. Ravi, a customer, required honest, clearly labelled, cited communication.

The discovery record preserves a material tension: whether CloudServe lacked articles or lacked a reliable way to locate its reviewed articles. The supplied development dataset marked 357 of 500 tickets (71.4%) answerable from reviewed documentation and 219 of 500 (43.8%) in its FCR-labelled field. These descriptive dataset values supported a controlled information-access and escalation-context problem rather than an unsupported claim that new documentation alone was required.

Language variation was a discovery concern, not proof that semantic retrieval solved a language gap. MiniLM retrieval was selected later as an engineering hypothesis; later fairness evidence remains preliminary and is reported separately.

The discovery evidence supports a workflow problem as well as a knowledge-access problem. A customer-facing answer needs a reviewed basis; an agent needs a way to find that basis; and an escalation needs sufficient context for the next human to act without restarting the investigation. These needs motivate the pipeline stages of normalization, retrieval, deterministic routing, structured escalation, and decision logging. They do not establish that every ticket should be answered automatically, that a semantic model eliminates language variation, or that a deployment would improve the brief's historical business baselines.

The development dataset supplied labels that are useful for design and descriptive analysis, but it is not an operational before-and-after study. Its answerability field is a constraint on what may be supported by reviewed documentation, not a measure of final customer resolution. Its FCR, CSAT, and repeat-contact fields similarly describe the supplied data rather than results caused by V1. This distinction is retained throughout the report because using development descriptive fields as live business evidence would overstate the project outcome.

### Brief historical baselines

| Brief business baseline | Value | Boundary |
|---|---:|---|
| First-contact resolution | 42% | Brief-reported baseline; not V1 performance. |
| Mean first response | 8–12 hours | Brief-reported operational baseline; not pipeline latency. |
| CSAT | 3.2/5 | Brief-reported baseline; not V1 performance. |
| Escalation | 58% | Brief-reported baseline; not V1 performance. |
| Repeat contacts | NOT MEASURED | No brief baseline supplied. |

### Development-dataset descriptive metrics

| Development-dataset field | Figure | Boundary |
|---|---:|---|
| Documentation answerability | 71.4% (357/500) | Development descriptive label, not V1 resolution. |
| FCR-labelled field | 43.8% (219/500) | Development descriptive field, not system-attributable FCR. |
| Mean CSAT field | 2.97/5 | Development descriptive field, not V1 CSAT. |
| Repeat-contact field | 21.6% (108/500) | Development descriptive field, not a V1 outcome. |
| Non-fluent tickets | 24.0% (120/500) | Explicit supplied field, not inferred identity data. |

The supplied dataset is not live operating telemetry. It does not establish deployed customer outcomes, availability, an operational comparison period, or validation human quality. Validation remained separate from development and was not used to tune V1. The hidden assessment was not accessed, reconstructed, or simulated.

### Problem-statement traceability

The problem statement is traceable to three evidence sources with different roles. The stakeholder perspectives describe the operational friction: response-delay pressure, difficulty locating reviewed information, escalation context gaps, and the need for honest cited communication. The development dataset describes the available ticket and documentation fields, including the proportion marked answerable from reviewed material and the presence of language-fluency and repeat-contact fields. The project requirements translate those observations into technical controls: four-channel normalization, evidence retrieval, deterministic routing, blocking guardrails, structured escalation, and decision logging.

This trace does not turn every observed concern into a measured system outcome. The discovery materials provide a reason to design for auditable, evidence-grounded assistance; they do not prove that the pipeline reduced workload, shortened a customer wait, increased first-contact resolution, or improved CSAT. The report retains that boundary because the brief baselines, development descriptive fields, validation technical measurements, and any future pilot observations belong to different populations. Their values can be compared only when a shared operational definition and observation period exists.

The design also responds to the difference between an answerable ticket and an automatically answerable ticket. A ticket may have relevant documentation but still need escalation because it concerns risk, has low or invalid confidence, lacks sufficient evidence for a supported answer, or triggers a guardrail. Conversely, an unsupported request should not be made to look complete by selecting a weakly related passage. This is why the problem framing includes both retrieval quality and fail-closed routing rather than treating document match alone as authority to respond.

The later technical evidence provides a limited check on the design hypotheses, not a retrospective rewrite of discovery. Retrieval was evaluated technically on the eligible validation population, and fairness segmentation documented that language-related quality questions remain preliminary. The development human review showed that strong citation and hallucination measures did not automatically imply high usefulness. These later findings clarify which assumptions require caution, while the discovery record remains a record of what the supplied materials indicated at the time of problem framing.

## 3. Requirements and success criteria

The PRD maps discovery evidence into FRs, NFRs, and scope boundaries. Its later reconciliation preserves original evidence and records retrospective reconstruction where applicable; it does not assert that every workbook preceded implementation.

| Requirement group | Final status and evidence boundary |
|---|---|
| FR-01 ingestion | PASS — email, live chat, documentation comments, and community forum inputs normalize while preserving channel. |
| FR-02 classification | PASS functionally — every valid ticket has intent, urgency, and confidence; urgency quality is weak on validation. |
| FR-03 retrieval | PASS — identifiable reviewed passages, ranking, and no-result behaviour through MiniLM and NumPy exact cosine. |
| FR-04 routing | **PARTIAL** against original three-state wording. The A5 two-outcome contract passes, but validation routing accuracy was 40%, automation 0%, and escalation 100%. |
| FR-05 generation | PASS functionally; validation semantic citation accuracy remains NOT MEASURED. |
| FR-06 to FR-09 guardrails | PASS functionally — grounding, private-data, injection, and commitment failures block/escalate. |
| FR-10 escalation context | PASS structurally; operator usefulness is NOT MEASURED. |
| FR-11 audit logging | PASS — 80/80 validation terminal decisions reconciled to persistent records. |
| FR-12 unattended evaluation | PASS — arbitrary-size harness writes machine- and human-readable artifacts. |

A1–A12 have credible PASS evidence: clean checkout, four-channel ingestion, classification, retrieval, deterministic routing, citation validation, guardrail blocking, decision logging, unattended evaluation, automatic metrics, failure handling, and one-command tests. A9 passes for the supplied arbitrary-size unattended evaluation workflow; execution on the inaccessible hidden assessment remains contingent on that assessment being supplied. This engineering acceptance finding is distinct from business, governance, and production targets.

### Acceptance-evidence structure

The acceptance record is deliberately implementation-facing. **A1** is bounded by the documented clean-checkout path rather than a claim about a production operating environment. **A2** is demonstrated by normalizing the four specified channels into one ticket representation while retaining the originating channel. **A3** requires a structured intent, urgency, and confidence output for each valid ticket; its functional presence does not turn weak urgency quality into a pass against a quality target.

**A4** is supported by retrieval records that identify reviewed documentation passages, rank them, and permit a genuine no-result result. **A5** is supported by deterministic two-outcome routing that records the applied threshold, risk, and evidence conditions; the original PRD's broader three-state wording remains documented as FR-04 PARTIAL rather than being rewritten. **A6** and **A7** are functional safeguards: citation validation and the direct-code guardrails prevent a response from being released when the necessary evidence or safety conditions are absent.

**A8** is the persistent SQLite decision record, which preserves inputs, classifications, retrieval provenance, routing outcome, guardrail/validation results, and requirement links without treating logs as a measure of customer benefit. **A9** and **A10** concern the unattended, arbitrary-size harness and its machine-readable plus human-readable output. The supplied 80-ticket validation run is evidence from that harness; the expected hidden assessment of up to 120 tickets was neither accessed nor assumed to have run.

Finally, **A11** is evidenced by controlled failure paths for malformed input, retrieval/provider/dependency failures, invalid generation, and logging failure. Each is designed to fail closed into escalation rather than silently release a confident answer. **A12** is the one-command Pytest evidence, supplemented by the observed hosted CI run. Together these criteria provide credible engineering acceptance evidence, while the deployment recommendation still depends on the separate measured quality, governance, and operational limits described below.

Traceability is maintained at the requirement level rather than by treating the application as one opaque assistant. Ingestion preserves the source channel in a common ticket representation. Classification produces the structured fields required by the downstream route. Retrieval returns identifiable reviewed passages or a legitimate no-result outcome. The route consumes explicit safety-relevant inputs and returns a terminal action with a reason. Generation and guardrails have separate responsibilities, and the logger persists the resulting decision record. This division makes it possible to test a component, inspect a terminal decision, and identify an evidence boundary without assuming that one successful component proves the full workflow is ready for production.

FR-04 remains an important qualification. The current two-outcome implementation expresses the A5 contract as AUTO_RESPOND or ESCALATE, with escalation serving as the human-review path. This structurally satisfies the applicable acceptance contract, while the original three-state wording remains only partially realized. More importantly, the 40.0% validation routing accuracy, 0.0% automation, and 100.0% escalation are reported as quality limitations rather than hidden behind structural compliance. The same approach is used for the NFRs: local latency, reproducibility, and decision-log coverage have evidence, while availability, load, recovery, authentication, authorization, and rate limiting remain production-hardening gaps.

### Canonical brief targets and evidence status

These are the report's authoritative brief-target tables. The category is included in the metric name so that business, technical, and governance rows remain visibly grouped without mixing target-free diagnostics into the table.

| Metric | Brief baseline where applicable | Brief target | Current evidence | Evidence population | Final status |
|---|---:|---:|---|---|---|
| **BUSINESS — FCR** | 42% | >=60% | System-attributable FCR was not measured. | No production or pilot outcome population. | NOT MEASURED |
| **BUSINESS — Mean first response** | 8–12 hours | <5 minutes | Customer first-response time was not measured; pipeline latency is not substituted. | No production or pilot outcome population. | NOT MEASURED |
| **BUSINESS — CSAT** | 3.2/5 | >=4.0/5 | System-attributable CSAT was not measured. | No production or pilot outcome population. | NOT MEASURED |
| **BUSINESS — Escalation** | 58% | <=30% | 100.0% escalation. | 80-ticket authorized validation technical rerun. | MEASURED + NOT MET |
| **BUSINESS — Repeat contacts** | NOT MEASURED | Approximately halved | System-attributable repeat contacts were not measured. | No production or pilot outcome population. | NOT MEASURED |
| **TECHNICAL — Classification precision** | — | >=85% | Intent macro precision was 100.0%. | 80-ticket authorized validation technical rerun; 22 represented intent classes. | MEASURED + MET |
| **TECHNICAL — Hallucination rate** | — | <=5% | 2.0% in human development review; validation hallucination was not measured. The numerical development result does not establish validation compliance. | 50 development candidates, two reviewers. | DEVELOPMENT ONLY |
| **TECHNICAL — Semantic citation accuracy** | — | >=95% | 98.0% in human development review; validation semantic citation accuracy was not measured. The numerical development result does not establish validation compliance. | 50 development candidates, two reviewers. | DEVELOPMENT ONLY |
| **TECHNICAL — Pipeline P95 latency** | — | <3 seconds | 0.0915 seconds LOCAL SEQUENTIAL PIPELINE LATENCY; not customer first-response time, production load latency, availability evidence, or production SLA evidence. | 80-ticket authorized validation technical rerun. | MEASURED + MET |
| **TECHNICAL — Availability** | — | >=99.5% | Production availability was not measured; `/health` and hosted CI are not availability evidence. | No production availability observation window. | NOT MEASURED |
| **GOVERNANCE — Private-data leakage** | — | Zero released-response leakage | Privacy and secret-blocking controls have functional test evidence, but validation released zero automatic responses; released-response leakage was not demonstrated. | No released validation-response population. | NOT MEASURED |
| **GOVERNANCE — Fairness quality difference** | — | <5 percentage points | Segmentation is preliminary and adequately powered cross-group human quality evidence is absent. | Development subgroups and limited validation subgroups. | NOT PROVEN |
| **GOVERNANCE — Decision-log coverage** | — | Complete coverage | 100.0% (80/80 terminal decisions); this does not establish production retention, recovery, concurrency, or access control. | 80-ticket authorized validation technical rerun. | MEASURED + MET |
| **GOVERNANCE — Confidence calibration error** | — | <=5 percentage points | 42.267%. | 80-ticket authorized validation technical rerun. | MEASURED + NOT MET |

### Additional measured diagnostics

These diagnostics are decision-relevant evidence but are not recast as brief threshold results where the brief supplied no threshold.

| Diagnostic | Current evidence | Evidence population | Final status |
|---|---:|---|---|
| Urgency accuracy | 42.5% | 80-ticket authorized validation technical rerun. | MEASURED — MATERIAL QUALITY LIMITATION |
| Urgency macro F1 | 41.417% | 80-ticket authorized validation technical rerun. | MEASURED — MATERIAL QUALITY LIMITATION |
| Routing accuracy | 40.0% | 80-ticket authorized validation technical rerun. | MEASURED — MATERIAL QUALITY LIMITATION |
| V1 automation | 0.0% | 80-ticket authorized validation technical rerun. | MEASURED — NO BRIEF THRESHOLD |
| Owner future automation target | 30% minimum worthwhile future automation | Owner-confirmed target; not a V1 observation. | OWNER FUTURE TARGET — NOT MEASURED RESULT |
| Retrieval Recall@1 / @3 / @5 | 76.4% / 87.7% / 88.7% | 53 eligible validation tickets. | MEASURED — NO BRIEF THRESHOLD |
| Retrieval Precision@1 / @3 / @5 | 90.6% / 36.8% / 25.6% | 53 eligible validation tickets. | MEASURED — NO BRIEF THRESHOLD |
| Retrieval MRR | 92.8% | 53 eligible validation tickets. | MEASURED — NO BRIEF THRESHOLD |
| Development correctness | 3.74/5 | 50 development candidates, two reviewers; 100 ratings. | DEVELOPMENT ONLY |
| Development usefulness | 2.87/5 | 50 development candidates, two reviewers; 100 ratings. | DEVELOPMENT ONLY |

The non-functional requirements are reported according to evidence type rather than
treated as automatic pass/fail outcomes. The local P95 target was measured and met, but
that observation is deliberately not reused as availability or load evidence. The
reproducibility path, modular workflow, and persistent logging have implementation and
test evidence. Auth/authz/rate limiting, verified load, alert delivery, backup, and
recovery remain production-hardening requirements with no qualifying measurement.

| Non-functional area | Current position |
|---|---|
| Local P95 pipeline latency | MEASURED + MET at 0.0915 seconds on the technical rerun; not load evidence. |
| Availability | NOT MEASURED; `/health` and CI do not establish availability. |
| Audit coverage | MEASURED + MET at 80/80 terminal decisions. |
| Privacy/security controls | Private-data and secret blocking controls have functional test evidence. Formal compliance, retention, and access-control validation are not evidenced; released-response leakage is NOT MEASURED because validation released zero automatic responses. |
| Fairness | NOT PROVEN; segmentation is preliminary and human cross-group quality is not measured. |
| Reproducibility | Documented setup, arbitrary-size harness, one-command tests, clean-checkout smoke, and hosted CI evidence. |
| Production service hardening | PRODUCTION-HARDENING GAP — auth/authz, API rate limiting, production load testing, production availability, alert-delivery verification, backup/recovery testing, and production retention/access controls are absent or lack qualifying evidence. These are not recast as A1–A12 failures. |

## 4. Architecture and implementation

```text
FastAPI entry point
       |
     Ticket
       ↓
   Normalize
       ↓
   Classify
       ↓
   Retrieve
       ↓
     Route
     ├── Escalate
     └── Generate
           ↓
 Guardrails / Validate
     ├── Release
     └── Escalate

All terminal decisions
       ↓
SQLite Decision Log

Prometheus / Grafana observe bounded operational measurements and decision outcomes.
```

Frozen V1 uses four-channel ingestion; TF-IDF word/character logistic-regression classification; MiniLM embeddings; NumPy exact-cosine retrieval; deterministic Python routing; provider-neutral grounded generation; direct-code guardrails; SQLite decision logging; FastAPI; monitoring/governance assets; and Pytest.

The frozen classification confidence threshold is 0.80 and retrieval threshold is 0.30. High-risk, insufficient-evidence, invalid-confidence, and failed-guardrail states fail closed. Generation specification `generation-v1.0.0` requires structured output and resolvable citations. The service exposes `/health`, `/metrics`, and `/tickets/process`.

LangChain/LangGraph, Chroma, and BM25 were baseline/reference options, not mandatory components. Explicit Python orchestration and NumPy exact cosine were chosen to reduce dependency and operating complexity while preserving inspectable stages and deterministic decisions. FastAPI, SQLite, and Pytest retain the baseline choices. These justified departures do not remove the observed urgency, calibration, routing, or automation limits.

The implementation keeps customer content separate from system/application instructions.
Routing is not delegated to free-form generated text, and a guardrail result can override
generation. Decision records include the terminal action, reasons, relevant confidence and
retrieval information, guardrail state, requirement identifiers, and prompt/specification
version while minimizing retained sensitive content. This gives reviewers a trace from a
ticket through a terminal outcome without making a provider response the final safety
authority.

### Classification design and limitation

Classification is implemented as direct-code machine learning rather than as a runtime prompt. The frozen path uses TF-IDF word and character features with logistic-regression classifiers to produce intent, urgency, and confidence. This choice makes feature processing and probability output reproducible locally, avoids provider dependence for the classification decision, and keeps the model's role narrow enough to test separately. The word and character representations support different surface forms in the ticket text without converting the classification stage into an uninspectable conversational inference step.

The validation evidence distinguishes the two tasks. Intent results were 100.0% accuracy, macro precision, recall, and F1 across the 22 represented classes. Urgency was materially weaker: 42.5% accuracy and 41.417% macro F1 across high, medium, and low. The report therefore does not generalize intent performance to urgency quality. Confidence is retained as a meaningful routing input, but the calibration result of 42.267% ECE shows that the stated confidence did not meet the <=5 percentage-point governance tolerance on the technical rerun. The classifier is functionally complete for A3; its urgency and calibration limitations remain deployment-relevant evidence.

### Retrieval design and model selection

Retrieval is designed to return evidence that a reviewer can identify, rather than to force a plausible answer from the corpus. Frozen V1 uses all-MiniLM-L6-v2 embeddings over section-aware documentation chunks and performs exact cosine ranking in NumPy. The architecture record describes 170 section-aware chunks and a 0.30 retrieval floor. A no-result is a valid outcome: it should lead to an escalated path rather than a fabricated answer. Returned source identifiers, passages, scores, and rank provide the evidence consumed by generation, guardrails, logging, and later review.

This is a documented departure from the baseline Chroma/BM25 proposal, not an omission. For the small local corpus, in-process exact cosine removes a service dependency and exposes an inspectable ranking path while preserving the required source identity and no-result behavior. The model-selection record compares MiniLM with BGE-small and E5-small on development retrieval checks. MiniLM was retained because it had the strongest recorded Recall@3 selection result and lower recorded experiment latency and parameter footprint than those alternatives. That development selection evidence explains the component choice; the authoritative validation retrieval evidence remains Recall@1/@3/@5 of 76.4%/87.7%/88.7%, Precision@1/@3/@5 of 90.6%/36.8%/25.6%, and MRR of 92.8% on the 53 eligible validation tickets.

### Routing, generation, and guardrails

Routing is deterministic direct-code logic, not a generated recommendation. It evaluates validity, risk, answerability, classification confidence, retrieval information, guardrail state, and failure conditions before selecting AUTO_RESPOND or ESCALATE. The frozen classification confidence threshold is 0.80 and retrieval floor is 0.30. These values are part of frozen V1; this report does not retune them against validation. When confidence is absent or invalid, evidence is insufficient, a ticket is high risk, or a guardrail blocks the candidate, the route fails closed to escalation. The route records its reason so that escalation is an auditable result rather than a silent fallback.

The only frozen runtime model prompt is the provider-neutral grounded generation specification `generation-v1.0.0`. It asks for structured output based on retrieved evidence, requires exact document/chunk citation pairs, and prohibits unsupported commitments. Classification, retrieval, routing, logging, and guardrail enforcement are explicitly direct-code behavior rather than prompt-driven behavior. This distinction matters because the final safety decision is not delegated to a model response: generation proposes a structured candidate, while independent validation determines whether it can proceed or must be blocked.

Guardrails cover private-data and secret patterns, grounding and evidence presence, citation integrity, prompt injection and system-disclosure attempts, unsupported commitments, malformed generation, missing evidence, confidence failures, and internal exceptions. Functional tests demonstrate block-and-escalate behavior. These controls support the engineering acceptance evidence and reduce unsafe-release pathways, but validation released no automatic responses. Consequently, validation human hallucination, semantic citation accuracy, released-response private-data leakage, and released-response guardrail coverage remain **NOT MEASURED** rather than being inferred from tests.

The grounded-generation contract is intentionally narrower than a general conversational assistant. A supported candidate must be structured, linked to retrieved evidence through exact document and chunk identifiers, and free of unsupported commitments. When the system lacks suitable context, the specification supports an unsupported result rather than a provider call intended to fill the gap. This reduces the chance that fluent prose will be mistaken for evidence. It also means that generated text is only one part of the workflow: the citation and grounding checks must still validate it against the retrieved material before a release decision is possible.

Input separation is equally important to the prompt-injection control. Customer-provided text is handled as ticket data; it is not allowed to revise system authority, routing policy, guardrail rules, or evidence requirements. The direct-code injection and disclosure checks cover both input and output patterns. Tests demonstrate the intended block/escalate behavior for adversarial requests, but they do not measure the prevalence of attacks in validation or production. The report therefore describes injection protection as functional control evidence, not as a measured production-security outcome.

The same boundary applies to unsupported commitments. Refunds, credits, guarantees, dates, service-level exceptions, policy exceptions, and roadmap promises require evidence and authority that the frozen system does not infer from a ticket. High-risk deterministic routing and commitment guardrails supply an independent block path in addition to the generation instruction. This is a practical example of why the route is not driven by generated prose: a candidate may sound helpful while still being unsuitable for automated release.

Retrieval design also records the engineering trade-off between corpus structure and operational simplicity. The documented corpus was segmented into section-aware chunks so that a returned result could identify a focused passage rather than only a whole article. Exact cosine over locally held embeddings is transparent for a small corpus: the returned score and ranked source list can be inspected without a separately operated vector service. This does not make a locally held corpus automatically complete, current, or representative of every support issue; it makes the retrieval calculation and evidence source more traceable.

### Decision logging, API, and operational boundaries

The SQLite decision store is the audit boundary for a processed ticket. A terminal record captures the ticket and decision identifiers, timestamp, prediction and confidence information, retrieved source identifiers and ranking information, routing threshold, selected action and reason, guardrail and validation results, prompt/specification version, and requirement identifiers where applicable. The implementation is designed to avoid unnecessary secret retention. This record is useful because an escalated result can be reviewed as a sequence of explicit decisions rather than as an unexplained refusal or a provider transcript.

The validation reconciliation shows the logging behavior at the terminal-decision level: 80 source tickets, 80 evaluated tickets, 80 terminal outcomes, and 80 logged records. That is the basis for the reported 100.0% decision-log coverage. It does not prove production retention duration, concurrent-write behavior, database recovery, access control, or backup restoration. Those distinctions are retained because an auditable local record and a production data-management system have different operational requirements.

FastAPI provides the documented application boundary for processing, health, and bounded metrics endpoints. The API and its tests support structured response and error behavior in the implementation. The `/health` endpoint is a local service check, and `/metrics` supports observability; neither is used as evidence of a highly available production service. Likewise, provider-neutral generation makes the system portable across configured providers, but provider smoke evidence is component-level development evidence and does not establish end-to-end production reliability.

### Test and acceptance evidence

The test suite is organized around the separated modules: ingestion, classification, retrieval, routing, generation, guardrails, logging, pipeline orchestration, and API behavior. Functional tests cover normal paths and fail-closed paths such as malformed tickets, invalid confidence, missing retrieval evidence, injection attempts, unsafe commitments, malformed provider output, provider unavailability, and logging failure. This test design supports the claim that A1–A12 have credible PASS evidence without requiring every test to make a business-performance claim.

Hosted CI adds an independent execution environment for the reproducibility path. The observed successful run covered dependency installation, `pip check`, clean-checkout smoke, and the complete Pytest suite. The report treats this as evidence that the documented repository workflow ran in hosted CI, not as a measurement of availability, alert reliability, customer response time, or security authorization. The test and CI evidence are therefore strong engineering controls while remaining bounded by their actual population and execution conditions.

## 5. Evaluation methodology

| Evidence set | Population and permitted use |
|---|---|
| Development | 500 supplied tickets: development design, retrieval checks, segmented analysis, and development human review. |
| Validation | 80 supplied tickets: authoritative technical validation only after the disclosed rerun. |
| Human review | 50 development candidates, independently assessed by two reviewers: DEVELOPMENT ONLY. |
| Hidden assessment | Expected up to 120 tickets: not accessed, inferred, run, or tuned against. |

The first validation attempt is preserved as an embedding-cache/token-path infrastructure failure. Infrastructure-only remediation retained the frozen V1 fingerprint and did not tune behaviour. The owner authorized one disclosed 80-ticket technical rerun, which is the authoritative usable validation evidence. The harness accepts arbitrary input sizes; it hard-codes neither 80 nor 120.

Pipeline P50/P95 measures local sequential end-to-end processing, not arrival-to-customer first-response time, load, or availability. Citation-ID validity is not semantic citation accuracy. Development, validation, and operational evidence are not substituted for one another.

The technical rerun retained the supplied validation role, input path, data hash, run ID,
and reconciliation counts in its machine-readable record. Its decision database is
run-specific. The initial failed attempt remains preserved rather than being overwritten.
This permits the report to distinguish infrastructure failure from the later usable
technical result without treating either as a production outcome.

Evaluation integrity is maintained through population boundaries and preserved artifacts. Development data was permitted for design, component comparison, segmented analysis, and the separate human-development review. The supplied validation data was not used to tune frozen V1; it is used here only through the authorized technical rerun. The hidden assessment was not accessed or reconstructed, and the evaluation harness is dataset-size agnostic rather than keyed to 80 or 120 tickets. These constraints ensure that the report's validation results can be traced to the supplied 80-ticket evidence rather than to an unrecorded or hidden evaluation path.

The rerun produces machine-readable and human-readable outputs that retain source/evaluated/terminal/logged reconciliation counts and decision information. Classification metrics include precision, recall, F1, and preserved confusion matrices; retrieval uses eligible-ticket denominators; routing, automation, escalation, failures, latency, decision logging, and calibration are recorded separately. This method avoids substituting one metric for another: a retrieval score is not a customer-resolution rate, a local sequential latency is not first-response time, and a CI result is not availability evidence. The methodology also retains the failed initial validation attempt as evidence of infrastructure risk instead of replacing it with the later usable technical result.

For classification, the use of macro measures matters because the represented intent labels are not equally frequent. The report retains the per-class matrix rather than relying on one aggregate percentage. For urgency, the three-class matrix shows the distribution of correct and incorrect high, medium, and low predictions, which is why the macro F1 is reported alongside accuracy. These measures describe technical label performance on the supplied validation data. They do not establish that a customer received a timely or useful response, because routing and release outcomes introduce further evidence conditions.

For retrieval, the denominator is the 53-ticket eligible population rather than all 80 validation tickets. Recall@K, Precision@K, and MRR answer different ranking questions and should not be collapsed into a single quality claim. The report preserves all three families: Recall@1/@3/@5 shows whether relevant evidence appeared among the returned results; Precision@1/@3/@5 shows the proportion of retrieved entries that were relevant at each cutoff; and MRR records the rank of the first relevant result. The values provide a technical evidence base for reviewed-document retrieval, while no result, unsupported content, and evidence insufficiency still remain valid escalation conditions.

The unattended harness is deliberately arbitrary-size. It accepts a supplied dataset path and produces reports without a manual evaluator in the execution loop. The supplied validation evidence contains 80 tickets, while the Build Specification expects a hidden final assessment of up to 120 tickets. The harness does not hard-code either count. This makes A9 and A10 evidence about the evaluation workflow rather than an assertion that an inaccessible hidden assessment has already been executed.

## 6. Authorized technical validation results

Evidence classification: **VALIDATION — authorized 80-ticket technical rerun**.

| Measure | Result | Population / status |
|---|---:|---|
| Source / evaluated / terminal / logged | 80 / 80 / 80 / 80 | Reconciliation PASS. |
| Intent accuracy / macro precision / recall / F1 | 100.0% / 100.0% / 100.0% / 100.0% | 80 tickets; 22 represented classes. |
| Urgency accuracy | 42.5% | 34/80 correct. |
| Urgency macro precision / recall / F1 | 41.852% / 41.524% / 41.417% | Three classes. |
| Retrieval Recall@1 / @3 / @5 | 76.4% / 87.7% / 88.7% | 53 eligible tickets. |
| Retrieval Precision@1 / @3 / @5 | 90.6% / 36.8% / 25.6% | 53 eligible tickets. |
| Retrieval MRR | 92.8% | 53 eligible tickets. |
| Routing accuracy | 40.0% | 80 tickets. |
| Automation / escalation | 0.0% / 100.0% | 80 terminal outcomes; escalation target fails. |
| Processing failures / decision-log coverage | 0.0% / 100.0% | 80 processed and reconciled tickets. |
| Pipeline latency P50 / P95 | 0.0502s / 0.0915s | Local sequential; P95 met, not load evidence. |
| Confidence calibration error | 42.267% | 80 tickets; fails <=5pp tolerance. |

Validation had no released automatic responses. Validation hallucination, semantic citation accuracy, correctness, usefulness, released-response guardrail coverage, citation-ID validity, and private-data release rate are therefore **NOT MEASURED**.

The confusion matrices in Appendix A were derived from preserved rerun records and supplied labels by ticket ID. The derivation performed no inference or evaluation rerun.

The validation outcome is deliberately reported as a set of separate measures. Perfect
intent performance does not replace the weak urgency measure. Retrieval relevance is
reported only on its 53-ticket eligible population. Routing accuracy, automation rate,
and escalation rate are distinct measures. The report therefore does not use one strong
technical figure to imply broader operational effectiveness.

The preserved confusion matrices provide the class-level context behind the aggregate classification measures. The intent matrix has all 80 represented predictions on its diagonal, consistent with the reported 100.0% intent macro precision. The urgency matrix has a diagonal of 34 of 80, consistent with 42.5% accuracy, and its class-level precision, recall, and F1 values produce the reported 41.417% macro F1. The matrices are technical classification evidence only. They do not measure response helpfulness, semantic support, fairness quality, business outcomes, or production readiness.

Routing requires a separate reading from classification. A ticket can have a correct intent prediction while still escalating because the evidence, risk, confidence, or validation state is not sufficient for a safe release. Conversely, the fact that every validation terminal result escalated cannot demonstrate successful automation. The observed 0.0% automation, 100.0% escalation, and 40.0% routing accuracy make the current safety posture visible without claiming that the system met the brief's escalation target. Processing failures were 0.0% and 80/80 terminal decisions were logged, which are reliability and audit results rather than proof of customer benefit.

The local sequential P50/P95 figures of 0.0502s and 0.0915s establish a bounded technical pipeline observation for the authorized rerun. They do not include arrival-to-customer queues, human review, provider load, service availability, alert delivery, or production traffic. Similarly, the 42.267% calibration ECE is a measured technical limitation. It signals that the reported confidence was not close enough to observed accuracy for the stated governance tolerance; it is not a reason to alter the frozen V1 threshold after validation.

## 7. Development human evaluation

Evidence classification: **HUMAN DEVELOPMENT EVALUATION — DEVELOPMENT ONLY**. Two independent reviewers assessed 50 development response candidates. The measured development hallucination rate was 2.0% and semantic citation accuracy was 98.0%. Development human evaluation met the nominal hallucination and citation thresholds, but this evidence is **DEVELOPMENT ONLY** and cannot establish validation or production compliance. Validation hallucination and validation semantic citation accuracy remain **NOT MEASURED**.

| Measure | Result | Denominator / agreement |
|---|---:|---|
| Hallucination rate | 2.0% | 1/50 candidates. |
| Semantic citation accuracy | 98.0% | 49/50 candidates. |
| Correctness | 3.74/5 | 100 reviewer ratings. |
| Usefulness | 2.87/5 | 100 reviewer ratings. |
| Unsupported-claim agreement | 100.0% | 50/50 raw agreement. |
| Citation-support agreement | 100.0% | 50/50 raw agreement. |
| Correctness agreement | Kappa 0.712 | Quadratic weighted kappa. |
| Usefulness agreement | Kappa 0.941 | Quadratic weighted kappa. |

Twenty-six samples had at least one ordinal disagreement and none was automatically adjudicated. The owner confirmed that the 2.87/5 DEVELOPMENT usefulness result is too low for production. It is not a validation usefulness measurement.

The human review answers a different question from automated classification and retrieval scoring: whether a sample of generated development responses appears supported and useful to independent reviewers. Two reviewers assessed 50 development response candidates, producing 100 ratings for correctness and usefulness. The agreement records are retained alongside the raw-agreement measures rather than implying that every subjective judgement was unanimous. This provides a documented human-development method, but it remains a development sample and cannot establish the quality of validation releases because V1 released none in the technical rerun.

The individual measures must remain separate. The 2.0% hallucination rate and 98.0% semantic citation accuracy meet their nominal thresholds within this **DEVELOPMENT ONLY** sample. Correctness was 3.74/5 and usefulness was 2.87/5, with the latter explicitly identified by the owner as too low for production. Strong citation and hallucination figures therefore do not convert into a positive usefulness finding. The report preserves this difference rather than using the strongest human-review values to mask the lower usefulness score or presenting development evidence as validation compliance.

The review method also makes its denominator visible. Hallucination is one unsupported-claim finding among 50 candidates, and semantic citation accuracy is 49 supported citations among 50 candidates. Correctness and usefulness each draw on 100 reviewer ratings because two reviewers assessed the 50 candidate responses. The raw agreements and quadratic weighted kappa values are reported separately so that agreement is not confused with response quality. None of these figures is extrapolated to tickets that were not in the development review sample.

This human-development evidence complements, but does not replace, the automated guardrail tests. A guardrail test can prove that a known unsafe pattern blocks; a human review can assess whether a sampled response appears supported or useful under the stated protocol. Neither result establishes production performance by itself. The report keeps the methods separate so a reviewer can see why functional safety evidence, development human judgement, validation technical metrics, and production outcomes require different claims and different follow-up evidence.

## 8. Fairness evidence

Segmentation used explicit customer-tier and language-fluency fields plus a deterministic short/long text rule; protected attributes were not inferred. Development analysis found Recall@3 of 79.9% for non-fluent versus 87.4% for fluent tickets, and 89.1% for long versus 82.6% for short tickets. These are automated subgroup observations, not customer-outcome fairness conclusions.

On validation, enterprise tickets (n=8) and non-fluent tickets (n=19) were below the registered minimum group size of 20 and are **NOT MEASURED**. Eligible text-length groups had urgency accuracy of 27.9% (short) and 59.5% (long); this does not establish a customer-quality outcome. Cross-group human response-quality evidence is NOT MEASURED. The <5pp fairness gate is **NOT PROVEN**.

The fairness approach uses only fields and rules that the data supports: explicit customer tier, explicit language-fluency information, and a deterministic text-length segmentation. It does not infer protected characteristics from names, text, or metadata. The development retrieval differences and validation text-length urgency differences are useful signals for further review, but their populations and outcomes do not support a claim that the deployment fairness target was achieved or failed. Small validation subgroups are intentionally left **NOT MEASURED** rather than converted into unstable percentage comparisons.

The fairness evidence is therefore preliminary in two senses. It is limited by subgroup size and it does not include adequately powered cross-group human response-quality or operational-resolution outcomes. The result is not a pass condition for production. It is a documented governance boundary: the system has segmented analysis and identifiable areas for pilot monitoring, while the <5 percentage-point quality-difference gate remains **NOT PROVEN**.

The segmentation findings must also be interpreted with the metric boundary in view. A Recall@3 difference describes whether reviewed material was retrieved among the first three results for the specified development subgroups. An urgency-accuracy difference describes label performance for the eligible validation text-length groups. Neither metric directly measures whether customers were treated fairly in resolution, response time, escalation experience, or human-reviewed answer quality. Reporting the subgroup denominators and leaving small groups **NOT MEASURED** is more informative than producing a definitive fairness claim from insufficient evidence.

For a future supervised setting, the existing segmentation fields provide a starting point for monitoring rather than a completed fairness certification. Any future comparison would need an agreed population, sufficient sample size, consistent outcome definitions, and a documented human-quality method where response quality is assessed. This report does not supply those future observations. It records the current preliminary evidence and preserves the fairness gate as **NOT PROVEN**.

## 9. Reliability and guardrails

Failure-injection and test evidence cover malformed tickets, no-result retrieval, provider timeout/outage and rate-limit paths, invalid generation, dependency failures, and audit-store failures. These paths fail closed to an auditable escalation rather than silently becoming a confident customer response.

Guardrails demonstrably block unsafe output. They cover private data/secrets, instruction manipulation, unsupported commitments, inadequate grounding, malformed generation, missing evidence, and invalid or missing confidence. The file-based kill switch can suppress automatic releases without a deployment; enabled tickets escalate with `KILL_SWITCH_ENABLED` while decision logging continues. These are tested controls, not evidence of production operator readiness.

The governance risk register covers confident-but-wrong output, private-data exposure,
prompt injection, uneven quality across groups, stale documentation, provider
unavailability, latency degradation, cost growth, and unsafe release. The incident
procedure specifies detection, containment, assessment, notification, remediation, and
review. These design and test artifacts are useful controls, but they do not establish
that a live team can meet response objectives under production conditions.

Reliability is implemented as explicit failure behavior rather than an assumption that every dependency responds correctly. Malformed input, no retrieval result, provider timeout or outage, rate limiting, malformed generation, dependency failure, and audit-store failure are tested paths. The intended terminal behavior is an auditable escalation, not a confident customer-facing fallback. This is why the decision log and escalation context are part of the safety design: a failure result should still provide a human reviewer with a reason and relevant process context.

The kill switch is an additional operational control. The file-based setting suppresses automatic releases without a deployment and routes enabled tickets to escalation with `KILL_SWITCH_ENABLED`, while decision logging continues. The control, governance incident procedure, and risk register provide concrete mechanisms for containment and review. They are not substitutes for evidence of live operator response times, alert delivery, recovery performance, or service availability, all of which remain outside the measured evidence.

## 10. Monitoring, governance, and reproducibility

Prometheus-compatible `/metrics` exposes bounded operational measurements without ticket bodies, customer identifiers, response text, retrieved passages, or secrets. Prometheus configuration and a Grafana dashboard cover ticket outcomes, latency, guardrail events, and confidence distribution. Governance artifacts provide a risk register, incident-response procedure, ownership roles, and kill-switch operation.

Historical frozen GitHub Actions CI was **SUCCESS** on run `34773077234` for
commit `6a80e91a3b7a82504f04afa98cdb8265f7617234`. Current post-freeze stabilized
CI was **SUCCESS** on run `34889316386` for commit
`7062f683e41a178e644713acee81478731dc9adc`. The current run covered checkout,
Python 3.12, dependency installation, `pip check`, credential-free startup, and
the complete 355-test suite with zero warnings. This is reproducibility evidence,
not production availability evidence.

### Post-Freeze Engineering Stabilization

Engineering was reopened after the V1 freeze to correct provider-configuration
leakage into deterministic tests, add complete Groq configuration, resolve
provider-specific model handling, stabilize compatibility-sensitive dependencies,
remove two warnings, and improve smoke-output and repository hygiene. The work was
implementation hardening rather than model or product tuning.

The stabilized baseline is commit
`7062f683e41a178e644713acee81478731dc9adc`. The complete suite contains 355
tests and passes with zero warnings when the parent environment selects offline,
OpenRouter, or Groq. A clean source export without `.env` also passed all 355 tests.
Dependencies use `requirements.txt` plus targeted `constraints.txt`; this is not
described as a complete lockfile. Unused direct LangChain, LangGraph, and LiteLLM
dependencies were removed because frozen V1 uses explicit Python orchestration and
the shared provider adapter directly.

OpenRouter now has provider-specific model resolution, while Groq is a first-class
provider with explicit credential, model, and base-URL configuration. The latest
successful live evidence for both providers remains a synthetic DEVELOPMENT
component smoke from Phase 4: each returned HTTP 200, valid structured output,
valid retrieved citations, and grounded content, then correctly failed closed on
`CONFIDENCE_FAILURE`. A later OpenRouter refresh was prevented by the execution
environment; this is not evidence of provider regression. These checks do not
establish end-to-end production provider reliability.

Stabilization did not rerun validation, access hidden data, change the 0.80/0.30
thresholds, modify `generation-v1.0.0`, weaken guardrails, or alter historical
evaluation artifacts. Therefore it creates no new validation-performance,
automation, routing-quality, hallucination, citation-quality, fairness, or business
outcome claim. The owner recommendation remains **LIMITED SUPERVISED PILOT — NOT
PRODUCTION-READY**.

The AI-use declaration records ChatGPT, Codex in VS Code, and Claude. The owner corrected or rejected suggestions that conflicted with evidence, safety, or project requirements, and retained final accountability.

Monitoring is deliberately bounded to avoid turning observability into another private-data exposure path. The Prometheus-compatible endpoint exposes operational measurements without ticket bodies, customer identifiers, response text, retrieved passages, or secrets. The accompanying Prometheus configuration and Grafana dashboard cover ticket outcomes, latency, guardrail events, and confidence distribution. These assets support inspection of the fail-closed system during a supervised use setting, but no load test, alert-delivery rehearsal, or production availability observation window was performed.

Reproducibility evidence is also kept separate from operational evidence. The observed hosted GitHub Actions run covered checkout, Python 3.12, dependency installation, `pip check`, offline clean-checkout smoke, and the complete Pytest suite. It demonstrates that the repository workflow ran successfully in that hosted CI execution. It does not demonstrate a continuously available service, an authenticated public API, recovery from backup, or performance under live demand.

Governance artifacts make the intended control ownership explicit. The risk register identifies confident-but-wrong output, private-data exposure, prompt injection treated as an instruction, uneven quality across groups, stale documentation, provider unavailability, latency degradation, unexpected cost growth, and unsafe release. The incident procedure supplies a Detect, Contain, Assess, Notify, Remediate, and Review sequence. Together with the kill switch, these artifacts give a reviewer a documented way to suspend release and preserve an audit trail when a safety condition is observed. They do not create evidence that the procedure has been exercised under a production incident.

Documentation is also treated as a governed dependency. Retrieval is limited to reviewed material rather than historical agent answers or personal snippets, and generation must cite the retrieved evidence used for a supported response. If the documentation is missing, stale, or insufficient for the request, the intended system response is escalation rather than a speculative answer. This design responds to the discovery concern about locating reviewed material while preserving the distinction between a retrieval mechanism and proof that the documentation corpus is complete or current in production.

## 11. V2 development experiment

Stage 20 was **DEVELOPMENT ONLY** and did not load validation. Isotonic calibration improved development ECE from 63.48% to 3.34%, but no evaluated policy met the zero-false-auto safety condition. The best policy had 18 false automatic responses. V2 was **REJECTED**, was not validated or promoted, and did not change frozen V1.

The V2 result is retained as a rejected development experiment rather than a hidden improvement claim. Its calibration result showed that an improvement in one development diagnostic did not establish a safe routing policy. The observed false automatic responses were incompatible with the project safety condition, so the experiment was not moved into validation and did not replace the frozen V1. This preserves the distinction between learning from a development experiment and promoting a change on the strength of that experiment alone.

### PRD revision and evidence-led change

The PRD revision record retains the original intent of the requirements while correcting assumptions contradicted by implementation and evidence. Earlier prescriptive wording that treated Chroma, BM25, or LangGraph as the frozen implementation was withdrawn from the current revision record. The final PRD describes outcome requirements: identifiable authoritative passages, measured retrieval quality, deterministic routing, blocking safety controls, and auditable logging. It records the actual MiniLM-plus-NumPy retrieval and explicit Python orchestration as justified departures from baseline options rather than as requirement failures.

The revision record also captures evidence that changed the deployment interpretation. Strong retrieval and development citation evidence did not establish useful responses; the human-development usefulness result remained 2.87/5. Development calibration improvement did not demonstrate safe automation; V2 remained rejected. Validation showed weak urgency, poor calibration, 0% automation, and 100% escalation. These facts update the current release posture without rewriting the original discovery record as though the later results had been known at the outset.

## 12. Production readiness and limitations

V1 is **NOT PRODUCTION-READY**. The following remain explicit limitations:

- FCR, CSAT, customer first-response time, production availability, load/alert performance, and backup/recovery performance are **NOT MEASURED**.
- Validation hallucination, semantic citation accuracy, usefulness, and correctness are **NOT MEASURED**.
- Production API authentication, authorization, and rate limiting are absent.
- Urgency quality and calibration are weak; ECE is about 42.3 percentage points.
- Safe non-zero automation is unproven: validation automation is 0% and escalation 100%.
- Development-only usefulness is 2.87/5 and is too low for production in the owner's view.
- Fairness evidence is preliminary and the fairness gate is not proven.
- Live-provider evidence is component-level development smoke evidence, not end-to-end validation or production evidence.

The production-readiness assessment is not a restatement of A1–A12. The engineering contract has credible PASS evidence for the frozen workflow, while production readiness requires additional evidence about real service operation, customer outcomes, security controls, and safe release behavior. In particular, the absence of API authentication, authorization, and rate limiting is a production-hardening gap; it is not retroactively classified as an A1–A12 failure. Likewise, the successful CI run and local P95 latency result demonstrate reproducibility and bounded technical performance, not availability or first-response performance.

The validation results also constrain the deployment posture. Intent classification and audit coverage are strong technical findings, but urgency and calibration are weak, and every validation terminal outcome escalated. The absence of released automatic validation responses prevents a claim about validation response quality or released-response privacy outcomes. The project therefore has a controlled, reviewable foundation suitable only for an evidence-gathering supervised setting, not a demonstrated basis for autonomous production support.

The proposed pilot boundary follows directly from these constraints. Any customer-impacting release decision must retain human review, an explicit override path, recorded terminal reasons, and the ability to stop automatic releases through the kill switch. Pilot observations would need to be recorded separately from development and validation evidence, with their own denominators and operational definitions. The current report does not claim those observations exist; it identifies the controls required for a limited supervised setting.

Automation is intentionally not treated as the single measure of progress. The 30% figure is an owner-confirmed future threshold for worthwhile automation, not an observed V1 result or a parameter to optimize retrospectively. A future pilot would need to demonstrate safety and usefulness before volume. The present validation outcome of 0.0% automation and 100.0% escalation remains the factual V1 result, and the owner decision explicitly prioritizes safety over automation.

## 13. Owner-approved recommendation

The confirmed owner recommendation is **LIMITED SUPERVISED PILOT**, not production deployment. A pilot must retain human oversight, explicit escalation and override, monitored outcomes, stop conditions, accountable reviewers, and appropriate customer/data handling controls. Safety is prioritized over automation.

**OWNER FUTURE TARGET — NOT MEASURED RESULT:** 30% is the owner's minimum worthwhile future automation target. It does not change V1 thresholds or its measured 0% validation automation result.

The recommendation is an owner decision based on the documented evidence boundaries, not a claim that the pilot outcomes have already been achieved. A limited supervised pilot is the only recommended deployment scope recorded here because it can preserve human accountability while gathering the operational evidence that is currently absent. It must not be described as production readiness, a successful automation result, or a fairness-gate pass. Human reviewers retain final accountability for customer-impacting decisions.

Before any production decision, the unresolved requirements remain explicit: stronger urgency and calibration evidence, demonstrated safe non-zero automation, improved usefulness, adequately powered fairness evidence, API authentication/authorization/rate limiting, production load and availability evidence, alert delivery evidence, and backup/recovery testing. These are future evidence requirements, not changes made to frozen V1 in this report.

### Supervised-pilot evidence boundary

The proposed pilot is an evidence-gathering deployment boundary, not a relabelling of the existing technical rerun. The rerun measured a fixed supplied population under the frozen workflow and reconciled terminal records; it did not observe customers, operator workload, first-response time, resolution, CSAT, FCR, availability, recovery, alert delivery, or customer-group response quality. Those measures retain their current NOT MEASURED or NOT PROVEN classifications until a separately defined pilot population produces them. A successful CI run and a clean checkout support reproducibility; they do not substitute for an operational observation window.

Within a limited supervised setting, the documented fail-closed route, explicit escalation context, decision log, and kill switch provide the implementation controls that keep human reviewers responsible for customer-impacting outcomes. Each terminal action must remain reviewable, and an escalation must be treated as a safety decision rather than as evidence that the customer issue was resolved. The owner recommendation therefore preserves a distinction between collecting evidence under supervision and authorizing an autonomous support service.

The pilot boundary also prevents the reported target gaps from being hidden by process compliance. Weak urgency performance, high calibration error, zero observed V1 automation, and low development usefulness are reasons to monitor and constrain use, not values to tune retrospectively against the held-out validation evidence. Likewise, functional private-data blocking tests and preliminary segmentation are useful safeguards and signals for review, but they do not demonstrate a released-response privacy outcome or a passed fairness gate. The next operational evidence would need its own agreed denominator, review process, and documented stop conditions before it could support a new production decision.

## 14. Owner-confirmed reflection

Only confirmed owner reflection is recorded here:

- The strongest engineering decisions were auditability, monitoring, and governance through a fail-closed design.
- Strong retrieval/citations did not guarantee useful answers; improved calibration did not guarantee safe automation; infrastructure could invalidate evaluation; and safe automation was harder than expected.
- If restarting, the owner would introduce monitoring and governance earlier and improve discovery through workflow review, an acceptance checklist, and an earlier pilot.

## 15. AI-use declaration

ChatGPT, Codex in VS Code, and Claude supported planning, implementation, review, debugging, testing, analysis, and documentation. Their role was development support rather than a substitute for accountable project decisions. The owner reviewed the assistance, corrected or rejected suggestions that conflicted with evidence, safety, or requirements, and retained final accountability.

The owner’s corrections and rejections covered architecture, prompts, implementation, evaluation, documentation, and the V2 decision. In particular, a recommendation or generated draft was not treated as evidence: preserved repository artifacts and their evidence classifications remain the basis for reported figures. This boundary also means that an AI-assisted explanation cannot convert development evidence into validation evidence or validation evidence into a production outcome.

The owner verified the final tool list and the corrections/overrides record on 12 September 2026. The owner remains responsible for understanding the code, verifying the declaration, authoring the assessed interpretation and business conclusions, and approving the final reflection. The complete approved declaration is retained in `docs/ai_use_declaration.md`.

<!-- HARD PAGE BREAK: REPORT BODY ENDS; APPENDICES START -->

<div style="page-break-before: always;"></div>

## 16. Appendices

### Appendix A. Validation classification confusion matrices

Method: the following matrices are reproduced from `docs/validation_confusion_matrix_appendix.md`, derived by joining preserved rerun records to supplied validation labels on `ticket_id`. All 80 IDs reconciled. No inference, validation rerun, V1/threshold change, or hidden-assessment access occurred. Rows are actual labels; columns are predicted labels.

#### A.1 Intent matrix

```text
I01 account_access             I09 data_residency          I17 rate_limit
I02 api_key_issue              I10 database_issue          I18 rollback_request
I03 api_usage_question         I11 deployment_failure      I19 security_incident
I04 authentication_failure     I12 feature_request         I20 sso_configuration
I05 billing_query              I13 integration_help        I21 unclear_request
I06 compliance_request         I14 onboarding              I22 webhook_issue
I07 configuration_help         I15 performance_degradation
I08 data_export                I16 quota_or_overage
```

```text
Actual\\Pred I01 I02 I03 I04 I05 I06 I07 I08 I09 I10 I11 I12 I13 I14 I15 I16 I17 I18 I19 I20 I21 I22 Support
I01           4   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0       4
I02           0   6   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0       6
I03           0   0   4   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0       4
I04           0   0   0   3   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0       3
I05           0   0   0   0  10   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0      10
I06           0   0   0   0   0   1   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0       1
I07           0   0   0   0   0   0   3   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0       3
I08           0   0   0   0   0   0   0   1   0   0   0   0   0   0   0   0   0   0   0   0   0   0       1
I09           0   0   0   0   0   0   0   0   6   0   0   0   0   0   0   0   0   0   0   0   0   0       6
I10           0   0   0   0   0   0   0   0   0   1   0   0   0   0   0   0   0   0   0   0   0   0       1
I11           0   0   0   0   0   0   0   0   0   0   5   0   0   0   0   0   0   0   0   0   0   0       5
I12           0   0   0   0   0   0   0   0   0   0   0   3   0   0   0   0   0   0   0   0   0   0       3
I13           0   0   0   0   0   0   0   0   0   0   0   0   3   0   0   0   0   0   0   0   0   0       3
I14           0   0   0   0   0   0   0   0   0   0   0   0   0   4   0   0   0   0   0   0   0   0       4
I15           0   0   0   0   0   0   0   0   0   0   0   0   0   0   3   0   0   0   0   0   0   0       3
I16           0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   2   0   0   0   0   0   0       2
I17           0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   1   0   0   0   0   0       1
I18           0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   6   0   0   0   0       6
I19           0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   4   0   0   0       4
I20           0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   1   0   0       1
I21           0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   6   0       6
I22           0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   0   3       3
```

All 80 intent predictions are on the diagonal. Each represented class has precision, recall, and F1 of 1.000; derived macro precision is 100.0%.

#### A.2 Urgency matrix

```text
Actual\\Pred  high  medium  low  Support
high             9       9    7       25
medium           9      17    9       35
low              2      10    8       20
Predicted total 20      36   24       80
```

| Actual urgency | Support | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| high | 25 | 45.0% | 36.0% | 40.0% |
| medium | 35 | 47.2% | 48.6% | 47.9% |
| low | 20 | 33.3% | 40.0% | 36.4% |

The urgency diagonal is 34/80, or 42.5%; derived macro F1 is 41.417%.

### Appendix B. Detailed metrics, human method, and traceability

The authoritative rerun report contains complete metric definitions, denominators, and status rules. The human-development method used 50 candidates and two independent reviewers; its agreement figures appear in Section 7. The A1–A12 mapping is maintained in `docs/final_a1_a12_acceptance_audit.md` and `docs/requirements_traceability.md`. The Section 4 diagram is the implemented frozen V1 architecture.
