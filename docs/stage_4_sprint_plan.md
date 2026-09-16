# Stage 4 Sprint Plan and Execution Reconciliation

## 1. Record status

This workbook separates the original plan from actual execution. The plan is preserved even where implementation, sequencing, capacity, or outcomes differed.

| Field | Value |
|---|---|
| Original planning period | Three-week capstone structure |
| Actual evidenced activity dates | 4–13 September 2026 |
| Actual effort | 51.5 hours — OWNER-RECONSTRUCTED ESTIMATE |
| Frozen V1 fingerprint | ddf89e82e7340a0257ee0c2ae1ce340612070545bc04f559e1e4c3ad733f59c1 |
| Final deployment state | Limited supervised pilot; NOT production-ready |

## 2. Capacity and commitments

### Original plan

The earlier sprint-plan draft allocated 20 hours to week one, 22 hours to week two, and 18 hours to week three. These were planning figures, not contemporaneously verified availability or actual effort.

| Week | Originally planned capacity | Original focus | Other commitments | Days unavailable |
|---|---:|---|---|---|
| Week one | 20 hours | Discovery, stakeholder analysis, PRD baseline | NOT RECORDED | NOT RECORDED |
| Week two | 22 hours | System build | NOT RECORDED | NOT RECORDED |
| Week three | 18 hours | Evaluation, workbooks, submission | NOT RECORDED | NOT RECORDED |

### Actual effort boundary

The owner confirmed approximately 3–5 hours per day in Claude before 10 September. The final effort log uses a 4-hour midpoint except 9 September at 5 hours. Total actual effort is an **OWNER-RECONSTRUCTED ESTIMATE of 51.5 hours**, based on AI-tool history, Git history, artifacts, CI evidence, and owner recollection. It was not automatically measured or contemporaneously tracked. Formal plan variance is therefore not calculable.

## 3. Original backlog preserved

This is the genuinely historical backlog recorded in the earlier workbook. Estimates are original planning estimates, not actual hours. Stale implementation names are annotated rather than presented as completed architecture.

| ID | Originally planned item | Planned hours | Priority | Dependency | Original definition of done / later note |
|---|---|---:|---|---|---|
| TASK-01 | Environment and configuration | 4 | Must | None | Environment variables load safely and tests pass. |
| TASK-02 | Data ingestion and normalization | 5 | Must | TASK-01 | Development tickets load; malformed payloads fail cleanly. |
| TASK-03 | Vector store and retrieval | 8 | Must | TASK-01 | Original draft named Chroma and Recall@3 above 85%; actual retrieval changed explicitly. |
| TASK-04 | Intent and urgency classification | 6 | Must | TASK-02 | Canonical labels and confidence produced. |
| TASK-05 | Deterministic routing | 6 | Must | TASK-03, TASK-04 | AUTO_RESPOND or ESCALATE with auditable reasons. |
| TASK-06 | Grounded response generation | 8 | Must | TASK-05 | Evidence-only response with structured citations or safe unsupported result. |
| TASK-07 | Safety guardrails | 8 | Must | TASK-06 | Unsafe output blocks and escalates. |
| TASK-08 | SQLite decision logging | 4 | Must | TASK-05 | Earlier draft incorrectly named src/logging.py; actual file is src/logging_store.py. |
| TASK-09 | FastAPI service | 4 | Must | TASK-07 | Earlier draft named /api/v1/ticket; actual processing route is POST /tickets/process, with GET /health and GET /metrics. |
| TASK-10 | Evaluation harness | 7 | Must | TASK-09 | Unattended reports over arbitrary dataset sizes. |

The original Word template also anticipated monitoring, CI, fairness, and final submission tasks. Those areas were implemented later even though the shortened historical Markdown backlog did not enumerate them separately.

## 4. Plan versus actual implementation

