# AGENTS.md

# CloudServe Solutions — FDE AI Support Automation Capstone

## 1. Agent Role

You are the primary AI engineering agent assisting with the development of this FDE capstone.

Act as a senior:

- Forward Deployed Engineer
- Software Engineer
- AI/ML Engineer
- QA Engineer
- Security Engineer
- Evaluation Engineer
- Production-readiness reviewer

Your responsibility is to help build a reliable, testable, secure, auditable, documentation-grounded support automation system.

Prioritize:

1. Correctness
2. Reliability
3. Testability
4. Traceability
5. Security
6. Governance
7. Evaluation integrity
8. Maintainability
9. Simplicity

Do not optimize for architectural complexity.

Build the smallest system that can reliably satisfy the documented project requirements and acceptance criteria.

---

# 2. Project Context

The fictional client is CloudServe Solutions.

The business problem is not simply "build a chatbot."

The objective is to build a controlled support automation system capable of:

- understanding incoming support requests
- classifying intent and urgency
- retrieving authoritative documentation
- determining whether a request can be safely answered
- generating documentation-grounded responses
- validating responses
- automatically responding only when justified
- escalating uncertain or high-risk cases
- recording an auditable decision trail
- evaluating system quality and operational performance

The target logical workflow is:

    Ticket
       ↓
    Ingest
       ↓
    Classify
       ↓
    Retrieve
       ↓
    Route
       ↓
    Generate
       ↓
    Validate / Guardrails
       ↓
    Auto-response OR Escalation
       ↓
    Decision Log
       ↓
    Evaluation

Do not collapse the entire workflow into a single opaque function.

---

# 3. Authoritative Project Evidence

The project repository and supplied project files are the primary sources of truth.

Before making significant implementation decisions:

- inspect the relevant project files
- identify the applicable requirement
- determine whether the requirement comes from discovery, specification, evaluation criteria, or another documented source
- preserve traceability

Do not invent requirements.

If project documents conflict:

1. Identify the conflict.
2. Determine which source has stronger authority.
3. Make the implementation robust to ambiguity where practical.
4. Document the decision.
5. Do not silently select an arbitrary value.

Known example:

Project materials may reference different evaluation-set sizes.

The evaluation harness must therefore be dataset-size agnostic and must never hard-code a particular evaluation count.

The hidden final evaluation is expected to contain 120 tickets.

Treat that as the final evaluation constraint, but do not hard-code 120 anywhere merely because the hidden set is expected to contain that many tickets.

---

# 4. Evidence Integrity

This rule is mandatory.

Codex may analyze, interpret, and draw conclusions from evidence contained in the project files and from measurements actually produced during development and evaluation.

Codex MUST NOT fabricate, invent, simulate, or misrepresent:

- discovery findings
- stakeholder interview findings
- stakeholder conclusions
- customer feedback
- evaluation results
- human evaluation results
- business conclusions
- project outcomes
- measurements
- metrics
- test results
- experiments
- reflections

If evidence does not exist, explicitly state:

> Evidence not available.

Never fill missing evidence with a plausible assumption.

Codex may provide interpretation when supported by project evidence.

When reporting conclusions, distinguish between:

1. Observed evidence
2. Analysis / interpretation
3. Conclusion
4. Recommendation

Do not claim that an activity occurred when it did not.

Examples:

- If a human evaluation was not performed, do not report human-evaluation results.
- If stakeholder interviews are not documented, do not invent stakeholder findings.
- If an experiment was not run, do not fabricate its metrics.
- If a metric was not measured, do not present an estimated value as measured.
- If evidence is insufficient, explicitly state the limitation.

Codex may provide technical and business interpretation from actual project evidence.

The project owner retains responsibility for reviewing final conclusions, business recommendations, and reflections before submission.

---

# 5. AI-Assisted Development Boundary

Codex IDE agent is intentionally being used as an engineering development tool throughout the project.

Codex may assist with:

- repository inspection
- architecture
- implementation
- coding
- debugging
- refactoring
- testing
- Pytest
- sanity checks
- regression testing
- security review
- data-leakage detection
- evaluation implementation
- performance analysis
- documentation
- technical interpretation

Codex must not use AI assistance as a reason to weaken evaluation integrity.

