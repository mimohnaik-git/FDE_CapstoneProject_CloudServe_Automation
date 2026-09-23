import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from scripts.evaluate_retrieval import evaluate_tickets
from src.orchestrator import SupportAutomationOrchestrator
from src.retrieve import (
    CHUNKING_CONFIGS,
    DocumentCorpusError,
    DocumentationRetrievalEngine,
    chunk_document,
    load_authoritative_documents,
)


class SemanticTestEmbedder:
    """Deterministic semantic test double for exact cosine ranking."""

    GROUPS = (
        ("password", "credentials", "login", "sign-in", "secret", "authentication"),
        ("invoice", "billing", "charge", "payment"),
        ("deploy", "build", "dependency", "release"),
        ("mfa", "authenticator", "code", "device", "clock", "recovery"),
        ("webhook", "integration", "callback"),
        ("database", "latency", "slow", "performance"),
    )

    def __init__(self):
        self.calls = 0

    def encode(self, texts, **_kwargs):
        self.calls += 1
        return np.asarray(
            [
                [float(sum(text.lower().count(term) for term in group)) for group in self.GROUPS]
                for text in texts
            ],
            dtype=np.float32,
        )


class BrokenEmbedder:
    def encode(self, _texts, **_kwargs):
        raise RuntimeError("embedding backend unavailable")


def document(doc_id, title, category, content):
    return {"doc_id": doc_id, "title": title, "category": category, "content": content}


def write_corpus(tmp_path: Path, documents):
    path = tmp_path / "documentation.json"
    path.write_text(json.dumps([documents]), encoding="utf-8")
    return path


def make_engine(tmp_path, documents, **kwargs):
    return DocumentationRetrievalEngine(
        embedding_model=kwargs.pop("embedding_model", SemanticTestEmbedder()),
        corpus_path=write_corpus(tmp_path, documents),
        min_relevance_score=kwargs.pop("min_relevance_score", 0.05),
        **kwargs,
    )


def test_authoritative_documentation_loads_and_preserves_ids():
    docs = load_authoritative_documents()
    assert len(docs) == 29
    assert len({doc["doc_id"] for doc in docs}) == len(docs)
    assert all(doc["content"].startswith("# ") for doc in docs)


def test_both_chunking_strategies_are_deterministic_and_different():
    text = "# Title\n\n" + "password login credentials " * 80 + "\n\n## Resolution\n\n" + "step " * 100
    a1 = chunk_document(text, CHUNKING_CONFIGS["strategy_a"])
    assert a1 == chunk_document(text, CHUNKING_CONFIGS["strategy_a"])
    assert a1 != chunk_document(text, CHUNKING_CONFIGS["strategy_b"])


def test_chunks_respect_sections_and_word_boundaries():
    text = "# Login\n\n" + "credential " * 100 + "\n\n## Resolution\n\nclear cookies and login again"
    chunks = chunk_document(text, CHUNKING_CONFIGS["strategy_a"])
    assert {item["section"] for item in chunks} == {"Login", "Resolution"}
    assert all(len(item["chunk_content"]) <= 480 for item in chunks)
    assert not any("## Resolution" in item["chunk_content"] and item["section"] == "Login" for item in chunks)


def test_exact_cosine_ranking_returns_expected_document(tmp_path):
    engine = make_engine(
        tmp_path,
        [
            document("DOC-AUTH-001", "Login help", "authentication", "# Login\nPassword login credentials are rejected."),
            document("DOC-BILL-001", "Invoice help", "billing", "# Billing\nInvoice payment and billing charge."),
        ],
        min_relevance_score=-1.0,
    )
    results = engine.query_authoritative_knowledge("my sign-in secret is rejected", top_k=2)
    assert results[0]["document_id"] == "DOC-AUTH-001"
    assert results[0]["rank"] == 1
    assert results[0]["similarity_score"] > results[1]["similarity_score"]


