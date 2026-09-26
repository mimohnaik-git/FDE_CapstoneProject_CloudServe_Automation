# Evaluation report — run 7d013121-2634-4306-90f0-2ed193d056f2

- **run_id**: 7d013121-2634-4306-90f0-2ed193d056f2
- **started_at**: 2026-09-26T10:40:48.332000+00:00
- **input**: data\cloudserve\validation_tickets.json
- **dataset_sha256**: 94c5b1adc1203f06d59522a909d755e8671e9bf1b165a0bc5a74ab62501c827b
- **source_tickets**: 80
- **evaluated_tickets**: 80
- **logged_decisions**: 80
- **decision_log_coverage**: 80/80
- **retrieval_backend**: tfidf
- **retrieval_configuration**: field-weighted-word-char-unique-docs-v1
- **config_fingerprint**: e9beb3c9b0fba1ac3561c19f890feaf871310e610aa03f29c866d6a60d22f750
- **intent_threshold**: 0.8
- **retrieval_threshold**: 0.1
- **operational_auto_policy_default**: OFF
- **controlled_evaluation_auto_policy**: ENABLED
- **customer_release_authorized**: True
- **eligibility_policy**: evidence-sufficiency-v1-fail-closed
- **training_dataset_sha256**: 5a0d8912238ee9fde07b4b793bda4672261fbf3ab965bf3eb418ef6e87f95d78
- **artifact_sha256**: {'answerability.joblib': 'dc048874f03d422693b9057d674683f8cd11f5fdfcc1964aad885235a13f5d02', 'intent.joblib': '6d10f379ca04f6cf2dde59f7cc159c828f959ff0dcf02ab1e2dcd23a66e89ba7', 'urgency.joblib': 'c2bcd0fe93baa30f76cf3be77f4c72e9adb5eddfb802e156b220dae41a04e527'}
- **python_version**: 3.12.10
- **sklearn_version**: 1.9.1
- **git_sha**: None
- **decision_database**: evaluation\results\final_capstone\decisions-7d013121-2634-4306-90f0-2ed193d056f2.sqlite3
- **finished_at**: 2026-09-26T10:41:07.507446+00:00
- **elapsed_seconds**: 19.175361

## Intent
- Accuracy: 100.00% (80/80)
- Macro F1: 1.0 over 22 classes
- ECE: 0.1451 (n=80, bins=10)
- Calibration status: NOT_ESTABLISHED
- Confidence bands: [{'low': 0.7, 'high': 0.8, 'n': 4, 'mean_confidence': 0.7576, 'observed_accuracy': 1.0, 'absolute_gap': 0.2424}, {'low': 0.8, 'high': 0.9, 'n': 76, 'mean_confidence': 0.8601, 'observed_accuracy': 1.0, 'absolute_gap': 0.1399}]

## Urgency
- Accuracy: 43.75% (35/80)
- Macro F1: 0.3306
- High recall: 28.00% (7/25)
- ECE: 0.0599 (n=80, bins=10)
- Calibration status: NOT_ESTABLISHED
- Confidence bands: [{'low': 0.3, 'high': 0.4, 'n': 7, 'mean_confidence': 0.3883, 'observed_accuracy': 0.4286, 'absolute_gap': 0.0403}, {'low': 0.4, 'high': 0.5, 'n': 38, 'mean_confidence': 0.4624, 'observed_accuracy': 0.4211, 'absolute_gap': 0.0414}, {'low': 0.5, 'high': 0.6, 'n': 35, 'mean_confidence': 0.5412, 'observed_accuracy': 0.4571, 'absolute_gap': 0.084}]

## Answerability
- Accuracy: 75.00% (60/80)
- Macro F1: 0.6549
- ECE: 0.0498 (n=80, bins=10)
- Calibration status: NOT_ESTABLISHED
- Confidence bands: [{'low': 0.5, 'high': 0.6, 'n': 9, 'mean_confidence': 0.5523, 'observed_accuracy': 0.6667, 'absolute_gap': 0.1144}, {'low': 0.6, 'high': 0.7, 'n': 30, 'mean_confidence': 0.6488, 'observed_accuracy': 0.7333, 'absolute_gap': 0.0846}, {'low': 0.7, 'high': 0.8, 'n': 23, 'mean_confidence': 0.7469, 'observed_accuracy': 0.7391, 'absolute_gap': 0.0078}, {'low': 0.8, 'high': 0.9, 'n': 18, 'mean_confidence': 0.8465, 'observed_accuracy': 0.8333, 'absolute_gap': 0.0131}]

## Retrieval (eligible tickets: 53, expected docs: 70)
- Recall@1: 71.43% (50/70); Hit@1: 94.34% (50/53); Precision@1: 0.9434
- Recall@3: 88.57% (62/70); Hit@3: 98.11% (52/53); Precision@3: 0.3899
- Recall@5: 88.57% (62/70); Hit@5: 98.11% (52/53); Precision@5: 0.234
- MRR: 0.9591

## Routing
- Accuracy: 48.75% (39/80)
- Expected AUTO: 48, expected ESCALATE: 32
- Automation rate: 8.75% (7/80)
- False automatic responses: 0
- False escalations: 41
- Must-not-auto violations: 0 / 14

## Business indicators
- Simulated FCR proxy: 8.75% (7/80)
- Simulated escalation rate: 91.25% (73/80)
- Historical FCR baseline in supplied records: 46.25% (37/80)
- Customer first-response time after automation: Evidence not available.
- Customer satisfaction after automation: Evidence not available.
- Note: Simulation proxies are routing outcomes, not observed customer resolutions. Historical fields describe the supplied baseline, not system performance.

## Guardrails
- Drafts checked: 78
- Tickets blocked: 0
- Blocks by guardrail: {}

## Latency (pipeline only — not customer first-response time)
- Steady state: {'n': 79, 'mean': 0.0271, 'p50': 0.0266, 'p95': 0.0369, 'max': 0.0406}
- Including warm-up: {'n': 80, 'mean': 0.0273, 'p50': 0.0266, 'p95': 0.0369, 'max': 0.0445}

## Subgroup gate
- channel: NOT_PROVEN (gap 9.39 pp; undersized: ['forum', 'chat', 'docs_comment'])
- customer_tier: NOT_PROVEN (gap 14.76 pp; undersized: ['enterprise'])
- customer_region: NOT_PROVEN (gap 33.33 pp; undersized: ['asia_pacific', 'north_america', 'europe', 'latin_america'])
- language_fluency: NOT_PROVEN (gap 11.99 pp; undersized: ['non_fluent'])
- Quality signal is routing correctness, not response quality. A response-quality fairness claim needs human-reviewed subgroup samples.

## Reviewer drafts vs references
```
{
  "references": 200,
  "drafts_generated": {
    "value": 1.0,
    "num": 200,
    "den": 200
  },
  "citation_resolvability": {
    "value": 1.0,
    "num": 200,
    "den": 200
  },
  "lexical_grounding_failures": 0,
  "must_mention_coverage": {
    "value": 0.8814,
    "num": 104,
    "den": 118
  },
  "tickets_satisfying_all_mentions": {
    "value": 0.8814,
    "num": 52,
    "den": 59
  },
  "must_not_claim_violations": 0,
  "top_doc_in_expected_set": {
    "value": 0.895,
    "num": 179,
    "den": 200
  },
  "references_without_ticket_input": 0,
  "note": "Automated, lexical checks. Not a substitute for human review."
}
```

## Not measured by this run
Hallucination (human), response correctness/usefulness, observed FCR, CSAT, customer first-response time, production availability, repeat contact.
