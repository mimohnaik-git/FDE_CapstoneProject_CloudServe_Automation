"""Unattended evaluation harness (A9, A10). Works on any number of tickets.

python -m evaluation.harness --input data/sample/validation_tickets.json \
    --output evaluation/results/val [--references data/sample/references.json]

Labels are read ONLY here, after the pipeline has produced its decision;
the pipeline never sees them."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import subprocess
import sys
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import sklearn

from src.audit import AuditStore
from src.config import get_settings
from src.pipeline import Pipeline

from . import metrics as M

LABEL_KEYS = {"intent", "urgency", "expected_route", "must_not_auto_respond",
              "expected_doc_ids", "answerable", "answerable_from_docs", "labels",
              "history"}


def load_tickets(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["tickets"] if isinstance(data, dict) else data


def strip_labels(t: dict) -> dict:
    return {k: v for k, v in t.items() if k not in LABEL_KEYS} if isinstance(t, dict) else t


def labels_for(t: dict) -> dict:
    """Support the official nested schema and the small legacy test fixtures."""
    nested = t.get("labels")
    return nested if isinstance(nested, dict) else t


def _match_tokens(value: str) -> list[str]:
    """Conservative lexical normalization for evaluator-only phrase matching."""
    tokens = re.findall(r"[a-z0-9]+", value.lower())
    normalized = []
    for token in tokens:
        if token.endswith("ies") and len(token) > 4:
            token = token[:-3] + "y"
        elif token.endswith("ed") and len(token) > 4:
            token = token[:-2]
        elif token.endswith("s") and len(token) > 3 and not token.endswith("ss"):
            token = token[:-1]
        normalized.append(token)
    return normalized


def must_mention_match(expected: str, response: str) -> bool:
    """Match normalized terms in order, allowing one intervening modifier.

    This credits narrow equivalents such as ``raw request body`` for
    ``raw body`` while continuing to reject incomplete responses.
    """
    wanted = _match_tokens(expected)
    actual = _match_tokens(response)
    if not wanted:
        return True
    positions = [i for i, token in enumerate(actual) if token == wanted[0]]
    for position in positions:
        frontier = [position]
        for token in wanted[1:]:
            frontier = sorted({i for prior in frontier
                               for i in range(prior + 1, min(len(actual), prior + 3))
                               if actual[i] == token})
            if not frontier:
                break
        if frontier:
            return True
    return False


def expected_route(t: dict) -> str | None:
    labels = labels_for(t)
    if labels.get("expected_route"):
        return str(labels["expected_route"]).upper()
    answerable_key = "answerable" if "answerable" in labels else "answerable_from_docs"
    if answerable_key in labels:
        return ("AUTO_RESPOND" if labels[answerable_key] and not labels.get("must_not_auto_respond")
                else "ESCALATE")
    return None


def analyze_decisions(tickets: list[dict], decisions: list[dict]) -> dict:
    """Calculate evaluator metrics for decisions produced by any transport.

    The offline harness and live-API runner share this function so metric
    definitions cannot drift.
    """
    labelled = [(t, d) for t, d in zip(tickets, decisions) if isinstance(t, dict)]
    rep: dict = {}

    ok = [(t, d) for t, d in labelled if d["intent"]]
    if any("intent" in labels_for(t) for t, _ in ok):
        pairs = [(t, d) for t, d in ok if "intent" in labels_for(t)]
        rep["intent"] = M.classification([labels_for(t)["intent"] for t, _ in pairs],
                                         [d["intent"]["label"] for _, d in pairs])
        rep["intent"]["ece"] = M.ece([d["intent"]["confidence"] for _, d in pairs],
                                     [labels_for(t)["intent"] == d["intent"]["label"]
                                      for t, d in pairs])
    if any("urgency" in labels_for(t) for t, _ in ok):
        pairs = [(t, d) for t, d in ok if "urgency" in labels_for(t)]
        rep["urgency"] = M.classification([labels_for(t)["urgency"] for t, _ in pairs],
                                          [d["urgency"]["label"] for _, d in pairs],
                                          positive="high")
        rep["urgency"]["ece"] = M.ece([d["urgency"]["confidence"] for _, d in pairs],
                                         [labels_for(t)["urgency"] == d["urgency"]["label"]
                                          for t, d in pairs])
    if any("answerable_from_docs" in labels_for(t) or "answerable" in labels_for(t)
           for t, _ in ok):
        pairs = [(t, d) for t, d in ok if d.get("answerability") and
                 ("answerable_from_docs" in labels_for(t) or "answerable" in labels_for(t))]
        if pairs:
            truth = ["answerable" if labels_for(t).get(
                "answerable_from_docs", labels_for(t).get("answerable")) else "not_answerable"
                     for t, _ in pairs]
            pred = [d["answerability"]["label"] for _, d in pairs]
            rep["answerability"] = M.classification(truth, pred,
                                                      positive="not_answerable")
            rep["answerability"]["ece"] = M.ece(
                [d["answerability"]["confidence"] for _, d in pairs],
                [expected == actual for expected, actual in zip(truth, pred)])
    if any(labels_for(t).get("expected_doc_ids") for t, _ in labelled):
        rank = [[p["doc_id"] for p in d["passages"]] for _, d in labelled]
        rank = [list(dict.fromkeys(r)) for r in rank]
        rep["retrieval"] = M.retrieval(rank, [set(labels_for(t).get("expected_doc_ids") or [])
                                              for t, _ in labelled])
    exp = []
    for t, d in labelled:
        route = expected_route(t)
        if route:
            exp.append((route, d["route"], bool(labels_for(t).get("must_not_auto_respond"))))
    if exp:
        rep["routing"] = M.routing([e[0] for e in exp], [e[1] for e in exp],
                                   [e[2] for e in exp])
        by = defaultdict(lambda: defaultdict(list))
        for t, d in labelled:
            er = expected_route(t)
            if er:
                by["channel"][d.get("channel") or "invalid"].append(er == d["route"])
                by["customer_tier"][d.get("customer_tier") or "unknown"].append(er == d["route"])
                by["customer_region"][d.get("customer_region") or "unknown"].append(
                    er == d["route"])
                by["language_fluency"][d.get("language_fluency") or "unknown"].append(
                    er == d["route"])
        subgroup_routing_gate: dict[str, object] = {
            dim: M.subgroup_gate(dict(g)) for dim, g in by.items()}
        subgroup_routing_gate["note"] = (
            "Quality signal is routing correctness, not response quality. "
            "A response-quality fairness claim needs human-reviewed subgroup samples.")
        rep["subgroup_routing_gate"] = subgroup_routing_gate

    blocks = Counter(b for d in decisions for b in (d.get("guardrails") or {}).get("blocks", []))
    rep["guardrails"] = {"drafts_checked": sum(bool(d.get("guardrails")) for d in decisions),
                         "tickets_blocked": sum(bool((d.get("guardrails") or {}).get("blocks"))
                                                for d in decisions),
                         "blocks_by_guardrail": dict(blocks)}
    rep["escalation_reasons"] = dict(Counter(r for d in decisions for r in d["reasons"]))
    rep["eligibility"] = dict(Counter((d.get("evidence") or {}).get("status", "NONE")
                                      for d in decisions))
    rep["latency_s"] = M.latency([d["total_latency_s"] for d in decisions])
    histories = [t.get("history") for t, _ in labelled if isinstance(t.get("history"), dict)]
    predicted_auto = sum(d["route"] == "AUTO_RESPOND" for d in decisions)
    rep["business"] = {
        "simulated_first_contact_resolution_proxy": M.ratio(predicted_auto, len(decisions)),
        "simulated_escalation_rate": M.ratio(len(decisions) - predicted_auto, len(decisions)),
        "historical_first_contact_resolution": M.ratio(
            sum(bool(h.get("first_contact_resolution")) for h in histories), len(histories)),
        "historical_repeat_contact_rate": M.ratio(
            sum(bool(h.get("repeat_contact")) for h in histories), len(histories)),
        "customer_first_response_time": {"value": None, "evidence": "not available"},
        "customer_satisfaction_after_automation": {"value": None, "evidence": "not available"},
        "note": ("Simulation proxies are routing outcomes, not observed customer resolutions. "
                 "Historical fields describe the supplied baseline, not system performance."),
    }
    rep["operational"] = {
        "processing_failures": ratio_err(decisions),
        "malformed_inputs_rejected": sum(str(d.get("error") or "").startswith("IngestError")
                                         for d in decisions),
        "routes": dict(Counter(d["route"] for d in decisions)),
    }
    return rep


def evaluate(pipeline: Pipeline, tickets: list[dict], run_id: str) -> tuple[list, dict]:
    decisions = [pipeline.process(strip_labels(t), run_id=run_id).to_dict() for t in tickets]
    return decisions, analyze_decisions(tickets, decisions)


def ratio_err(decisions):
    """Processing failures = unexpected errors that still produced a logged
    ESCALATE (retrieval outage, audit failure, unhandled). Malformed input
    rejected by ingest and provider fallbacks are handled paths, counted
    separately."""
    handled = ("IngestError", "Provider", "Malformed", "UnexpectedProvider")
    errs = [d for d in decisions if d.get("error") and not str(d["error"]).startswith(handled)]
    return M.ratio(len(errs), len(decisions))


def evaluate_references(pipeline: Pipeline, refs: list[dict],
                        tickets_by_id: dict[str, dict] | None = None,
                        run_id: str = "reference-eval") -> dict:
    """Offline reviewer-draft evaluation against senior-agent references.
    References are evaluation targets only; never runtime knowledge."""
    must_hit = must_total = all_ok = with_reqs = violations = resolvable = 0
    top_in_expected = unsupported = drafts = 0
    missing_tickets = 0
    for r in refs:
        ticket = r.get("ticket") or (tickets_by_id or {}).get(r.get("ticket_id"))
        if not ticket:
            missing_tickets += 1
            continue
        d = pipeline.process(strip_labels(ticket), run_id=run_id).to_dict()
        draft = d.get("draft") or {}
        text = (draft.get("text") or "").lower()
        if draft.get("status") == "EVIDENCE_ASSEMBLY_COMPLETE":
            drafts += 1
        valid = {p["doc_id"] + "#" + p["section"]
                 for p in d.get("supporting_passages", [])}
        cites = draft.get("citations") or []
        resolvable += bool(cites) and all(c in valid for c in cites)
        g = (d.get("guardrails") or {})
        unsupported += "grounding" in g.get("blocks", [])
        req = [m.lower() for m in r.get("must_mention", [])]
        if req:
            with_reqs += 1
            hits = sum(must_mention_match(m, text) for m in req)
            must_hit += hits
            must_total += len(req)
            all_ok += hits == len(req)
        violations += any(c.lower() in text for c in r.get("must_not_claim", []))
        if d["passages"] and r.get("expected_doc_ids"):
            top_in_expected += d["passages"][0]["doc_id"] in r["expected_doc_ids"]
    n = len(refs) - missing_tickets
    return {"references": n, "drafts_generated": M.ratio(drafts, n),
            "citation_resolvability": M.ratio(resolvable, n),
            "lexical_grounding_failures": unsupported,
            "must_mention_coverage": M.ratio(must_hit, must_total),
            "tickets_satisfying_all_mentions": M.ratio(all_ok, with_reqs),
            "must_not_claim_violations": violations,
            "top_doc_in_expected_set": M.ratio(top_in_expected, n),
            "references_without_ticket_input": missing_tickets,
            "note": "Automated, lexical checks. Not a substitute for human review."}


def to_markdown(report: dict) -> str:
    lines = [f"# Evaluation report — run {report['run']['run_id']}", ""]
    for k, v in report["run"].items():
        lines.append(f"- **{k}**: {v}")
    def fmt(r):
        return f"{r['value']:.2%} ({r['num']}/{r['den']})" if isinstance(r, dict) and r.get("value") is not None else str(r)
    sec = report["metrics"]
    if "intent" in sec:
        lines += ["", "## Intent", f"- Accuracy: {fmt(sec['intent']['accuracy'])}",
                  f"- Macro F1: {sec['intent']['macro_f1']} over {sec['intent']['macro_over_classes']} classes",
                  f"- ECE: {sec['intent']['ece']['value']} (n={sec['intent']['ece']['n']}, bins={sec['intent']['ece']['bins']})",
                  f"- Calibration status: {sec['intent']['ece']['calibration_status']}",
                  f"- Confidence bands: {sec['intent']['ece']['bands']}"]
    if "urgency" in sec:
        u = sec["urgency"]
        lines += ["", "## Urgency", f"- Accuracy: {fmt(u['accuracy'])}",
                  f"- Macro F1: {u['macro_f1']}", f"- High recall: {fmt(u.get('high_recall'))}",
                  f"- ECE: {u['ece']['value']} (n={u['ece']['n']}, bins={u['ece']['bins']})",
                  f"- Calibration status: {u['ece']['calibration_status']}",
                  f"- Confidence bands: {u['ece']['bands']}"]
    if "answerability" in sec:
        a = sec["answerability"]
        lines += ["", "## Answerability", f"- Accuracy: {fmt(a['accuracy'])}",
                  f"- Macro F1: {a['macro_f1']}",
                  f"- ECE: {a['ece']['value']} (n={a['ece']['n']}, bins={a['ece']['bins']})",
                  f"- Calibration status: {a['ece']['calibration_status']}",
                  f"- Confidence bands: {a['ece']['bands']}"]
    if "retrieval" in sec:
        r = sec["retrieval"]
        lines += ["", f"## Retrieval (eligible tickets: {r['eligible_tickets']}, "
                      f"expected docs: {r['expected_docs_total']})"]
        for k in (1, 3, 5):
            lines.append(f"- Recall@{k}: {fmt(r[f'recall@{k}'])}; Hit@{k}: {fmt(r[f'hit@{k}'])}; "
                         f"Precision@{k}: {r[f'precision@{k}']}")
        lines.append(f"- MRR: {r['mrr']}")
    if "routing" in sec:
        r = sec["routing"]
        lines += ["", "## Routing",
                  f"- Accuracy: {fmt(r['routing_accuracy'])}",
                  f"- Expected AUTO: {r['expected_auto']}, expected ESCALATE: {r['expected_escalate']}",
                  f"- Automation rate: {fmt(r['automation_rate'])}",
                  f"- False automatic responses: {r['false_automatic_responses']}",
                  f"- False escalations: {r['false_escalations']}",
                  f"- Must-not-auto violations: {r['must_not_auto_violations']} / {r['must_not_auto_tickets']}"]
    b = sec["business"]
    lines += ["", "## Business indicators",
              f"- Simulated FCR proxy: {fmt(b['simulated_first_contact_resolution_proxy'])}",
              f"- Simulated escalation rate: {fmt(b['simulated_escalation_rate'])}",
              f"- Historical FCR baseline in supplied records: {fmt(b['historical_first_contact_resolution'])}",
              "- Customer first-response time after automation: Evidence not available.",
              "- Customer satisfaction after automation: Evidence not available.",
              f"- Note: {b['note']}"]
    g = sec["guardrails"]
    lines += ["", "## Guardrails", f"- Drafts checked: {g['drafts_checked']}",
              f"- Tickets blocked: {g['tickets_blocked']}",
              f"- Blocks by guardrail: {g['blocks_by_guardrail']}"]
    lt = sec["latency_s"]
    lines += ["", "## Latency (pipeline only — not customer first-response time)",
              f"- Steady state: {lt['steady_state']}",
              f"- Including warm-up: {lt['including_warmup']}"]
    if "subgroup_routing_gate" in sec:
        lines += ["", "## Subgroup gate"]
        for dim, v in sec["subgroup_routing_gate"].items():
            if isinstance(v, dict):
                lines.append(f"- {dim}: {v['status']} (gap {v['gap_pp']} pp; undersized: {v['undersized_groups']})")
        lines.append(f"- {sec['subgroup_routing_gate']['note']}")
    if "reference_drafts" in report:
        lines += ["", "## Reviewer drafts vs references", "```",
                  json.dumps(report["reference_drafts"], indent=2), "```"]
    lines += ["", "## Not measured by this run",
              "Hallucination (human), response correctness/usefulness, observed FCR, CSAT, "
              "customer first-response time, production availability, repeat contact."]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--references", type=Path)
    ap.add_argument("--reference-tickets", type=Path,
                    help="Ticket file used to join official references by ticket_id")
    ap.add_argument(
        "--db", default=None,
        help="SQLite path (default: <output>/decisions-<run-id>.sqlite3)",
    )
    ap.add_argument("--artifacts", type=Path, help="Trained classifier directory")
    ap.add_argument("--kb", type=Path, help="Knowledge-base JSON path")
    ap.add_argument("--training-data", type=Path,
                    default=Path("data/cloudserve/development_tickets.json"))
    ap.add_argument("--retrieval-backend", choices=["tfidf", "minilm"])
    ap.add_argument("--fail-on-must-not-auto", action="store_true")
    ap.add_argument("--enable-auto-policy", action="store_true",
                    help="Evaluate the automatic-response path; safe default is escalation-only")
    a = ap.parse_args(argv)

    wall_started = time.perf_counter()
    started = datetime.now(timezone.utc).isoformat()
    run_id = str(uuid.uuid4())
    a.output.mkdir(parents=True, exist_ok=True)
    raw = a.input.read_bytes()
    tickets = load_tickets(a.input)
    db_path = Path(a.db) if a.db else a.output / f"decisions-{run_id}.sqlite3"
    overrides = {
        "db_path": str(db_path),
        "customer_release_authorized": a.enable_auto_policy,
    }
    if a.artifacts:
        overrides["artifacts_dir"] = str(a.artifacts)
    if a.kb:
        overrides["kb_path"] = str(a.kb)
    settings = get_settings(**overrides)
    p = Pipeline.from_settings(settings, retrieval_backend=a.retrieval_backend)
    decisions, rep = evaluate(p, tickets, run_id)
    logged = p.audit.count(run_id)
    artifact_hashes = {f.name: hashlib.sha256(f.read_bytes()).hexdigest()
                       for f in Path(settings.artifacts_dir).glob("*.joblib")}
    training_sha = (hashlib.sha256(a.training_data.read_bytes()).hexdigest()
                    if a.training_data.exists() else None)
    try:
        git_sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                                 text=True, check=True).stdout.strip()
    except Exception:
        git_sha = None
    report = {"run": {
        "run_id": run_id, "started_at": started, "input": str(a.input),
        "dataset_sha256": hashlib.sha256(raw).hexdigest(),
        "source_tickets": len(tickets), "evaluated_tickets": len(decisions),
        "logged_decisions": logged,
        "decision_log_coverage": f"{logged}/{len(decisions)}",
        "retrieval_backend": p.retriever.backend_name,
        "retrieval_configuration": settings.retrieval_configuration,
        "config_fingerprint": p.fingerprint,
        "intent_threshold": settings.intent_confidence_threshold,
        "retrieval_threshold": p.retrieval_threshold,
        "operational_auto_policy_default": "OFF",
        "controlled_evaluation_auto_policy": "ENABLED" if a.enable_auto_policy else "OFF",
        "customer_release_authorized": settings.customer_release_authorized,
        "eligibility_policy": settings.eligibility_policy,
        "training_dataset_sha256": training_sha,
        "artifact_sha256": artifact_hashes,
        "python_version": platform.python_version(),
        "sklearn_version": sklearn.__version__,
        "git_sha": git_sha,
        "decision_database": str(db_path),
    }, "metrics": rep}
    if a.references:
        reference_tickets = load_tickets(a.reference_tickets) if a.reference_tickets else tickets
        by_id = {t.get("ticket_id"): t for t in reference_tickets if isinstance(t, dict)}
        report["reference_drafts"] = evaluate_references(
            p, json.loads(a.references.read_text(encoding="utf-8")), by_id,
            run_id=f"{run_id}:references")

    report["run"]["finished_at"] = datetime.now(timezone.utc).isoformat()
    report["run"]["elapsed_seconds"] = round(time.perf_counter() - wall_started, 6)

    with open(a.output / "results.jsonl", "w", encoding="utf-8") as f:
        for d in decisions:
            f.write(json.dumps(d, default=str) + "\n")
    (a.output / "metrics_report.json").write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8")
    (a.output / "metrics_report.md").write_text(to_markdown(report), encoding="utf-8")
    print(f"run {run_id}: {len(decisions)} tickets -> {a.output}")
    if a.fail_on_must_not_auto and rep.get("routing", {}).get("must_not_auto_violations", 0):
        print("FAIL: must-not-auto violation", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
