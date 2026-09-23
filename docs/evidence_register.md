# Evidence Register

This register links requirements to implementation and observed evidence. Evidence
classes are kept explicit: `DEVELOPMENT`, `VALIDATION`, `HUMAN DEVELOPMENT
EVALUATION`, local test evidence, and operational evidence are not interchangeable.
The frozen V1 aggregate fingerprint is
`ddf89e82e7340a0257ee0c2ae1ce340612070545bc04f559e1e4c3ad733f59c1`.

## Feature and requirement register

| Capability | Source requirement | Implementation | Tests | Evaluation evidence | A1–A12 impact | Status and limitation |
|---|---|---|---|---|---|---|
| Four-channel ingestion and normalization | Build Specification; `AGENTS.md` §§11, 20 A2 | `src/ingest.py` | `tests/test_ingest.py`; pipeline/API channel tests | Stage 9 development records cover normalized pipeline processing | A2, A11 | **IMPLEMENTED / TESTED.** Email, live chat, documentation comments, and community forum are supported. Validation metrics do not separately certify each channel. |
| Intent and urgency classifier | Build Specification; `AGENTS.md` §§12, 20 A3, 23 | `src/classify.py` | `tests/test_classify.py`, `tests/test_calibration.py` | Stage 16 validation: intent accuracy/precision/recall/F1 100% on 80; urgency accuracy 42.5%, macro F1 41.4%; ECE 42.3% | A3, A5 | **PARTIAL.** Intent evidence is strong on this validation set; urgency and calibration are weak. V1 confidence threshold remains 0.80. |
| Authoritative retrieval | Build Specification; `AGENTS.md` §§13, 20 A4 | `src/retrieve.py`; `data/raw/documentation.json` | `tests/test_retrieve.py`, reliability tests | Stage 16 validation, 53 eligible: Recall@1/3/5 76.4%/87.7%/88.7%; Precision@1/3/5 90.6%/36.8%/25.6%; MRR 92.8% | A4, A5, A6, A11 | **MEASURED.** Exact cosine over MiniLM/NumPy returns identifiable chunks. Fully disconnected use requires pre-provisioned weights. |
| Deterministic routing and evidence sufficiency | Build Specification; `AGENTS.md` §§14, 20 A5 | `src/route.py`; `src/evidence.py`; thresholds in `src/config.py` | `tests/test_route.py`, `tests/test_calibration.py`, pipeline tests | Stage 11 retained 0.80/0.30; Stage 16 routing accuracy 40%, automation 0%, escalation 100%; post-validation engine diagnostics are fail-closed | A5, A11 | **SAFE BUT NOT BUSINESS-VIABLE.** `EvidenceSufficiencyEngine` is implemented and does not declare `sufficient=True`; no safe non-zero automation is proven. No validation auto-responses; escalation target ≤30% failed. |
| Grounded generation | Build Specification; `AGENTS.md` §§15, 20 A6 | `src/generate.py`; `prompts/build/generation_v1.txt` | `tests/test_generate.py`, guardrail/pipeline tests | Validation had no generation-eligible releases. Stage 18 human-development sample evaluated 50 generated candidates | A6, A7, A11 | **IMPLEMENTED; VALIDATION PERFORMANCE NOT MEASURED.** Human evidence is development-only and must not be described as validation auto-response quality. |
| Blocking guardrails | Governance Framework; `AGENTS.md` §§16, 20 A7 | `src/guardrails.py` | `tests/test_guardrails.py`, `tests/test_generate.py`, reliability tests | Adversarial tests prove blocking. Stage 16 guardrail coverage is NOT MEASURED because zero tickets reached generation | A6, A7, A11 | **IMPLEMENTED / TESTED.** No eligible validation release population. |
| Persistent decision logging | Build Specification; Governance Framework; `AGENTS.md` §§17, 20 A8 | `src/logging_store.py`; orchestrator integration | `tests/test_logging_store.py`, pipeline/reliability/API tests | Stage 16: 80 source/evaluated/terminal/logged, 100% decision-log coverage, reconciliation PASS | A8, A11 | **PASS.** SQLite is local; deployed durability, backup, concurrency, and retention are not measured. |
| End-to-end orchestration | Build Specification pipeline; `AGENTS.md` §26 Stage 9 | `src/orchestrator.py`; `src/pipeline.py` compatibility export | `tests/test_pipeline.py`, `tests/test_reliability.py` | Stage 9 development run: 500/500 processed and reconciled | A2–A8, A11 | **IMPLEMENTED / TESTED.** Direct Python stages remain explicit and independently testable. |
| Unattended evaluation harness | Evaluation Framework; `AGENTS.md` §§20 A9/A10, 22 | `evaluation/harness.py`, `metrics.py`, `report.py` | `tests/test_evaluation_harness.py`, `test_evaluation_framework.py`, `test_validation_readiness.py` | Stage 10 development and Stage 16 validation JSON/Markdown reports; arbitrary-count tests | A9, A10, A12 | **PASS.** Missing and human/operational metrics are not promoted to PASS. |
| Frozen validation boundary | Evaluation/Governance Frameworks; Stage 12 policy | `evaluation/freeze.py`; Stage 12/15 manifests | `tests/test_validation_readiness.py`, calibration path-rejection tests | Stage 12 fingerprint; Stage 13 preserved incident evidence; Stage 16 authorized technical rerun | A1, A5, A9, A10 | **PASS WITH DISCLOSED INCIDENT.** Attempt 1 failed retrieval infrastructure; attempt 2 was the single authorized technical rerun with no tuning. |
| One-time validation evidence | Evaluation Framework | `evaluation/results/validation-final.*`; `validation-technical-rerun.*` | Full regression suite before/after governed execution | Stage 16: 80/80 reconciled; dataset SHA-256 `8f2bd9…e78f`; evidence class VALIDATION | A3–A11 | **MEASURED.** Attempt 2 is the usable validation result. It must remain disclosed as the second attempt. |
| Fairness analysis | Governance target; `AGENTS.md` §24 | `evaluation/fairness.py` | `tests/test_fairness.py` | Stage 18 reports development and validation groups separately | A3–A6, A10 | **PARTIAL.** Explicit fields only. Validation enterprise (n=8) and non-fluent (n=19) were NOT MEASURED under minimum n=20. Cross-group human quality target remains NOT MEASURED. |
| Human review | Evaluation Framework hallucination method; `AGENTS.md` §22.1 | `evaluation/human_review.py`; protocol/templates and completed reviewer files | `tests/test_fairness.py` human-review aggregation tests | 50 HUMAN DEVELOPMENT EVALUATION candidates, two reviewers: hallucination 2%, semantic citation accuracy 98%, correctness 3.74/5, usefulness 2.87/5 | A6, A7, A10 | **DEVELOPMENT EVIDENCE.** Binary agreement 100%; correctness/usefulness kappas 0.712/0.941. Twenty-six samples contain at least one ordinal disagreement and were not adjudicated. |
| FastAPI interface | Operationalization requirement; `AGENTS.md` §26 Stage 17 | `src/api.py` | `tests/test_api.py` | Local smoke and 425-test regression evidence | A1, A2, A8, A11, A12 | **IMPLEMENTED / LOCALLY TESTED.** Application-level bearer authentication for ticket processing, separate reviewer authentication, bounded single-process rate limiting, `/ready`, exact reviewer-handoff retrieval, and immutable reviewer actions are implemented. Production IAM/RBAC, distributed rate limiting, gateway/edge abuse protection, and deployed availability remain unproven. |
| Prometheus/Grafana monitoring | `AGENTS.md` §26 Stage 14 | `src/monitoring.py`; `monitoring/prometheus.yml`; `monitoring/grafana/dashboard.json`; `/metrics` | Monitoring tests in `tests/test_api.py` | Local endpoint and privacy tests | A1, A11, A12 | **IMPLEMENTED / NOT OPERATIONALLY MEASURED.** No observed scrape, alert delivery, retention, or availability performance. |
| Deterministic kill switch | Governance Framework; `AGENTS.md` §26 Stage 16 | `src/operations.py`; API gate; `docs/governance.md` | Kill-switch API tests | Synthetic local test proves suppression, escalation reason, and audit persistence | A7, A8, A11 | **IMPLEMENTED / TESTED.** In-flight behavior and operator response time are documented, not measured in deployment. |
| Governance and incident response | Governance Framework; `AGENTS.md` §26 Stage 16 | `docs/governance.md` | Safety, reliability, logging, kill-switch tests | Risk register and procedures are documentary evidence | A7, A8, A11 | **DOCUMENTED.** Named individuals, operational rehearsal, alert thresholds, backups, and access controls remain unavailable. |
| V2 remediation experiment | Stage 20 owner task; evidence-integrity policy | `src/v2/*`; `evaluation/v2_experiment.py` | `tests/test_v2_candidate.py` | Stage 20 DEVELOPMENT: isotonic ECE improved, but best routing policy had 18 false auto-responses | A3–A7, A10 | **V2 REJECTED.** No V2 threshold selected, no validation run, and no human usefulness improvement claimed. Frozen V1 remains the historical evaluated baseline; it is not production-ready. |
| Git, CI, and clean checkout | `AGENTS.md` §§20 A1/A12, 26 Stages 15/19 | `.gitignore`; `.github/workflows/ci.yml`; `README.md`; `scripts/clean_checkout_smoke.py` | Full pytest suite and smoke script | Historical Stage 21 fresh-clone proof recorded 342 tests. Verified hosted CI run `35909582906`: SUCCESS at verified post-validation engineering checkpoint `f430ea6`; post-validation regression suite: 425 passing tests. | A1, A12 | **HOSTED CI OBSERVED PASSING.** This confirms the workflow at the named commit; it does not measure production availability. |

