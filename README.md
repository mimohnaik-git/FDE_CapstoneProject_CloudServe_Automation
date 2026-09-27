# CloudServe Controlled Support Automation

CloudServe is a deterministic, auditable support-automation system for the Forward Deployed AI Engineering capstone.

It classifies support tickets, retrieves reviewed CloudServe documentation, generates grounded cited responses, applies guardrails, routes to `AUTO_RESPOND` or `ESCALATE`, logs decisions, and exposes Prometheus metrics.

**Default operating state:** automatic customer release is OFF.

---

## Quick Flow

```text
Setup
→ pip check
→ tests
→ Safe Mode
→ Demo Mode
→ AUTO demo
→ escalation demo
→ guardrail demo
→ disable-override test
→ Validation-80 evaluation
→ Prometheus
→ Grafana
→ monitored demos
→ restore Safe Mode
→ shutdown
```

Use:

```text
Terminal 1 = CloudServe API
Terminal 2 = tests / demos
Terminal 3 = Prometheus
Browser    = Grafana
```

Run commands from the cloned repository root.

---

# 1. Setup

## Windows PowerShell

Create and activate the virtual environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## macOS / Linux

Create and activate the virtual environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
pip check
```

Expected:

```text
No broken requirements found.
```

Run the regression suite:

```bash
python -m pytest -q
python -m pytest -q -W error
```

Current verified baseline:

```text
92 passed
92 passed
```

---

# 2. CloudServe Safe Mode

Safe Mode keeps customer `AUTO_RESPOND` release disabled.

## Windows PowerShell — Terminal 1

```powershell
$Host.UI.RawUI.WindowTitle = "CloudServe SAFE MODE - API"
Write-Host "=== CloudServe SAFE MODE | AUTO DISABLED ==="

$env:CLOUDSERVE_AUTO_RESPONSE_ENABLED="false"
$env:CLOUDSERVE_AUTO_RESPONSE_DISABLE="true"

python -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```

## macOS / Linux — Terminal 1

```bash
export CLOUDSERVE_AUTO_RESPONSE_ENABLED=false
export CLOUDSERVE_AUTO_RESPONSE_DISABLE=true

echo "=== CloudServe SAFE MODE | AUTO DISABLED ==="
python -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```

Leave Terminal 1 running.

Verify from Terminal 2.

### Windows PowerShell

```powershell
$h = Invoke-RestMethod http://127.0.0.1:8000/health
Write-Host "Safe Mode | AUTO enabled:" $h.customer_release_authorized
```

### macOS / Linux

```bash
curl -s http://127.0.0.1:8000/health
```

Expected state:

```text
customer_release_authorized: false
```

---

# 3. CloudServe Demo Mode

Stop Terminal 1 with `Ctrl+C`.

Demo Mode enables the final customer-release gate. It does **not** bypass policy, confidence, evidence, ambiguity, guardrails, or audit controls.

## Windows PowerShell — Terminal 1

```powershell
$Host.UI.RawUI.WindowTitle = "CloudServe DEMO MODE - API"
Write-Host "=== CloudServe DEMO MODE | AUTO ENABLED ==="

$env:CLOUDSERVE_AUTO_RESPONSE_ENABLED="true"
$env:CLOUDSERVE_AUTO_RESPONSE_DISABLE="false"

python -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```

## macOS / Linux — Terminal 1

```bash
export CLOUDSERVE_AUTO_RESPONSE_ENABLED=true
export CLOUDSERVE_AUTO_RESPONSE_DISABLE=false

echo "=== CloudServe DEMO MODE | AUTO ENABLED ==="
python -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```

Verify:

### Windows PowerShell

```powershell
$h = Invoke-RestMethod http://127.0.0.1:8000/health
Write-Host "Demo Mode | AUTO enabled:" $h.customer_release_authorized
```

### macOS / Linux

```bash
curl -s http://127.0.0.1:8000/health
```

Expected state:

```text
customer_release_authorized: true
```

---

# 4. Demo Features

Run these from Terminal 2 while Demo Mode is running.

## Successful automatic response

```bash
python -m scripts.demo --case auto
```

Expected:

```text
Ticket: VAL-0005
Decision: Automatic response approved.
```

## Human escalation

```bash
python -m scripts.demo --case escalate
```

Expected:

```text
Ticket: VAL-0002
Decision: Escalated for human review.
```

## Synthetic prompt-injection guardrail

```bash
python -m scripts.demo --case guardrail
```

Expected:

```text
Decision: Escalated for human review.

Safety controls that blocked release:
- prompt injection
```

---

# 5. Verify the Disable Override

Stop Terminal 1 with `Ctrl+C`.

Set both controls to `true`. `DISABLE` must win.

## Windows PowerShell — Terminal 1

```powershell
$Host.UI.RawUI.WindowTitle = "CloudServe DISABLE OVERRIDE - API"
Write-Host "=== DISABLE OVERRIDE | EXPECT AUTO OFF ==="

$env:CLOUDSERVE_AUTO_RESPONSE_ENABLED="true"
$env:CLOUDSERVE_AUTO_RESPONSE_DISABLE="true"

python -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```

## macOS / Linux — Terminal 1

```bash
export CLOUDSERVE_AUTO_RESPONSE_ENABLED=true
export CLOUDSERVE_AUTO_RESPONSE_DISABLE=true

echo "=== DISABLE OVERRIDE | EXPECT AUTO OFF ==="
python -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```

Verify from Terminal 2:

```bash
python -m scripts.demo --case auto
```

Expected:

```text
Decision: Escalated for human review.