| Planned item | Actual implementation | Deviation | Reason | Evidence |
|---|---|---|---|---|
| Configuration | Typed environment/configuration handling | Broadly aligned | Secrets must not block import/tests until a credentialed provider is initialized. | src/config.py and configuration tests |
| Four-channel ingestion | Normalization for email, live chat, documentation comments, and community forum | Expanded beyond generic JSON loading | A2 required channel preservation and graceful malformed-input handling. | src/ingest.py; tests/test_ingest.py |
| Chroma vector retrieval with BM25 fallback | MiniLM embeddings with NumPy exact-cosine retrieval | Material architecture departure | Small corpus, simpler reproducibility, no managed/local vector service, exact inspectable ranking. | src/retrieve.py; retrieval tests and metrics |
| Intent/urgency classifier | TF-IDF word/character logistic-regression classifiers | Direct deterministic ML selected | Reproducible local inference with meaningful probabilities and no LLM prompt dependency. | src/classify.py; classification tests/evidence |
| Multi-factor router | Deterministic Python AUTO_RESPOND/ESCALATE routing | Aligned in purpose | Safety decision kept outside generative prose. | src/route.py; route/pipeline tests |
| Citation generator | Provider-neutral grounded generation using frozen generation-v1.0.0 | More explicit schema/failure contract | Provider portability and fail-closed structured output. | prompts/build/generation_v1.txt; src/generate.py; tests |
| Guardrails | Direct-code validation for private data, grounding, citations, injection/disclosure, commitments, invalid output, evidence, confidence, and internal failures | Expanded | Required blocking, traceability, and failure handling. | src/guardrails.py; guardrail/pipeline tests |
| SQLite logger at src/logging.py | SQLite logger at src/logging_store.py | File name corrected | Actual repository structure. | src/logging_store.py; logging tests; 80/80 validation records |
| FastAPI /api/v1/ticket | FastAPI POST /tickets/process; GET /health and /metrics | Route corrected | Actual tested API contract. | src/api.py; tests/test_api.py |
| Evaluation over development and “120 validation tickets” | 500-ticket development evaluation; supplied validation contains 80; first attempt failed and was preserved; authorized 80-ticket technical rerun is authoritative | Count and sequence corrected | Harness is arbitrary-size; hidden final assessment expected up to 120 was not run or inspected. | Evaluation artifacts, harness tests, freeze manifests |
| Unit tests ending at “75/75” | Historical frozen result: 342 passed, 2 warnings. Post-freeze stabilized result: 355 passed, 0 warnings. | Test count grew materially | Coverage expanded across acceptance, reliability, monitoring, governance, API, reproducibility, provider isolation, and evaluation. | Historical and stabilized evidence are reported separately; validation was not rerun. |
| No explicit monitoring/governance work in shortened backlog | Prometheus/Grafana configuration, risk/incident/kill-switch governance, and acceptance evidence | Added | Required operational visibility and governance outputs. | docs/governance.md, monitoring artifacts/tests |
| CI as final packaging activity | GitHub Actions implemented and observed successful | Completed with hosted evidence | Clean-checkout reproducibility and assessment requirement. | Historical frozen run 34773077234 at 6a80e91: SUCCESS. Current stabilized run 34889316386 at 7062f68: SUCCESS. |

## 5. Original detailed sprint sequence

The earlier workbook recorded this intended sequence:

- Week two, days 1–2: ingestion, Chroma indexing, and semantic retrieval.
- Week two, days 3–4: classification, routing, and citation generation.
- Week two, day 5: guardrails and SQLite logging.
- Week three, days 1–2: evaluation over 500 development and an incorrectly assumed 120 validation tickets.
- Week three, days 3–4: evaluation reporting and workbook synthesis.
- Week three, day 5: a then-current “75/75” regression claim and packaging.

Actual execution did not follow that plan exactly. Chroma/BM25 were replaced, the supplied validation set was 80, evaluation/freeze/reliability/governance work expanded, and test coverage grew. Exact historical start/end times and day-level completion percentages were not recorded.

## 6. Evaluation-count reconciliation

