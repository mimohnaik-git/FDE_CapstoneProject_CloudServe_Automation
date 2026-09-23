# Evaluation framework implementation

Stage 10 uses the registry in `evaluation/metrics.py` as the authoritative
inventory of metrics, definitions, eligible populations, documented targets,
measurement types, and status rules. Machine output contains the registry,
denominator-aware measurements, flat status assessments, evidence provenance,
limitations, and reconciliation status. The unattended harness also writes a
Markdown report.

Only `PASS`, `FAIL`, `NOT MEASURED`, `NOT APPLICABLE`, and
`MEASURED — NO FORMAL TARGET` are valid statuses. A missing value or a zero
eligible denominator is `NOT MEASURED`, never `PASS`.

Automated measures include intent and urgency classification metrics,
Recall@1/3/5, Precision@1/3/5, MRR, routing and automation measures, guardrail
coverage, processing failures, decision-log coverage, citation ID validity,
calibration, and P50/P95 pipeline latency. Citation ID validity is an identifier
resolution check and is not semantic citation accuracy.

Hallucination rate, semantic citation accuracy, response correctness, and
response usefulness require real human review. `evaluation/human_review_template.json`
is intentionally blank. FCR, customer first-response time, CSAT, availability,
and repeat contacts require operational evidence and are not inferred from
pipeline timing, routing outcomes, or historical fields in the supplied data.

Run from the repository root:

    python -m evaluation.harness --input <tickets.json> --output evaluation/results/run.json --dataset-role development

Use `validation` or `final` only for a deliberately authorized run of that
evidence class. Development, validation, and final results must remain separate.

## Stage 11 calibration

Stage 11 uses `evaluation/calibration.py` and only the configured development
dataset. A deterministic five-fold stratified group split assigns three folds
to training, one to policy calibration, and one to confirmation. Normalized
duplicate text groups cannot cross populations. Candidate thresholds are
selected on calibration evidence and checked on the untouched development
evaluation fold.

    python -m evaluation.calibration

The command writes `evaluation/results/stage11-calibration.json` and a companion
Markdown report. Production defaults change only when a viable policy has zero
false auto-responses, zero must-not-auto-respond violations, and zero true
high-risk violations on both held-out populations.

## Stage 12 validation freeze

Development tuning is complete. Stage 11 retained classification confidence
`0.80` and retrieval routing `0.30` because no nontrivial policy satisfied all
safety constraints. `evaluation/results/stage12-freeze-manifest.json` records
the frozen production/evaluation configuration and practical fingerprints.

Validation remains untouched. Readiness preflight checks only the validation
path's existence and never reads, parses, counts, or fingerprints its content.
The fingerprint and ticket count are produced only by a later, explicitly
authorized execution. Any post-validation tuning invalidates the validation
claim and requires a newly isolated validation set.

    python -m evaluation.harness --input data/raw/validation_tickets.json --output evaluation/results/validation-final.json --dataset-role validation --preflight

Frozen one-shot command, documented but not executed in Stage 12:

    python -m evaluation.harness --input data/raw/validation_tickets.json --output evaluation/results/validation-final.json --dataset-role validation

## Post-validation evidence-sufficiency development study

**Evidence classification:** DEVELOPMENT ONLY - POST-VALIDATION REMEDIATION.

This study was performed after the historical frozen-V1 validation run. It did not
rerun or tune against the 80-ticket validation set and did not access final/hidden
assessment data.

The 500 development tickets contain 343 normalized request-text groups. Thirty-six
groups, covering 104 tickets, contain contradictory `answerable_from_docs` labels for
the same normalized request text. Those ambiguous groups were therefore excluded from
supervised evidence-sufficiency modelling rather than split across training and
evaluation.

The resulting development population contained 307 unambiguous independent text
groups: 224 answerable and 83 unanswerable.

| Development diagnostic | Result |
|---|---:|
| Raw retrieval Top-1 ROC-AUC | 0.668244 |
| Retrieval-feature 5-fold OOF ROC-AUC | 0.662167 |
| Text + retrieval 5-fold OOF ROC-AUC | 0.681368 |
| Retrieval-model zero-observed-false-positive coverage | 7/307 (2.28%) |
| Text + retrieval zero-observed-false-positive coverage | 2/307 (0.65%) |

The combined model improved ROC-AUC only modestly and its zero-observed-false-positive
region covered only two independent development groups. That evidence was judged
insufficient to justify a production automatic-release threshold.

**Decision:** no evidence-sufficiency threshold was promoted. The runtime evidence
gate remains fail-closed. Historical validation metrics remain unchanged.
