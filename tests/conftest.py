import json
from dataclasses import replace
from pathlib import Path

import pytest

from src.audit import AuditStore
from src.classify import TicketClassifier
from src.config import get_settings
from src.ingest import normalize
from src.pipeline import Pipeline
from src.retrieve import Retriever, load_kb
from src.schemas import Prediction

DATA = Path(__file__).resolve().parent.parent / "data" / "sample"


@pytest.fixture(scope="session")
def dev():
    return json.loads((DATA / "dev_tickets.json").read_text())


@pytest.fixture(scope="session")
def kb():
    return load_kb(DATA / "kb.json")


@pytest.fixture(scope="session")
def classifier(dev):
    texts = [normalize(t).text for t in dev]
    return TicketClassifier.train(texts, [t["intent"] for t in dev],
                                  [t["urgency"] for t in dev])


@pytest.fixture(scope="session")
def retriever(kb):
    return Retriever(kb, "unused", backend="tfidf")


@pytest.fixture
def settings():
    return get_settings(db_path=":memory:", kb_path=str(DATA / "kb.json"))


@pytest.fixture
def pipeline(classifier, retriever, settings):
    return Pipeline(classifier, retriever, AuditStore(":memory:"), settings)


class AutoClassifier:
    def classify_with_answerability(self, text):
        return (Prediction("data_export", .99, []), Prediction("low", .99, []),
                Prediction("answerable", .99, []))


@pytest.fixture
def auto_pipeline(retriever, settings):
    enabled = replace(settings, customer_release_authorized=True)
    return Pipeline(AutoClassifier(), retriever, AuditStore(":memory:"), enabled)


@pytest.fixture
def auto_ticket():
    return {"ticket_id": "AUTO-1", "channel": "email", "body": "export data csv"}


@pytest.fixture
def email_ticket():
    return {"ticket_id": "T-1", "channel": "email", "customer_tier": "pro",
            "subject": "API key", "body": "How do I rotate my API key safely?"}