## Validation headline evidence

- Attempt 1 run ID `ccb57d71-618f-452d-88c5-ce017772fa6e` preserved the
  infrastructure-failure evidence: retrieval metrics 0%, processing failures 100%.
- Attempt 2 run ID `c5f1e1dc-531a-4586-b5d9-cbd1545789d4` is the authorized
  technical rerun after cache-only remediation. No tuning occurred between attempts.
- Attempt 2 processed and reconciled 80/80 tickets with zero processing failures,
  100% decision-log coverage, P50 0.0502 seconds, and P95 0.0915 seconds.
- Business metrics—FCR, first substantive response time, CSAT, availability, and
  repeat-contact rate—remain NOT MEASURED.

## Post-validation evidence-sufficiency remediation

| Evidence item | Classification | Result |
|---|---|---|
| Development answerability-group audit | DEVELOPMENT ONLY | 343 normalized groups; 36 contradictory groups covering 104 tickets |
| Unambiguous supervised population | DEVELOPMENT ONLY | 307 groups: 224 answerable, 83 unanswerable |
| Raw Top-1 retrieval discrimination | DEVELOPMENT ONLY | ROC-AUC 0.668244 |
| Retrieval-feature OOF model | DEVELOPMENT ONLY | ROC-AUC 0.662167; zero-observed-false-positive coverage 7/307 (2.28%) |
| Text + retrieval OOF model | DEVELOPMENT ONLY | ROC-AUC 0.681368; zero-observed-false-positive coverage 2/307 (0.65%) |
| Threshold promotion decision | GOVERNANCE / DEVELOPMENT | No evidence-sufficiency threshold promoted |
| Runtime remediation | ENGINEERING | `src/evidence.py` added at `e20a173`; orchestrator/audit integration added at `f744522` |
| Regression evidence | ENGINEERING | Historical integration evidence: 390/390 tests passed after integration; post-validation regression suite: 425 passing tests |
| Validation use | BOUNDARY | No validation rerun or development tuning against validation |
| Hidden/final use | BOUNDARY | Not accessed |

The remediation does not supersede or alter the historical frozen-V1 validation
artifacts. It explains why the current runtime retains fail-closed automatic-release
behaviour.
