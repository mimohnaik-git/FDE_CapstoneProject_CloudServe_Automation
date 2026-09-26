# CloudServe Controlled Support Automation

CloudServe is a deterministic, auditable support-automation system for classifying support tickets, retrieving evidence from a knowledge base, generating cited responses, applying guardrails, routing tickets, recording decisions, and evaluating system behavior.

The validated release configuration does not require an external LLM or API key.

```text
Ticket
  -> Ingest
  -> Classify
  -> Retrieve
  -> Assess Evidence
  -> Generate Draft
  -> Guardrails
  -> AUTO_RESPOND or ESCALATE
  -> Decision Log
  -> Evaluation / Monitoring
```

The production-safe default is escalation-only. Automatic response must be explicitly enabled and still passes through all routing, evidence, confidence, and guardrail gates.

---

## Features

- Four-channel ticket ingestion
- Intent classification
- Urgency classification
- Answerability classification
- Deterministic TF-IDF knowledge-base retrieval
- Evidence-sufficiency checks
- Deterministic cited response generation
- Guardrails for secrets, prompt injection, unsupported commitments, citation integrity, and grounding
- Fail-closed routing
- Automatic-response and escalation paths
- Persistent SQLite decision logging
- Human review workflow
- FastAPI service
- Prometheus-compatible metrics
- Grafana dashboard configuration
- Development-only model-selection evidence
- Unattended evaluation harness
- Frozen Validation-80 evidence
- Automated unit, integration, policy, API, and failure tests

---

## Requirements

Verified runtime:

```text
Python 3.12
```

The submitted release uses the deterministic TF-IDF retrieval backend.

MiniLM remains available in the codebase as an optional backend, but `sentence-transformers` is not required by the submitted deterministic release configuration.

---

## Quick Start

From the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip check
python -m pytest -q
```

Start the API:

```powershell
python -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```

Keep that terminal running.

Open a second PowerShell terminal and check service health:

```powershell
Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/health" `
    -Method Get
```

Check runtime metrics:

```powershell
Invoke-WebRequest `
    -Uri "http://127.0.0.1:8000/metrics" `
    -UseBasicParsing |
    Select-Object -ExpandProperty Content
```

---

## Run the Full Test Suite

```powershell
python -m pytest -q
```

The test suite covers ingestion, classification, retrieval, routing, evidence policy, guardrails, API behavior, failure handling, configuration fingerprints, and evaluation behavior.

---

## Run the Controlled Operational Demo

```powershell
python -m scripts.demo
```

The operational demonstration exercises the implemented support workflow without requiring an external API or LLM service.

Operational demonstration evidence is stored under:

```text
evaluation/results/operational_demo/
```

---

## API Endpoints

The FastAPI service exposes:

```text
POST /tickets
GET  /decisions/{ticket_id}
GET  /review/{ticket_id}
POST /review/{ticket_id}
GET  /health
GET  /metrics
```

`POST /tickets` returns a customer-facing `answer` and resolvable `citations` only when the final route is `AUTO_RESPOND`.

Escalated tickets return the route, reasons, classifier state, and configuration fingerprint. Any generated draft remains internal and is available through audited decision/review interfaces.

Review approval is recorded in the audit trail and does not send a customer message.

---

## Automatic-Response Policy

Automatic response is disabled by default:

```text
CLOUDSERVE_AUTO_RESPONSE_ENABLED=false
```

To explicitly enable the controlled automatic-response path for local testing:

```powershell
$env:CLOUDSERVE_AUTO_RESPONSE_ENABLED="true"
python -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```

To restore the safe default:

```powershell
Remove-Item Env:CLOUDSERVE_AUTO_RESPONSE_ENABLED -ErrorAction SilentlyContinue
```

Restart the service after changing the environment variable.

Automatic response is not enabled by the switch alone. A ticket must still pass the configured intent, confidence, answerability, evidence, operational-state, and guardrail gates.

### Auto-eligible intents

```text
api_usage_question
data_export
onboarding
sso_configuration
billing_query
quota_or_overage
```

### Never-automate intents

```text
security_incident
compliance_request
feature_request
unclear_request
billing_dispute
legal_request
account_deletion
outage_report
data_breach
```

If a required condition is not established, routing fails closed to `ESCALATE`.

---

## Unattended Evaluation

To reproduce a local Validation-80 evaluation without overwriting the frozen final evidence:

```powershell
python -m evaluation.harness `
    --input data/cloudserve/validation_tickets.json `
    --output evaluation/results/local_validation_run `
    --references data/cloudserve/ground_truth_responses.json `
    --reference-tickets data/cloudserve/development_tickets.json `
    --kb data/cloudserve/documentation.json `
    --retrieval-backend tfidf `
    --enable-auto-policy `
    --fail-on-must-not-auto
```

The output directory contains:

```text
evaluation/results/local_validation_run/
├── results.jsonl
├── metrics_report.json
├── metrics_report.md
└── decisions-<run-id>.sqlite3
```

The evaluation report records:

- run ID
- evaluated ticket count
- decision-log coverage
- classifier outputs and confidence
- retrieval metrics
- routing metrics
- guardrail outcomes
- configuration fingerprint
- model artifact hashes
- runtime versions
- dataset hashes
- latency measurements
- policy state
- Git SHA when available

Business outcomes that were not measured from live customers are not presented as observed production results.

### Inspect the evaluation report

```powershell
Get-Content `
    evaluation\results\local_validation_run\metrics_report.md
```