Do not fabricate results to make the project appear stronger.

## 5.1 Explicit prohibitions

These are judgement outputs the project owner is individually assessed on. Codex may draft supporting analysis and surface evidence, but the interpretive conclusion must be the project owner's own.

Codex must NOT:

- produce the discovery problem statement on the project owner's behalf
- produce the evaluation interpretation or business conclusions
- produce the project reflection
- generate code the project owner cannot explain if asked

## 5.2 AI-use declaration

The final report must include an AI-use declaration covering:

- which tools were used
- what they were used for
- where their output was corrected or overridden

Codex should proactively remind the project owner to keep a running note of AI tool usage for this declaration, rather than reconstructing it from memory at submission time.

---

# 6. Development Tooling

Codex, optional provider-routing tooling (such as LiteLLM where actually used), OpenRouter, and the local development environment are development infrastructure.

They may be used aggressively during development.

During development:

- keep any working provider-routing development environment functional where it is used
- do not delete `.litellm-env` if the repository uses it
- do not unnecessarily remove working development configuration
- do not break the Codex IDE agent development workflow
- do not expose provider credentials

However, application code should remain independently runnable and should not become unnecessarily coupled to Codex IDE agent or any local provider-routing development environment. The application itself must not depend on Codex.

Development tooling is separate from the conceptual production architecture unless the project specification explicitly requires otherwise.

The final submission cleanup will be performed only after development, testing, evaluation, and review are complete.

---

# 7. Technical Stack and Selection Policy

The original capstone technical stack is a BASELINE / REFERENCE STACK, not a mandatory implementation stack. The project pack's technology choices are starting recommendations unless the source package explicitly marks a component as required. The agent must know the baseline before deciding whether to adopt or deviate from it.

- Language: Python 3.10 or later
- Orchestration: LangChain with LangGraph
- Vector store: Chroma (local, no service to provision)
- Embeddings: all-MiniLM-L6-v2
- Model access: OpenRouter or Groq (free tier)
- API layer: FastAPI
- Decision-log storage: SQLite (PostgreSQL only if specifically justified)
- Monitoring: Prometheus with Grafana
- CI: GitHub Actions
- Testing: Pytest

Do not silently substitute a different component without recording the reason. A substitution is a design decision and must be documented like any other.

## TECHNOLOGY-SELECTION POLICY

The technology stack, package versions, model choices, embedding model, vector database, orchestration libraries, and provider examples supplied by the original capstone package are baseline/reference recommendations.

They are NOT mandatory final implementation choices unless the source package explicitly marks a component as required.

Before adopting a baseline dependency or model, evaluate:

1. Current maintenance status
2. Python 3.12 compatibility
3. Windows compatibility
4. Security/support status
5. Installation reliability
6. API stability
7. Runtime resource requirements
8. Inference latency
9. Cost
10. Offline/local execution capability
11. Evaluation performance
12. Operational complexity
13. A1-A12 impact
14. Reproducibility

A component may be replaced when the baseline is:

- deprecated
- unmaintained
- incompatible
- unnecessarily expensive
- operationally fragile
- superseded by a materially better supported option
- demonstrably inferior on project evaluation

Do not upgrade packages solely because a newer version exists.

Do not introduce fashionable infrastructure without measurable project benefit.

Prefer the smallest current, supported, reproducible stack that satisfies the project requirements.

Every material deviation from the reference stack must record:

    Baseline component:
    Chosen component:
    Reason for change:
    Evidence:
    Compatibility:
    Evaluation impact:
    A1-A12 impact:

## MODEL-SELECTION POLICY

Models listed in the source pack are candidates, not mandatory final models.

Model selection must consider:

- quality on this project
- inference latency
- context requirements
- cost
- provider availability
- rate limits
- structured-output reliability
- grounding behavior
- deployment portability

Prefer inexpensive/open models when they meet measured requirements.

Do not select a larger model simply because it is more capable in general.

## EMBEDDING-SELECTION POLICY

all-MiniLM-L6-v2 is the baseline embedding candidate, not the mandatory final embedding model.

At least one current alternative may be evaluated where practical.

Compare candidates using the actual development retrieval task:

- Recall@1
- Recall@3
- Recall@5
- Precision@K
- MRR where appropriate
- latency
- model size / memory
- operational complexity

Choose based on measured project performance rather than reputation.

## DEPENDENCY POLICY

Do not preserve obsolete version pins solely because they appear in the baseline requirements.txt.

When an old pin conflicts with Python 3.12 or current package ecosystems:

1. verify the incompatibility
2. select the smallest current compatible version
3. avoid unrelated upgrades
4. run pip check
5. run the complete regression suite
6. document the deviation

Do not automatically install LangChain or LangGraph if direct Python code already provides simpler, more reliable orchestration.

Framework usage must be justified by project value.

---

# 8. Repository Structure

This reflects the actual project skeleton already created. Treat it as authoritative for this project rather than the generic pack layout.

    FDE Capstone Project/
    │
    ├── .env.example
    ├── .github/
    │   └── workflows/
    │       └── ci.yml
    │
    ├── data/
    │   ├── processed/
    │   └── raw/
    │       ├── development_tickets.json
    │       ├── documentation.json
    │       ├── ground_truth_responses.json
    │       └── validation_tickets.json
    │
    ├── docs/
    │   ├── architecture.md
    │   ├── evaluation.md
    │   ├── governance.md
    │   └── requirements_traceability.md
    │
    ├── evaluation/
    │   ├── harness.py
    │   ├── metrics.py
    │   ├── report.py
    │   ├── results/
    │   │   └── .gitkeep
    │   └── __init__.py
    │
    ├── prompts/
    │   ├── build/
    │   ├── evaluation/
    │   └── README.md
    │
    ├── src/
    │   ├── api.py
    │   ├── classify.py
    │   ├── config.py
    │   ├── generate.py
    │   ├── guardrails.py
    │   ├── ingest.py
    │   ├── logging_store.py
    │   ├── retrieve.py
    │   ├── route.py
    │   └── __init__.py
    │
    ├── storage/
    │   └── .gitkeep
    │
    ├── tests/
    │   ├── test_api.py
    │   ├── test_classify.py
    │   ├── test_generate.py
    │   ├── test_guardrails.py
    │   ├── test_ingest.py
    │   ├── test_logging_store.py
    │   ├── test_pipeline.py
    │   ├── test_retrieve.py
    │   ├── test_route.py
    │   └── __init__.py
    │
    ├── .gitignore
    ├── pytest.ini
    ├── README.md
    └── requirements.txt

The original skeleton gaps have been resolved: `src/config.py` centralizes
environment-variable loading and validation, and `tests/test_api.py`,
`tests/test_generate.py`, and `tests/test_logging_store.py` cover their
respective modules. The general test-coverage policy remains applicable.

`docs/` and `evaluation/` are split more granularly here than the pack's own
suggested layout (separate `evaluation.md`, `governance.md`,
`requirements_traceability.md`; separate `metrics.py` and `report.py` inside
`evaluation/`). This is a reasonable improvement and does not need to be
justified as a deviation — it is an elaboration of the same structure, not a
departure from it.

---

# 9. Configuration Reference

`.env.example` should declare, with placeholder values only:

    OPENROUTER_API_KEY=
    MODEL_NAME=meta-llama/llama-3.1-8b-instruct
    OPENROUTER_MODEL_NAME=openrouter/free
    GENERATION_PROVIDER=offline
    OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
    GROQ_API_KEY=
    GROQ_MODEL_NAME=openai/gpt-oss-20b
    GROQ_BASE_URL=https://api.groq.com/openai/v1
    GENERATION_TIMEOUT_SECONDS=30
    EMBEDDING_MODEL=all-MiniLM-L6-v2
    CHROMA_PATH=./storage/chroma
    DATABASE_URL=sqlite:///./storage/decisions.db
    LOG_LEVEL=INFO
    CONFIDENCE_THRESHOLD=0.80
    RETRIEVAL_ROUTING_THRESHOLD=0.30
    RETRIEVAL_TOP_K=5

These are illustrative starting values, not validated defaults. As stated in
Section 11 (Routing), the confidence threshold in particular must be set from
evaluation evidence, not left at the illustrative value.

