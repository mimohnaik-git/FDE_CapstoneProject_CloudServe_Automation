# CloudServe Controlled Support Automation

CloudServe is a deterministic, auditable support-automation system for the Forward Deployed AI Engineering capstone.

It classifies support tickets, retrieves reviewed CloudServe documentation, generates grounded cited responses, applies guardrails, routes to `AUTO_RESPOND` or `ESCALATE`, logs decisions, and exposes Prometheus metrics.

**Default operating state:** automatic customer release is OFF.

---

## Operating flow

```text
Terminal 1 -> CloudServe API
Terminal 2 -> Prometheus
Terminal 3 -> Demo Mode OR Evaluator Mode
Browser    -> Grafana
```

Run commands from the cloned repository root. Keep Grafana open while running Demo Mode or Evaluator Mode so the activity is visible on the dashboard.

---

# 1. Setup

## Windows PowerShell

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

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Install dependencies and verify them:

```bash
python -m pip install -r requirements.txt
python -m pip check
```

Run the regression suite:

```bash
python -m pytest -q
```

Observed final-audit result (29 September 2026):

```text
99 passed
```

---

# 2. Start the CloudServe API - Terminal 1

The runner never changes the release controls. Demo Mode and Evaluator Mode require an API that was intentionally started with controlled automatic release enabled.

## Windows PowerShell

```powershell
$env:CLOUDSERVE_AUTO_RESPONSE_ENABLED="true"
$env:CLOUDSERVE_AUTO_RESPONSE_DISABLED="false"

python -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```

## macOS / Linux

```bash
export CLOUDSERVE_AUTO_RESPONSE_ENABLED=true
export CLOUDSERVE_AUTO_RESPONSE_DISABLED=false

python -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```

Verify the API from another terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

The controlled run state should include:

```text
status: ok
customer_release_authorized: true
```

Enabling the release control does not bypass classification, confidence, evidence, ambiguity, guardrail, or audit gates.

---

# 3. Start Prometheus - Terminal 2

CloudServe already includes `prometheus-client` through `requirements.txt`.

`prometheus-client` is a Python dependency that allows CloudServe to expose `/metrics`; it does **not** install the external Prometheus Server application. Prometheus Server must be installed separately.

## Windows PowerShell PATH troubleshooting

First verify that PowerShell can locate Prometheus:

```powershell
Get-Command prometheus -ErrorAction SilentlyContinue
```

Then verify the installed version:

```powershell
prometheus --version
```

If `prometheus` is not recognized, Prometheus may already be installed but the folder containing `prometheus.exe` is not on the current PowerShell PATH.

Locate an existing installation:

```powershell
Get-ChildItem `
    "$env:USERPROFILE\Downloads", `
    "C:\Program Files", `
    "C:\Program Files (x86)" `
    -Filter prometheus.exe `
    -File `
    -Recurse `
    -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty FullName
```

Add the directory containing `prometheus.exe` to the current PowerShell session:

```powershell
$PrometheusDir = "C:\path\to\prometheus-folder"
$env:Path = "$PrometheusDir;$env:Path"
```

This changes `PATH` only for the current PowerShell session.

Verify again:

```powershell
prometheus --version
```

Only continue after `prometheus --version` succeeds.

Start Prometheus from the repository root:

```powershell
prometheus --config.file=monitoring/prometheus.yml --storage.tsdb.path=var/prometheus
```

## macOS / Linux

```bash
command -v prometheus
prometheus --version
prometheus --config.file=monitoring/prometheus.yml --storage.tsdb.path=var/prometheus
```

If Prometheus is installed but not on `PATH`, run the installed Prometheus binary directly with the same `--config.file=monitoring/prometheus.yml` argument.

Prometheus is available at:

```text
Start-Process "http://127.0.0.1:9090"
```

Verify the CloudServe scrape target:

```powershell
(Invoke-RestMethod "http://127.0.0.1:9090/api/v1/targets").data.activeTargets |
    Select-Object health,scrapeUrl,lastError
```

Expected target:

```text
health: up
scrapeUrl: http://127.0.0.1:8000/metrics
```

---

# 4. Open Grafana - Browser

Grafana:

```text
Start-Process "http://127.0.0.1:3000"
```

In Grafana, open **Connections > Data sources > Add new data source**, select
**Prometheus**, set the server URL to `http://127.0.0.1:9090`, and select
**Save & test**. When importing the dashboard below, choose that Prometheus
data source for the dashboard input.