Why:
- Automatic customer release is currently disabled.
```

---

# 6. Validation-80 Evaluation

Run from Terminal 2.

## Windows PowerShell

```powershell
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$OutputPath = "evaluation/results/local_demo_$Timestamp"

python -m evaluation.harness --input data/cloudserve/validation_tickets.json --output $OutputPath --references data/cloudserve/ground_truth_responses.json --reference-tickets data/cloudserve/development_tickets.json --kb data/cloudserve/documentation.json --retrieval-backend tfidf --enable-auto-policy --fail-on-must-not-auto

Get-Content "$OutputPath\metrics_report.md" -Encoding UTF8
```

## macOS / Linux

```bash
Timestamp=$(date +"%Y%m%d_%H%M%S")
OutputPath="evaluation/results/local_demo_$Timestamp"

python -m evaluation.harness --input data/cloudserve/validation_tickets.json --output "$OutputPath" --references data/cloudserve/ground_truth_responses.json --reference-tickets data/cloudserve/development_tickets.json --kb data/cloudserve/documentation.json --retrieval-backend tfidf --enable-auto-policy --fail-on-must-not-auto

cat "$OutputPath/metrics_report.md"
```

Do not overwrite the frozen canonical evidence:

```text
evaluation/results/final_c1_validation80_20260926_191933/
```

---

# 7. Monitoring

Restart **Demo Mode** in Terminal 1 before monitoring.

Verify CloudServe metrics.

## Windows PowerShell — Terminal 2

```powershell
$metrics = Invoke-WebRequest http://127.0.0.1:8000/metrics -UseBasicParsing
Write-Host "Metrics endpoint status:" $metrics.StatusCode
```

## macOS / Linux — Terminal 2

```bash
curl -I http://127.0.0.1:8000/metrics
```

Expected:

```text
HTTP 200
```

## Start Prometheus — Terminal 3

Use the existing Prometheus installation:

```bash
prometheus --config.file=monitoring/prometheus.yml
```

If `prometheus` is not on `PATH`, run the installed Prometheus binary directly with the same `--config.file` argument.

Prometheus:

```text
http://127.0.0.1:9090
```

Verify the CloudServe scrape target.

### Windows PowerShell

```powershell
(Invoke-RestMethod "http://127.0.0.1:9090/api/v1/targets").data.activeTargets |
    Select-Object health,scrapeUrl,lastError
```

### macOS / Linux

```bash
curl -s http://127.0.0.1:9090/api/v1/targets
```

Expected target:

```text
health: up
scrapeUrl: http://127.0.0.1:8000/metrics
```

---

# 8. Grafana

Grafana:

```text
http://127.0.0.1:3000
```

Prometheus data source:

```text
http://127.0.0.1:9090
```

Dashboard file:

```text
monitoring/grafana/cloudserve-dashboard.json
```

Open Grafana:

## Windows PowerShell

```powershell
Start-Process "http://127.0.0.1:3000"
```

## macOS

```bash
open http://127.0.0.1:3000
```

## Linux

```bash
xdg-open http://127.0.0.1:3000
```

While Grafana is open, run from Terminal 2:

```bash
python -m scripts.demo --case auto
python -m scripts.demo --case escalate
python -m scripts.demo --case guardrail
```

Wait about 15–30 seconds, then inspect:

```text
Tickets processed
AUTO_RESPOND %
ESCALATE %
Tickets by channel
Decisions by route
Pipeline P50 / P95
Guardrail blocks
Handled failures
Prediction confidence distribution
```

A zero `Handled failures` value is valid during a clean run.

---

# 9. Shutdown

## Restore Safe Mode

Stop Terminal 1 with `Ctrl+C`.

### Windows PowerShell

```powershell
$env:CLOUDSERVE_AUTO_RESPONSE_ENABLED="false"
$env:CLOUDSERVE_AUTO_RESPONSE_DISABLE="true"

python -c "from src.config import Settings; print('Automatic customer release enabled:', Settings().customer_release_authorized)"
```

### macOS / Linux

```bash
export CLOUDSERVE_AUTO_RESPONSE_ENABLED=false
export CLOUDSERVE_AUTO_RESPONSE_DISABLE=true

python -c "from src.config import Settings; print('Automatic customer release enabled:', Settings().customer_release_authorized)"
```

Expected:

```text
Automatic customer release enabled: False
```

Stop Prometheus in Terminal 3 with:

```text
Ctrl+C
```

Close the Grafana browser tab.

Exit the virtual environment in Terminal 1 and Terminal 2:

```bash
deactivate
```

---

# AUTO Control Reference

| ENABLED | DISABLE | AUTO release |
|---|---|---|
| `false` | `false` | OFF |
| `true` | `false` | ON |
| `false` | `true` | OFF |
| `true` | `true` | OFF — DISABLE wins |

---

# Architecture

```text
Ticket
  -> Ingest
  -> Classify
  -> Retrieve
  -> Assess Evidence
  -> Generate
  -> Guardrails
  -> Route
  -> Audit
  -> Monitoring / Evaluation
```

```text
Python:                 3.12
API:                    FastAPI
API entrypoint:         src.api:app
Retrieval:              deterministic TF-IDF
Generation:             deterministic grounded assembler
External LLM required:  No
Default release state:  OFF
```

---

# Evaluation Provenance

Canonical Validation-80 evidence was produced by:

```text
a09826071fcd95d0330ffc0e000b6dc73c49ca47
```

Canonical evidence:

```text
evaluation/results/final_c1_validation80_20260926_191933/
```