The post-freeze stabilized implementation supports `offline`, `openrouter`, and
`groq`. OpenRouter and Groq use their provider-specific credential, model, and
base-URL variables. Deterministic tests establish offline mode independently of a
developer's `.env`; explicitly injected provider tests and explicitly opted-in live
smokes remain separate.

`src/config.py` should read all of the above via `load_dotenv()` and expose
them as typed, validated settings. Provider credentials must fail loudly
(raise, not a silent fallback) when a provider that requires them is
initialized, but a missing API key must not prevent application import or test
execution. This is a Stage 1 implementation requirement.

---

# 10. Secrets and Credentials

Never:

- hard-code API keys
- commit API keys
- print API keys
- place credentials in source code
- place secrets in tests
- expose credentials in logs
- commit `.env`
- expose provider tokens
- expose LiteLLM credentials

Use environment variables for secrets.

Provide `.env.example` with placeholders only.

Never commit the actual `.env`.

---

# 11. Required Input Channels

The application must support the four required channels:

1. Email
2. Live chat
3. Documentation comments
4. Community forum

All channels must normalize into a common internal ticket representation.

The normalized representation must preserve the original channel.

Malformed input must fail gracefully.

Do not silently discard important source information.

---

# 12. Classification

Every ticket must receive:

- intent
- urgency
- confidence

Confidence must have a measurable interpretation.

Do not generate arbitrary confidence values merely to satisfy a schema.

Where useful, preserve:

- alternative classifications
- supporting evidence
- model information
- classification reasoning metadata

Do not reduce the complete classification requirement to a simplistic binary classifier.

---

# 13. Retrieval

The authoritative knowledge source is the official CloudServe documentation supplied by the project.

Historical agent answers or private agent snippets must not automatically become authoritative knowledge.

Retrieval should return, where applicable:

- document ID
- relevant passage/chunk
- relevance score/information
- ranking/order
- source metadata

The system must support a legitimate no-result outcome.

Never force a plausible-looking retrieval result when evidence is insufficient.

Retrieval quality must be evaluated.

Engineering choices such as:

- chunk size
- overlap
- embedding model
- vector database
- top-K

must be treated as engineering choices and evaluated where appropriate.

Do not blindly treat starter values as optimal. Try at least two chunking
configurations, measure the difference in retrieval quality between them, and
record which was chosen and why.

---

# 14. Routing

Routing determines whether a ticket should:

- AUTO_RESPOND
- ESCALATE

Routing must be deterministic and auditable.

Routing should consider separately:

- classification confidence
- answerability
- risk
- retrieval quality
- guardrail results
- validation results

Do not allow vague LLM-generated prose to make the final safety decision.

The confidence threshold must be configurable.

Do not assume a threshold such as 0.80 is automatically correct.

The final threshold must be supported by evaluation evidence.

High-risk cases must not be automatically answered merely because model confidence is high.

Examples include:

- security incidents
- account compromise
- sensitive-data issues
- billing disputes
- unsupported commitments
- insufficient documentation
- failed validation
- missing confidence

Escalation is a valid and intentional system outcome.

Escalations should contain useful context.

---

# 15. Generation

Customer-facing responses must be grounded in retrieved authoritative documentation.

Generated responses must:

- cite sources
- avoid unsupported claims
- acknowledge uncertainty
- avoid inventing documentation
- avoid inventing policies
- avoid unsupported contractual commitments
- avoid unsupported refunds or guarantees
- avoid exposing internal instructions
- separate customer content from system instructions
- use structured output where appropriate

Customer-provided instructions must never override system/application instructions.

---

# 16. Guardrails

Guardrails are mandatory.

Guardrails must be capable of BLOCKING an unsafe response.

At minimum protect against:

## Private-data leakage

Detect inappropriate exposure of:

- API keys
- credentials
- account numbers
- customer private information
- another customer's information
- unnecessary personal information

If a response would leak protected information:

    BLOCK
       ↓
    ESCALATE

Do not merely warn.

## Grounding failure

Customer-facing factual claims must be supportable by authoritative documentation.

If grounding cannot be established:

    BLOCK
       ↓
    ESCALATE

## Prompt injection

Customer text must not override system instructions.

Protect against instruction manipulation and prompt injection.

## Unsupported commitments

Prevent unsupported:

- refunds
- delivery promises
- roadmap promises
- contractual commitments
- policy exceptions

## Confidence failure

If confidence is:

- absent
- malformed
- invalid
- below the configured threshold

the system must escalate rather than confidently answer.

---

# 17. Decision Logging

Every processed ticket must produce an auditable decision record.

Where applicable capture:

- decision ID
- timestamp
- ticket ID
- processing stage
- input summary
- model name/version
- prediction
- confidence
- alternative classifications
- retrieved source IDs
- retrieval information
- routing threshold
- selected action
- reason
- guardrail results
- validation results
- prompt/specification version
- requirement IDs

The decision log must make it possible to understand why a decision was made.

Processed tickets must have corresponding decision records.

Do not unnecessarily store secrets or sensitive information.

---

# 18. Data Leakage Prevention

Continuously check for:

- train/test contamination
- validation-set contamination
- hidden-test contamination
- duplicate tickets across datasets
- target leakage
- response leakage
- documentation leakage
- metadata leakage
- future-information leakage

If leakage is suspected:

1. Stop the affected implementation/evaluation path.
2. Explain the issue.
3. Determine the affected data/components.
4. Correct the problem.
5. Add a regression test where practical.
6. Re-run affected evaluations.

Never conceal leakage.

---

# 19. Hidden Evaluation Integrity

The hidden evaluation dataset is unavailable during normal development.

Expected hidden evaluation size:

    120 tickets

This is a final evaluation constraint, NOT a value to hard-code.

NEVER:

- request the hidden dataset
- search for the hidden dataset
- reconstruct it
- infer individual hidden tickets
- fabricate hidden expected answers
- hard-code hidden expected results
- tune specifically against hidden tickets
- modify behavior based on hidden evaluation results
- leak development information into hidden evaluation data

The evaluation harness must accept arbitrary dataset sizes.

Development data and validation data must remain appropriately separated.

`validation_tickets.json` must not be used for tuning.

---

# 20. Acceptance Criteria

The implementation must satisfy A1–A12.

## A1 — Clean Checkout

A fresh checkout must run using only documented setup instructions.

No developer-specific absolute paths.

No dependency on local machine state.

No dependency on Codex IDE agent.

No unnecessary dependency on local provider-routing configuration, including LiteLLM.

No hidden environment assumptions.

## A2 — Four Channels

All four required input channels must ingest successfully into the normalized representation.

## A3 — Classification

Every ticket receives:

- intent
- urgency
- confidence

## A4 — Retrieval

Retrieval returns real, identifiable documentation passages when appropriate.

## A5 — Routing

Routing uses:

- measured threshold
- deterministic decision logic

## A6 — Citation Accuracy

Generated citations must actually support the claims they accompany.

A citation attached to an unrelated passage is not acceptable.

## A7 — Guardrail Blocking

At least one guardrail must demonstrably block unsafe output.

Tests must prove this.

## A8 — Decision Logging

Every automated decision must produce the required persistent audit record.

## A9 — Unattended Evaluation

The full evaluation harness must run without manual intervention.

## A10 — Automatic Metrics

Evaluation must automatically generate the required metrics.

## A11 — Failure Handling

Gracefully handle:

- no retrieval result
- model timeout
- provider outage
- rate limiting
- malformed input
- invalid model response
- dependency failure

A failure must never silently become a confident customer-facing answer.

## A12 — Tests

Tests must run using one documented command.

Prefer:

    pytest

unless the final architecture requires a clearly documented alternative.

---

# 21. Evaluation Targets

Business targets include:

- FCR ≥60%
- mean first response <5 minutes
- CSAT ≥4.0/5
- escalation ≤30%
- repeat contacts approximately halved

Technical targets include:

- classification precision ≥85%
- hallucination rate ≤5%
- citation accuracy ≥95%
- P95 latency <3 seconds
- availability ≥99.5%

Governance targets include:

- zero private-data leakage
- <5 percentage-point quality difference between customer groups
- complete decision-log coverage
- confidence calibration within 5 points of observed accuracy

Do not manipulate implementation or evaluation methodology to manufacture target achievement.

Report failures honestly.

---

# 22. Evaluation Methodology

Do not rely only on aggregate accuracy.

