# Final capstone audit

This audit reconciles the accepted candidate with the supplied Project Brief,
Build Specification, Evaluation Framework, Governance Framework, and Submission
Guide. Statuses distinguish executed evidence from historical baselines and
unavailable production evidence.

## Evidence classes

- **Development OOF:** three-fold `StratifiedGroupKFold` evidence from the 500
  development tickets with normalized duplicate/template groups kept together.
- **Validation-80:** frozen canonical C1 run
  `c9985a56-8a9f-427e-ba88-8910d4b1ddb0`, retained under
  `evaluation/results/final_c1_validation80_20260926_191933/`.
- **Automated reference:** deterministic lexical/citation checks against 200
  senior-agent references; not human semantic review.
- **Historical baseline:** supplied descriptions of the support operation before
  automation; not outcomes caused by this system.
- **Unavailable:** no qualifying record was found. No value is inferred.

## Frozen candidate and provenance

| Item | Frozen value |
|---|---|
| Intent and urgency models | Existing calibrated word and character TF-IDF logistic classifiers |
| Answerability model | Existing calibrated classifier; routing confidence threshold `0.75` |
| Retrieval | Explicit TF-IDF; field-weighted title/heading/body, word and character features, unique-document top-k |
| Retrieval threshold | `0.10` |
| Intent threshold | `0.60` |
| AUTO allowlist | `api_usage_question`, `data_export`, `onboarding`, `sso_configuration`, `billing_query`, `quota_or_overage` |
| Evidence resolution-ratio minimum | `0.40` |
| Evidence symptom-margin maximum | `0.30` |
| Operational AUTO | OFF by default |
| Policy | `evidence-sufficiency-v1-fail-closed` |
| Controlled-evaluation settings fingerprint | `937126cfc35e1e0f7d14c972dceb11df74b77a878a0c87d6f32585cfeb5c3aad` |
| Controlled-evaluation pipeline fingerprint (TF-IDF) | `d31827b2b20b1c8e4db4ce85b61f62cbbc9e815b6f9b3896462b34962be304b2` |
| Production AUTO-OFF settings fingerprint | `b016c2b7a6eab6e884daedb487e97d0337db108253658f3b0d4fe86b2e521c7b` |
| Clean-trained intent artifact | `7c1cdb4422bba122914a09061dc9686a2f6676710090768798c5ac78c4edb674` |
| Clean-trained urgency artifact | `fb0ce6b96abfb4d604a2e9057f828085bc5e0a1d0937165b31bc1d34d000b978` |
| Clean-trained answerability artifact | `91945355cfc317990d7f6034d69b9152e73193b948a9e484dd1455881ab9b980` |
| Python / scikit-learn | 3.12.10 / 1.9.1 |

Input SHA-256 fingerprints are: development
`5a0d8912238ee9fde07b4b793bda4672261fbf3ab965bf3eb418ef6e87f95d78`,
Validation-80 `94c5b1adc1203f06d59522a909d755e8671e9bf1b165a0bc5a74ab62501c827b`,
KB `6622c2bd291b375437ea472959f81d106978f0ecfb9e3bb7eb40d3a9b8d3c038`,
and references `fd38accb2a11fa8986f9b1f37bf746209fc53ee0ba183621923e9c45c6b54cc8`.

## Development data audit and selection evidence

The 500 development tickets formed 179 normalized template groups: 91 exact
duplicate groups, 90 multi-ticket template groups, and a largest group of 15.
Intent had 0 contradictory groups. Urgency had 68 contradictory groups covering
359 tickets; answerability had 48 covering 271. These conflicts explain a
material ceiling on group-isolated urgency and answerability prediction.

The retained urgency candidate achieved development OOF accuracy 250/500
(50.0%), macro F1 0.3388, high-urgency recall 40/146 (27.40%), and ECE 0.0372.
The retained answerability model achieved accuracy 368/500 (73.6%), macro F1
0.4934, and ECE 0.0204 before routing threshold application. The 0.75 threshold
was selected from development evidence by requiring at least 50% answerable
recall and then minimizing false-answerable predictions.

Development retrieval improved from Hit@1 84.03%, Recall@5 75.84%, and MRR
0.8763 to Hit@1 90.20%, Recall@5 89.26%, and MRR 0.9356. The development-selected C1 routing policy expanded the AUTO allowlist to six intents and added an evidence-ambiguity fail-closed gate. Gate attribution is multi-label: intent confidence 303,
intent eligibility 228, evidence sufficiency 147, answerability confidence 117,
plan mismatch 25, other gates 25, must-not-auto policy 9, urgency 8, and account
or operational state 5.

The initial frozen development OOF route produced 3 AUTO decisions, including
1 false AUTO (DEV-0031, a `rate_limit` ticket labeled not answerable) and no
must-not-auto violation. Its OOF answerability prediction was answerable at
0.8517, so the existing intent, evidence, and confidence gates all passed. The
smallest development-supported correction removed `rate_limit` from the AUTO
allowlist; it did not change models, thresholds, retrieval, generation, or
validation logic. The rerun produced 2 AUTO decisions, precision 2/2, recall
2/311, 0 false AUTO, 309 false escalations, and 0/87 must-not-auto violations.
The final Validation-80 safety-closure run retained every required gate.
Production AUTO remains disabled.

