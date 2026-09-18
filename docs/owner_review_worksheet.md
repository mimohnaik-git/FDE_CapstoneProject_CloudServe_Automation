# Owner Review Worksheet — Stage 27

## Purpose and evidence boundary

This worksheet records measured evidence and confirmed owner decisions. It does not
change V1 or claim an unmeasured outcome. The deployment decision below is an owner
decision, not an automated recommendation.

Frozen V1 aggregate fingerprint (preserved):
`ddf89e82e7340a0257ee0c2ae1ce340612070545bc04f559e1e4c3ad733f59c1`.
Frozen routing thresholds: classification confidence `0.80`; retrieval `0.30`.

Evidence precedence: the authorized technical rerun is the usable validation result.
The earlier `validation-final.*` report is retained as the disclosed infrastructure-failed
attempt, not as the basis for the validation metrics below. See
[`submission_claims.md`](submission_claims.md),
[`validation-technical-rerun.md`](../evaluation/results/validation-technical-rerun.md),
and [`stage15-rerun-freeze-manifest.json`](../evaluation/results/stage15-rerun-freeze-manifest.json).

## Measured evidence

### VALIDATION — frozen V1 authorized technical rerun

Dataset: 80 validation tickets; retrieval measures have 53 eligible tickets. This is
technical validation evidence, not production evidence.

| Measure | Result | Boundary / source |
|---|---:|---|
| Intent accuracy | 100.0% | 80 tickets |
| Urgency accuracy / macro F1 | 42.5% / 41.4% | 80 tickets; weak urgency quality |
| Recall@1 / @3 / @5 | 76.4% / 87.7% / 88.7% | 53 retrieval-eligible tickets |
| Precision@1 / @3 / @5 | 90.6% / 36.8% / 25.6% | 53 retrieval-eligible tickets |
| MRR | 92.8% | 53 retrieval-eligible tickets |
| Routing accuracy | 40.0% | 80 tickets |
| V1 automation / escalation | 0.0% / 100.0% | 80 terminal outcomes; escalation target <=30% failed |
| Processing failures / decision-log coverage | 0.0% / 100.0% | 80 source, evaluated, terminal, and logged records reconciled |
| Local sequential pipeline P50 / P95 | 0.0502s / 0.0915s | 80 tickets; not customer first-response time, load, or availability |
| Expected calibration error | 42.3 percentage points | 80 tickets; governance tolerance <=5 points failed |

Primary sources: [`validation-technical-rerun.md`](../evaluation/results/validation-technical-rerun.md),
[`validation-technical-rerun.json`](../evaluation/results/validation-technical-rerun.json),
and [`submission_claims.md`](submission_claims.md).

### DEVELOPMENT ONLY — human evaluation

Fifty development response candidates were independently reviewed by two humans. These
figures are not validation automatic-response performance and must not be described as
production outcomes.

| Measure | Result | Boundary |
|---|---:|---|
| Hallucination rate | 2.0% (1/50) | 50 human-development candidates; passed the <=5% target |
| Semantic citation accuracy | 98.0% (49/50) | 50 human-development candidates; passed the >=95% target |
| Correctness | 3.74 / 5 | 100 reviewer ratings across 50 candidates; no formal target |
| Usefulness | 2.87 / 5 | 100 reviewer ratings across 50 candidates; no formal target |
| Binary reviewer agreement | 100% (50/50) | Unsupported-claim and citation-support checks |
| Ordinal reviewer agreement | Correctness kappa 0.712; usefulness kappa 0.941 | 26 samples had at least one ordinal disagreement; no automatic adjudication |

Source: [`stage18-human-evaluation.md`](../evaluation/results/stage18-human-evaluation.md).

### Fairness findings — DEVELOPMENT and VALIDATION kept separate

- Development: only explicit customer-tier and language-fluency fields plus deterministic
  text-length grouping were used; no protected attributes were inferred. Development
  non-fluent tickets had lower Recall@3 than fluent tickets (79.9% vs 87.4%), and
  long tickets had higher Recall@3 than short tickets (89.1% vs 82.6%). These are
  automated subgroup observations, not customer-outcome fairness conclusions.
- Validation: enterprise (n=8) and non-fluent (n=19) groups were below the registered
  minimum n=20 and are therefore NOT MEASURED. The eligible short/long comparison showed
  urgency accuracy 27.9% vs 59.5%; this automated gap does not establish customer-outcome
  fairness. Cross-group human-quality difference is NOT MEASURED.

Source: [`stage18-fairness.md`](../evaluation/results/stage18-fairness.md).

### OPERATIONAL — hosted CI observation

GitHub Actions CI was observed passing on `main` commit
`1186641c253b5d6531f8dc0e739a015970e9dc37`, run `34683618597`. Checkout, Python
3.12 setup, dependency installation, `pip check`, offline clean-checkout smoke, and the
complete pytest suite succeeded. This is a single hosted CI observation; it does not
measure production availability or ongoing operational performance.

Source: [`submission_claims.md`](submission_claims.md) and
[`final_a1_a12_acceptance_audit.md`](final_a1_a12_acceptance_audit.md).

## NOT MEASURED

The following have no qualifying measurement and must not be inferred from local
pipeline timing, historical dataset fields, configuration, or the development review:

- System-attributable FCR
- CSAT
- Production availability
- Customer first-response time
- Load performance and alert delivery/acknowledgement/response performance
- Backup and recovery performance
- Validation hallucination rate and validation semantic citation accuracy
- Production business outcomes, including ticket deflection, costs, resolution outcomes,
  repeat contacts, and satisfaction improvement

Validation generated/released zero responses, so validation guardrail coverage,
citation-ID validity, private-data release rate, hallucination, semantic citation
accuracy, correctness, and usefulness have no eligible released-response population.

## Verified limitations and blockers

These are verified evidence limitations or recorded blockers only; they are not new
conclusions.

- V1 was fail-closed but operationally over-conservative: validation produced 0%
  automation and 100% escalation; routing accuracy was 40%.
- Urgency performance (42.5% accuracy; 41.4% macro F1) and calibration (42.3-point ECE)
  are weak on validation.
- Human-development usefulness was 2.87/5; it is not validation response-quality evidence.
- Safe non-zero automation is unproven. V2 was a development-only experiment and was
  rejected because no policy met the zero-false-auto safety rule; the best observed policy
  had 18 false automatic responses.
- Validation subgroup evidence is underpowered for enterprise and non-fluent groups;
  cross-group human quality is not measured.
- API authentication, authorization, and rate limiting are not implemented/proven for a
  deployed service. Live provider behavior is only development component evidence.
- Load, production availability, alert response, durable backup/recovery, deployed access
  controls, retention, and operational ownership are not measured/proven.

Sources: [`evidence_gaps.md`](evidence_gaps.md),
[`final_a1_a12_acceptance_audit.md`](final_a1_a12_acceptance_audit.md), and
[`stage_5_prd_revision_log.md`](stage_5_prd_revision_log.md).

## Deployment choices and confirmed owner decision

| Option | What it would mean | Evidence-aligned conditions and unresolved issues |
|---|---|---|
| Production | Unsupervised customer-facing deployment of V1. | Validation does not establish safe useful automation: V1 automated 0%, urgency/calibration were weak, usefulness evidence is development-only and low, and operational controls/evidence are incomplete. The owner must determine whether this evidence is sufficient; this worksheet does not recommend this option. |
| Limited supervised pilot | A bounded learning deployment with human oversight, explicit escalation/override, monitored outcomes, and no claim of production readiness. | Requires owner-defined scope, accountable reviewers, success/safety gates, stop conditions, customer/data handling controls, and evidence collection plan. Existing owner input supports this direction only with human oversight and live-provider testing before broader use. |
| No deployment | Keep V1 as development/submission evidence and conduct no customer-facing release. | Avoids release risk while the verified quality, safety-automation, fairness-power, API/security, and operational gaps are addressed on appropriate new/development evidence. |

**CONFIRMED OWNER DEPLOYMENT RECOMMENDATION: Limited supervised pilot.**

The owner confirms that V1 is **not production-ready**. A limited supervised pilot
must retain human oversight, explicit escalation/override, monitored outcomes, and no
claim of production readiness. Safety takes priority over automation.

**OWNER TARGET, NOT MEASURED RESULT:** A future automation rate of **30%** is the
owner's minimum worthwhile target for a future pilot. V1 validation automation remains
the measured result of **0.0%**, and this target does not alter V1 thresholds, routing,
or evaluation evidence.

## CONFIRMED OWNER INPUT

The following are confirmed owner positions. They are owner decisions and reflections;
they do not change the measured evidence above.

- **Deployment:** Limited supervised pilot; V1 is not production-ready.
- **Safety and automation:** Safety takes priority over automation. The owner target for
  future worthwhile automation is 30%; it is not a measured V1 result.
- **Biggest blockers:** weak urgency performance; low usefulness; safe automation not
  proven; missing API authentication/authorization/rate limiting; untested
  load/availability/alerts; and untested backup/recovery.
- **Usefulness:** The 2.87/5 development usefulness result is too low for production.
- **Fairness:** Current fairness evidence is preliminary and must not be presented as
  final proof of fairness.
- **Strongest engineering decisions:** auditability, monitoring, and governance through
  a fail-closed design.
- **Biggest surprises:** strong retrieval/citations do not guarantee useful answers;
  calibration improvement does not guarantee safe automation; infrastructure can
  invalidate evaluation; and safe automation is harder than expected.
- **If restarting:** introduce monitoring and governance earlier, and improve discovery
  through workflow review, an acceptance checklist, and an earlier pilot.
- **AI tools used:** ChatGPT, Codex in VS Code, and Claude. The owner corrected or
  rejected AI suggestions where they conflicted with evidence, safety, or project
  requirements. Humans retain final accountability.

## Remaining owner input

No additional owner input is required to complete this worksheet's evidence interpretation
and limited supervised pilot recommendation. This does not resolve the deployment gates,
open questions, accountable-owner assignments, or production-entry controls identified
above; those remain required before pilot or production use as applicable.

## Owner sign-off

- Owner name: Mimoh Naik
- Date: 12 September 2026
- Evidence reviewed: Yes
- Confirmed owner input reviewed: Yes
- Final interpretation approved: Yes
- Deployment recommendation approved: Yes â€” limited supervised pilot only
- Production approval: No
- Required changes or caveats: The unresolved production limitations and pilot-entry gates listed above remain in force.
