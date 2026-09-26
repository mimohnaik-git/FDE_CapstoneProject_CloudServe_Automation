import json
import os
from pathlib import Path

root = Path(os.environ["FINAL_C1_OUT"])
report_path = root / "metrics_report.json"
results_path = root / "results.jsonl"

report = json.loads(
    report_path.read_text(encoding="utf-8")
)

rows = [
    json.loads(line)
    for line in results_path.read_text(
        encoding="utf-8"
    ).splitlines()
    if line.strip()
]

run = report.get("run", {})
metrics = report.get("metrics", {})

def route(r):
    return str(r.get("route", "")).upper()

pred_auto = sum(
    route(r) == "AUTO_RESPOND"
    for r in rows
)

pred_esc = len(rows) - pred_auto

gate_rows = [
    r for r in rows
    if "evidence_ambiguity_review_required"
    in (r.get("reasons") or [])
]

fingerprints = sorted({
    r.get("config_fingerprint")
    for r in rows
    if r.get("config_fingerprint")
})

trace_configs = sorted({
    (
        (r.get("trace") or {}).get(
            "intent_threshold"
        ),
        (r.get("trace") or {}).get(
            "answerability_threshold"
        ),
        tuple(
            (r.get("trace") or {}).get(
                "auto_eligible_intents",
                [],
            )
        ),
        (r.get("trace") or {}).get(
            "evidence_resolution_ratio_min"
        ),
        (r.get("trace") or {}).get(
            "evidence_symptom_margin_max"
        ),
    )
    for r in rows
})

print("=== FINAL C1 VALIDATION AUDIT ===")
print("Run ID:", run.get("run_id"))
print("Evaluated:", run.get("evaluated_tickets"))
print("Logged:", run.get("logged_decisions"))
print(
    "Decision log coverage:",
    run.get("decision_log_coverage"),
)
print(
    "Pipeline fingerprint:",
    run.get("config_fingerprint"),
)
print(
    "Retrieval backend:",
    run.get("retrieval_backend"),
)
print(
    "Retrieval configuration:",
    run.get("retrieval_configuration"),
)

print("\n=== ROUTING ===")
print("Predicted AUTO:", pred_auto)
print("Predicted ESCALATE:", pred_esc)
print(
    "Evidence gate escalations:",
    len(gate_rows),
)
print(
    "Evidence gate ticket IDs:",
    [r["ticket_id"] for r in gate_rows],
)

print("\n=== DECISION FINGERPRINT CONSISTENCY ===")
print("Unique fingerprints:", fingerprints)

print("\n=== TRACE POLICY ===")
for x in trace_configs:
    print("Intent threshold:", x[0])
    print("Answer threshold:", x[1])
    print("Allowlist:", x[2])
    print("Resolution ratio min:", x[3])
    print("Symptom margin max:", x[4])

print("\n=== HARNESS METRICS ===")
print(json.dumps(metrics, indent=2))