| Dataset/evidence | Correct handling |
|---|---|
| Development | 500 supplied tickets; used for development evaluation and permitted development experiments. |
| Supplied validation | 80 tickets. The initial infrastructure/cache failure remains preserved. |
| Authoritative validation | Explicitly authorized technical rerun of all 80 supplied validation tickets after cache-only remediation. |
| Evaluation harness | Accepts arbitrary dataset sizes; no hard-coded ticket count. |
| Hidden final assessment | Expected up to 120 tickets under the Build Specification. It was not run, inspected, reconstructed, or used for tuning. |

## 7. Cut order and prioritization

**Evidence label: RETROSPECTIVE OWNER-VERIFIED PRIORITIZATION.** No sufficiently complete contemporaneous cut-order table was retained, so this section does not claim the order was written before implementation.

Protected priorities, in order, were safety/fail-closed behavior, the A1–A12 acceptance contract, evaluation integrity, traceability, governance, and automation only when evidence supported it.

| Cut order | Item that could be deferred | Consequence | Reporting treatment |
|---:|---|---|---|
| 1 | Additional automation optimization or a V3 | Lower automation; avoids validation-driven tuning and unsafe release pressure. | Report V1 automation honestly and keep 30% as an owner future target. |
| 2 | Optional framework/vector-store complexity | Less architectural similarity to the reference stack, without losing required behavior. | Document explicit Python and NumPy departures and rationale. |
| 3 | Production deployment | No unsupervised production release. | Recommend limited supervised pilot and list production gates. |

Safety controls, A1–A12 evidence, evaluation separation, decision logging, governance essentials, and the frozen evidence were not candidates for removal.

## 8. Risk plan

**Evidence label: RETROSPECTIVE RECONSTRUCTION FROM PROJECT EVIDENCE.** Dates below are used only where preserved artifacts or Git/effort history support them.

| Risk/event | Evidence timing | Response and outcome |
|---|---|---|
| Secret/configuration mishandling | Build-wide | Placeholder-only configuration, delayed credential validation, leakage tests, and sanitized logs. No production secret-management claim. |
| Reproducibility / clean checkout | Build-wide; Git evidence 11 September | Clean-checkout corrections, documented setup, smoke checks, and hosted CI. |
| Provider/network limitation | Development evidence | Provider-neutral generation, failure injection, safe timeout/outage/rate-limit handling, and component-only live-provider smoke evidence. |
| Validation infrastructure/cache failure | 10 September | Failed first attempt preserved; cache-only remediation; explicitly authorized 80-ticket technical rerun used as authoritative evidence. |
| Calibration weakness | 10 September evaluation evidence | Frozen V1 retained; approximately 42.3 percentage-point validation ECE disclosed; automation remained fail-closed. |
| Usefulness gap | DEVELOPMENT human review | Usefulness 2.87/5 disclosed separately from strong retrieval/citation evidence; no production claim. |
| Stale documentation drift | Final reconciliation stages | Cross-document audits and workbook reconciliation; claims kept subordinate to authoritative artifacts. |
| Unsafe optimization | V2 development experiment | V2 rejected after 18 false automatic responses in the best development candidate; no validation or promotion. |

## 9. Every-second-day progress record

**Evidence label: RETROSPECTIVE RECONSTRUCTION FROM PROJECT EVIDENCE.** This is not a contemporaneous daily check-in. Exact times, percentages, and unrecorded blockers are omitted.

| Date | Finished / evidenced by this boundary | Next evidenced focus | Blocked by |
|---|---|---|---|
| 4 September 2026 | Discovery and baseline PRD work recorded. | Requirements, prompt/specification, sprint planning, and build preparation. | NOT RECORDED |
| 6 September 2026 | Continued design, requirements, prompt-library/planning, and early build work according to the owner-approved effort reconstruction. | Modular implementation and testing. | NOT RECORDED |
| 8 September 2026 | Continued pipeline, guardrail, and evaluation-preparation work according to the owner-approved effort reconstruction. | Development evaluation, calibration, freeze, and validation. | NOT RECORDED |
| 10 September 2026 | Development evaluation, calibration, V1 freeze, preserved validation failure, cache remediation, and authorized 80-ticket rerun. | Reproducibility, evidence reconciliation, CI, and live-provider component checks. | Embedding-cache/infrastructure failure during first validation attempt |
| 12 September 2026 | Owner interpretation/sign-off, workbook and effort-log work, and latest hosted CI confirmation. | Submission export/package completion. | Remaining export/package work; no engineering blocker asserted |

