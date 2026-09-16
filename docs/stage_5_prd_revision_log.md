# PRD Revision Record — CloudServe Support Automation

## Document control

| Field | Value |
|---|---|
| Revision | 2.1 final owner-approved reconciliation |
| Date | 12 September 2026 |
| Scope | Reconcile the original PRD with final frozen V1, evaluation, operational, and owner-review evidence |
| Evidence boundary | Frozen V1 validation, human development evaluation, development-only V2 experiment, operational/reproducibility evidence, and observed GitHub Actions CI |
| Approval status | Owner review completed and approved on 12 September 2026 |
| Production decision | Limited supervised pilot; V1 is not production-ready; V2 remains rejected |

This record supersedes the earlier revision narrative that claimed a BM25 implementation,
a 0.82 threshold, 75 passing tests, and stakeholder approval. Those claims do not describe
the frozen V1 evidence and are withdrawn from the current revision record. The original
source-pack workbooks remain historical inputs and are not altered.

## Requirement changes

| Requirement | Version 1 expectation | Version 2 evidence-based requirement or status | Trigger and evidence | Owner decision |
|---|---|---|---|---|
| FR-02 classification | Intent and urgency classification with intent precision above 85% | Retain intent classification; treat urgency quality and confidence calibration as unresolved quality gaps. Any successor must define urgency acceptance criteria and demonstrate calibration within the governance tolerance before release. | Validation intent macro precision was 100%, but urgency accuracy was 42.5%, urgency macro F1 was 41.4%, and V1 ECE was 42.3%. | Owner confirmed weak urgency/calibration as a production blocker. A limited supervised pilot requires human oversight; V1 is not production-ready. |
| FR-03 retrieval | Chroma plus MiniLM with BM25 fallback and Recall@3 above 85% | Require identifiable authoritative passages and measured retrieval quality without prescribing Chroma or BM25. Frozen V1 uses exact cosine over MiniLM/NumPy. | Validation Recall@3 was 87.7% over 53 eligible tickets. Architecture and clean-checkout evidence contradict the V1 design prescription. | Owner-approved outcome-based wording and the recorded stack deviation. |
| FR-04 routing | Safe automatic response or escalation using multi-factor routing | Retain deterministic fail-closed routing, but do not call V1 operationally successful: it produced 0% automation and 100% escalation. A successor may be promoted only after zero false automatic responses under the registered safety rule and a new governed validation cycle. | Validation routing accuracy was 40%; escalation target <=30% failed. Stage 20 V2 policies produced false automatic responses. | Owner selected a limited supervised pilot and prioritizes safety over automation. **OWNER TARGET, NOT MEASURED RESULT:** 30% is the minimum worthwhile future automation target. |
| FR-05 and FR-06 generation and grounding | Grounded answers with explicit citations and no released hallucinations | Preserve grounding and citation controls. Report response-quality evidence only within its population: human development evaluation, not validation releases. | Two reviewers on 50 development candidates measured hallucination 2% (1/50), semantic citation accuracy 98% (49/50), correctness 3.74/5, and usefulness 2.87/5. Validation released no responses. | Owner confirmed that 2.87/5 usefulness is too low for production; any pilot must be supervised and learning-oriented. |
| FR-07 to FR-09 safety | Block private data, injection effects, and unsupported financial commitments | Retain blocking controls and mandatory escalation. Production claims require deployed security and abuse-control evidence. | Unit/integration evidence demonstrates blocking; validation guardrail coverage and private-data release rate were ineligible because no response was released. | Owner prioritizes safety over automation. Deployed security controls and evidence remain required before production. |
| FR-11 audit logging | Persistent and complete decision records | Retain. Require deployed durability, access control, retention, backup, and recovery evidence before production. | Validation reconciled 80 source/evaluated/terminal/logged records and achieved 100% decision-log coverage. SQLite production durability remains unmeasured. | Required: name the accountable owner and retention/recovery policy. |
| FR-12 evaluation | Unattended automated metrics | Retain arbitrary-size unattended evaluation and explicit evidence classes. Human and operational metrics must never be inferred from automated results. | Evaluation harness, frozen manifests, validation reports, fairness analysis, and human-review artifacts exist. | Owner approved the final evidence interpretation. No new validation run is required. |
| NFR operational readiness | Latency, availability, security, testability, and local operation | Separate locally demonstrated controls from production evidence. Historical frozen CI run `34773077234` at `6a80e91` succeeded. Post-freeze implementation hardening is recorded by stabilized commit `7062f68` and successful CI run `34889316386`, including dependency installation, consistency checks, offline startup, and 355 tests with zero warnings. Production availability, load, alerts, access control, and recovery remain gaps. | Governance, monitoring, traceability, clean-checkout, provider isolation, dependency constraints, and hosted CI evidence. | Owner selected a limited supervised pilot. Production remains blocked by the unresolved operational and security limitations. |