## Final Validation-80 and reference results

| Area | Observed result | Evidence class |
|---|---|---|
| Intent | Accuracy 80/80; macro precision/recall/F1 1.000; ECE 0.1451, `NOT_ESTABLISHED` | Validation-80 |
| Urgency | Accuracy 35/80; macro precision 0.4651; recall 0.3671; F1 0.3306; high recall 7/25; ECE 0.0599, `NOT_ESTABLISHED` | Validation-80 |
| Answerability | Accuracy 60/80; macro precision 0.7787; recall 0.6478; F1 0.6549; ECE 0.0498, `NOT_ESTABLISHED` | Validation-80 |
| Answerable class | Precision 0.7391; recall 0.9623; F1 0.8361 | Validation-80 |
| Not-answerable class | Precision 0.8182; recall 0.3333; F1 0.4737 | Validation-80 |
| Retrieval Hit@1/3/5 | 50/53; 52/53; 52/53 | Validation-80 |
| Retrieval Recall@1/3/5 | 50/70; 62/70; 62/70 | Validation-80 |
| Retrieval MRR | 0.9591 | Validation-80 |
| Routing | 8 AUTO, 72 escalations; precision 8/8; recall 8/48; 40 false escalations; 0 false AUTO | Validation-80 |
| Must-not-auto | 0/14 violations | Validation-80 |
| Operations | 80 processed; 80 logged; 0 processing failures | Validation-80 |
| Pipeline latency | steady-state p50 0.0260 s; p95 0.0468 s over 79 post-warm-up tickets | Validation-80; not customer reply time |
| Citation resolvability | 200/200 | Automated reference |
| Must-mention coverage | 104/118; 52/59 responses fully satisfied | Automated reference |
| Must-not-claim violations | 0/200 | Automated reference |
| Top document match | 179/200 | Automated reference |
| Lexical grounding failures | 0/200 | Automated reference |

## Acceptance criteria A1 to A12

| ID | Authoritative requirement | Implementation and evidence | Result | Status |
|---|---|---|---|---|
| A1 | Run from clean checkout using README | Python 3.12 and `requirements.txt`; clean rehearsal plus current 99-test regression | Setup reproduced; current source passes locally | MET |
| A2 | Normalize four ticket channels | Typed ingestion plus four-channel tests | All supported channels tested | MET |
| A3 | Intent and urgency with confidence | Calibrated classifiers and explicit failure fallback | Predictions and numeric confidences recorded | MET |
| A4 | Retrieve real supplied-document passages | Explicit deterministic TF-IDF and resolvable passage IDs | Hit@1 50/53; citations map to KB | MET |
| A5 | Thresholded deterministic routing | Versioned thresholds and deterministic gates | Repeated-input and threshold tests pass | MET |
| A6 | Answers cite passages actually used | Persisted `supporting_passages` invariant | Reference citations resolved 200/200 | MET |
| A7 | Guardrail can block | PASS/BLOCK execution records and induced blocks | Guardrail tests pass | MET |
| A8 | Every decision persistently logged | Run-scoped SQLite plus fail-closed fallback | 80/80 decisions logged | MET |
| A9 | Full arbitrary-size unattended evaluation | CLI accepts input/output paths | Validation-80 completed unattended | MET |
| A10 | Automatic metrics report | JSON and Markdown reports | Report generated without manual calculation | MET |
| A11 | Defined failures do not stop processing | Malformed, retrieval, classifier, provider and audit boundaries | Failure-injection tests pass; 0/80 unexpected failures | MET |
| A12 | One documented test command | `python -m pytest -q` | 99 tests passed in the 29 September 2026 final audit | MET |

## Evaluation Framework reconciliation

| Criterion | Required target | Observed result | Evidence class | Status |
|---|---|---|---|---|
| Intent classification precision | At least 85% | Macro precision 100% | Validation-80 | MET |
| Human hallucination rate | At most 5%, at least 50 responses, two assessors | No traceable review of frozen outputs | Unavailable | NOT MEASURED |
| Semantic citation accuracy | At least 95% | 200/200 automated resolvability; no frozen-output human semantic review | Automated reference | NOT MEASURED |
| Pipeline latency p95 | Under 3 seconds | 0.0468 seconds over 79 post-warm-up tickets | Validation-80 | MET |
| Availability | At least 99.5% | Provider/failure behavior tested; production uptime not observed | Unavailable | NOT MEASURED |
| Confidence calibration | Each band within approximately 5 percentage points | Intent gaps 13.99–24.24 pp; urgency maximum 8.40 pp; answerability lower bands 8.46–11.44 pp | Validation-80 | NOT MET |
| FCR target | At least 60% | 10.0% simulated AUTO proxy; no observed production resolution | Simulation only | NOT MEASURED |
| First response time | Under 5 minutes | Pipeline latency is not customer first-response time | Unavailable | NOT MEASURED |
| CSAT | At least 4.0/5 | No post-automation customer measurement | Unavailable | NOT MEASURED |
| Escalation rate | At most 30% | Simulated 72/80 (90.0%) | Validation simulation | NOT MET |
| Repeat contacts | Report impact | No post-automation measurement | Unavailable | NOT MEASURED |
| Subgroup response quality | Demonstrate comparable human-reviewed quality | Routing proxy only; undersized groups | Validation proxy | NOT PROVEN |