Structured JSON:

```powershell
Get-Content `
    evaluation\results\local_validation_run\metrics_report.json `
    -Raw
```

---

## Development-Only Selection Evidence

Development-only selection evidence is retained under:

```text
evaluation/results/development/
```

To inspect the development out-of-fold routing workflow:

```powershell
python -m scripts.inspect_development_oof `
    --development data/cloudserve/development_tickets.json `
    --kb data/cloudserve/documentation.json `
    --out evaluation/results/local_development_oof.json
```

This workflow is development-only and does not use Validation-80 labels for candidate selection.

---

## Decision Logging

Every processed ticket is persisted to the audit database.

A decision record includes:

- ticket ID
- route
- routing reasons
- intent prediction
- urgency prediction
- answerability prediction
- retrieved passages
- evidence state
- generated draft
- guardrail results
- configuration fingerprint
- timestamp
- run ID where applicable

Retrieve a recorded decision through:

```text
GET /decisions/{ticket_id}
```

---

## Human Review Workflow

Review state is available through:

```text
GET  /review/{ticket_id}
POST /review/{ticket_id}
```

Review actions are recorded in the audit trail.

Approval records the reviewer decision but does not send a customer message.

---

## Monitoring

Prometheus configuration:

```text
monitoring/prometheus.yml
```

Grafana dashboard:

```text
monitoring/grafana/cloudserve-dashboard.json
```

Start the API:

```powershell
python -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```

Prometheus should scrape:

```text
http://127.0.0.1:8000/metrics
```

Import the supplied Grafana dashboard JSON to visualize the exposed runtime metrics.

---

## Data

```text
data/cloudserve/development_tickets.json
    500 labelled development tickets

data/cloudserve/validation_tickets.json
    80 labelled validation tickets

data/cloudserve/documentation.json
    29 knowledge-base articles

data/cloudserve/ground_truth_responses.json
    200 senior-agent reference responses

data/sample/
    synthetic fixtures used by fast tests
```

Runtime code does not receive development or validation labels as model inputs. The evaluation harness handles labels separately after the pipeline has produced its decisions.

---

## Core Architecture

| Component | Responsibility |
|---|---|
| `src/ingest.py` | Normalize supported channels and validate input |
| `src/classify.py` | Intent, urgency, and answerability classification |
| `src/retrieve.py` | Knowledge-base retrieval |
| `src/eligibility.py` | Evidence and policy assessment |
| `src/generate.py` | Deterministic cited draft generation |
| `src/guardrails.py` | Grounding and safety controls |
| `src/router.py` | `AUTO_RESPOND` / `ESCALATE` routing |
| `src/audit.py` | Persistent decision and review logging |
| `src/api.py` | FastAPI service |
| `src/monitoring.py` | Runtime metrics |
| `evaluation/harness.py` | Unattended evaluation |
| `evaluation/metrics.py` | Evaluation metrics |
| `tests/` | Automated verification |

---

## Frozen Evidence

The submission retains intentional evidence under:

```text
evaluation/results/development/
evaluation/results/final_c1_validation80_20260926_191933/
evaluation/results/final_capstone/
evaluation/results/final_clean_verification/
evaluation/results/operational_demo/
```

The canonical final C1 Validation-80 evidence is:

```text
evaluation/results/final_c1_validation80_20260926_191933/
```

Do not overwrite this directory.

Use a separate output directory for reproduction runs, for example:

```text
evaluation/results/local_validation_run/
```

---

## Documentation

Detailed project documentation is available in:

```text
docs/ARCHITECTURE.md
docs/TRACEABILITY.md
docs/GOVERNANCE.md
docs/VERIFICATION.md
docs/FINAL_CAPSTONE_AUDIT.md
docs/HISTORICAL_EVIDENCE_REGISTER.md
```

- `docs/ARCHITECTURE.md` — system boundaries, pipeline stages, runtime behavior, and data flow
- `docs/TRACEABILITY.md` — requirements-to-code and requirements-to-evidence mapping
- `docs/GOVERNANCE.md` — fail-closed behavior, kill-switch controls, operational risk, and incident handling
- `docs/VERIFICATION.md` — executed verification and evaluation evidence
- `docs/FINAL_CAPSTONE_AUDIT.md` — final acceptance and submission reconciliation
- `docs/HISTORICAL_EVIDENCE_REGISTER.md` — historical evidence separated from the final submitted implementation

---

## Operational Safety Principles

The implementation follows these principles:

- escalation is the safe default
- automatic response requires explicit authorization
- unsafe intents are never automatically answered
- insufficient evidence causes escalation
- unsupported claims are blocked
- citations must resolve to retrieved documentation
- decisions are logged
- failures degrade safely
- evaluation output is separated from runtime behavior
- development evidence is separated from final validation evidence

---

## Attribution and AI Assistance

The project is grounded in the supplied CloudServe project brief, specification, stakeholder material, datasets, documentation corpus, and approved reference implementation.

Open-source dependencies are listed in `requirements.txt`.

AI-assisted development tooling was used for implementation support, auditing, debugging, and targeted remediation.

Final reported measurements come from executed tests and retained evaluation artifacts rather than generated prose.

No external model-generated customer evidence is represented as an observed project result.
