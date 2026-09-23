"""Stage 9 reliability tests exercise the public production pipeline."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import requests

from evaluation.harness import run_evaluation
from src.classify import TicketClassificationEngine
from src.generate import (
    ResponseGenerationEngine, OpenRouterProvider, OfflineGroundedProvider,
    ProviderRateLimitError, ProviderUnavailableError,
)
from src.guardrails import GuardrailEngine
from src.logging_store import DecisionLogStore
from src.pipeline import SupportPipelineOrchestrator
from src.route import TicketRoutingEngine
from tests.test_retrieve import make_engine, document, BrokenEmbedder

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_MARKER = "SYNTHETIC_PRIVATE_EXCEPTION_9"
EVIDENCE = [{
    "document_id": "DOC-AUTH-001", "doc_id": "DOC-AUTH-001",
    "chunk_id": "DOC-AUTH-001-test", "relevance_score": .95, "similarity_score": .95,
    "passage": "Clear stale login credentials and authenticate again.",
    "chunk_content": "Clear stale login credentials and authenticate again.",
    "source": "authoritative_documentation",
}]


def ticket(case="valid"):
    return {"ticket_id": case, "channel": "chat", "customer_tier": "standard",
            "body": case + " login help", "subject": "Login"}


class Classifier:
    def process_classification(self, value):
        case = value["ticket_id"]
        if case == "classification":
            raise RuntimeError(PRIVATE_MARKER)
        return {"intent": "authentication_failure", "urgency": "medium",
                "confidence": .2 if case == "low-confidence" else .99,
                "urgency_confidence": .9, "test_case": case}


class Retriever:
    model_name = "deterministic-test"
    def query_authoritative_knowledge(self, query, top_k=5):
        if query.startswith("retrieval "):
            raise RuntimeError(PRIVATE_MARKER)
        if query.startswith("no-result "):
            return []
        return copy.deepcopy(EVIDENCE)


class Router(TicketRoutingEngine):
    def route(
        self,
        classification,
        retrieval_results,
        **kwargs,
    ):
        if classification.get("test_case") == "routing":
            raise RuntimeError(PRIVATE_MARKER)

        return super().route(
            classification,
            retrieval_results,
            **kwargs,
        )


class Provider:
    name = "deterministic-provider"
    model = "test"
    def generate(self, system_instructions, customer_input, retrieved_context, structured_schema):
        case = customer_input.split()[0]
        errors = {"timeout": TimeoutError, "connection": ConnectionError,
                  "rate-limit": ProviderRateLimitError, "unavailable": ProviderUnavailableError,
                  "provider-error": RuntimeError}
        if case in errors:
            raise errors[case](PRIVATE_MARKER)
        if case == "malformed-provider":
            return {"wrong": True}
        if case == "empty-provider":
            return ""
        # The real generation engine and guardrails validate this provider result.
        return {"answer": EVIDENCE[0]["passage"] + (
                    " api_key=SYNTHETIC_STAGE9_SECRET" if case == "unsafe" else ""),
                "citations": [{"document_id": "DOC-AUTH-001", "chunk_id": "DOC-AUTH-001-test"}],
                "supported": True, "uncertainty": None}


class Guardrails(GuardrailEngine):
    def check(self, generation, classification, normalized, retrieval=None):
        if normalized["ticket_id"] == "guardrail":
            raise RuntimeError(PRIVATE_MARKER)
        return super().check(generation, classification, normalized, retrieval)


class Store(DecisionLogStore):
    def log_decision(self, decision):
        if decision["ticket_id"] == "logging":
            raise OSError(PRIVATE_MARKER)
        return super().log_decision(decision)


def pipeline(db_url="sqlite:///:memory:", **overrides):
    args = dict(classifier=Classifier(), retriever=Retriever(), router=Router(),
                generator=ResponseGenerationEngine(provider=Provider()), guardrails=Guardrails(),
                logger=Store(db_url))
    args.update(overrides)
    return SupportPipelineOrchestrator(**args)


def dataset(tmp_path, values, wrapper="flat"):
    path = tmp_path / "arbitrary-input.json"
    raw = [values] if wrapper == "nested" else {"tickets": values} if wrapper == "object" else values
    path.write_text(json.dumps(raw), encoding="utf-8")
    return path


FAILURE_CASES = [
    ("valid", None), ("malformed", "INGESTION_FAILURE"), ("unknown-channel", "INGESTION_FAILURE"),
    ("classification", "CLASSIFICATION_FAILURE"), ("retrieval", "RETRIEVAL_FAILURE"),
    ("routing", "ROUTING_FAILURE"), ("timeout", "GENERATION_FAILED"),
    ("connection", "GENERATION_FAILED"), ("rate-limit", "GENERATION_FAILED"),
    ("unavailable", "GENERATION_FAILED"), ("provider-error", "GENERATION_FAILED"),
    ("malformed-provider", "GENERATION_FAILED"), ("empty-provider", "GENERATION_FAILED"),
    ("guardrail", "GUARDRAIL_INTERNAL_ERROR"), ("logging", "AUDIT_PERSISTENCE_FAILED"),
    ("unsafe", "SECRET_DISCLOSURE"), ("no-result", "NO_RETRIEVAL"), ("last-valid", None),
]


def run_failure_batch(tmp_path):
    values = [None if name == "malformed" else
              {**ticket(name), "channel": "unknown"} if name == "unknown-channel" else ticket(name)
              for name, _ in FAILURE_CASES]
    p = pipeline(f"sqlite:///{(tmp_path / 'faults.sqlite').as_posix()}")
    report = run_evaluation(str(dataset(tmp_path, values)), orchestrator=p, dataset_role="development")
    rows = p.logging_store.get_decisions_for_run(report["run"]["run_id"])
    p.logging_store.engine.dispose()
    return report, rows


def test_mixed_batch_continues_and_reconciles_truthfully(tmp_path, capsys):
    report, rows = run_failure_batch(tmp_path)
    records = report["records"]
    assert len(records) == len(FAILURE_CASES)
    assert report["reconciliation"]["terminal_result_count"] == len(FAILURE_CASES)
    assert report["reconciliation"]["decision_log_count"] == len(FAILURE_CASES) - 1
    assert not report["reconciliation"]["reconciled"]
    assert records[-1]["predicted_route"] == "ESCALATE"
    for (_, expected), record in zip(FAILURE_CASES, records):
        if expected:
            assert record["predicted_route"] == "ESCALATE"
            assert record["reason_code"] == expected
            assert record["response_released"] is False
        assert record["audit_record_present"] == (record["reason_code"] != "AUDIT_PERSISTENCE_FAILED")
    assert len({row["decision_id"] for row in rows}) == len(rows)
    payload = json.dumps(report) + json.dumps(rows) + capsys.readouterr().err
    assert PRIVATE_MARKER not in payload
    assert "SYNTHETIC_STAGE9_SECRET" not in payload


@pytest.mark.parametrize("wrapper", ["flat", "nested", "object"])
@pytest.mark.parametrize("count", [1, 7, 19])
def test_arbitrary_counts_and_wrappers(tmp_path, wrapper, count):
    report = run_evaluation(str(dataset(tmp_path, [ticket(str(i)) for i in range(count)], wrapper)),
                            orchestrator=pipeline())
    assert report["reconciliation"]["reconciled"]
    assert len(report["records"]) == count


def test_duplicate_ids_preserve_events(tmp_path):
    report = run_evaluation(str(dataset(tmp_path, [ticket(), ticket()])), orchestrator=pipeline())
    assert report["reconciliation"]["reconciled"]
    assert len({row["decision_id"] for row in report["records"]}) == 2
    assert [row["input_index"] for row in report["records"]] == [0, 1]


@pytest.mark.parametrize("bad", [None, "bad", {}, {"intent": "authentication_failure", "urgency": "medium"},
    {"intent": "authentication_failure", "urgency": "medium", "confidence": float("nan")}])
def test_invalid_classifier_outputs_logged(bad):
    class InvalidClassifier:
        def process_classification(self, _): return bad
    result = pipeline(classifier=InvalidClassifier()).process_ticket(ticket())
    assert result["reason_code"] == "CLASSIFICATION_FAILURE"
    assert result["audit_record"]
    assert result["response_text"] is None


def test_classifier_lazy_initialization_failure(monkeypatch):
    classifier = TicketClassificationEngine()
    def fail(): raise OSError(PRIVATE_MARKER)
    monkeypatch.setattr(classifier, "_get_bundle", fail)
    result = pipeline(classifier=classifier).process_ticket(ticket())
    assert result["reason_code"] == "CLASSIFICATION_FAILURE"
    assert result["classification"] == {}
    assert PRIVATE_MARKER not in json.dumps(result)


@pytest.mark.parametrize("kind", ["empty", "malformed", "corrupt", "embedding", "model"])
def test_real_retrieval_failure_is_not_normal_no_result(tmp_path, monkeypatch, kind):
    docs = [document("DOC-AUTH-001", "Login", "auth", "# Login\npassword credentials")]
    if kind == "empty": docs = []
    if kind == "malformed": docs = [{"doc_id": "BAD"}]
    engine = make_engine(tmp_path, docs, **({"embedding_model": BrokenEmbedder()} if kind == "embedding" else {}))
    if kind == "corrupt": engine.corpus_path.write_text("{bad", encoding="utf-8")
    if kind == "model":
        def fail(): raise OSError(PRIVATE_MARKER)
        monkeypatch.setattr(engine, "_get_model", fail)
    result = pipeline(retriever=engine).process_ticket(ticket())
    assert result["reason_code"] == "RETRIEVAL_FAILURE"
    assert result["audit_record"]["retrieval_status"] == "FAILED"
    assert result["audit_record"]["error_category"] == "RETRIEVAL_FAILURE"
    assert PRIVATE_MARKER not in json.dumps(result)


@pytest.mark.parametrize("bad", ["bad", [{"doc_id": "DOC", "relevance_score": float("nan")}],
                               [{"doc_id": "DOC", "relevance_score": float("inf")} ]])
def test_malformed_retrieval_never_auto_responds(bad):
    class BadRetriever:
        def query_authoritative_knowledge(self, *_args, **_kwargs): return bad
    result = pipeline(retriever=BadRetriever()).process_ticket(ticket())
    assert result["reason_code"] == "RETRIEVAL_FAILURE"
    assert result["audit_record"]


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf")])
def test_invalid_router_config_is_run_level_failure(value):
    with pytest.raises(ValueError):
        TicketRoutingEngine(confidence_threshold=value)


def test_database_initialization_failure_suppresses_response(tmp_path):
    # SQLite cannot open a directory as a database.
    result = SupportPipelineOrchestrator(
        classifier=Classifier(), retriever=Retriever(),
        generator=ResponseGenerationEngine(provider=Provider()),
        db_url=f"sqlite:///{tmp_path.as_posix()}",
    ).process_ticket(ticket())
    assert result["reason_code"] == "AUDIT_PERSISTENCE_FAILED"
    assert result["response_released"] is False


def test_reconciliation_query_failure_still_writes_output(tmp_path, monkeypatch):
    p = pipeline()
    monkeypatch.setattr(p.logging_store, "get_decisions_for_run",
                        lambda _: (_ for _ in ()).throw(OSError(PRIVATE_MARKER)))
    output = tmp_path / "output.json"
    report = run_evaluation(str(dataset(tmp_path, [ticket()])), str(output), orchestrator=p)
    assert report["reconciliation"]["decision_log_count"] is None
    assert not report["reconciliation"]["reconciled"]
    assert json.loads(output.read_text())["run"]["status"] == "COMPLETED"
    assert PRIVATE_MARKER not in output.read_text()


def test_checkpoint_survives_interruption(tmp_path):
    p = pipeline()
    process = p.process_ticket
    def interrupted(value, **kwargs):
        if value["ticket_id"] == "interrupt": raise KeyboardInterrupt()
        return process(value, **kwargs)
    p.process_ticket = interrupted
    output = tmp_path / "partial.json"
    with pytest.raises(KeyboardInterrupt):
        run_evaluation(str(dataset(tmp_path, [ticket(), ticket("interrupt")])), str(output), orchestrator=p)
    saved = json.loads(output.read_text())
    assert saved["run"]["status"] == "INTERRUPTED"
    assert saved["run"]["evidence_status"] == "partial_run"
    assert len(saved["records"]) == 1
    assert saved["records"][0]["run_id"] == saved["run"]["run_id"]


def test_offline_deterministic_components_and_pipeline():
    p = pipeline(generator=ResponseGenerationEngine(provider=OfflineGroundedProvider()))
    first = p.process_ticket(ticket())
    second = p.process_ticket(ticket())
    assert p.ingester.normalize_ticket(ticket()) == p.ingester.normalize_ticket(ticket())
    for key in ("classification", "routing", "guardrails", "response_text"):
        assert first[key] == second[key]
    assert first["decision_record"]["retrieval"] == second["decision_record"]["retrieval"]
    assert first["decision_id"] != second["decision_id"]


@pytest.mark.parametrize("status,expected", [(429, "PROVIDER_RATE_LIMIT"), (503, "PROVIDER_UNAVAILABLE"),
                                           (400, "PROVIDER_ERROR")])
def test_http_provider_statuses_through_pipeline(status, expected):
    class Session:
        calls = 0
        def post(self, *args, **kwargs):
            self.calls += 1
            assert kwargs["timeout"] == 2.5
            return type("Response", (), {"status_code": status})()
    session = Session()
    adapter = OpenRouterProvider("synthetic-test-key", "test", timeout_seconds=2.5, session=session)
    result = pipeline(generator=ResponseGenerationEngine(provider=adapter)).process_ticket(ticket())
    assert result["reason_code"] == "GENERATION_FAILED"
    assert result["failure_state"] == expected
    assert result["audit_record"]
    assert not result["response_released"]
    assert session.calls == 1


def test_cli_offline_without_credentials_and_no_interaction(tmp_path):
    # Malformed input deliberately exercises the real CLI without model downloads.
    path = dataset(tmp_path, [None, {"ticket_id": "bad", "channel": "unknown"}])
    output = tmp_path / "cli.json"
    env = {**os.environ, "GENERATION_PROVIDER": "offline", "OPENROUTER_API_KEY": ""}
    result = subprocess.run([sys.executable, "-m", "evaluation.harness", "--input", str(path),
                             "--output", str(output), "--dataset-role", "development"],
                            cwd=ROOT, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text())
    assert report["reconciliation"]["reconciled"]
    assert report["run"]["status"] == "COMPLETED"
    store = DecisionLogStore("sqlite:///" + Path(report["run"]["decision_database"]).as_posix())
    assert store.count_decisions(run_id=report["run"]["run_id"]) == 2
    store.engine.dispose()


def test_cli_run_level_error_has_nonzero_exit(tmp_path):
    result = subprocess.run([sys.executable, "-m", "evaluation.harness", "--input",
                             str(tmp_path / "missing.json")], cwd=ROOT,
                            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)
    assert result.returncode == 1
    assert json.loads(result.stderr)["error_type"] == "FileNotFoundError"


@pytest.mark.parametrize("error,expected", [(requests.Timeout, "PROVIDER_TIMEOUT"),
                                         (requests.ConnectionError, "PROVIDER_UNAVAILABLE")])
def test_http_provider_exceptions_through_pipeline(error, expected):
    class Session:
        def post(self, *args, **kwargs): raise error(PRIVATE_MARKER)
    adapter = OpenRouterProvider("synthetic", "test", session=Session())
    result = pipeline(generator=ResponseGenerationEngine(provider=adapter)).process_ticket(ticket())
    assert result["failure_state"] == expected
    assert result["audit_record"]
    assert PRIVATE_MARKER not in json.dumps(result)


@pytest.mark.parametrize("stage", ["routing", "generation", "guardrail"])
def test_invalid_component_result_fails_closed(stage):
    class BadRouter(Router):
        def route(self, *args): return {"action": "OTHER"}
    class BadGenerator:
        def generate_response(self, *args): return "bad"
    class BadGuardrail(Guardrails):
        def check(self, *args): return {"passed": "yes"}
    components = {"routing": {"router": BadRouter()},
                  "generation": {"generator": BadGenerator()},
                  "guardrail": {"guardrails": BadGuardrail()}}
    result = pipeline(**components[stage]).process_ticket(ticket())
    assert result["status"] == "ESCALATE"
    assert result["audit_record"]
    assert not result["response_released"]


def test_readback_failure_does_not_retry_or_claim_reconciliation(tmp_path, monkeypatch):
    p = pipeline()
    calls = []
    original = p.logging_store.log_decision
    def write(record):
        calls.append(record)
        return original(record)
    monkeypatch.setattr(p.logging_store, "log_decision", write)
    monkeypatch.setattr(p.logging_store, "get_decision_by_id",
                        lambda _: (_ for _ in ()).throw(OSError(PRIVATE_MARKER)))
    report = run_evaluation(str(dataset(tmp_path, [ticket()])), orchestrator=p)
    assert len(calls) == 1
    assert report["records"][0]["reason_code"] == "AUDIT_PERSISTENCE_FAILED"
    assert not report["records"][0]["response_released"]
    assert report["reconciliation"]["decision_log_count"] == 1
    assert not report["reconciliation"]["reconciled"]


def test_broken_stderr_does_not_cause_recursive_logging(monkeypatch):
    class BrokenStream:
        def write(self, _): raise OSError("closed")
    p = pipeline()
    monkeypatch.setattr("src.orchestrator.sys.stderr", BrokenStream())
    result = p.process_ticket(ticket("logging"))
    assert result["reason_code"] == "AUDIT_PERSISTENCE_FAILED"
    assert not result["response_released"]


def test_two_offline_batches_have_equal_deterministic_fields(tmp_path):
    path = dataset(tmp_path, [ticket("valid"), ticket("low-confidence"), ticket("no-result")])
    reports = [run_evaluation(str(path), orchestrator=pipeline(
        generator=ResponseGenerationEngine(provider=OfflineGroundedProvider()))) for _ in range(2)]
    variable = {"run_id", "decision_id", "latency_seconds"}
    stable = [[{key: value for key, value in row.items() if key not in variable}
               for row in report["records"]] for report in reports]
    assert stable[0] == stable[1]
    assert reports[0]["run"]["run_id"] != reports[1]["run"]["run_id"]


def test_atomic_save_failure_preserves_previous_checkpoint(tmp_path, monkeypatch):
    from evaluation.harness import _atomic_write
    path = tmp_path / "checkpoint.json"
    _atomic_write(path, {"status": "RUNNING", "records": []})
    monkeypatch.setattr("evaluation.harness.os.replace",
                        lambda *args: (_ for _ in ()).throw(OSError("synthetic write error")))
    with pytest.raises(OSError):
        _atomic_write(path, {"status": "COMPLETED"})
    assert json.loads(path.read_text())["status"] == "RUNNING"
    assert not list(tmp_path.glob("*.tmp"))


def test_no_output_can_overwrite_input(tmp_path):
    path = dataset(tmp_path, [ticket()])
    original = path.read_bytes()
    with pytest.raises(ValueError):
        run_evaluation(str(path), str(path), orchestrator=pipeline())
    assert path.read_bytes() == original


@pytest.mark.parametrize("failures", [1, 4])
def test_atomic_windows_sharing_retry_is_bounded(tmp_path, monkeypatch, failures):
    from evaluation.harness import _atomic_write
    path = tmp_path / "checkpoint.json"
    _atomic_write(path, {"old": True})
    replace = os.replace
    attempts, delays = [], []
    def locked(source, destination):
        attempts.append(1)
        if len(attempts) <= failures:
            raise PermissionError("synthetic sharing violation")
        return replace(source, destination)
    monkeypatch.setattr("evaluation.harness.os.replace", locked)
    monkeypatch.setattr("evaluation.harness.time.sleep", delays.append)
    if failures == 4:
        with pytest.raises(PermissionError):
            _atomic_write(path, {"new": True})
        assert json.loads(path.read_text()) == {"old": True}
        assert len(attempts) == 4
        assert delays == [.05, .1, .2]
    else:
        _atomic_write(path, {"new": True})
        assert json.loads(path.read_text()) == {"new": True}
        assert len(attempts) == 2
        assert delays == [.05]
    assert not list(tmp_path.glob("*.tmp"))


def test_security_sqlite_files_and_terminal_payload(tmp_path):
    report, rows = run_failure_batch(tmp_path)
    raw = b"".join(path.read_bytes() for path in tmp_path.glob("faults.sqlite*"))
    for marker in (PRIVATE_MARKER, "SYNTHETIC_STAGE9_SECRET"):
        assert marker.encode() not in raw
    p = pipeline()
    result = p.process_ticket(ticket("unsafe"))
    assert "SYNTHETIC_STAGE9_SECRET" not in json.dumps(result)


def test_malformed_id_and_canonical_channel_preserved_in_audit():
    result = pipeline().process_ticket({**ticket("preserved"), "channel": "unknown"})
    assert result["audit_record"]["ticket_id"] == result["ticket_id"] == "preserved"
    result = pipeline().process_ticket(ticket())
    assert result["audit_record"]["channel"] == "live_chat"
    assert result["audit_record"]["original_channel"] == "chat"
