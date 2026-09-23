# CloudServe Support Automation

This repository contains a Python 3.12 support-ticket pipeline with deterministic
routing, documentation retrieval, grounded generation, guardrails, decision
logging, a FastAPI interface, Prometheus metrics, and unattended evaluation.

Frozen V1 uses TF-IDF word/character logistic-regression classification, MiniLM
embeddings, NumPy exact-cosine retrieval, deterministic Python routing and
orchestration, provider-neutral grounded generation, direct-code guardrails,
SQLite decision logging, FastAPI, and Pytest. Chroma, BM25, LangChain, and
LangGraph are reference-stack or historical options, not frozen V1 runtime
components.

The authoritative frozen V1 fingerprint is
`ddf89e82e7340a0257ee0c2ae1ce340612070545bc04f559e1e4c3ad733f59c1`.

## Setup

Run every command from the repository root. Python 3.12 is the supported and CI-tested version.

### Windows PowerShell

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

### macOS/Linux

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

`requirements.txt` applies the targeted compatibility constraints in
`constraints.txt`; this is a tested constraints strategy, not a complete lockfile.
`.env.example` contains placeholders and safe defaults only. Keep
`GENERATION_PROVIDER=offline` for credential-free operation. OpenRouter uses
`GENERATION_PROVIDER=openrouter`, `OPENROUTER_API_KEY`,
`OPENROUTER_MODEL_NAME`, and `OPENROUTER_BASE_URL`. Groq uses
`GENERATION_PROVIDER=groq`, `GROQ_API_KEY`, `GROQ_MODEL_NAME`, and
`GROQ_BASE_URL`. Store credentials only in the untracked `.env` or process
environment; never commit them.

Operational ticket processing requires `SUPPORT_API_KEY`. Human-review access uses
the separate `SUPPORT_REVIEWER_API_KEY`; the two credentials must be distinct.
`SUPPORT_API_RATE_LIMIT_PER_MINUTE` applies a bounded, single-process application
rate limit. These controls are post-validation supervised-pilot controls, not
evidence of production-grade IAM, RBAC, distributed rate limiting, edge protection,
or denial-of-service protection.

The semantic retriever uses `sentence-transformers/all-MiniLM-L6-v2`. Normal first
use may download that public model. Fully disconnected operation requires the same
weights to be provisioned in a readable Hugging Face cache in advance; provider
credentials are not required.

## API and operational controls

Start the API from the repository root:

```bash
python -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```

- `GET /health` reports process liveness only and does not initialize pipeline dependencies.
- `GET /ready` verifies that the pipeline and mandatory audit store initialized successfully; it does not claim external-provider or network availability.
- `GET /metrics` exposes bounded, Prometheus-compatible operational metrics.
- `POST /tickets/process` processes one authenticated ticket through the support orchestrator.
- `GET /review/decisions/{decision_id}` allows an authenticated reviewer to retrieve the exact original internal escalation handoff without rerunning inference.
- `POST /review/decisions/{decision_id}/action` records one immutable `APPROVE_DRAFT` or `REJECT_DRAFT` human-review audit event. Approval does not release or send a customer response.

The deterministic automatic-response kill switch is the exact file
`storage/auto_response.disabled`. An authorized operator enables it without a
deployment by creating that file. While it exists, customer auto-responses are
suppressed, tickets escalate with `KILL_SWITCH_ENABLED`, and decision logging
continues. Delete only that file to restore normal handling. See
`docs/governance.md` for authorization and incident procedures.

## Verification

The single documented complete test command is:

```bash
python -m pytest
```

Dependency consistency and the credential-free checkout smoke check are available as:

```bash
python -m pip check
python scripts/clean_checkout_smoke.py
```

The smoke check imports the application and evaluation tooling and calls `/health`;
it does not load validation data or initialize the embedding model.

The ordinary Pytest suite establishes `GENERATION_PROVIDER=offline` before
application settings are imported. It therefore remains deterministic when a
developer's shell or `.env` selects offline, OpenRouter, or Groq. Provider and
reliability tests use explicit injected providers. Development-only live component
smokes require an explicit provider and use a synthetic fixture:

```bash
python scripts/live_provider_generation_smoke.py --live-provider openrouter --synthetic
python scripts/live_provider_generation_smoke.py --live-provider groq --synthetic
```

These commands can make real external HTTP calls and require the matching provider
credential. Their results are development component evidence, not validation or
production-reliability evidence.

## Evaluation

Run unattended evaluation with an explicitly classified dataset role:

```bash
python -m evaluation.harness --input data/raw/development_tickets.json --output evaluation/results/local-development.json --dataset-role development
```

The harness accepts arbitrary dataset sizes and writes JSON, Markdown, and a
run-specific decision database. Validation execution is governed by the frozen
evaluation procedure and must not be used for development tuning.

The supplied validation set contains 80 tickets. The first validation attempt is
preserved as an infrastructure/cache failure; the explicitly authorized 80-ticket
technical rerun is the authoritative usable validation result. A hidden final
assessment is expected to contain up to 120 tickets, but it has not been run,
inspected, or used for tuning.

## Evidence and deployment boundary

The completed two-reviewer human evaluation applies to DEVELOPMENT responses only.
Validation hallucination, semantic citation accuracy, human usefulness, and human
correctness are not measured. FCR, CSAT, customer first-response time, production
availability, load/alert performance, and backup/recovery are also not measured.

The owner recommendation is a limited supervised pilot. Frozen V1 is not
production-ready: validation automation was 0%, safe non-zero automation was not
proven, urgency and calibration were weak, fairness evidence was preliminary, and
post-validation application-level bearer authentication, separate reviewer
authorization, and single-process rate limiting are now implemented and regression
tested, but production-grade IAM/RBAC, distributed rate limiting, edge protection,
load, alert, durable review-queue, backup, and recovery evidence remain incomplete. The owner's 30% future automation target is not a
measured V1 result, and safety takes priority over automation.

Repository provenance is tracked as three distinct states:

- **Frozen evaluated V1:** commit `6a80e91a3b7a82504f04afa98cdb8265f7617234`;
  GitHub Actions run `34773077234`. This is the authoritative evaluated V1
  engineering baseline.
- **Post-freeze stabilization:** commit
  `7062f683e41a178e644713acee81478731dc9adc`; GitHub Actions run `34889316386`
  completed successfully with dependency installation, `pip check`,
  credential-free startup, and all 355 tests. Stabilization improved
  reproducibility and provider portability without rerunning validation or
  changing its results.
- **Post-validation remediation state:** the frozen evaluated V1 baseline and its
  authoritative 80-ticket validation artifacts remain unchanged. After validation,
  the repository added an explicit fail-closed evidence-sufficiency stage on branch
  `fix/evidence-sufficiency-engine`. Development-only analysis found insufficient
  evidence to justify any non-zero automatic-release policy, so no evidence threshold
  was promoted and the current runtime still cannot produce a trusted
  `evidence_sufficient=True` decision. The 0.80 classification and 0.30 retrieval
  thresholds remain unchanged. Validation was not rerun and hidden/final data was not
  accessed. Commits `e20a173` and `f744522` implement and integrate this remediation.
  This is post-validation engineering evidence, not a new validation baseline.

- **Post-validation runtime remediation:** subsequent engineering work added safe
  internal escalation handoffs, resolution-context enrichment for generation,
  authenticated processing and reviewer APIs, fail-closed readiness checks, exact
  ephemeral reviewer handoff retrieval, and immutable reviewer-action auditing.
  The ordinary customer-processing endpoint still releases no response unless the
  pipeline explicitly reaches `AUTO_RESPOND`; reviewer approval is audit-only and
  there is no customer-send/release endpoint. Reviewer draft text remains ephemeral
  and is deliberately excluded from the canonical SQLite decision record.
  These changes have not been evaluated on the frozen validation set and create no
  new validation, automation, usefulness, hallucination, fairness, business-outcome,
  availability, or production-readiness claim.

CI success is engineering evidence only; it is not production availability evidence.
