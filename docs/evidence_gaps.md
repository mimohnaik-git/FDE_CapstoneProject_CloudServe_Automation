# Evidence Gaps

`Evidence not available` means the project has no qualifying measurement. The labels
below describe when the gap should be closed; they do not imply that missing evidence passed.

## Required before submission

| Gap | Current evidence | Required action |
|---|---|---|
| Submission evidence packaging decision | Immutable evaluation JSON contains original absolute execution paths, and SQLite decision evidence is locally preserved but intentionally ignored as runtime state. Stage 23 recorded hashes but did not package the databases. | Decide which decision databases the submission requires and how Git history will be supplied; do not edit frozen Stage 13/16 artifacts. |
| Final package production | The existing `submission/` tree is a pre-reconciliation staging reference and its source snapshot predates stabilized commit `7062f68`. The MP4/link, final 20–30 page PDF, refreshed workbook set, final archive, and a delivery mechanism for required repository history remain pending. | Complete documentation reconciliation, regenerate and inspect the existing seven report/workbook artifacts, refresh the source snapshot, complete the owner-controlled video, resolve the history-delivery mechanism, and assemble the exact four-folder archive without rerunning validation. |

## Recommended

| Gap | Current evidence | Recommendation |
|---|---|---|
| Human-review disagreement adjudication | Twenty-six of 50 samples have at least one ordinal correctness/usefulness disagreement; no binary grounding disagreement exists. | Conduct a documented adjudication if the Evaluation Framework or assessor expects final consensus scores; preserve original ratings. |
| Validation subgroup power | Enterprise n=8 and non-fluent n=19 were below the registered minimum n=20. | Collect a new governed dataset for subgroup evidence. Do not reuse or tune against existing validation. |
| Cross-group human quality | Governance target `<5 percentage points` is NOT MEASURED. | Run appropriately powered human review stratified by explicit groups on new evidence. |
| V2 answerability research | Stage 20 calibration improved but no strictly safe non-zero policy existed. | Continue only on development/new data with an inference-available answerability signal; retain V1 until a new validation cycle is authorized. |
| End-to-end generated-response validation | V1 validation released zero responses, so guardrail coverage, citation validity, and response quality were ineligible. | Evaluate a future version on a new frozen validation set only after safe automation is demonstrated on development evidence. |

## Production-only

| Gap | Why current evidence is insufficient | Required production evidence |
|---|---|---|
| Availability ≥99.5% | Local runs and `/health` are not an availability study. | Deployed observation window with defined service boundary and downtime accounting. |
| First substantive response time | Pipeline latency is not ticket-arrival-to-customer-response time. | Timestamped production workflow measurement. |
| FCR ≥60% and repeat contacts | Routing outcomes do not establish resolution or later contact. | Linked outcome/follow-up data with a governed baseline. |
| CSAT ≥4.0/5 | No customer ratings attributable to system responses exist. | Production or controlled-pilot survey evidence. |
| Load and latency under concurrency | Validation P95 0.0915 seconds was a local sequential pipeline measurement. | Representative load test covering API, retrieval, provider, database, and tail latency. |
| Alert delivery and response | Metrics/dashboard configuration and local tests do not prove paging. | Alert thresholds, routed notification test, acknowledgement and response-time exercise. |
| Backup and recovery | SQLite recovery behavior is documented but not rehearsed. | Restore drill with RPO/RTO, integrity, WAL handling, and decision reconciliation. |
| Authentication, authorization, and abuse controls | FastAPI exposes no measured production access-control boundary. | Identity, authorization, TLS, rate limiting, request limits, and security testing. |
| Live-provider reliability/cost | Offline mode was the default evidence path. | Provider SLA/error/latency/cost observation with approved retry and fallback policy. |
| Named accountable operators | Governance defines roles but explicitly says named individuals are unavailable. | Assign trained System Owner, on-call, Support Operations, Security, ML/Evaluation, and Platform owners. |
| Kill-switch operational performance | Synthetic tests prove logic, not fleet-wide propagation or human response time. | Rehearsed exercise across every instance, including in-flight traffic and audit failure. |

## Completed evidence confirmations

- Owner review and sign-off were completed by **Mimoh Naik** on **12 September 2026**.
  The owner approved a **limited supervised pilot**, confirmed V1 is **not
  production-ready**, and prioritized safety over automation.
- Historical frozen GitHub Actions run `34773077234` was **SUCCESS** on commit
  `6a80e91a3b7a82504f04afa98cdb8265f7617234`. Current stabilized run
  `34889316386` was **SUCCESS** on commit
  `7062f683e41a178e644713acee81478731dc9adc`, including dependency installation,
  consistency checks, offline startup, and the 355-test suite with zero warnings.
  These runs are reproducibility evidence, not production availability evidence.
- Provider-mode ambiguity, deterministic-test contamination from developer `.env`,
  the two dependency warnings, and the missing compatibility-constraints contract
  were resolved by post-freeze implementation hardening. This did not rerun
  validation or change any validation result.
- The 2% hallucination and 98% semantic citation figures remain **HUMAN DEVELOPMENT
  EVALUATION** results. Validation hallucination and validation semantic citation
  accuracy remain **NOT MEASURED**.
- **OWNER TARGET, NOT MEASURED RESULT:** 30% is a future worthwhile-automation target,
  not a V1 result. Validation V1 automation remains 0%.
