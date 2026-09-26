from src.classify import TicketClassifier
from src.config import get_settings
from src.retrieve import Retriever, chunk_articles


def test_classifier_returns_intent_urgency_confidence_alternatives(classifier):
    intent, urgency = classifier.classify("my API key returns 401 unauthorized")
    assert intent.label == "api_key_issue"
    assert 0 <= intent.confidence <= 1 and len(intent.alternatives) == 2
    assert urgency.label in {"low", "medium", "high"}


def test_classifier_roundtrip(tmp_path, classifier):
    classifier.save(tmp_path)
    again = TicketClassifier.load(tmp_path)
    t = "export my data to csv"
    assert again.classify(t)[0] == classifier.classify(t)[0]


def test_retrieval_returns_real_docs_with_scores(retriever):
    res = retriever.search("429 too many requests rate limit", k=5)
    assert res[0].doc_id == "KB-004"
    assert all(p.doc_id.startswith("KB-") and p.citation for p in res)
    assert [p.score for p in res] == sorted([p.score for p in res], reverse=True)


def test_retrieval_is_deterministic(retriever):
    q = "cannot connect to database"
    assert [p.citation for p in retriever.search(q)] == [p.citation for p in retriever.search(q)]


def test_empty_query_returns_nothing(retriever):
    assert retriever.search("   ") == []


def test_retrieval_threshold_applied_at_boundary(retriever):
    assert retriever.search("429 rate limit", threshold=1.1) == []


def test_validated_backend_is_explicitly_locked(kb):
    settings = get_settings()
    assert settings.retrieval_backend == "tfidf"
    assert Retriever(kb, settings.embedding_model,
                     backend=settings.retrieval_backend).backend_name == "tfidf"


def test_passages_for_resolution_sections(retriever):
    ps = retriever.passages_for("KB-003", "resolution")
    assert len(ps) == 2 and all(p.section.startswith("Resolution") for p in ps)


def test_official_markdown_kb_schema_is_chunked_by_section():
    chunks = chunk_articles([{
        "doc_id": "DOC-1", "title": "Login help",
        "applies_to": "Business and Enterprise plans",
        "content": "# Login help\n\n## Symptoms\n\nCannot log in.\n\n"
                   "## Resolution\n\n1. Clear the cached token.\n\n## Notes\n\nSafe.",
    }])
    assert [c["section"] for c in chunks] == ["Symptoms", "Resolution", "Notes"]
    assert chunks[1]["plans"] == ["business", "enterprise"]
