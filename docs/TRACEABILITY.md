# CloudServe requirements and traceability

This register separates supplied evidence from engineering interpretation. The
authoritative build requirements are the twelve acceptance criteria in
`01_Read_First/02_Build_Specification.docx`. Discovery evidence comes from the
five supplied stakeholder transcripts and the official datasets.

## Acceptance criteria

| ID | Supplied requirement | Implementation | Verification |
|---|---|---|---|
| A1 | Run from a clean checkout using the README | `README.md`, dependency files, training CLI | Clean-checkout commands; CI |
| A2 | Normalize email, chat, docs comments, and forum | `src/ingest.py`; original and normalized text remain distinct | `tests/test_ingest.py`, four-channel pipeline test |
| A3 | Intent and urgency with numeric confidence | `src/classify.py`; explicit unknown states on classifier failure | classifier/failure tests; evaluation precision, recall, ECE and calibration bands |
| A4 | Retrieve identifiable passages from supplied docs | `src/retrieve.py`; explicit field-weighted word+character TF-IDF, boundary threshold, unique-document top-k | retrieval/backend tests; frozen-run Hit@1 50/53, Recall@5 62/70, MRR 0.9591 |
| A5 | Deterministic threshold routing | `src/eligibility.py`, `src/router.py` | policy determinism and gate tests |
| A6 | Grounded answers with resolvable citations | `src/generate.py`, `src/guardrails.py`, decision `supporting_passages` | deterministic top-document Common causes + Resolution assembly; every generated citation resolves to supplied generation evidence and a real KB passage |
| A7 | A guardrail runs on every draft and can block | `src/guardrails.py` | named PASS/BLOCK records for expected controls plus block tests |
| A8 | Persistent auditable decision log | `src/audit.py`, decision payload/trace; final fail-closed state is also used for fallback persistence | reconciliation, forced audit failure, and API tests |
| A9 | Any-size unattended evaluation | `evaluation/harness.py`; per-run ID and database | parametrized sizes 1, 7, and 43; run-isolation test; official CLI run |
| A10 | Metrics report without manual work | `evaluation/harness.py`, `evaluation/metrics.py` | CLI artifact test |
| A11 | Fail safely under defined faults | pipeline exception boundaries and provider fallback | induced failure tests |
| A12 | One documented test command | `python -m pytest` | test suite and CI |

Cross-cutting release controls are implemented in `src/config.py`,
`src/pipeline.py`, `src/api.py`, `requirements.txt`, and CI.
They cover the default-off release flag, one-way emergency disable latch,
AUTO-only external answer/citation payload, explicit retrieval selection,
configuration fingerprint, and the verified Python 3.12 dependency set.

Final results and criterion statuses are consolidated in
`docs/FINAL_CAPSTONE_AUDIT.md`. Development-only selection evidence is stored in
`evaluation/results/development/development_selection.json`; it records the
group-isolated split, candidates, contradictions, selected configuration, and
artifact hashes without using Validation-80 labels for selection.
Historical business, human-review, calibration, fairness, and production-gap
claims are separately classified with immutable provenance in
`docs/HISTORICAL_EVIDENCE_REGISTER.md`.

## Discovery evidence to design decisions

| Evidence ID | Observed evidence | Analysis | Implemented decision |
|---|---|---|---|
| D1 | Sofia and Ines describe documentation search as the bottleneck; Daniel says many escalations need only a page and short answer | Retrieval and escalation context address the operational constraint more directly than a conversational UI | Passage retrieval, citations, and reviewer drafts are core; no chatbot UI is required |
| D2 | Marcus would rather send nothing than a wrong answer; Ravi wants honest automation disclosure | False automation has a higher cost than escalation | Fail-closed routing, explicit release switch, citations, and block-capable guardrails |
| D3 | Security is always escalated; Daniel also flags billing commitments and data-location consequences | Some intents require deterministic restrictions independent of confidence | Never-automate intent policy plus commitment and safety checks |
| D4 | Sofia reports worse outcomes for non-fluent English; Marcus and Ravi raise tier differences | Aggregate accuracy cannot establish equitable quality | Reports segment routing correctness by language fluency, tier, region, and channel; undersized groups return `NOT_PROVEN` |
| D5 | Daniel says escalations arrive without summary or attempted evidence | A safe escalation can still reduce handling time | Escalations retain predictions, reasons, draft, sources, flags, and trace data |
| D6 | Ines distinguishes reviewed articles from unreviewed private snippets | Runtime knowledge must be limited to the authoritative corpus | Retrieval uses only `documentation.json`; reference responses remain evaluation-only |

## Evidence conflicts

The pack is inconsistent about evaluation counts. The physical files contain
500 development and 80 validation tickets. The Project Instructions, Build
Specification, and Dataset Guide describe a hidden set of 120. Other passages
refer to 100. The explicit user constraint and the more specific schema guides
support 120 as the expected hidden size. The implementation does not encode any
of these counts; it processes the number of records present at runtime.

The Project Brief says validation should be run once near the end, while the
Dataset Guide says the 80-ticket validation set may be used repeatedly and the
hidden 120-ticket set is the protected final measure. The Dataset Guide is more
specific and internally consistent with the hidden-set design. This repository
therefore treats the 80 records as validation and keeps the harness arbitrary-
size for the protected hidden evaluation.