Dashboard file:

```text
monitoring/grafana/cloudserve-dashboard.json
```

Import the dashboard, select the desired `run_mode`, and keep Grafana open while running Demo Mode or Evaluator Mode in Terminal 3.

The primary assessment dashboard intentionally contains exactly six panels:

- Tickets processed (last 1h)
- Total AUTO_RESPOND decisions
- Decisions by route
- Pipeline P95 latency (s)
- Guardrail blocks
- Handled failures

Its `run_mode` selector offers `demo` and `evaluator`, with All implemented by
the `.*` value. The broader historical dashboard is retained at
`monitoring/grafana/evidence/cloudserve-supervised-support.json`. That extended
evidence view contains additional panels such as route percentages, tickets by
channel, P50 latency, and confidence distributions; those panels are not part
of the primary six-panel dashboard.

---

# 5. Demo Mode - Terminal 3

Run all important feature demonstrations with one command:

```bash
python -m scripts.run demo mode
```

Demo Mode exercises the live production API and pipeline for:

- successful `AUTO_RESPOND`;
- human escalation;
- prompt-injection blocking;
- multi-channel handling;
- malformed-input handling;
- ambiguity and review-required behavior;
- audit persistence and review workflow; and
- release-control precedence.

Terminal output is vertical and human-readable, followed by a compact PASS/FAIL summary. The requests also generate Prometheus telemetry with `run_mode="demo"`.

---

# 6. Evaluator Mode - Terminal 3

Run the configured default evaluation dataset:

```bash
python -m scripts.run evaluator mode
```

Run the same live-API evaluator with a user-supplied labelled dataset:

```bash
python -m scripts.run evaluator mode --input <dataset.json>
```

Evaluator Mode verifies API health and the controlled release state before processing. It never silently enables `AUTO_RESPOND`. Every ticket is processed through the live CloudServe API, so evaluator traffic is visible in Prometheus and Grafana with `run_mode="evaluator"`.

Ticket totals, progress, route percentages, classification metrics, retrieval metrics, guardrail counts, and latency statistics are calculated dynamically from the loaded dataset. The evaluator is not tied to a fixed dataset size.

The terminal presents compact, human-readable progress and an aggregate summary. Detailed JSON and JSONL are the authoritative evidence and are stored in a new directory for each run:

```text
evaluation/results/evaluator_<timestamp>/
  run_metadata.json
  results.jsonl
  metrics_report.json
  metrics_report.md
```

Do not overwrite frozen canonical evidence directories.

---

# 7. AUTO_RESPOND control reference

| `CLOUDSERVE_AUTO_RESPONSE_ENABLED` | `CLOUDSERVE_AUTO_RESPONSE_DISABLED` | AUTO release |
|---|---|---|
| `false` | `false` | OFF |
| `true` | `false` | ON |
| `false` | `true` | OFF |
| `true` | `true` | OFF - `DISABLED` wins |

The default is fail-closed. `CLOUDSERVE_AUTO_RESPONSE_DISABLED=true` always overrides the enabled switch.

To restore Safe Mode, stop the API and restart it with:

## Windows PowerShell

```powershell
$env:CLOUDSERVE_AUTO_RESPONSE_ENABLED="false"
$env:CLOUDSERVE_AUTO_RESPONSE_DISABLED="true"

python -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```

## macOS / Linux

```bash
export CLOUDSERVE_AUTO_RESPONSE_ENABLED=false
export CLOUDSERVE_AUTO_RESPONSE_DISABLED=true

python -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```

---

# 8. Architecture

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

# 9. Historical evaluation provenance

Canonical Validation-80 evidence was produced by:

```text
a09826071fcd95d0330ffc0e000b6dc73c49ca47
```

Canonical evidence:

```text
evaluation/results/final_c1_validation80_20260926_191933/
```

This historical statement identifies the retained canonical evaluation. Current evaluator operation remains dataset-size agnostic.

---

# 10. Shutdown

- Stop the CloudServe API and Prometheus with `Ctrl+C` in their terminals.
- Close the Grafana browser tab.
- Exit the virtual environment with `deactivate`.