def test_ranked_document_includes_resolution_support_for_generation(tmp_path):
    engine = make_engine(
        tmp_path,
        [
            document(
                "DOC-AUTH-001",
                "Login recovery",
                "authentication",
                "# Login recovery\n"
                "password credentials login authentication failure\n\n"
                "## Symptoms\n"
                "Login fails with invalid credentials.\n\n"
                "## Resolution\n"
                "1. Clear stale cookies.\n"
                "2. Authenticate again.",
            )
        ],
        min_relevance_score=-1.0,
    )

    result = engine.query_authoritative_knowledge(
        "password credentials login authentication",
        top_k=1,
    )[0]

    assert result["document_id"] == "DOC-AUTH-001"
    assert result["rank"] == 1
    assert result["section"] != "Resolution"

    support = result["supporting_passages"]
    assert support
    assert support[0]["document_id"] == "DOC-AUTH-001"
    assert support[0]["section"] == "Resolution"
    assert "Clear stale cookies" in support[0]["passage"]
    assert support[0]["chunk_id"] != result["chunk_id"]


def test_score_exposure_uses_cosine_similarity(tmp_path):
    engine = make_engine(
        tmp_path,
        [document("DOC-AUTH-001", "Login", "authentication", "# Login\npassword credentials login")],
    )
    result = engine.query_authoritative_knowledge("password credentials login", top_k=1)[0]
    assert result["similarity_score"] == pytest.approx(1.0, abs=1e-6)
    assert result["relevance_score"] == result["similarity_score"]


def test_threshold_produces_legitimate_no_result(tmp_path):
    engine = make_engine(
        tmp_path,
        [document("DOC-AUTH-001", "Login", "authentication", "# Login\npassword credentials login")],
        min_relevance_score=0.80,
    )
    assert engine.query_authoritative_knowledge("password and invoice", top_k=5) == []


def test_empty_queries_return_no_result_without_initializing(tmp_path):
    engine = make_engine(tmp_path, [document("DOC-AUTH-001", "Login", "auth", "# Login\npassword")])
    assert engine.query_authoritative_knowledge("") == []
    assert engine.query_authoritative_knowledge("   ") == []
    assert engine._initialized is False


def test_empty_corpus_fails_closed(tmp_path):
    corpus = tmp_path / "documentation.json"
    corpus.write_text("[]", encoding="utf-8")
    engine = DocumentationRetrievalEngine(embedding_model=SemanticTestEmbedder(), corpus_path=corpus)
    assert engine.query_authoritative_knowledge("login") == []
    assert "DocumentCorpusError" in engine.last_error


def test_malformed_document_fails_closed(tmp_path):
    corpus = write_corpus(tmp_path, [{"doc_id": "DOC-X-001", "title": "Broken", "category": "x"}])
    engine = DocumentationRetrievalEngine(embedding_model=SemanticTestEmbedder(), corpus_path=corpus)
    assert engine.query_authoritative_knowledge("anything") == []
    assert engine.last_error == "DocumentCorpusError"


def test_duplicate_document_ids_are_rejected(tmp_path):
    docs = [
        document("DOC-X-001", "One", "x", "# One\npassword"),
        document("DOC-X-001", "Two", "x", "# Two\ninvoice"),
    ]
    with pytest.raises(DocumentCorpusError, match="Duplicate document ID"):
        load_authoritative_documents(write_corpus(tmp_path, docs))


def test_index_is_built_lazily_once_and_repeated_queries_are_stable(tmp_path):
    embedder = SemanticTestEmbedder()
    engine = make_engine(
        tmp_path,
        [document("DOC-AUTH-001", "Login", "authentication", "# Login\npassword credentials login")],
        embedding_model=embedder,
    )
    assert engine._initialized is False
    first = engine.query_authoritative_knowledge("password login")
    state_id = id(engine._state)
    second = engine.query_authoritative_knowledge("password login")
    assert [row["chunk_id"] for row in first] == [row["chunk_id"] for row in second]
    assert id(engine._state) == state_id
    assert embedder.calls == 3  # one index batch plus two query calls


def test_results_include_traceable_metadata_and_stable_chunk_ids(tmp_path):
    engine = make_engine(
        tmp_path,
        [document("DOC-AUTH-001", "Login", "authentication", "# Login\npassword credentials login")],
    )
    result = engine.query_authoritative_knowledge("password login", top_k=1)[0]
    expected_hash = hashlib.sha256(result["passage"].encode("utf-8")).hexdigest()[:12]
    assert result["chunk_id"].endswith(expected_hash)
    assert result["doc_id"] == result["document_id"] == "DOC-AUTH-001"
    assert result["source_metadata"]["title"] == "Login"
    assert result["source_metadata"]["category"] == "authentication"
    assert result["source_metadata"]["section"] == "Login"
    assert Path(result["source_path"]).resolve() == engine.corpus_path