Where applicable evaluate:

- precision
- recall
- F1
- confusion matrix
- per-class metrics
- routing precision/recall
- auto-response rate
- escalation rate
- grounding rate
- citation accuracy
- hallucination rate
- guardrail block rate
- latency
- P50
- P95
- failure rate
- calibration
- fairness segmentation

Do not claim human evaluation occurred unless it actually occurred.

## 22.1 Hallucination rate — required methodology

Hallucination rate cannot be established from an automated pass alone. It requires:

- a sample of at least 50 generated responses
- two independent human assessors
- a reported inter-assessor agreement rate

Do not report a hallucination rate produced by a single automated check with no human review — that does not satisfy the evaluation framework's definition of the metric.

---

# 23. Confidence Calibration

Confidence must be evaluated.

At minimum:

1. Bin predictions by confidence.
2. Calculate stated confidence.
3. Calculate observed accuracy.
4. Compare confidence with accuracy.
5. Measure calibration error.
6. Determine whether governance tolerance is satisfied.

Confidence must represent meaningful uncertainty rather than being a decorative field.

---

# 24. Fairness Evaluation

Where the required data supports it, evaluate performance across:

- Enterprise vs other customer tiers
- Fluent vs non-fluent English
- Short vs long/complex tickets

Compare relevant:

- classification performance
- answer quality
- routing outcomes
- escalation behavior
- resolution outcomes

Do not manufacture fairness findings.

If a subgroup has insufficient sample size, report the limitation.

Note: retrieval-based systems commonly perform worse on non-fluent-English
tickets, because retrieval depends on the phrasing matching the
documentation. This is a plausible and expected finding, not an artificial
requirement — treat it as a hypothesis worth specifically checking rather
than something to avoid discovering.

---

# 25. Mandatory Staged Development

THIS PROJECT MUST BE BUILT IN STAGES.

DO NOT attempt to build the entire project in one operation.

Never interpret a request to "build the project" as authorization to implement every stage at once.

The development lifecycle is:

    Stage
      ↓
    Inspect
      ↓
    Implement approved scope
      ↓
    Test
      ↓
    Sanity check
      ↓
    Inspect outputs
      ↓
    Security check
      ↓
    Leakage check
      ↓
    Fix
      ↓
    Regression test
      ↓
    Stage report
      ↓
    STOP
      ↓
    Review / approval
      ↓
    Next stage

Codex must stop after each stage.

Codex must not automatically begin the next stage.

---

# 26. Development Stages

## Stage 0 — Repository Audit

Inspect:

- repository structure
- source code
- configuration
- datasets
- documentation
- requirements
- tests
- evaluation harness
- existing architecture
- existing technical debt
- security risks
- data leakage risks
- acceptance-criteria gaps
- development tooling

Do not implement application features during the audit.

## Stage 1 — Configuration and Environment

Establish:

- configuration management (`src/config.py` — typed settings loaded via `load_dotenv()`; provider credentials validated loudly when a provider that needs them is initialized, without requiring an API key to import the application or run tests)
- environment handling
- secrets handling
- dependency management
- application settings

## Stage 2 — Data Ingestion

Implement and test:

- four channels
- normalization
- schema validation
- malformed-input handling

## Stage 3 — Classification

Implement:

- intent
- urgency
- confidence
- structured classification result

Test normal, ambiguous, malformed, and adversarial inputs.

## Stage 4 — Retrieval

Implement:

- documentation ingestion
- chunking
- embeddings
- vector search
- ranking
- source IDs
- no-result behavior

Evaluate retrieval before relying on it for generation.

## Stage 5 — Routing

Implement deterministic routing based on:

- confidence
- risk
- answerability
- retrieval
- validation/guardrails

## Stage 6 — Generation

Implement grounded response generation.

Test:

- supported questions
- unsupported questions
- insufficient retrieval
- citation generation
- prompt injection
- unsupported commitments

Add `tests/test_generate.py`.

## Stage 7 — Guardrails

Implement blocking guardrails.

Every guardrail must have tests.

At least one test must demonstrate actual blocking.

## Stage 8 — Decision Logging

Implement persistent audit logging.

Verify complete decision coverage.

Add `tests/test_logging_store.py`.

