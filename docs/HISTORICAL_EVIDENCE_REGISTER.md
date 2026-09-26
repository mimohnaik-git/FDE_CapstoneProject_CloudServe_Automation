# Historical evidence register

This register separates historical development evidence from the current
CloudServe candidate. Historical files are referenced at immutable Git commit
`65f71c3fd10603421566fb786b452fdd2aa4b57b`; they are not runtime inputs and
have not been copied into this repository.

Repository: `mimohnaik-git/FDE_CapstoneProject_CloudServe_Automation`

Immutable tree: `https://github.com/mimohnaik-git/FDE_CapstoneProject_CloudServe_Automation/tree/65f71c3fd10603421566fb786b452fdd2aa4b57b`

## Historical business baseline

| Metric | Value and population | Evidence class | Repository and exact path | Immutable commit | Section or artifact | Date or version | Applicability to current build | Allowed claim |
|---|---|---|---|---|---|---|---|---|
| Weekly volume | More than 500 tickets per week for six agents | HISTORICAL PRE-AUTOMATION BASELINE | `mimohnaik-git/FDE_CapstoneProject_CloudServe_Automation`; `docs/stage_1_discovery_workbook.md` | `65f71c3fd10603421566fb786b452fdd2aa4b57b` | Stakeholder interview synthesis, lines 15 and 150 | Repository state 2026-09-24 | Context only | Marcus reported this historical workload; it is not a measured current workload. |
| FCR | Approximately 42% stakeholder estimate; supplied development history 219/500 = 43.8% | HISTORICAL PRE-AUTOMATION BASELINE | Same repository; `docs/stage_1_discovery_workbook.md` | Same immutable commit | Lines 15, 25 and 54 | Repository state 2026-09-24 | Baseline only | Historical FCR was described as about 42%; the supplied development records contain 219/500 first-contact resolutions. |
| CSAT | Project-brief baseline approximately 3.2/5; supplied development-history mean 2.97/5, n=500 | HISTORICAL PRE-AUTOMATION BASELINE | Same repository; `docs/stage_1_discovery_workbook.md` | Same immutable commit | Lines 56 and 96; reconciled with authoritative Project Brief | Repository state 2026-09-24 | Baseline only | Report the brief and dataset values separately; neither is a system outcome. |
| First response | Approximately 8–12 hours; stakeholder report, no event-level denominator | HISTORICAL PRE-AUTOMATION BASELINE | Same repository; `docs/stage_1_discovery_workbook.md` | Same immutable commit | Lines 15 and 150 | Repository state 2026-09-24 | Context only | Historical stakeholder estimate; not current pipeline latency. |
| Escalation | Project-brief baseline approximately 58%; supplied development-history field 281/500 = 56.2% | HISTORICAL PRE-AUTOMATION BASELINE | Same repository; `docs/stage_1_discovery_workbook.md` | Same immutable commit | Lines 27 and 55 | Repository state 2026-09-24 | Baseline only | Keep the brief baseline separate from the dataset descriptive field. |

## Historical human development evaluation

The source population is HDE-001 through HDE-050. The sample file maps every
HDE identifier to a development ticket. The two completed reviewer files contain
100 independent reviewer records. These results describe historical development
candidates, not the current build or Validation-80.

