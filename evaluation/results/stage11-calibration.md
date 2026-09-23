# Stage 11 Confidence Calibration and Routing Threshold Selection

## Calibration Method

Evidence class: **DEVELOPMENT**. The classifier was fit on 305 tickets. Intent confidence uses group-safe sigmoid calibration; the urgency head remains uncalibrated. Policy selection used 95 disjoint calibration tickets; confirmation used 100 disjoint evaluation tickets.

## Leakage Check

- Group key: normalized lowercase subject+body with collapsed whitespace
- Train/calibration overlap: 0
- Train/evaluation overlap: 0
- Calibration/evaluation overlap: 0
- Split assignment SHA-256: `d9b91a05a76b94f87bbdf9511993a4cc744aeaac8455d11bd1394f1b4c869810`
- Validation or final data loaded: `False`

## Calibration Metrics

| Population | Tickets | Expected calibration error |
| :--- | ---: | ---: |
| Calibration | 95 | 12.5% |
| Evaluation | 100 | 6.1% |

Reliability buckets and per-intent confidence behavior (minimum five examples) are recorded in the machine-readable result.

## Threshold Grid

These routing rows are **counterfactual policy simulations** with `evidence_sufficient=True`. They measure classification/retrieval threshold behavior after an independent evidence-sufficiency gate has hypothetically passed. They are not observed production automation rates.

| Class threshold | Retrieval threshold | Route accuracy | Auto precision | Auto recall | Automation | Escalation | False auto | False escalation | Must-not violations | High-risk violations | Safety satisfied |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| 0.30 | 0.30 | 75.8% | 83.1% | 86.5% | 81.1% | 18.9% | 13 | 10 | 0 | 0 | False |
| 0.30 | 0.40 | 75.8% | 83.1% | 86.5% | 81.1% | 18.9% | 13 | 10 | 0 | 0 | False |
| 0.30 | 0.50 | 71.6% | 82.2% | 81.1% | 76.8% | 23.2% | 13 | 14 | 0 | 0 | False |
| 0.30 | 0.60 | 51.6% | 80.4% | 50.0% | 48.4% | 51.6% | 9 | 37 | 0 | 0 | False |
| 0.40 | 0.30 | 75.8% | 83.1% | 86.5% | 81.1% | 18.9% | 13 | 10 | 0 | 0 | False |
| 0.40 | 0.40 | 75.8% | 83.1% | 86.5% | 81.1% | 18.9% | 13 | 10 | 0 | 0 | False |
| 0.40 | 0.50 | 71.6% | 82.2% | 81.1% | 76.8% | 23.2% | 13 | 14 | 0 | 0 | False |
| 0.40 | 0.60 | 51.6% | 80.4% | 50.0% | 48.4% | 51.6% | 9 | 37 | 0 | 0 | False |
| 0.50 | 0.30 | 76.8% | 84.2% | 86.5% | 80.0% | 20.0% | 12 | 10 | 0 | 0 | False |
| 0.50 | 0.40 | 76.8% | 84.2% | 86.5% | 80.0% | 20.0% | 12 | 10 | 0 | 0 | False |
| 0.50 | 0.50 | 72.6% | 83.3% | 81.1% | 75.8% | 24.2% | 12 | 14 | 0 | 0 | False |
| 0.50 | 0.60 | 51.6% | 80.4% | 50.0% | 48.4% | 51.6% | 9 | 37 | 0 | 0 | False |
| 0.60 | 0.30 | 71.6% | 83.1% | 79.7% | 74.7% | 25.3% | 12 | 15 | 0 | 0 | False |
| 0.60 | 0.40 | 71.6% | 83.1% | 79.7% | 74.7% | 25.3% | 12 | 15 | 0 | 0 | False |
| 0.60 | 0.50 | 67.4% | 82.1% | 74.3% | 70.5% | 29.5% | 12 | 19 | 0 | 0 | False |
| 0.60 | 0.60 | 51.6% | 80.4% | 50.0% | 48.4% | 51.6% | 9 | 37 | 0 | 0 | False |
| 0.70 | 0.30 | 71.6% | 83.1% | 79.7% | 74.7% | 25.3% | 12 | 15 | 0 | 0 | False |
| 0.70 | 0.40 | 71.6% | 83.1% | 79.7% | 74.7% | 25.3% | 12 | 15 | 0 | 0 | False |
| 0.70 | 0.50 | 67.4% | 82.1% | 74.3% | 70.5% | 29.5% | 12 | 19 | 0 | 0 | False |
| 0.70 | 0.60 | 51.6% | 80.4% | 50.0% | 48.4% | 51.6% | 9 | 37 | 0 | 0 | False |
| 0.80 | 0.30 | 71.6% | 83.1% | 79.7% | 74.7% | 25.3% | 12 | 15 | 0 | 0 | False |
| 0.80 | 0.40 | 71.6% | 83.1% | 79.7% | 74.7% | 25.3% | 12 | 15 | 0 | 0 | False |
| 0.80 | 0.50 | 67.4% | 82.1% | 74.3% | 70.5% | 29.5% | 12 | 19 | 0 | 0 | False |
| 0.80 | 0.60 | 51.6% | 80.4% | 50.0% | 48.4% | 51.6% | 9 | 37 | 0 | 0 | False |

## Candidate Policies

| Policy | Class / retrieval | Calibration automation | Evaluation automation | Evaluation safety |
| :--- | :--- | ---: | ---: | :---: |
| Safest viable candidate (fails strict safety if False below) | 0.80 / 0.60 | 48.4% | 34.0% | False |
| Best balanced candidate | 0.50 / 0.30 | 80.0% | 71.0% | False |
| Highest automation satisfying strict safety | Not identified | - | - | - |

## Selected Thresholds

- Status: **CURRENT_DEFAULTS_RETAINED_INSUFFICIENT_EVIDENCE**
- Old thresholds: classification 0.80; retrieval 0.30
- New thresholds: none
- Production configuration changed: `False`
- Evidence: Calibration-fold selection and disjoint development evaluation-fold confirmation.
- Trade-off: Safety constraints are mandatory; higher escalation is accepted rather than unsafe automation.

## Safety Results

Safety-constrained candidates require zero false auto-responses, zero must-not-auto-respond violations, and zero true high-risk violations. The escalation target is not used as a selection constraint.

## Conditional Routing Metrics After Intent Calibration

Under the counterfactual `evidence_sufficient=True` assumption, the currently configured 0.80 / 0.30 thresholds produce the following behavior. Production remains fail-closed when evidence sufficiency is unverified:

| Population | Route accuracy | Auto precision | Auto recall | Automation | Escalation | False auto | False escalation | Must-not violations | High-risk violations |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Calibration | 71.6% | - | 79.7% | 74.7% | 25.3% | 12 | 15 | 0 | 0 |
| Evaluation | 73.0% | - | 89.3% | 71.0% | 29.0% | 21 | 6 | 0 | 0 |

## Remaining Risks

- This is development evidence, not validation or final evidence.
- Small per-intent populations limit intent-specific calibration conclusions.
- The urgency head remains weak and uncalibrated; high predicted urgency is nevertheless a routing input for database and performance incidents.
- No tested threshold pair satisfied the zero-false-auto safety requirement with viable automation.
- Production does not obtain `evidence_sufficient=True` from retrieval score or generated-response support.