## 10. Milestones and evidence

| Milestone | Actual outcome | Evidence boundary |
|---|---|---|
| Discovery | Stakeholder/data findings recorded and later reconciled without retrospective leakage. | Stage 1 workbook and source material |
| PRD | Requirements established and reconciled with actual outcomes/deployment decision. | Stage 2 workbook and revision log |
| Prompt/specification library | Frozen generation prompt and direct-code specifications traced to FR-01–FR-12. | Stage 3 workbook and generation prompt |
| Pipeline | Modular ingest-classify-retrieve-route-generate-validate-log flow completed. | Source modules and pipeline tests |
| Guardrails | Fail-closed blocking and escalation demonstrated. | Guardrail, generation, route, and pipeline tests |
| Evaluation | Arbitrary-size unattended harness and development results completed. | Evaluation code, tests, and reports |
| V1 freeze | Frozen fingerprint recorded; thresholds unchanged. | Freeze manifests; fingerprint above |
| Validation | Failed first attempt retained; authorized 80-ticket technical rerun authoritative. | Validation-final and technical-rerun artifacts |
| Fairness/human review | Preliminary fairness analysis and two-reviewer 50-response DEVELOPMENT evaluation completed. | Stage 18 artifacts; validation human metrics NOT MEASURED |
| Monitoring/governance | Metrics/dashboard configuration, risk register, incident response, and kill switch completed/tested at capstone scope. | Monitoring and governance artifacts/tests |
| API | FastAPI /tickets/process, /health, and /metrics implemented/tested. | src/api.py and API tests |
| V2 experiment | Rejected; not validated or promoted. | Stage 20 development artifact |
| CI | GitHub Actions observed successful for the frozen and stabilized baselines. | Historical run 34773077234 at 6a80e91; current run 34889316386 at 7062f68 |
| Owner review | Mimoh Naik signed off on 12 September 2026. | Owner review worksheet |
| Workbook completion | Reconciliation progressed through discovery, PRD, prompt library, and sprint plan. | Submission-facing Markdown workbooks |

## 11. Test and CI evidence

- Historical frozen local result: **342 passed, 2 warnings** at `6a80e91`.
- Post-freeze stabilized local result: **355 passed, 0 warnings** at `7062f68`, including deterministic runs under offline, OpenRouter, and Groq parent environments.
- Historical hosted GitHub Actions: run **34773077234**, commit **6a80e91a3b7a82504f04afa98cdb8265f7617234**, result **SUCCESS**.
- Current stabilized hosted GitHub Actions: run **34889316386**, commit **7062f683e41a178e644713acee81478731dc9adc**, result **SUCCESS**.
- Stabilization occurred after the original sprint and freeze. It did not rerun validation, alter thresholds or prompts, or change any frozen evaluation metric.
- CI success supports reproducibility and the test workflow. It does not measure production availability, load behavior, alert performance, first-response time, FCR, or CSAT.

## 12. Sprint outcome and evidence boundaries

- A1–A12 have credible PASS evidence.
- Frozen V1 is NOT production-ready; the owner recommendation is a limited supervised pilot with safety prioritized over automation.
- V1 validation automation was 0% and escalation 100%; safe automation was not proven.
- **30% automation is an OWNER FUTURE TARGET, NOT A MEASURED RESULT.**
- DEVELOPMENT human evaluation only: hallucination 2%, semantic citation accuracy 98%, correctness 3.74/5, usefulness 2.87/5.
- Validation hallucination and semantic citation accuracy are NOT MEASURED.
- FCR, CSAT, customer first-response time, production availability, load/alert performance, backup/recovery, and production business outcomes are NOT MEASURED.
- The 51.5 effort hours are an OWNER-RECONSTRUCTED ESTIMATE, not automatically measured or contemporaneously tracked.