| Metric | Value and population | Evidence class | Repository and exact path | Immutable commit | Section or artifact | Date or version | Applicability to current build | Allowed claim |
|---|---|---|---|---|---|---|---|---|
| Human sample | 50 responses; HDE-001..HDE-050 | HISTORICAL DEVELOPMENT HUMAN | Same repository; `evaluation/results/human-development-evaluation/human-review-sample.json` | Same immutable commit | `samples` | Schema 1.0 | Historical candidates only | Fifty development response candidates were reviewed. |
| Reviewer records | Two independent reviewers; 100 records | HISTORICAL DEVELOPMENT HUMAN | Same repository; `evaluation/results/human-development-evaluation/reviewer-1-completed.json`; `reviewer-2-completed.json` | Same immutable commit | `reviews`, `independent_review_confirmed` | Schema 1.0 | Historical candidates only | Two independent reviewers completed one record per sample. |
| Unsupported claim or hallucination | 1/50 = 2% | HISTORICAL DEVELOPMENT HUMAN | Same repository; `evaluation/results/stage18-human-evaluation.json` | Same immutable commit | `metrics.hallucination_rate` | Generated 2026-09-10 | Does not measure current outputs | Historical development human unsupported-claim rate was 2%. |
| Semantic citation support | 49/50 = 98% | HISTORICAL DEVELOPMENT HUMAN | Same repository; `evaluation/results/stage18-human-evaluation.json` | Same immutable commit | `metrics.semantic_citation_accuracy` | Generated 2026-09-10 | Does not replace current citation-resolvability measurement | Historical development human citation-support accuracy was 98%. |
| Correctness | Mean 3.74/5 across 100 ratings | HISTORICAL DEVELOPMENT HUMAN | Same repository; `evaluation/results/stage18-human-evaluation.json` | Same immutable commit | `metrics.response_correctness` | Generated 2026-09-10 | Historical candidates only | Historical mean correctness was 3.74/5. |
| Usefulness | Mean 2.87/5 across 100 ratings | HISTORICAL DEVELOPMENT HUMAN | Same repository; `evaluation/results/stage18-human-evaluation.json` | Same immutable commit | `metrics.response_usefulness` | Generated 2026-09-10 | Historical candidates only | Historical mean usefulness was 2.87/5. |
| Unsupported-claim agreement | 50/50 = 100% | HISTORICAL DEVELOPMENT HUMAN | Same repository; `evaluation/results/stage18-human-evaluation.json` | Same immutable commit | `reviewer_agreement.unsupported_claim` | Generated 2026-09-10 | Historical reviewer agreement only | Binary unsupported-claim agreement was 100%. |
| Citation-support agreement | 50/50 = 100% | HISTORICAL DEVELOPMENT HUMAN | Same repository; `evaluation/results/stage18-human-evaluation.json` | Same immutable commit | `reviewer_agreement.citation_support` | Generated 2026-09-10 | Historical reviewer agreement only | Binary citation-support agreement was 100%. |
| Correctness agreement | Quadratic weighted kappa 0.711538 | HISTORICAL DEVELOPMENT HUMAN | Same repository; `evaluation/results/stage18-human-evaluation.json` | Same immutable commit | `reviewer_agreement.correctness_quadratic_weighted_kappa` | Generated 2026-09-10 | Historical reviewers only | Historical correctness agreement was approximately 0.712. |
| Usefulness agreement | Quadratic weighted kappa 0.940669 | HISTORICAL DEVELOPMENT HUMAN | Same repository; `evaluation/results/stage18-human-evaluation.json` | Same immutable commit | `reviewer_agreement.usefulness_quadratic_weighted_kappa` | Generated 2026-09-10 | Historical reviewers only | Historical usefulness agreement was approximately 0.941. |
| Ordinal disagreements | 26 distinct samples; no automatic adjudication | HISTORICAL DEVELOPMENT HUMAN | Same repository; `evaluation/results/stage18-human-evaluation.json` | Same immutable commit | `disagreements.sample_ids`, `count`, `adjudicated` | Generated 2026-09-10 | Historical reviewers only | Twenty-six samples had an ordinal disagreement; none was automatically adjudicated. |

## Historical calibration and rejected experiments

| Metric | Value and population | Evidence class | Repository and exact path | Immutable commit | Section or artifact | Date or version | Applicability to current build | Allowed claim |
|---|---|---|---|---|---|---|---|---|
| V1 evaluation ECE | 0.634794 on 97 eligible historical development-evaluation cases | HISTORICAL DEVELOPMENT EXPERIMENT | Same repository; `evaluation/results/stage20-v2-development.json` | Same immutable commit | `v1.evaluation_calibration` | Stage 20 | Historical experiment only | Historical V1 ECE was about 63.48%. |
| Isotonic V2 evaluation ECE | 0.033383 on 97 eligible historical development-evaluation cases | HISTORICAL DEVELOPMENT EXPERIMENT | Same repository; `evaluation/results/stage20-v2-development.json` | Same immutable commit | `v2.evaluation_calibration` | Stage 20 | Must not substitute for current ECE | Historical isotonic V2 reduced ECE to about 3.34%. |
| Rejected V2 routing | Best observed policy had 18 false AUTO in 100 selection cases; candidate decision `V2 REJECTED` | HISTORICAL DEVELOPMENT EXPERIMENT | Same repository; `evaluation/results/stage20-v2-development.json` | Same immutable commit | `best_observed_policy_without_strict_safety`, `candidate_decision`, `viability_checks` | Stage 20 | Rejected; not part of current candidate | V2 calibration improved but its unsafe AUTO routing caused rejection. |

## Human subgroup analysis recovered from historical ratings

These aggregates join `human-review-sample.json` ticket IDs to
`data/raw/development_tickets.json`, then average the two existing reviewer
scores per response. Hallucination marks a response when either reviewer marked
an unsupported claim; citation support requires both reviewers to mark support.
No rating was synthesized. All groups are small, especially enterprise n=6 and
non-fluent n=10, so comparative response quality remains preliminary rather than
proven.

