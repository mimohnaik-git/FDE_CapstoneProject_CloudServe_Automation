# CloudServe verification record

## Observed evidence

Verification was run on 26 September 2026 using Python 3.12.10 and the TF-IDF
retrieval backend. The source set was the supplied 500-ticket development file,
80-ticket validation file, 29-document knowledge base, and 200 senior-agent
reference-response file.

The supplied validation file was run ten times during development, including
the retained clean-directory rehearsal below. The frozen canonical C1 result is
`c9985a56-8a9f-427e-ba88-8910d4b1ddb0` under
`evaluation/results/final_c1_validation80_20260926_191933/`. The protected
hidden evaluation set was not available and was not run.

- Current-source verification on 29 September 2026: `python -m pytest -q`
  collected and passed 99 tests. The restricted audit environment prevented
  pytest from writing its optional cache, producing one cache warning without
  affecting test execution or the successful exit code. Earlier 83-, 90-, and
  92-test runs are historical milestones rather than the current baseline.
- Earlier clean-directory rehearsal: environment creation, dependency installation,
  training, the then-current 72 tests, and the 80-ticket unattended run completed.
  The run logged 80 of 80 decisions and produced zero false automatic responses.
- Final clean-directory rehearsal: a fresh copy with no `.venv`, generated
  artifacts, or prior evaluation outputs installed `requirements.txt` on
  Python 3.12.10, trained on the 500 development tickets, and passed 83 tests.
  Validation run `7d013121-2634-4306-90f0-2ed193d056f2` logged 80/80 decisions,
  with zero false automatic responses and zero must-not-auto violations. Its
  observed routing, retrieval, and reference metrics are retained provenance;
  the later frozen C1 policy supersedes its routing metrics.
- Final safety-closure run: `cada144f-aa9f-4851-9f72-84d274ccb5a7`.
  It followed a development-only group-isolated OOF replay: removing
  `rate_limit` from AUTO eligibility changed OOF routing from 3 AUTO with 1
  false AUTO to 2 AUTO with 0 false AUTO; must-not-auto violations stayed 0.
- Intent classification accuracy: 80/80 (100%). ECE was 0.1451 on 80 tickets;
  calibration status was `NOT_ESTABLISHED`. The report includes two populated
  confidence bands; the sample-size warning applies.
- Urgency accuracy: 35/80 (43.75%); macro F1 was 0.3306 and high-urgency recall
  was 7/25 (28%). ECE was 0.0599 and calibration remains `NOT_ESTABLISHED`.
- Answerability accuracy: 60/80 (75%); macro precision was 0.7787, macro recall
  0.6478, and macro F1 0.6549.
  Its 80-ticket ECE was 0.0498; confidence bands are reported around the 0.75
  routing threshold, but calibration remains `NOT_ESTABLISHED` at this sample size.
- Urgency calibration is also reported using the same bands (ECE 0.0599, n=80);
  it remains `NOT_ESTABLISHED`.
- Retrieval Hit@1: 50/53 (94.34%). Hit@3 and Hit@5 were both 52/53 (98.11%).
  Recall@1 was 50/70 (71.43%); Recall@3 and Recall@5 were both 62/70
  (88.57%); MRR was 0.9591.
- Frozen C1 routing accuracy: 40/80 (50.00%). Eight tickets auto-routed and all eight
  matched the expected route, giving automatic-response precision 8/8 (100%).
  There were 40 false escalations, zero false automations, and zero must-not-auto
  violations among 14 must-not-auto tickets.
- Decision-log coverage: 80/80. Unexpected processing failures: 0/80.
- Canonical steady-state pipeline latency p50 was 0.0260 seconds and p95 was
  0.0468 seconds over 79 post-warm-up tickets. This is not customer
  first-response time.
