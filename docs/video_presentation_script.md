# CloudServe Support Automation Video Preparation Script

**Target duration:** 20 minutes
**Status:** Recording input only; no MP4 has been produced

This script uses current evidence. The presenter must deliver the interpretation and
reflection in their own words and demonstrate the real frozen V1 system. Do not describe
the development human review as validation performance.

## 0:00–2:00 — Problem

- Introduce the CloudServe support-automation problem.
- Label 43.8% historical FCR, 2.97/5 historical CSAT, and 71.4% document
  answerability as findings from the supplied 500-ticket development dataset—not as
  outcomes caused by the built system.
- State the core constraint: automate only when classification, retrieval, risk, and
  guardrails all support release; otherwise escalate.

## 2:00–5:00 — Discovery evidence

- Show the completed discovery workbook and the authoritative 29-article corpus.
- Explain which findings affected the design, citing the actual source evidence.
- Do not claim system-attributable FCR, CSAT, first-response time, availability, load,
  alerting, or other business outcomes; these remain NOT MEASURED.

## 5:00–7:00 — Frozen V1 architecture

- Walk through normalization, TF-IDF/logistic-regression classification, exact MiniLM/NumPy
  retrieval, deterministic routing, grounded generation, blocking guardrails, and
  SQLite decision logging.
- State the frozen thresholds: classification 0.80 and retrieval 0.30.
- Explain that ChromaDB and BM25 were reference/earlier design ideas, not the final V1
  retrieval implementation.

## 7:00–14:00 — Live demonstration

The recording must show at least seven minutes of the system actually running.

1. Start the API in offline mode from repository-root README instructions.
2. Show `/health` without describing it as proof of provider availability.
3. Process a valid ticket and show its controlled terminal result and decision ID.
4. Show an ordinary low-confidence escalation.
5. Show a prompt-injection or private-data guardrail case ending in safe escalation.
6. Enable the deterministic kill switch, show AUTO_RESPOND suppression with an explicit
   auditable reason, then disable it.
7. Show `/metrics` and verify it contains no ticket body, customer identifier, retrieved
   passage, response text, or secret.
8. Show the preserved unattended validation rerun report with 80 source, evaluated,
   terminal, and decision records reconciled.

V1 validation had zero automatic releases. Do not stage or claim a validation
auto-response success. A successful demonstration can instead show correct ingestion,
retrieval structure, controlled escalation, guardrail blocking, logging, and metrics.

## 14:00–17:00 — What the evidence says

State the evidence class and denominator with every result.

- **VALIDATION:** intent metrics 100% on 80 tickets; urgency accuracy 42.5%; retrieval
  Recall@3 87.7% on 53 eligible tickets; routing accuracy 40%; automation 0%; escalation
  100%; processing failures 0%; decision-log coverage 100%; local pipeline P50/P95
  0.0502s/0.0915s; calibration error 42.3%.
- **HUMAN DEVELOPMENT EVALUATION:** hallucination 2% (1/50), semantic citation accuracy
  98% (49/50), response correctness 3.74/5 and usefulness 2.87/5 across 100 reviewer
  ratings.
- **NOT MEASURED:** validation hallucination/citation/response quality, FCR, CSAT,
  availability, customer first-response time, repeat contact, deployed load behavior,
  and alert delivery.

Disclose that validation attempt 1 failed because of infrastructure and attempt 2 was
the single authorized technical rerun, with no tuning between attempts.

## 17:00–18:00 — Governance and risk

- Show the risk register, deterministic kill switch, incident procedure, audit logging,
  and fail-closed provider/audit failure behavior.
- Explain that local tests verify logic; they do not establish production availability,
  operator response time, or alert performance.

## 18:00–20:00 — Owner reflection and next steps

The project owner must present their own interpretation and reflection. Evidence that
may inform it:

- V1 is safe but operationally over-conservative: 0% automation and 100% escalation.
- V2 improved development calibration but was rejected because candidate routing still
  produced false auto-responses; it was not validated.
- Remaining work includes a new safe answerability signal and validation cycle,
  operational security, hosted CI observation, load/availability/alert studies,
  backup/restore rehearsal, and named operators.

## Recording checklist

- Produce one MP4, 1080p or better, roughly 18–22 minutes.
- Be visible for the introduction and close.
- Keep terminal and report text legible.
- Use the required enrolment-name filename.
- If linking instead of embedding the file, place only the link text file in
  `01_Video/`.