| Dimension and group | n | Correctness /5 | Usefulness /5 | Hallucination | Citation support | Evidence class and immutable source |
|---|---:|---:|---:|---:|---:|---|
| Tier business | 14 | 3.964 | 3.179 | 0/14 | 14/14 | HISTORICAL DEVELOPMENT HUMAN; sample, both reviewer files, and `data/raw/development_tickets.json` at commit `65f71c3fd10603421566fb786b452fdd2aa4b57b` |
| Tier enterprise | 6 | 3.667 | 2.750 | 0/6 | 6/6 | Same |
| Tier standard | 30 | 3.650 | 2.750 | 1/30 | 29/30 | Same |
| Region Asia Pacific | 12 | 3.792 | 2.917 | 0/12 | 12/12 | Same |
| Region Europe | 15 | 4.133 | 3.433 | 0/15 | 15/15 | Same |
| Region Latin America | 12 | 3.458 | 2.375 | 0/12 | 12/12 | Same |
| Region North America | 11 | 3.455 | 2.591 | 1/11 | 10/11 | Same |
| Language fluent | 40 | 3.662 | 2.775 | 1/40 | 39/40 | Same |
| Language non-fluent | 10 | 4.050 | 3.250 | 0/10 | 10/10 | Same |
| Text length long, more than 25 words | 29 | 3.741 | 2.793 | 0/29 | 29/29 | Same |
| Text length short, at most 25 words | 21 | 3.738 | 2.976 | 1/21 | 20/21 | Same |

Largest observed mean gaps were 0.675 correctness points and 1.058 usefulness
points across regions, 0.314 and 0.429 across tiers, 0.388 and 0.475 across
language-fluency groups, and 0.003 and 0.183 across text-length groups. These are
descriptive gaps without uncertainty estimates or adequate subgroup power.

## Historical automated subgroup and operational evidence

| Claim | Value and population | Evidence class | Repository and exact path | Immutable commit | Section or artifact | Date or version | Applicability and allowed claim |
|---|---|---|---|---|---|---|---|
| Automated development and validation subgroup metrics | Explicit tier, fluency and deterministic text-length populations; several validation groups below historical minimum n=20 | HISTORICAL DEVELOPMENT AUTOMATED | Same repository; `evaluation/results/stage18-fairness.json` | Same immutable commit | `results.DEVELOPMENT`, `results.VALIDATION` | Generated 2026-09-10 | Historical automated quality only; do not call it human subgroup response quality. |
| Monitoring configuration | Prometheus-compatible metrics and Grafana-ready configuration existed | HISTORICAL DEVELOPMENT AUTOMATED | Same repository; `docs/submission_claims.md` | Same immutable commit | Monitoring row | Repository state 2026-09-24 | Configuration and tests only; alert delivery and scrape retention were not measured. |
| Hosted CI | Historical workflow run 34617707232 passed at commit `b97f40bd308127fc7569b79e97ed5a297f226c1b` | HISTORICAL DEVELOPMENT AUTOMATED | Same repository; `docs/submission_claims.md` | Same immutable commit | CI row | Repository state 2026-09-24 | Reproducibility evidence, not production availability. |

## Pilot and production evidence search

The historical Git tree and claim register were searched for FCR, CSAT,
customer first-response time, repeat contacts, escalation, availability, load,
alert effectiveness, recovery or backup behavior, and business impact. The
archive explicitly states that there was no deployed observation window, no
representative load test, no alert-delivery study, no production or controlled
pilot outcome study, and no linked customer outcomes. Accordingly:

| Metric | Evidence class | Result | Exact historical source | Allowed claim |
|---|---|---|---|---|
| System FCR, CSAT, customer first-response time, repeat contacts and business impact | PRODUCTION OBSERVATION | NOT MEASURED | `docs/submission_claims.md`, commit `65f71c3fd10603421566fb786b452fdd2aa4b57b`, rows 46–52 | Evidence not available. |
| Production availability and load behavior | PRODUCTION OBSERVATION | NOT MEASURED | Same source and commit, rows 48 and 50 | Evidence not available. |
| Alert effectiveness and recovery or backup behavior | PRODUCTION OBSERVATION | NOT MEASURED | Same source and commit, row 51 and production-gap narrative | Evidence not available. |

## Current evidence boundary

Current Validation-80 and Reference-200 values live in the frozen canonical C1
run `c9985a56-8a9f-427e-ba88-8910d4b1ddb0` under
`evaluation/results/final_c1_validation80_20260926_191933/`. Its reference results are
104/118 must-mention items, 52/59 fully satisfied responses, 200/200 resolvable
citations, 0/200 prohibited-claim violations, 179/200 top-document matches, and
0/200 lexical-grounding failures. These values supersede historical automated metrics
when directly comparable. Historical human results remain relevant only as
evidence about their documented 50 development candidates; they do not validate
the current response assembler or current frozen policy.