- Reference evaluation: citations resolved for 200/200 drafts; must-mention
  coverage was 104/118, with 52/59 reference responses fully satisfying their
  must-mention set; must-not-claim violations were 0/200; the top document
  matched 179/200; and lexical grounding failures were 0/200. These are automated lexical checks, not human
  hallucination or semantic citation review.
- Fairness status: `NOT_PROVEN` for channel, customer tier, customer region, and
  language fluency because at least one subgroup in each dimension had fewer
  than 30 validation tickets.

The machine-readable evidence is in
`evaluation/results/final_c1_validation80_20260926_191933/metrics_report.json`; individual
decisions are in that directory's `results.jsonl` and run-specific SQLite audit
database named in the report. The report records dataset/training/artifact
hashes, Python 3.12.10, scikit-learn 1.9.1, the explicit TF-IDF backend,
thresholds, policy states, configuration fingerprint, and elapsed time. The
canonical artifact records Git SHA as `None`; its provenance is retained
separately as source commit
`a09826071fcd95d0330ffc0e000b6dc73c49ca47` and is not reassigned to the
later repository-cleanup commit.

## Analysis and interpretation

The development-selected retrieval configuration improved Validation-80 Hit@1
from 45/53 to 50/53 and Recall@5 from 54/70 to 62/70 without changing routing.
The frozen C1 evidence-ambiguity safeguard still deliberately limits automation
and routing recall.
Strong intent accuracy and improved retrieval do not offset weak urgency,
unmet calibration, or unproven subgroup response quality.

The 100% automatic-response precision is based on only eight validation tickets
and must not be generalized to production. The 10.0% simulated automation rate
is a routing proxy, not observed first-contact resolution. No live customer
outcomes were measured.

## Conclusion

The repository satisfies the executable workflow and fail-safe acceptance
mechanisms, including arbitrary-size unattended evaluation, persistent logging,
defined failure handling, and one-command tests. The current evidence does not
justify production automatic release.

## Recommendation

Keep the release switch disabled. Improve urgency classification, answerability
recall, and retrieval coverage using development data only; then evaluate once
on a fresh held-out set. Before any deployment, complete human review of at
least 50 responses with two assessors, establish subgroup sample sizes, assign
incident owners and notification SLAs, and record explicit release approval.

Evidence not available for the current frozen candidate: human hallucination
rate, human semantic citation-accuracy review, post-automation customer
satisfaction, observed first-contact resolution, repeat contacts after
automation, and production availability.

Historical development human-review evidence was recovered from immutable Git
commit `65f71c3fd10603421566fb786b452fdd2aa4b57b`: 50 sampled responses,
100 independent reviewer records, 1/50 unsupported-claim rate, and 49/50
semantic citation support. It evaluates historical candidates, not the current
frozen outputs. Exact provenance and subgroup calculations are recorded in
`docs/HISTORICAL_EVIDENCE_REGISTER.md`. Historical business baselines are also
not outcomes of this system.

## Final C1 routing policy

The final development-selected routing policy uses:

- intent confidence threshold: 0.60
- answerability confidence threshold: 0.75
- AUTO allowlist: `api_usage_question`, `data_export`, `onboarding`,
  `sso_configuration`, `billing_query`, `quota_or_overage`
- evidence resolution-ratio minimum: 0.40
- evidence symptom-margin maximum: 0.30
- production automatic-response authorization remains OFF by default
- controlled evaluation explicitly enables automatic-response authorization

The final group-isolated Development OOF result was 18 AUTO / 482 ESCALATE,
with 0 false automatic responses and 0 must-not-auto violations.

The frozen Validation-80 run produced 8 AUTO / 72 ESCALATE, 0 false automatic
responses, 40 false escalations, 0 must-not-auto violations, and 100% AUTO
precision on 8 routed tickets. Four otherwise eligible automatic responses were
escalated by the evidence-ambiguity safeguard.

The Validation-80 result is a held-out evaluation result. It was not used for
further policy tuning after C1 was frozen from Development OOF.