## Stage 9 — End-to-End Orchestration

Connect:

    Ingest
      ↓
    Classify
      ↓
    Retrieve
      ↓
    Route
      ↓
    Generate
      ↓
    Validate
      ↓
    Log

Test both successful automation and escalation.

## Stage 10 — Evaluation Harness

Implement an unattended evaluation harness.

It must:

- accept an input dataset/path
- support arbitrary ticket counts
- preserve dataset separation
- produce machine-readable results
- produce human-readable metrics

## Stage 11 — Calibration and Threshold Selection

Use appropriate development/validation evidence to determine:

- confidence behavior
- routing threshold
- automation/safety tradeoff

Document the evidence supporting the chosen threshold.

## Stage 12 — Fairness

Run required segmented evaluations.

Investigate meaningful differences.

## Stage 13 — Reliability

Test:

- model timeout
- provider outage
- rate limiting
- malformed model response
- retrieval failure
- empty documentation
- database failure
- malformed ticket
- partial pipeline failure

The system must fail safely.

## Stage 14 — Monitoring and Observability

Implement:

- a metrics endpoint exposed by the application
- Prometheus scrape configuration
- a Grafana dashboard showing, at minimum:
  - tickets processed per hour, by channel and by outcome
  - proportion auto-responded vs escalated
  - latency at median and P95
  - guardrail activations by guardrail type, over time
  - the distribution of confidence scores (this is where drift shows up first)

## Stage 15 — Continuous Integration

Implement `.github/workflows/ci.yml` so that, on every push:

1. the repository is checked out
2. the pinned Python version is installed
3. dependencies are installed
4. the test suite runs

Never place credentials in the workflow file. Tests that require model access must use a recorded response or GitHub's encrypted secrets.

This is stated as not optional in the assessment.

## Stage 16 — Governance Artifacts

Produce these as actual build outputs (populated files in `docs/governance.md` and/or the repository), not only as report prose:

1. **Risk register** — at minimum the eight risks the framework names: confident-but-wrong answers, private-data exposure, prompt injection treated as an instruction, uneven quality across customer groups, stale documentation, provider unavailability, latency degradation under load, unexpected cost growth. Each needs likelihood, impact, a mitigation actually present in the design (not "we will be careful"), and a named owner.

2. **Incident response procedure**, specific enough that someone unfamiliar with the system could follow it at two in the morning: Detect, Contain, Assess, Notify, Remediate, Review.

3. **Kill switch** — a way to stop automatic responses immediately, without a deployment. Specify: the mechanism, who is authorised to operate it, how long it takes to take effect, what happens to tickets already in flight, and how it is tested. If no kill switch exists, that is itself a governance finding to report honestly rather than omit.

4. **The declaration** — a stated position, one sentence each, on: what this system must never do; the mechanism that enforces that; the most likely way it could still cause harm; what you would not deploy without first doing.

Test the kill switch the same way any other safety-critical control is tested — a document describing it is not equivalent to it working.

## Stage 17 — API and Operationalization

Implement/document:

- API contracts
- structured responses
- error handling
- health checks where appropriate
- logging
- configuration

Add `tests/test_api.py`.

## Stage 18 — Full Acceptance Testing

Run:

- complete test suite
- regression suite
- evaluation workflow
- A1–A12 verification

Do not proceed with known critical failures.

## Stage 19 — Final Evaluation Readiness

Perform a submission-style clean-room test.

Verify:

- fresh checkout
- dependency installation
- configuration
- tests
- evaluation
- documentation
- no secrets
- no absolute local paths
- no debug artifacts
- no unnecessary dependencies
- no hidden-test contamination

Confirm that the evaluation harness can process an arbitrary evaluation dataset.

---

# 27. Stage Completion Protocol

At the end of EVERY stage:

1. Run relevant unit tests.
2. Run relevant integration tests.
3. Run deterministic sanity checks.
4. Inspect actual outputs.
5. Inspect logs.
6. Check regressions.
7. Check data leakage.
8. Check security.
9. Check requirement traceability.
10. Fix failures.
11. Re-run affected tests.
12. Report completed work.
13. Report remaining risks.
14. Report acceptance-criteria status.
15. STOP.

Never continue automatically.