def test_ground_truth_and_labels_are_not_indexed(tmp_path):
    docs = [document("DOC-AUTH-001", "Login", "authentication", "# Login\npassword credentials login")]
    (tmp_path / "ground_truth_responses.json").write_text('{"secret": "NEVER_INDEX_THIS"}', encoding="utf-8")
    (tmp_path / "development_tickets.json").write_text('{"expected_doc_ids": ["SECRET-LABEL"]}', encoding="utf-8")
    engine = make_engine(tmp_path, docs)
    engine.query_authoritative_knowledge("password")
    passages = [chunk["chunk_content"] for chunk in engine._state.chunks]
    assert all("NEVER_INDEX_THIS" not in passage and "SECRET-LABEL" not in passage for passage in passages)
    assert len(passages) == len(engine._build_chunks(docs))


def test_retrieval_failure_returns_empty_and_production_path_escalates(tmp_path):
    engine = make_engine(
        tmp_path,
        [document("DOC-AUTH-001", "Login", "authentication", "# Login\npassword credentials login")],
        embedding_model=BrokenEmbedder(),
    )

    class HighConfidenceClassifier:
        def process_classification(self, _ticket):
            return {"intent": "authentication_failure", "urgency": "medium", "confidence": 0.99}

    orchestrator = SupportAutomationOrchestrator(
        classifier=HighConfidenceClassifier(), retriever=engine, db_url="sqlite:///:memory:"
    )
    result = orchestrator.process_ticket(
        {"ticket_id": "T-FAIL", "channel": "chat", "customer_tier": "standard", "body": "password login"}
    )
    assert result["action"] == "ESCALATE"
    assert result["reason_code"] == "RETRIEVAL_FAILURE"
    assert engine.last_error == "RuntimeError"


def test_production_orchestrator_invokes_semantic_retriever(tmp_path):
    engine = make_engine(
        tmp_path,
        [document("DOC-AUTH-001", "Login", "authentication", "# Login\npassword credentials login")],
    )

    class HighConfidenceClassifier:
        def process_classification(self, _ticket):
            return {"intent": "authentication_failure", "urgency": "medium", "confidence": 0.99}

    result = SupportAutomationOrchestrator(
        classifier=HighConfidenceClassifier(), retriever=engine, db_url="sqlite:///:memory:"
    ).process_ticket(
        {"ticket_id": "T-OK", "channel": "chat", "customer_tier": "standard", "body": "sign-in secret rejected"}
    )
    retrieval = result["decision_record"]["retrieval"]
    assert retrieval[0]["document_id"] == "DOC-AUTH-001"
    assert retrieval[0]["source"] == "authoritative_documentation"
    assert engine._state.embeddings.shape[0] > 0


def test_real_corpus_expected_document_retrieval(tmp_path):
    engine = DocumentationRetrievalEngine(embedding_model=SemanticTestEmbedder(), min_relevance_score=0.05)
    results = engine.query_authoritative_knowledge(
        "authenticator code rejected after device clock drift; need MFA recovery", top_k=5
    )
    assert "DOC-AUTH-002" in [row["document_id"] for row in results]


def test_development_metric_denominators_support_arbitrary_ticket_counts():
    class StubEngine:
        def query_authoritative_knowledge(self, query, top_k=5):
            return [] if query == "no docs" else [{"doc_id": "DOC-1", "relevance_score": 0.9}]

    tickets = [
        {"ticket_id": "1", "body": "answer", "labels": {"expected_doc_ids": ["DOC-1"]}},
        {"ticket_id": "2", "body": "wrong", "labels": {"expected_doc_ids": ["DOC-2"]}},
        {"ticket_id": "3", "body": "no docs", "labels": {"expected_doc_ids": []}},
    ]
    metrics = evaluate_tickets(StubEngine(), tickets)
    assert metrics["ticket_count"] == 3
    assert metrics["eligible_count"] == 2
    assert metrics["unanswerable_count"] == 1
    assert metrics["recall@1"] == pytest.approx(0.5)
    assert metrics["precision@1"] == pytest.approx(0.5)
    assert metrics["unanswerable_no_result_rate"] == pytest.approx(1.0)