## Assumptions reconciled

| Version 1 assumption | Evidence outcome | Revision |
|---|---|---|
| Documentation answerability would translate into useful automation. | Did not hold for V1 validation: 0% automation and 100% escalation. | Treat answerability, routing safety, and response usefulness as separate gates. |
| Intent confidence was sufficiently calibrated for routing. | Did not hold: V1 ECE was 42.3% on validation. | Require explicit calibration evidence and preserve fail-closed routing. |
| Urgency performance would be adequate alongside intent performance. | Did not hold: validation urgency accuracy was 42.5% and macro F1 was 41.4%. | Make urgency remediation a named product-quality gap. |
| Strong automated citation checks would establish response quality. | Did not hold as a complete claim. Semantic citation support required human review; usefulness averaged 2.87/5. | Keep automated and human evidence distinct and report denominators. |
| The fairness target could be evaluated on supplied data. | Did not hold. Validation enterprise n=8 and non-fluent n=19 were below the registered n=20 minimum; cross-group human quality was not measured. | Require a new, appropriately powered governed dataset and stratified human review. |
| Calibration repair would enable safe non-zero automation. | Partly held for calibration, not routing safety. Development-only isotonic V2 ECE improved from 63.48% to 3.34%, but the selected candidate had 18 false automatic responses. | Reject V2; do not validate or promote it. |
| Local implementation evidence was equivalent to production readiness. | Did not hold. Monitoring, governance, and clean-checkout controls exist, but deployed operational outcomes remain unmeasured. | Add explicit production-entry gaps and owner gates. |

## Deliberately unchanged

- Frozen V1 code, configuration, validation outputs, and fingerprint are unchanged.
- The failed initial validation attempt remains preserved. The authorized 80-ticket
  technical rerun is the authoritative validation evidence.
- V2 remains development-only and rejected; it was not run on validation.
- Historical source workbooks remain source evidence even where their claims are superseded here.

## Post-freeze implementation hardening

Post-freeze work improved implementation quality without changing the product
requirements. Provider portability now covers explicit offline, OpenRouter, and Groq
selection; OpenRouter and Groq have provider-specific model, credential, and base-URL
configuration. Deterministic tests are isolated from developer `.env` provider values.
The dependency contract now combines `requirements.txt` with targeted
`constraints.txt`, and warning-producing compatibility issues were resolved without
warning filters. Provider-smoke output protection, sanitization, and repository/runtime
hygiene were also strengthened.

This hardening created no PRD V3. No business requirement, routing threshold,
generation prompt, guardrail policy, validation result, or frozen V1 metric changed.
Validation was not rerun, and the development-only V2 remains rejected, not validated,
and not promoted.

## Final owner decision and unresolved production limitations

The owner approved a **limited supervised pilot**, not production deployment. V1 remains
**not production-ready**, and safety is prioritized over automation.

**OWNER TARGET, NOT MEASURED RESULT:** 30% is the owner's minimum worthwhile future
automation target. It does not change frozen V1 thresholds, routing, or the measured V1
validation automation rate of 0%.

The following limitations remain unresolved before production:

- weak urgency performance and confidence calibration;
- V1 validation automation of 0%;
- human-development usefulness of 2.87/5;
- safe non-zero automation not proven;
- preliminary/underpowered fairness evidence;
- absent deployed API authentication, authorization, and rate limiting;
- untested load, production availability, and alert performance;
- untested backup and recovery; and
- live-provider evidence limited to development component smoke checks, not end-to-end
  validation or production evidence.

## Evidence references

- `evaluation/results/validation-technical-rerun.md`
- `evaluation/results/stage18-fairness.md`
- `evaluation/results/stage18-human-evaluation.md`
- `evaluation/results/stage20-v2-development.json`
- `docs/governance.md`
- `docs/requirements_traceability.md`
- `docs/evidence_register.md`
- `docs/evidence_gaps.md`
- `docs/owner_review_worksheet.md`
- `docs/effort_log.md`

## Owner approval fields

- Owner name: Mimoh Naik
- Approval date: 12 September 2026
- Owner review: completed
- Final interpretation: approved
- Deployment recommendation: approved — limited supervised pilot
- Production status: not production-ready
- Recorded caveats: the unresolved production limitations listed above remain in force.