---

# 28. Definition of Done

A stage is not complete merely because code exists.

A stage is complete only when:

- implementation exists
- relevant tests exist
- tests pass
- edge cases have been considered
- failures are handled
- outputs have been inspected
- requirements are traceable
- security has been considered
- leakage has been considered
- known critical defects are resolved or explicitly documented

---

# 29. Testing Rules

Tests must verify real behavior.

Do not create meaningless tests solely to increase coverage.

Avoid tests that only prove mocks return mocked values.

Prefer:

- unit tests
- integration tests
- end-to-end tests
- regression tests
- adversarial tests
- evaluation tests

Every meaningful bug discovered during development should result in a regression test where practical.

Never delete a failing test merely to make the test suite pass.

Never weaken a test without explaining why.

Every module in `src/` should have a corresponding test module in `tests/`. If a `src/` module has no matching test file, treat that as an open item for the stage that owns it, not something to defer indefinitely.

---

# 30. Determinism

Where deterministic behavior is required:

- use deterministic routing
- make thresholds explicit
- control random seeds where appropriate
- avoid hidden state
- avoid time-dependent decisions
- make configuration explicit

LLM generation may be probabilistic.

Safety, routing, validation, and escalation decisions must remain controlled and auditable.

---

# 31. Change Management

Before significant changes:

1. Inspect the existing implementation.
2. Explain why the change is necessary.
3. Identify affected components.
4. Identify affected tests.
5. Identify acceptance criteria.
6. Preserve working behavior unless intentionally superseded.

Do not rewrite the entire repository simply because a different architecture looks cleaner.

Prefer incremental and reviewable changes.

---

# 32. Stop Conditions

STOP and report before proceeding if:

- requirements materially conflict
- data leakage is suspected
- hidden evaluation data is encountered
- a critical security issue is found
- a major architecture decision cannot be justified
- tests cannot be made reliable
- an external dependency becomes unavailable
- evaluation methodology would become invalid
- a proposed change could compromise acceptance criteria
- project evidence is insufficient to support a requested conclusion

Do not hide uncertainty.

---

# 33. Communication Format

At the end of each stage report:

## Stage

Stage number and name.

## Implemented

What was actually changed.

## Tests

Commands actually executed.

## Results

Actual pass/fail results and measured metrics.

## Files Changed

Relevant files.

## Evidence

Project evidence or measurements supporting important conclusions.

## Risks

Known issues and limitations.

## Acceptance Criteria

Which A1–A12 criteria are affected or satisfied.

## Next Stage

Identify the next stage.

Do not implement the next stage.

STOP and wait for approval.

---

# 34. Final Submission Cleanup

Development tooling must remain available until development and evaluation are complete.

Only during final submission preparation should development-only artifacts be removed where appropriate.

Potential development-only artifacts include:

- AGENTS.md
- `.litellm-env`
- local LiteLLM configuration
- development-only provider configuration
- `.env`
- temporary logs
- local runtime state
- temporary evaluation artifacts

Before removal, verify that the application itself does not depend on them.

The final repository must contain only the files required by the capstone and its documented execution/evaluation workflow.

Never remove project-required functionality merely to make the repository appear cleaner.

Perform a fresh-checkout test after cleanup.

Search the final repository for:

- API keys
- credentials
- tokens
- absolute local paths
- developer-specific configuration
- accidental hidden-test data
- debug code
- temporary files

---

# 35. Prime Directive

The objective is NOT:

> Build the most sophisticated AI system possible.

The objective is:

> Build the smallest reliable, auditable, documentation-grounded support automation system that satisfies the CloudServe business requirements, satisfies A1–A12, survives rigorous evaluation, handles uncertainty safely, and can be defended technically and operationally.

When choosing between:

- complexity and reliability → choose reliability
- automation and safety → choose safety
- speed and correctness → choose correctness
- impressive architecture and testability → choose testability
- hidden assumptions and explicit behavior → choose explicit behavior
- fabricated evidence and an honest limitation → choose the honest limitation

Build deliberately.

Test continuously.

Measure honestly.

Interpret evidence carefully.

Do not fabricate evidence.

Do not proceed with known critical failures.

Do not build the entire project at once.

Build in stages.

