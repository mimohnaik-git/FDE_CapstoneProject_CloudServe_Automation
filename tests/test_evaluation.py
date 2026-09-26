import json
import sqlite3
from pathlib import Path

import pytest

from evaluation import metrics as M
from evaluation.harness import evaluate, expected_route, must_mention_match, strip_labels


def test_must_mention_normalization_accepts_narrow_equivalence():
    assert must_mention_match("raw body", "Compute the signature over the raw request body.")
    assert must_mention_match("account lock", "Confirm whether the account is locked.")


def test_must_mention_normalization_rejects_incomplete_response():
    assert not must_mention_match("raw body", "Compute a signature over parsed data.")
    assert not must_mention_match("account lock", "Review the account settings.")


def test_ratio_keeps_denominator():
    assert M.ratio(32, 80) == {"value": 0.4, "num": 32, "den": 80}
    assert M.ratio(0, 0)["value"] is None


def test_routing_reports_expected_split_and_false_escalations():
    r = M.routing(["AUTO_RESPOND"] * 48 + ["ESCALATE"] * 32, ["ESCALATE"] * 80, [False] * 80)
    assert r["routing_accuracy"]["value"] == 0.4
    assert r["false_escalations"] == 48 and r["false_automatic_responses"] == 0
    assert r["auto_precision"]["value"] is None


def test_latency_excludes_warmup():
    v = [30.0] + [0.08] * 79
    lat = M.latency(v)
    assert lat["including_warmup"]["mean"] > lat["including_warmup"]["p95"]
    assert lat["steady_state"]["mean"] == pytest.approx(0.08)


def test_ece_reports_sample_size():
    e = M.ece([0.9, 0.8, 0.95], [True, True, False])
    assert e["n"] == 3 and e["small_sample_warning"]
    assert e["calibration_status"] == "NOT_ESTABLISHED"
    assert all({"n", "mean_confidence", "observed_accuracy", "absolute_gap"} <= set(b)
               for b in e["bands"])


def test_retrieval_counts_eligible_only():
    r = M.retrieval([["A", "B"], ["C"], ["X"]], [{"A"}, set(), {"Y"}])
    assert r["eligible_tickets"] == 2 and r["recall@1"]["num"] == 1


def test_subgroup_gate_not_proven_when_small():
    g = M.subgroup_gate({"a": [True] * 10, "b": [True] * 10})
    assert g["status"] == "NOT_PROVEN"
    g = M.subgroup_gate({"a": [True] * 40, "b": [True] * 39 + [False]})
    assert g["status"] == "PASS"


def test_label_contradictions():
    r = M.label_contradictions(["Help me!", "help me", "other"], [True, False, True])
    assert r["contradictory_groups"] == 1 and r["tickets_in_contradictory_groups"] == 2


@pytest.mark.parametrize("n", [1, 7, 43])
def test_harness_arbitrary_sizes(pipeline, n):
    tickets = [{"ticket_id": f"X{i}", "channel": "forum", "body": "export my data",
                "intent": "data_export", "urgency": "low", "expected_route": "ESCALATE"}
               for i in range(n)]
    decisions, rep = evaluate(pipeline, tickets, "run-n")
    assert len(decisions) == n and pipeline.audit.count("run-n") == n
    assert rep["routing"]["routing_accuracy"]["den"] == n


def test_harness_cli(tmp_path, classifier):
    from pathlib import Path
    from evaluation.harness import main
    data = Path(__file__).resolve().parent.parent / "data" / "sample"
    artifacts = tmp_path / "artifacts"
    classifier.save(artifacts)
    rc = main(["--input", str(data / "validation_tickets.json"), "--output", str(tmp_path),
               "--retrieval-backend", "tfidf", "--fail-on-must-not-auto",
               "--artifacts", str(artifacts), "--kb", str(data / "kb.json"),
               "--references", str(data / "references.json")])
    assert rc == 0
    rep = json.loads((tmp_path / "metrics_report.json").read_text())
    assert rep["run"]["logged_decisions"] == rep["run"]["evaluated_tickets"]
    assert rep["metrics"]["guardrails"]["blocks_by_guardrail"].get("prompt_injection", 0) >= 1
    assert (tmp_path / "metrics_report.md").exists()


def test_train_refuses_validation_file(tmp_path):
    from scripts.train import main
    f = tmp_path / "validation_tickets.json"
    f.write_text("[]")
    with pytest.raises(SystemExit):
        main(["--input", str(f)])


def test_official_nested_labels_are_used_only_by_evaluator():
    ticket = {"ticket_id": "N1", "channel": "email", "body": "help",
              "labels": {"intent": "account_access", "urgency": "low",
                         "expected_route": "auto_respond",
                         "answerable_from_docs": True,
                         "must_not_auto_respond": False},
              "history": {"first_contact_resolution": True}}
    assert expected_route(ticket) == "AUTO_RESPOND"
    assert "labels" not in strip_labels(ticket) and "history" not in strip_labels(ticket)


def test_each_evaluation_run_gets_isolated_database(tmp_path, classifier):
    from evaluation.harness import main
    data = Path(__file__).resolve().parent.parent / "data" / "sample"
    artifacts = tmp_path / "artifacts"
    classifier.save(artifacts)
    ticket_file = tmp_path / "tickets.json"
    ticket_file.write_text(json.dumps([{
        "ticket_id": "ISO-1", "channel": "email", "body": "export data csv",
        "intent": "data_export", "urgency": "low", "expected_route": "ESCALATE",
    }]))
    args = ["--input", str(ticket_file), "--output", str(tmp_path / "out"),
            "--artifacts", str(artifacts), "--kb", str(data / "kb.json")]
    assert main(args) == 0 and main(args) == 0
    databases = list((tmp_path / "out").glob("decisions-*.sqlite3"))
    assert len(databases) == 2
    assert all(sqlite3.connect(db).execute(
        "SELECT COUNT(*) FROM decisions").fetchone()[0] == 1 for db in databases)