## Governance Framework reconciliation

| Control | Evidence | Status |
|---|---|---|
| Decision logging and reconstruction | Predictions, reasons, thresholds, configuration, evidence, guardrails, timing, run ID and hashes persisted | MET |
| Private-data control | Secret, personal-contact and card patterns block and escalate | MET |
| Citation and grounding | Citation provenance invariant and lexical grounding guardrail | MET for automated control; human semantic quality NOT MEASURED |
| Instruction integrity and commitments | Prompt-injection and unsupported-commitment blocks | MET |
| Kill switch | Default-off environment gate plus one-way in-process emergency disable | MET technically; production operator authorization NOT PROVEN |
| Calibration | Confidence-band gaps exceed the five-point condition | NOT MET |
| Fairness | Routing correctness segmented; subgroup human response quality unavailable | NOT PROVEN |
| Production release | Development OOF safety gate passes; current-candidate calibration and human-review gates remain unmet | NOT MET; AUTO remains OFF |

## Historical evidence classification

### HISTORICAL DEVELOPMENT HUMAN EVIDENCE — VERIFIED, NOT CURRENT-CANDIDATE EVIDENCE

The recovered historical figures are n=50; hallucination 1/50 (2%); semantic
citation accuracy 49/50 (98%); correctness approximately 3.74/5; usefulness
approximately 2.87/5; binary reviewer agreement 100%; weighted kappa 0.712 for
correctness and 0.941 for usefulness. The response sample, two completed
reviewer files, and calculation output are present at immutable Git commit
`65f71c3fd10603421566fb786b452fdd2aa4b57b`. They are verified historical
development evidence, but are not evidence about the frozen candidate. See
`docs/HISTORICAL_EVIDENCE_REGISTER.md` for exact paths and subgroup analysis.

### HISTORICAL PRE-AUTOMATION BUSINESS BASELINE — VERIFIED

The supplied Project Brief records FCR approximately 42%, CSAT approximately
3.2/5, first-response time approximately 8–12 hours, and escalation approximately
58%. These are historical client baselines, not system outcomes.

## Submission requirements

| Required item | Observed state | Status |
|---|---|---|
| `01_Video` | Final presentation is present as `MimohNaik_Capstone_Video.mp4` | MET |
| `02_Report` | Required single 20–30 page PDF is present; final audit adds the required AI-use declaration and required filename | MET after final packaging |
| `03_Workbooks` | Five completed workbooks plus effort log are present and preserve their evidence boundaries | MET after final naming |
| `04_Source_Code` | Source, tests, data, CI, documentation and retained evaluation evidence are reconciled from current Git-tracked source | MET after final synchronization |
| Four-folder final archive | Exactly `01_Video`, `02_Report`, `03_Workbooks`, and `04_Source_Code` are present | MET structurally |
| Git history/provenance | Final packaged source is the clean Git HEAD of `main`; `43a3b60594539af59b3ace388b319653de7e24dd` is the historical pre-documentation baseline; `9149ce8f211800f2600f54720c5c51121d07bf3b` remains the previous verified engineering baseline; `origin` is configured | MET |
| AI-use declaration | Final report contains a bounded declaration of AI assistance and retained owner judgement | MET after final report packaging |

## Final conclusion

The executable acceptance gate is met and the accepted retrieval candidate
improves retrieval and reference quality without changing Validation-80 routing
safety. The technical source, report, workbooks, evidence provenance, and
four-folder package structure are ready after final reconciliation. The
supplied package includes the required final video. Calibration, frozen-output
human review, and production outcomes remain explicitly unproven or not measured.
Production automatic release remains disabled.

### Final C1 frozen evidence

- Development OOF gated result SHA-256: `fe3f481e035d0ae8c8df4a75b531042e4ca42fa0bb9370d3ca8fdc369b36008f`
- Validation-80 metrics report SHA-256: `97762301cd698f1ff6257da0559d4a4e761f227f40baabbb794f51375354f611`
- Validation-80 decisions SHA-256: `dacff54560d6f342ee842d53129de059fd24083e86382b2d1aaa0223be4d5744`
- Final Validation-80 run ID: `c9985a56-8a9f-427e-ba88-8910d4b1ddb0`
- Final routing: 8 AUTO / 72 ESCALATE
- False automatic responses: 0
- Must-not-auto violations: 0
- Evidence-ambiguity escalations: 4
